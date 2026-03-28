"""
Core infrastructure modules for mini-software-house.

This package contains fundamental services:
- database: SQLModel setup and session management
- models: SQLModel schema definitions
- events: Event bus for pub/sub communication
- logger: Structured logging with structlog
"""

from .database import engine, get_session, get_session_direct, init_db
from .events import Event, EventBus
from .logger import configure_logger, get_logger
from .models import AgentLog, DPOTuple, PipelineRun, Project, Task, TaskStatus

__all__ = [
    "init_db",
    "get_session",
    "get_session_direct",
    "engine",
    "Project",
    "Task",
    "TaskStatus",
    "AgentLog",
    "PipelineRun",
    "DPOTuple",
    "Event",
    "EventBus",
    "get_logger",
    "configure_logger",
]
