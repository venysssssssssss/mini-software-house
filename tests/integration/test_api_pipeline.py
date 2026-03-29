"""Integration test: Full API pipeline flow."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from src.api.app import create_app


@pytest.fixture
def in_memory_engine():
    engine = create_engine(
        "sqlite://",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture
def client(in_memory_engine, tmp_path):
    from src.core.database import get_session

    app = create_app()

    def override():
        with Session(in_memory_engine) as s:
            yield s

    app.dependency_overrides[get_session] = override

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


class TestFullAPIFlow:
    @patch("src.api.routes.init_db")
    @patch("src.api.routes._run_pipeline")
    def test_create_and_check_status(self, mock_run, mock_init, client):
        """POST /pipeline/run -> GET /pipeline/{id}/status."""
        # Create a run
        resp = client.post("/pipeline/run", json={"task": "Build a calculator"})
        assert resp.status_code == 200
        run_id = resp.json()["id"]

        # Check status
        resp = client.get(f"/pipeline/{run_id}/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == run_id
        assert data["user_request"] == "Build a calculator"
        assert data["status"] == "pending"

    @patch("src.api.routes.init_db")
    @patch("src.api.routes._run_pipeline")
    def test_multiple_runs_are_independent(self, mock_run, mock_init, client):
        """Two POST requests create separate runs."""
        r1 = client.post("/pipeline/run", json={"task": "Task A"}).json()
        r2 = client.post("/pipeline/run", json={"task": "Task B"}).json()

        assert r1["id"] != r2["id"]

        s1 = client.get(f"/pipeline/{r1['id']}/status").json()
        s2 = client.get(f"/pipeline/{r2['id']}/status").json()
        assert s1["user_request"] == "Task A"
        assert s2["user_request"] == "Task B"

    @patch("src.api.routes.init_db")
    @patch("src.api.routes._run_pipeline")
    def test_artifacts_endpoint(self, mock_run, mock_init, client):
        """GET /pipeline/{id}/artifacts returns empty for new run."""
        resp = client.post("/pipeline/run", json={"task": "Test"})
        run_id = resp.json()["id"]

        resp = client.get(f"/pipeline/{run_id}/artifacts")
        assert resp.status_code == 200
        assert resp.json()["files"] == []

    @patch("src.api.routes.init_db")
    @patch("src.api.routes._run_pipeline")
    def test_metrics_after_run(self, mock_run, mock_init, client):
        """GET /agents/metrics returns empty initially."""
        resp = client.get("/agents/metrics")
        assert resp.status_code == 200
        assert resp.json() == []
