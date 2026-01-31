"""Database connection management using SQLAlchemy pooling."""
from sqlalchemy import create_engine, Engine, pool
from sqlalchemy.orm import Session, sessionmaker
from contextlib import contextmanager
from typing import Generator
from .config import settings


class DatabaseManager:
    """Thread-safe database connection manager."""

    def __init__(self, db_url: str | None = None):
        self._db_url = db_url or settings.RT_DB_URL
        self._engine: Engine | None = None
        self._session_factory: sessionmaker | None = None

    @property
    def engine(self) -> Engine:
        if self._engine is None:
            self._engine = create_engine(
                self._db_url,
                poolclass=pool.QueuePool,
                pool_size=10,
                max_overflow=20,
                pool_pre_ping=True,
                pool_recycle=3600,
                echo=False
            )
        return self._engine

    @property
    def session_factory(self) -> sessionmaker:
        if self._session_factory is None:
            self._session_factory = sessionmaker(
                bind=self.engine,
                autocommit=False,
                autoflush=False
            )
        return self._session_factory

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        session = self.session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def dispose(self):
        if self._engine is not None:
            self._engine.dispose()
            self._engine = None
            self._session_factory = None


_db_manager = DatabaseManager()


def get_engine() -> Engine:
    return _db_manager.engine


def get_session() -> Generator[Session, None, None]:
    return _db_manager.get_session()


def dispose_engine():
    _db_manager.dispose()


def set_test_database(db_url: str):
    global _db_manager
    _db_manager.dispose()
    _db_manager = DatabaseManager(db_url)
