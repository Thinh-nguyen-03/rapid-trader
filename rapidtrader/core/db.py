from sqlalchemy import create_engine, Engine
from .config import settings

_engine = None

def get_engine() -> Engine:
    global _engine
    if _engine is None:
        _engine = create_engine(settings.RT_DB_URL, echo=False)
    return _engine
