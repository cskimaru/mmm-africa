"""Fetches page data from the directory service.

Anonymous visitors share a briefly cached copy of each response, so a burst of
visitors costs the backend one request every few seconds. If the directory
service is down, the last good copy is served instead of an error page.
"""

import asyncio
import logging
import time
from dataclasses import dataclass

import httpx

from mmm_common.logging import request_id_var

from .config import Settings

log = logging.getLogger("content")


@dataclass
class Result:
    data: object = None
    status: int = 200
    degraded: bool = False

    @property
    def ok(self) -> bool:
        return self.status == 200 and self.data is not None


class ContentClient:
    def __init__(self, settings: Settings, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self.s = settings
        self.http = httpx.AsyncClient(timeout=settings.upstream_timeout_seconds, transport=transport)
        self._cache: dict[str, tuple[float, Result]] = {}
        self._last_good: dict[str, object] = {}
        self._lock = asyncio.Lock()

    async def close(self) -> None:
        await self.http.aclose()

    async def _fetch(self, path: str, headers: dict | None) -> Result:
        rid = request_id_var.get()
        h = dict(headers or {})
        if rid:
            h["X-Request-ID"] = rid
        try:
            r = await self.http.get(f"{self.s.directory_url}{path}", headers=h)
        except httpx.HTTPError as e:
            log.warning("Upstream fetch failed", extra={"fields": {"path": path, "error": repr(e)}})
            return self._fallback(path)
        if r.status_code == 404:
            return Result(None, 404)
        if r.status_code != 200:
            log.warning("Upstream error", extra={"fields": {"path": path, "status": r.status_code}})
            return self._fallback(path)
        return Result(r.json(), 200)

    def _fallback(self, path: str) -> Result:
        if path in self._last_good:
            return Result(self._last_good[path], 200, degraded=True)
        return Result(None, 503, degraded=True)

    async def get(self, path: str, auth_headers: dict | None = None) -> Result:
        # Signed-in officers always see fresh data, including hidden items.
        if auth_headers:
            return await self._fetch(path, auth_headers)
        now = time.monotonic()
        hit = self._cache.get(path)
        if hit and now - hit[0] < self.s.page_cache_seconds:
            return hit[1]
        async with self._lock:
            hit = self._cache.get(path)
            if hit and time.monotonic() - hit[0] < self.s.page_cache_seconds:
                return hit[1]
            res = await self._fetch(path, None)
            if res.ok and not res.degraded:
                self._last_good[path] = res.data
            if len(self._cache) > 500:
                self._cache.clear()
            self._cache[path] = (time.monotonic(), res)
            return res
