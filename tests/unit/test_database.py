"""Tests for database session lifecycle."""

import pytest
from sqlmodel import Session, SQLModel, create_engine, select

from src.core.models import Project, Task


@pytest.fixture
def engine():
    """In-memory SQLite engine."""
    eng = create_engine("sqlite://", echo=False)
    SQLModel.metadata.create_all(eng)
    return eng


def test_session_lifecycle(engine):
    """Test that a session can create, read, and close properly."""
    with Session(engine) as session:
        project = Project(name="lifecycle", path="/tmp")
        session.add(project)
        session.commit()
        session.refresh(project)
        pid = project.id

    # Read back in a new session
    with Session(engine) as session:
        project = session.get(Project, pid)
        assert project is not None
        assert project.name == "lifecycle"


def test_rollback_on_error(engine):
    """Test that uncommitted changes are rolled back on exception."""
    try:
        with Session(engine) as session:
            session.add(Project(name="will-rollback", path="/tmp"))
            raise RuntimeError("simulated error")
    except RuntimeError:
        pass

    with Session(engine) as session:
        projects = session.exec(select(Project)).all()
        assert len(projects) == 0


def test_multiple_sessions_see_committed_data(engine):
    """Test that committed data is visible across sessions."""
    with Session(engine) as s1:
        s1.add(Project(name="shared", path="/tmp"))
        s1.commit()

    with Session(engine) as s2:
        projects = s2.exec(select(Project)).all()
        assert len(projects) == 1
        assert projects[0].name == "shared"


def test_cascade_project_tasks(engine):
    """Test creating a project with tasks in one transaction."""
    with Session(engine) as session:
        project = Project(name="cascade", path="/tmp")
        session.add(project)
        session.commit()
        session.refresh(project)

        for i in range(3):
            session.add(Task(project_id=project.id, description=f"task-{i}"))
        session.commit()

    with Session(engine) as session:
        tasks = session.exec(select(Task)).all()
        assert len(tasks) == 3


def test_update_and_read_back(engine):
    """Test that updates persist correctly."""
    with Session(engine) as session:
        project = Project(name="v1", path="/tmp")
        session.add(project)
        session.commit()
        session.refresh(project)
        pid = project.id

    with Session(engine) as session:
        project = session.get(Project, pid)
        project.name = "v2"
        session.add(project)
        session.commit()

    with Session(engine) as session:
        project = session.get(Project, pid)
        assert project.name == "v2"
