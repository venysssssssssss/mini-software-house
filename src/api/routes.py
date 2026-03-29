"""REST and WebSocket endpoints."""

import os
from typing import Annotated

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
)
from sqlmodel import Session, func, select

from ..core.database import get_session, init_db
from ..core.events import EventBus
from ..core.models import AgentLog, PipelineRun, TaskStatus
from .schemas import (
    AgentMetricsResponse,
    CreatePipelineRequest,
    PipelineCreatedResponse,
    PipelineStatusResponse,
)
from .websocket import event_stream_manager

router = APIRouter()
SessionDep = Annotated[Session, Depends(get_session)]


def _run_pipeline(run_id: int, task: str, git: bool = False):
    """Background task: execute the pipeline and update the DB record."""
    from ..agents.orchestrator import OrchestratorAgent

    orchestrator = OrchestratorAgent()
    # Point the orchestrator at the existing run record
    orchestrator._pipeline_run_id = run_id
    orchestrator.execute_pipeline(task)


@router.post("/pipeline/run", response_model=PipelineCreatedResponse)
def start_pipeline(
    req: CreatePipelineRequest,
    background_tasks: BackgroundTasks,
    session: SessionDep,
):
    """Create a PipelineRun and start the orchestrator in the background."""
    init_db()

    run = PipelineRun(
        user_request=req.task,
        status=TaskStatus.PENDING,
    )
    session.add(run)
    session.commit()
    session.refresh(run)

    # Subscribe the event stream manager before launching
    EventBus.subscribe("*", event_stream_manager.push_event)

    background_tasks.add_task(_run_pipeline, run.id, req.task, req.git)

    return PipelineCreatedResponse(id=run.id, status="pending")


@router.get("/pipeline/{run_id}/status", response_model=PipelineStatusResponse)
def get_status(run_id: int, session: SessionDep):
    """Query PipelineRun by id."""
    run = session.get(PipelineRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Pipeline run not found")

    return PipelineStatusResponse(
        id=run.id,
        status=run.status.value,
        user_request=run.user_request,
        completed_phases=run.completed_phases,
        total_phases=run.total_phases,
        execution_time_s=run.execution_time_s,
        workspace_path=run.workspace_path,
        git_commit_hash=run.git_commit_hash,
        total_prompt_tokens=run.total_prompt_tokens,
        total_response_tokens=run.total_response_tokens,
        total_agent_calls=run.total_agent_calls,
    )


@router.get("/pipeline/{run_id}/artifacts")
def get_artifacts(run_id: int, session: SessionDep):
    """List files in the workspace directory for a run."""
    run = session.get(PipelineRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Pipeline run not found")

    workspace_path = run.workspace_path
    if not workspace_path or not os.path.isdir(workspace_path):
        return {"run_id": run_id, "files": []}

    files = []
    for root, _dirs, filenames in os.walk(workspace_path):
        for fname in filenames:
            full = os.path.join(root, fname)
            files.append(os.path.relpath(full, workspace_path))

    return {"run_id": run_id, "files": sorted(files)}


@router.get("/agents/metrics", response_model=list[AgentMetricsResponse])
def get_metrics(session: SessionDep):
    """Aggregate AgentLog metrics by agent_name."""
    stmt = select(
        AgentLog.agent_name,
        AgentLog.model,
        func.count(AgentLog.id).label("total_calls"),
        func.avg(
            # SQLite doesn't have a native bool->int cast, success is stored as 0/1
            AgentLog.success
        ).label("success_rate"),
        func.avg(AgentLog.latency_ms).label("avg_latency_ms"),
        func.sum(AgentLog.prompt_tokens).label("total_prompt_tokens"),
        func.sum(AgentLog.response_tokens).label("total_response_tokens"),
    ).group_by(AgentLog.agent_name, AgentLog.model)

    rows = session.exec(stmt).all()

    return [
        AgentMetricsResponse(
            agent_name=row[0],
            model=row[1],
            total_calls=row[2],
            success_rate=float(row[3] or 0),
            avg_latency_ms=float(row[4] or 0),
            total_prompt_tokens=int(row[5] or 0),
            total_response_tokens=int(row[6] or 0),
        )
        for row in rows
    ]


@router.websocket("/pipeline/{run_id}/stream")
async def stream_pipeline(websocket: WebSocket, run_id: int):
    """WebSocket endpoint for real-time pipeline event streaming."""
    await websocket.accept()
    queue = event_stream_manager.subscribe(run_id)
    try:
        while True:
            event = await queue.get()
            await websocket.send_json(event)
            if event.get("type") == "pipeline.finished":
                break
    except WebSocketDisconnect:
        pass
    finally:
        event_stream_manager.unsubscribe(run_id, queue)
