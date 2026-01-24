"""Database connection management for RapidTrader.

Uses SQLAlchemy connection pooling for thread-safe database access.
"""
from sqlalchemy import create_engine, Engine, pool
from sqlalchemy.orm import Session, sessionmaker
from contextlib import contextmanager
from typing import Generator
from .config import settings


class DatabaseManager:
    """Thread-safe database connection manager."""

    def __init__(self, db_url: str | None = None):
        """Initialize database manager with connection pooling.

        Args:
            db_url: Database connection URL (defaults to settings.RT_DB_URL)
        """
        self._db_url = db_url or settings.RT_DB_URL
        self._engine: Engine | None = None
        self._session_factory: sessionmaker | None = None

    @property
    def engine(self) -> Engine:
        """Get or create database engine with connection pooling."""
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
        """Get or create session factory."""
        if self._session_factory is None:
            self._session_factory = sessionmaker(
                bind=self.engine,
                autocommit=False,
                autoflush=False
            )
        return self._session_factory

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """Context manager for database sessions.

        Usage:
            with db_manager.get_session() as session:
                results = session.execute(query)
        """
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
        """Close all connections in the pool."""
        if self._engine is not None:
            self._engine.dispose()
            self._engine = None
            self._session_factory = None


# Global instance for application use
_db_manager = DatabaseManager()


def get_engine() -> Engine:
    """Get the database engine.

    This function maintains backward compatibility with existing code.
    Thread-safe due to connection pooling in the engine.

    Returns:
        SQLAlchemy Engine instance with connection pooling
    """
    return _db_manager.engine


def get_session() -> Generator[Session, None, None]:
    """Get a database session context manager.

    Usage:
        with get_session() as session:
            results = session.execute(query)

    Yields:
        SQLAlchemy Session instance
    """
    return _db_manager.get_session()


def dispose_engine():
    """Dispose of the database engine and close all connections.

    Useful for testing or application shutdown.
    """
    _db_manager.dispose()


def set_test_database(db_url: str):
    """Set a different database URL for testing.

    Args:
        db_url: Test database connection URL
    """
    global _db_manager
    _db_manager.dispose()
    _db_manager = DatabaseManager(db_url)
