"""Tests for the FastAPI endpoints."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from src.core.models import AgentLog, PipelineRun, TaskStatus


@pytest.fixture
def engine_and_session():
    engine = create_engine(
        "sqlite://",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture
def session(engine_and_session):
    with Session(engine_and_session) as s:
        yield s


@pytest.fixture
def client(engine_and_session, tmp_path):
    from src.api.app import create_app
    from src.core.database import get_session

    app = create_app()

    def override():
        with Session(engine_and_session) as s:
            yield s

    app.dependency_overrides[get_session] = override

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


@pytest.fixture
def sample_run(session):
    run = PipelineRun(
        user_request="Build a todo app",
        status=TaskStatus.COMPLETED,
        completed_phases=4,
        total_phases=4,
        execution_time_s=12.5,
        total_prompt_tokens=1000,
        total_response_tokens=2000,
        total_agent_calls=8,
    )
    session.add(run)
    session.commit()
    session.refresh(run)
    return run


@pytest.fixture
def sample_logs(session, sample_run):
    logs = [
        AgentLog(
            pipeline_run_id=sample_run.id,
            agent_name="planner",
            model="qwen2.5:3b",
            level="INFO",
            message="llm_call",
            prompt_tokens=100,
            response_tokens=200,
            latency_ms=500.0,
            success=True,
        ),
        AgentLog(
            pipeline_run_id=sample_run.id,
            agent_name="executor",
            model="qwen2.5-coder:3b",
            level="INFO",
            message="llm_call",
            prompt_tokens=300,
            response_tokens=500,
            latency_ms=1200.0,
            success=True,
        ),
    ]
    for log in logs:
        session.add(log)
    session.commit()
    return logs


class TestPipelineEndpoints:
    @patch("src.api.routes.init_db")
    @patch("src.api.routes._run_pipeline")
    def test_post_pipeline_run(self, mock_run, mock_init, client):
        resp = client.post("/pipeline/run", json={"task": "Build a REST API"})
        assert resp.status_code == 200
        data = resp.json()
        assert "id" in data
        assert data["status"] == "pending"

    def test_get_status(self, client, sample_run):
        resp = client.get(f"/pipeline/{sample_run.id}/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == sample_run.id
        assert data["status"] == "completed"
        assert data["completed_phases"] == 4
        assert data["execution_time_s"] == 12.5

    def test_get_status_not_found(self, client):
        resp = client.get("/pipeline/99999/status")
        assert resp.status_code == 404

    def test_get_artifacts_no_workspace(self, client, sample_run):
        resp = client.get(f"/pipeline/{sample_run.id}/artifacts")
        assert resp.status_code == 200
        data = resp.json()
        assert data["files"] == []

    def test_get_artifacts_with_files(self, client, session, tmp_path):
        ws = tmp_path / "test-project"
        ws.mkdir()
        (ws / "main.py").write_text("print('hello')")
        (ws / "README.md").write_text("# Test")

        run = PipelineRun(
            user_request="test",
            status=TaskStatus.COMPLETED,
            workspace_path=str(ws),
        )
        session.add(run)
        session.commit()
        session.refresh(run)

        resp = client.get(f"/pipeline/{run.id}/artifacts")
        assert resp.status_code == 200
        data = resp.json()
        assert sorted(data["files"]) == ["README.md", "main.py"]

    def test_get_metrics(self, client, sample_logs):
        resp = client.get("/agents/metrics")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        names = {m["agent_name"] for m in data}
        assert "planner" in names
        assert "executor" in names

    def test_get_metrics_empty(self, client):
        resp = client.get("/agents/metrics")
        assert resp.status_code == 200
        assert resp.json() == []


class TestWebSocket:
    def test_websocket_connect_and_receive(self, client):
        from src.api.websocket import event_stream_manager

        with client.websocket_connect("/pipeline/1/stream") as ws:
            from src.core.events import Event

            event = Event(type="pipeline.started", payload={"request": "test"})
            event_stream_manager.push_event(event)

            data = ws.receive_json()
            assert data["type"] == "pipeline.started"
            assert data["payload"]["request"] == "test"

            finish = Event(type="pipeline.finished", payload={"status": "success"})
            event_stream_manager.push_event(finish)

            data = ws.receive_json()
            assert data["type"] == "pipeline.finished"
