"""Shared pytest fixtures.

Patches `app.database.engine` with an in-memory SQLite engine so that tests
can run without a live PostgreSQL instance.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import patch

from app.database import Base, get_db
from app.main import app

# ── In-memory SQLite stand-in ─────────────────────────────────────────────────
SQLITE_URL = "sqlite://"

_test_engine = create_engine(SQLITE_URL, connect_args={"check_same_thread": False})
_TestingSession = sessionmaker(bind=_test_engine, autocommit=False, autoflush=False)


def override_get_db():
    db = _TestingSession()
    try:
        yield db
    finally:
        db.close()


# Override the FastAPI dependency globally for all tests
app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """Create all tables in the SQLite test DB and patch the module-level engine."""
    with patch("app.database.engine", _test_engine):
        Base.metadata.create_all(bind=_test_engine)
        yield
        Base.metadata.drop_all(bind=_test_engine)
