"""Synapse DB — read-only connection to community-data.zoomrx.com."""
from contextlib import contextmanager
from urllib.parse import quote_plus

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from config import env


def _build_url() -> str:
    return (
        f"mysql+mysqlconnector://{env.SYNAPSE_DB_USERNAME}"
        f":{quote_plus(env.SYNAPSE_DB_PASSWORD)}"
        f"@{env.SYNAPSE_DB_HOST}:{env.SYNAPSE_DB_PORT}"
        f"/{env.SYNAPSE_DB_NAME}"
    )


_engine = None
_SessionFactory = None


def _get_session_factory():
    global _engine, _SessionFactory
    if _SessionFactory is None:
        _engine = create_engine(
            _build_url(),
            pool_size=3,
            max_overflow=2,
            pool_recycle=3600,
        )
        _SessionFactory = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
    return _SessionFactory


@contextmanager
def get_synapse_db():
    Session = _get_session_factory()
    session = Session()
    try:
        yield session
    finally:
        session.close()
