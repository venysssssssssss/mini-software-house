"""
Core infrastructure modules for mini-software-house.

This package contains fundamental services:
- database: SQLModel setup and session management
- models: SQLModel schema definitions
- events: Event bus for pub/sub communication
- logger: Structured logging with structlog
"""

from .database import init_db, get_session, get_session_direct, engine
from .models import Project, Task, TaskStatus, AgentLog
from .events import Event, EventBus
from .logger import get_logger, configure_logger

__all__ = [
    "init_db",
    "get_session",
    "get_session_direct",
    "engine",
    "Project",
    "Task",
    "TaskStatus",
    "AgentLog",
    "Event",
    "EventBus",
    "get_logger",
    "configure_logger",
]
