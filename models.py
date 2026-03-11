from typing import Optional, List
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship
from enum import Enum

class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"

class Project(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    path: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    tasks: List["Task"] = Relationship(back_populates="project")

class Task(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: Optional[int] = Field(default=None, foreign_key="project.id")
    description: str
    status: TaskStatus = Field(default=TaskStatus.PENDING)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    project: Optional[Project] = Relationship(back_populates="tasks")

class AgentLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    task_id: Optional[int] = Field(default=None, foreign_key="task.id")
    agent_name: str
    level: str
    message: str
    structured_data: Optional[str] = None # JSON string for extra data
    timestamp: datetime = Field(default_factory=datetime.utcnow)