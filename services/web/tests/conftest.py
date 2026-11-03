import os
import sys
from pathlib import Path

import pytest

os.environ.update(
    SITE_ORIGIN="http://testserver",
    ENVIRONMENT="test",
    DIRECTORY_URL="http://directory.internal",
    PAGE_CACHE_SECONDS="0",
)
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from httpx import ASGITransport, AsyncClient


@pytest.fixture
async def client():
    from app.main import app

    app.state.content._cache.clear()
    app.state.content._last_good.clear()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as c:
        yield c
