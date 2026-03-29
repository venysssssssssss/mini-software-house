"""Integration test: full pipeline with mock Ollama server.

Validates: plan -> execute -> test -> document flow,
state persistence (DB), and event emission (EventBus).
"""

import json
from unittest.mock import patch

import pytest
from sqlmodel import Session, SQLModel, create_engine, select

from src.agents.orchestrator import OrchestratorAgent
from src.core.events import EventBus
from src.core.models import AgentLog, PipelineRun, Project, Task, TaskStatus

# --- Canned LLM responses ---

PLAN_RESPONSE = json.dumps(
    {
        "project_name": "build-todo-api",
        "architecture": "Single-file Flask REST API",
        "files_to_create": ["app.py"],
        "dependencies": ["flask"],
        "logical_steps": ["Create Flask app", "Add CRUD routes"],
    }
)

EXECUTOR_RESPONSE = (
    "Here is the code:\n\n"
    "```python\n"
    "# filepath: app.py\n"
    "from flask import Flask\n"
    "app = Flask(__name__)\n"
    "\n"
    "@app.route('/')\n"
    "def index():\n"
    "    return 'Hello'\n"
    "```\n"
)

TEST_RESPONSE = "```python\n# filepath: test_app.py\ndef test_index():\n    assert True\n```\n"

DOC_RESPONSE = "# Todo API\n\nA simple Flask REST API for managing todos."


def _mock_ollama_chat(model, messages, **kwargs):
    """Route canned responses based on which agent is calling."""
    system_msg = messages[0]["content"] if messages else ""

    if "Architect" in system_msg or "Planner" in system_msg:
        content = PLAN_RESPONSE
    elif "expert software developer" in system_msg:
        content = EXECUTOR_RESPONSE
    elif "QA" in system_msg or "Test Engineer" in system_msg:
        content = TEST_RESPONSE
    elif "Technical Writer" in system_msg:
        content = DOC_RESPONSE
    else:
        content = "fallback response"

    return {
        "message": {"content": content},
        "prompt_eval_count": 50,
        "eval_count": len(content) // 4,  # rough token estimate
    }


@pytest.fixture(autouse=True)
def clean_event_bus():
    EventBus.reset()
    yield
    EventBus.reset()


@pytest.fixture
def in_memory_db(monkeypatch):
    """Replace the real DB with an in-memory SQLite for isolation."""
    engine = create_engine("sqlite://", echo=False)
    SQLModel.metadata.create_all(engine)

    monkeypatch.setattr("src.agents.orchestrator.init_db", lambda: None)
    monkeypatch.setattr(
        "src.agents.orchestrator.get_session_direct",
        lambda: Session(engine),
    )
    return engine


@pytest.fixture
def orchestrator(in_memory_db, tmp_path, monkeypatch):
    """Create an orchestrator with all external deps mocked."""
    with (
        patch("src.agents.base.ollama") as mock_ollama,
        patch("src.agents.tester.DockerRunner", side_effect=Exception("no docker")),
        patch("src.agents.rag.chromadb", None),
    ):
        mock_ollama.chat.side_effect = _mock_ollama_chat

        orch = OrchestratorAgent()
        # Point executor's FileManager to temp dir
        orch.executor.file_manager.workspace_dir = str(tmp_path)

        yield orch


class TestFullPipeline:
    def test_pipeline_succeeds(self, orchestrator):
        result = orchestrator.execute_pipeline("Build a todo API")

        assert result["status"] == "success"
        assert result["plan"]["architecture"] == "Single-file Flask REST API"
        assert len(result["execution_results"]) == 1
        assert result["test_results"]["exit_code"] == 0
        assert "Todo API" in result["documentation"] or result["documentation"] == ""

    def test_pipeline_emits_events(self, orchestrator):
        orchestrator.execute_pipeline("Build a todo API")

        history = EventBus.get_history()
        event_types = [e.type for e in history]

        assert "pipeline.started" in event_types
        assert "phase.started" in event_types
        assert "phase.completed" in event_types
        assert "pipeline.finished" in event_types

        # Check specific phase events
        phase_started = [e for e in history if e.type == "phase.started"]
        phases = [e.payload["phase"] for e in phase_started]
        assert "planning" in phases
        assert "development" in phases
        assert "testing" in phases
        assert "documentation" in phases

    def test_pipeline_persists_to_db(self, orchestrator, in_memory_db):
        orchestrator.execute_pipeline("Build a todo API")

        with Session(in_memory_db) as session:
            projects = session.exec(select(Project)).all()
            assert len(projects) == 1
            assert "Build a todo API" in projects[0].name

            tasks = session.exec(select(Task)).all()
            assert len(tasks) == 1
            assert tasks[0].status == TaskStatus.COMPLETED

            logs = session.exec(select(AgentLog)).all()
            assert len(logs) >= 2  # at least planner + executor logs

    def test_pipeline_writes_files(self, orchestrator, tmp_path):
        orchestrator.execute_pipeline("Build a todo API")

        # Files are in a timestamped project subdirectory (e.g., build-todo-api_20260329_010000/)
        project_dirs = [
            d for d in tmp_path.iterdir() if d.is_dir() and d.name.startswith("build-todo-api")
        ]
        assert len(project_dirs) == 1
        project_dir = project_dirs[0]
        assert (project_dir / "app.py").exists()
        content = (project_dir / "app.py").read_text()
        assert "Flask" in content

    def test_pipeline_event_subscriber_called(self, orchestrator):
        events_received = []
        EventBus.subscribe("pipeline.finished", lambda e: events_received.append(e))

        orchestrator.execute_pipeline("Build a todo API")

        assert len(events_received) == 1
        assert events_received[0].payload["status"] == "success"

    def test_pipeline_creates_pipeline_run(self, orchestrator, in_memory_db):
        orchestrator.execute_pipeline("Build a todo API")

        with Session(in_memory_db) as session:
            runs = session.exec(select(PipelineRun)).all()
            assert len(runs) == 1
            run = runs[0]
            assert run.status == TaskStatus.COMPLETED
            assert run.completed_phases == 4
            assert run.execution_time_s is not None
            assert run.finished_at is not None
            assert run.user_request == "Build a todo API"
            assert run.total_agent_calls >= 1

    def test_pipeline_logs_have_metrics(self, orchestrator, in_memory_db):
        orchestrator.execute_pipeline("Build a todo API")

        with Session(in_memory_db) as session:
            llm_logs = session.exec(select(AgentLog).where(AgentLog.message == "llm_call")).all()
            assert len(llm_logs) >= 1
            for log in llm_logs:
                assert log.prompt_tokens >= 0
                assert log.response_tokens >= 0
                assert log.latency_ms >= 0
                assert log.model is not None


class TestPipelineFailure:
    def test_planning_failure_marks_task_failed(self, in_memory_db, tmp_path):
        with (
            patch("src.agents.base.ollama") as mock_ollama,
            patch("src.agents.tester.DockerRunner", side_effect=Exception("no docker")),
            patch("src.agents.rag.chromadb", None),
        ):
            # Return invalid JSON to make planning fail
            mock_ollama.chat.return_value = {"message": {"content": "not json"}}

            orch = OrchestratorAgent()
            orch.executor.file_manager.workspace_dir = str(tmp_path)
            result = orch.execute_pipeline("Will fail")

        assert result["status"] == "failed"
        assert "Planning" in result["error"]

        with Session(in_memory_db) as session:
            tasks = session.exec(select(Task)).all()
            assert tasks[0].status == TaskStatus.FAILED
