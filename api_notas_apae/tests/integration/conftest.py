from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.infrastructure.config import get_settings
from app.infrastructure.dependencies import get_unit_of_work
from app.main import create_app
from app.models.all_models import *  # noqa: F403
from app.models.base import Base
from app.repositories.contracts import Transaction
from app.repositories.unit_of_work import (
    SQLAlchemyUnitOfWork,
)


@pytest.fixture()
def session_factory(tmp_path: Path) -> Generator[sessionmaker[Session], None, None]:
    database_path = tmp_path / "test.db"
    engine = create_engine(
        f"sqlite+pysqlite:///{database_path}",
        connect_args={"check_same_thread": False, "timeout": 30},
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    yield factory
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture()
def client(
    session_factory: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
) -> TestClient:
    monkeypatch.setenv("WORKER_API_KEY", "test-worker-key")
    monkeypatch.setenv("NOTAS_API_INTERNAL_KEY", "test-internal-key")
    get_settings.cache_clear()
    app = create_app()

    def override_uow() -> Transaction:
        return SQLAlchemyUnitOfWork(session_factory)

    app.dependency_overrides[get_unit_of_work] = override_uow
    return TestClient(app)
