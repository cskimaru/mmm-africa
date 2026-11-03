from functools import lru_cache

from mmm_common.config import CommonSettings


class Settings(CommonSettings):
    service_name: str = "directory"


@lru_cache
def get_settings() -> Settings:
    return Settings()
