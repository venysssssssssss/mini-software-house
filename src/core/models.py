"""SQLModel schema definitions for mini-software-house."""

from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional

from sqlmodel import Field, Relationship, SQLModel


class TaskStatus(str, Enum):
    """Task execution status enum."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class Project(SQLModel, table=True):
    """Project model with relationship to tasks."""

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    path: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    tasks: List["Task"] = Relationship(back_populates="project")


class Task(SQLModel, table=True):
    """Task model with project relationship."""

    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: Optional[int] = Field(default=None, foreign_key="project.id")
    description: str
    status: TaskStatus = Field(default=TaskStatus.PENDING)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    project: Optional[Project] = Relationship(back_populates="tasks")


class PipelineRun(SQLModel, table=True):
    """Links all artifacts for a single pipeline invocation."""

    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: Optional[int] = Field(default=None, foreign_key="project.id")
    task_id: Optional[int] = Field(default=None, foreign_key="task.id")
    user_request: str
    status: TaskStatus = Field(default=TaskStatus.PENDING)
    total_phases: int = Field(default=4)
    completed_phases: int = Field(default=0)
    total_prompt_tokens: int = Field(default=0)
    total_response_tokens: int = Field(default=0)
    total_latency_ms: float = Field(default=0.0)
    total_agent_calls: int = Field(default=0)
    execution_time_s: Optional[float] = None
    workspace_path: Optional[str] = None
    git_commit_hash: Optional[str] = None
    git_remote_url: Optional[str] = None
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    finished_at: Optional[datetime] = None


class AgentLog(SQLModel, table=True):
    """Agent execution log model with metrics."""

    id: Optional[int] = Field(default=None, primary_key=True)
    task_id: Optional[int] = Field(default=None, foreign_key="task.id")
    pipeline_run_id: Optional[int] = Field(default=None, foreign_key="pipelinerun.id")
    agent_name: str
    model: Optional[str] = None
    level: str
    message: str
    prompt_tokens: int = Field(default=0)
    response_tokens: int = Field(default=0)
    latency_ms: float = Field(default=0.0)
    success: bool = Field(default=True)
    structured_data: Optional[str] = None  # JSON string for extra data
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class DPOTuple(SQLModel, table=True):
    """Data point for Direct Preference Optimization (data flywheel)."""

    id: Optional[int] = Field(default=None, primary_key=True)
    pipeline_run_id: Optional[int] = Field(default=None, foreign_key="pipelinerun.id")
    agent_name: str
    prompt: str
    generated_code: str
    test_result: str  # "pass" or error details
    corrected_code: Optional[str] = None  # if correction was needed
    error_type: Optional[str] = None  # e.g., "ImportError", "SyntaxError"
    correction_successful: Optional[bool] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
