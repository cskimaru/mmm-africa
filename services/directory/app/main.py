from mmm_common.app import create_app
from mmm_common.db import Database

from .config import get_settings
from .routes import router

settings = get_settings()
db = Database(settings.database_url)
app = create_app(settings, title="MMM Africa directory", db=db)
app.include_router(router)
