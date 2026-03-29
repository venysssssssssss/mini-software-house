"""Pydantic request/response models for the API layer."""

from pydantic import BaseModel


class CreatePipelineRequest(BaseModel):
    task: str
    max_retries: int = 3
    git: bool = False


class PipelineStatusResponse(BaseModel):
    id: int
    status: str
    user_request: str
    completed_phases: int
    total_phases: int
    execution_time_s: float | None = None
    workspace_path: str | None = None
    git_commit_hash: str | None = None
    total_prompt_tokens: int = 0
    total_response_tokens: int = 0
    total_agent_calls: int = 0


class AgentMetricsResponse(BaseModel):
    agent_name: str
    model: str | None = None
    total_calls: int
    success_rate: float
    avg_latency_ms: float
    total_prompt_tokens: int
    total_response_tokens: int


class PipelineCreatedResponse(BaseModel):
    id: int
    status: str
