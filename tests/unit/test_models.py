"""Tests for SQLModel schema definitions."""

import pytest
from sqlmodel import Session, SQLModel, create_engine, select

from src.core.models import AgentLog, DPOTuple, PipelineRun, Project, Task, TaskStatus


@pytest.fixture
def db_session():
    """Provide an in-memory SQLite session for each test."""
    engine = create_engine("sqlite://", echo=False)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def test_create_project(db_session):
    project = Project(name="test-project", path="/tmp/workspace")
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    assert project.id is not None
    assert project.name == "test-project"
    assert project.path == "/tmp/workspace"
    assert project.created_at is not None


def test_create_task_with_project(db_session):
    project = Project(name="proj", path="/tmp")
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    task = Task(project_id=project.id, description="Build API")
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    assert task.id is not None
    assert task.project_id == project.id
    assert task.status == TaskStatus.PENDING
    assert task.description == "Build API"


def test_task_status_enum_values():
    assert TaskStatus.PENDING == "pending"
    assert TaskStatus.IN_PROGRESS == "in_progress"
    assert TaskStatus.COMPLETED == "completed"
    assert TaskStatus.FAILED == "failed"


def test_task_status_transitions(db_session):
    project = Project(name="p", path="/tmp")
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    task = Task(project_id=project.id, description="task")
    db_session.add(task)
    db_session.commit()

    task.status = TaskStatus.IN_PROGRESS
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)
    assert task.status == TaskStatus.IN_PROGRESS

    task.status = TaskStatus.COMPLETED
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)
    assert task.status == TaskStatus.COMPLETED


def test_create_agent_log(db_session):
    project = Project(name="p", path="/tmp")
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    task = Task(project_id=project.id, description="t")
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    log = AgentLog(
        task_id=task.id,
        agent_name="planner",
        level="INFO",
        message="Plan generated",
        structured_data='{"key": "value"}',
    )
    db_session.add(log)
    db_session.commit()
    db_session.refresh(log)

    assert log.id is not None
    assert log.agent_name == "planner"
    assert log.level == "INFO"
    assert log.timestamp is not None


def test_project_task_relationship(db_session):
    project = Project(name="rel-test", path="/tmp")
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    t1 = Task(project_id=project.id, description="task 1")
    t2 = Task(project_id=project.id, description="task 2")
    db_session.add_all([t1, t2])
    db_session.commit()

    db_session.refresh(project)
    assert len(project.tasks) == 2


def test_query_tasks_by_status(db_session):
    project = Project(name="q", path="/tmp")
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    for desc, status in [
        ("a", TaskStatus.PENDING),
        ("b", TaskStatus.COMPLETED),
        ("c", TaskStatus.PENDING),
    ]:
        db_session.add(Task(project_id=project.id, description=desc, status=status))
    db_session.commit()

    from sqlmodel import select

    pending = db_session.exec(select(Task).where(Task.status == TaskStatus.PENDING)).all()
    assert len(pending) == 2

    completed = db_session.exec(select(Task).where(Task.status == TaskStatus.COMPLETED)).all()
    assert len(completed) == 1


def test_agent_log_without_task_id(db_session):
    log = AgentLog(agent_name="executor", level="ERROR", message="something broke")
    db_session.add(log)
    db_session.commit()
    db_session.refresh(log)

    assert log.id is not None
    assert log.task_id is None


# ---- Sprint 2: PipelineRun model ----


def test_create_pipeline_run(db_session):
    project = Project(name="p", path="/tmp")
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    task = Task(project_id=project.id, description="t")
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    run = PipelineRun(
        project_id=project.id,
        task_id=task.id,
        user_request="Build a todo app",
        status=TaskStatus.IN_PROGRESS,
    )
    db_session.add(run)
    db_session.commit()
    db_session.refresh(run)

    assert run.id is not None
    assert run.user_request == "Build a todo app"
    assert run.status == TaskStatus.IN_PROGRESS
    assert run.total_phases == 4
    assert run.completed_phases == 0


def test_pipeline_run_tracks_metrics(db_session):
    run = PipelineRun(user_request="test")
    db_session.add(run)
    db_session.commit()

    run.total_prompt_tokens = 500
    run.total_response_tokens = 1200
    run.total_latency_ms = 3500.5
    run.total_agent_calls = 8
    run.execution_time_s = 12.3
    run.status = TaskStatus.COMPLETED
    db_session.add(run)
    db_session.commit()
    db_session.refresh(run)

    assert run.total_prompt_tokens == 500
    assert run.total_response_tokens == 1200
    assert run.total_latency_ms == 3500.5
    assert run.total_agent_calls == 8
    assert run.execution_time_s == 12.3


# ---- Sprint 2: AgentLog with metrics ----


def test_agent_log_with_metrics(db_session):
    log = AgentLog(
        agent_name="Executor",
        model="qwen2.5-coder:3b",
        level="INFO",
        message="llm_call",
        prompt_tokens=120,
        response_tokens=450,
        latency_ms=2345.6,
        success=True,
    )
    db_session.add(log)
    db_session.commit()
    db_session.refresh(log)

    assert log.model == "qwen2.5-coder:3b"
    assert log.prompt_tokens == 120
    assert log.response_tokens == 450
    assert log.latency_ms == 2345.6
    assert log.success is True


def test_agent_log_failed_call(db_session):
    log = AgentLog(
        agent_name="Planner",
        model="qwen2.5:3b",
        level="ERROR",
        message="llm_call",
        prompt_tokens=80,
        response_tokens=0,
        latency_ms=100.0,
        success=False,
        structured_data='{"error": "connection refused"}',
    )
    db_session.add(log)
    db_session.commit()
    db_session.refresh(log)

    assert log.success is False
    assert log.response_tokens == 0


# ---- Sprint 2: DPOTuple model ----


def test_create_dpo_tuple(db_session):
    dpo = DPOTuple(
        agent_name="executor",
        prompt="Create a Flask app",
        generated_code="app.py",
        test_result="pass",
    )
    db_session.add(dpo)
    db_session.commit()
    db_session.refresh(dpo)

    assert dpo.id is not None
    assert dpo.agent_name == "executor"
    assert dpo.test_result == "pass"
    assert dpo.corrected_code is None


def test_dpo_tuple_with_correction(db_session):
    dpo = DPOTuple(
        agent_name="executor",
        prompt="Fix the import",
        generated_code="from flsk import Flask",
        test_result="ImportError: No module named 'flsk'",
        corrected_code="from flask import Flask",
        error_type="ImportError",
        correction_successful=True,
    )
    db_session.add(dpo)
    db_session.commit()
    db_session.refresh(dpo)

    assert dpo.error_type == "ImportError"
    assert dpo.correction_successful is True
    assert dpo.corrected_code == "from flask import Flask"


def test_query_dpo_by_error_type(db_session):
    for etype in ["ImportError", "ImportError", "SyntaxError", None]:
        db_session.add(
            DPOTuple(
                agent_name="executor",
                prompt="fix",
                generated_code="code",
                test_result="fail",
                error_type=etype,
            )
        )
    db_session.commit()

    import_errors = db_session.exec(
        select(DPOTuple).where(DPOTuple.error_type == "ImportError")
    ).all()
    assert len(import_errors) == 2
