from functools import lru_cache

from mmm_common.config import CommonSettings


class Settings(CommonSettings):
    service_name: str = "web"
    directory_url: str = "http://directory:8000"
    # Anonymous visitors share a briefly cached copy of each page's data.
    page_cache_seconds: float = 30.0
    upstream_timeout_seconds: float = 4.0
    # Added to /static URLs so browsers fetch new styles after an update. Empty: derived from the files.
    asset_version: str = ""
    # Private preview before launch: shows a "not yet public" bar. The gateway adds a password.
    site_preview: bool = False
    # Colour scheme for the whole site: sunrise, coast, highlands or evening.
    site_palette: str = "sunrise"
    # Public contact details shown in the footer and on the contact page.
    contact_email: str = ""
    contact_phone: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
