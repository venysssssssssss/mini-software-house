# Sprint 3 Implementation Plan — "Developer Experience"

**Created:** 2026-03-28
**Status:** Ready for execution
**Prerequisite:** Sprint 2 complete (120 tests, 83% coverage, all green)

---

## Phase 0: Documentation Discovery & API Inventory

### Allowed APIs (verified from source)

**EventBus** (`src/core/events.py`):
```python
EventBus.subscribe(event_type: str, callback: Callable[[Event], None])
EventBus.publish(event_type: str, payload: Dict[str, Any] = None)
EventBus.get_history() -> List[Event]
EventBus.reset()
```

**Database** (`src/core/database.py`):
```python
engine = create_engine("sqlite:///software_house.db")
get_session()        # Generator — use with FastAPI Depends()
get_session_direct() # Direct — use in sync orchestrator code
init_db()            # Creates all tables
```

**Orchestrator** (`src/agents/orchestrator.py`):
```python
OrchestratorAgent.execute_pipeline(user_request: str) -> Dict[str, Any]
# Returns: {"status": "success"|"failed", "plan": dict, "execution_results": list,
#           "test_results": dict, "documentation": str,
#           "pipeline_summary": {"pipeline_run_id": int, "execution_time": float, ...}}
```

**Agent Base** (`src/agents/base.py`):
```python
Agent.__init__(name: str, model: str, system_prompt: str, color=Fore.WHITE)
Agent.generate_response(user_prompt: str, **kwargs) -> str
Agent.reset_metrics() / Agent.get_collected_metrics()
get_model_for_role(role: str) -> str
```

**Models** (`src/core/models.py`): Project, Task, PipelineRun, AgentLog, DPOTuple, TaskStatus

**FastAPI patterns** (from docs):
```python
# Session dependency
SessionDep = Annotated[Session, Depends(get_session)]

# Background tasks
background_tasks.add_task(func, *args)  # runs after response sent

# WebSocket
@app.websocket("/ws/{id}")
async def ws(websocket: WebSocket): await websocket.accept(); await websocket.send_json(data)

# Static files
app.mount("/artifacts", StaticFiles(directory="workspace", html=True), name="artifacts")
```

### Anti-patterns to avoid
- Do NOT use `asyncio.run()` inside FastAPI endpoints (already in async loop)
- Do NOT use `get_session_direct()` in FastAPI routes — use `Depends(get_session)` instead
- Do NOT make EventBus async — it's class-level sync; use a threading bridge for WebSocket
- Do NOT add `httpx` or `aiohttp` — reqwest in Rust handles connection pooling
- Do NOT import `fastapi` in core modules — keep API layer separate

---

## Phase 1: FastAPI Backend (3.1)

**Goal:** Create `src/api/` module with REST + WebSocket endpoints.

### 1a. Add dependencies

**File:** `pyproject.toml`
```
fastapi = "^0.115"
uvicorn = {version = "^0.34", extras = ["standard"]}
```

Run: `poetry add fastapi "uvicorn[standard]"`

### 1b. Create API module structure

**Files to create:**
- `src/api/__init__.py` — empty
- `src/api/app.py` — FastAPI app factory, CORS, mount static files
- `src/api/routes.py` — All REST endpoints
- `src/api/websocket.py` — WebSocket streaming + EventBus bridge
- `src/api/schemas.py` — Pydantic request/response models

### 1c. Implement `src/api/schemas.py`

Define Pydantic models (not SQLModel — API layer only):
```python
class CreatePipelineRequest(BaseModel):
    task: str
    max_retries: int = 3
    git: bool = False  # Sprint 3.2 flag

class PipelineStatusResponse(BaseModel):
    id: int
    status: str
    completed_phases: int
    total_phases: int
    execution_time_s: float | None
    # ...

class AgentMetricsResponse(BaseModel):
    agent_name: str
    model: str
    total_calls: int
    success_rate: float
    avg_latency_ms: float
    total_prompt_tokens: int
    total_response_tokens: int
```

### 1d. Implement `src/api/routes.py`

**Endpoints:**
| Method | Path | Handler | Description |
|--------|------|---------|-------------|
| POST | `/pipeline/run` | `start_pipeline()` | Creates PipelineRun, starts orchestrator in BackgroundTasks, returns run_id |
| GET | `/pipeline/{id}/status` | `get_status()` | Query PipelineRun by id |
| GET | `/pipeline/{id}/artifacts` | `get_artifacts()` | List files in workspace/{project}/ |
| GET | `/agents/metrics` | `get_metrics()` | Aggregate AgentLog by agent_name |

**Pattern for POST /pipeline/run:**
```python
@router.post("/pipeline/run")
async def start_pipeline(req: CreatePipelineRequest, background_tasks: BackgroundTasks,
                         session: SessionDep):
    # Create PipelineRun record immediately
    # Return {"id": run.id, "status": "pending"}
    # background_tasks.add_task(_run_pipeline, run.id, req.task)
```

Use `get_session()` with `Depends()` for all DB access.

### 1e. Implement `src/api/websocket.py`

**EventBus -> WebSocket bridge:**
```python
class EventStreamManager:
    """Bridges sync EventBus to async WebSocket clients."""
    # Per-run dict of asyncio.Queue
    _queues: dict[int, list[asyncio.Queue]]

    def subscribe(self, run_id: int) -> asyncio.Queue
    def unsubscribe(self, run_id: int, queue: asyncio.Queue)
    def push_event(self, event: Event)  # Called from EventBus callback
```

Register `EventStreamManager.push_event` via `EventBus.subscribe("*", ...)` before starting the pipeline in the background task. The WebSocket endpoint reads from the queue:

```python
@router.websocket("/pipeline/{run_id}/stream")
async def stream(websocket: WebSocket, run_id: int):
    await websocket.accept()
    queue = manager.subscribe(run_id)
    try:
        while True:
            event = await queue.get()
            await websocket.send_json({"type": event.type, "payload": event.payload})
            if event.type == "pipeline.finished":
                break
    except WebSocketDisconnect:
        manager.unsubscribe(run_id, queue)
```

### 1f. Implement `src/api/app.py`

```python
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from .routes import router

def create_app() -> FastAPI:
    app = FastAPI(title="Mini Software House API")
    app.include_router(router)
    app.mount("/artifacts", StaticFiles(directory="workspace", html=True), name="artifacts")
    return app
```

### 1g. Add Makefile target

```makefile
api: ## Start FastAPI server (port 8000)
    poetry run uvicorn src.api.app:create_app --factory --host 0.0.0.0 --port 8000 --reload
```

### Verification checklist
- [ ] `poetry run uvicorn src.api.app:create_app --factory` starts without error
- [ ] `POST /pipeline/run` returns `{"id": N, "status": "pending"}`
- [ ] `GET /pipeline/N/status` returns run data from DB
- [ ] `GET /agents/metrics` returns aggregated stats
- [ ] WebSocket at `/pipeline/N/stream` receives events during a run
- [ ] Unit tests for all endpoints (mocked orchestrator, in-memory DB)

---

## Phase 2: Project Isolation (3.3)

**Goal:** Each run gets its own timestamped workspace; CLI can list and resume.

### 2a. Update workspace directory creation

**File:** `src/agents/orchestrator.py` — `_execute_development()`

Current: `workspace/{project_name}/`
Change to: `workspace/{project_name}_{YYYYMMDD_HHMMSS}/`

```python
from datetime import datetime
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
project_dir = f"{project_name}_{timestamp}"
```

Store the full path in `PipelineRun` (add `workspace_path` field to model if needed).

### 2b. Add `workspace_path` to PipelineRun model

**File:** `src/core/models.py`
```python
class PipelineRun(SQLModel, table=True):
    # ... existing fields ...
    workspace_path: Optional[str] = None  # e.g., "workspace/build-todo-api_20260328_190000"
```

### 2c. Remove state.json dependency

**File:** `src/main.py` — Remove state.json writes. All state lives in DB now.

Keep `workspace/state.json` only for backward compat with Streamlit Live Run View (or remove entirely and query DB).

### 2d. Update CLI with list/resume

**File:** `src/cli.py` — Add subcommands:

```
python -m src.cli list          # List all PipelineRuns from DB
python -m src.cli resume <id>   # Resume a failed run by ID
python -m src.cli status <id>   # Show run details
```

Query `PipelineRun` table, display formatted table with id, status, request, workspace_path.

### Verification checklist
- [ ] `make run TASK="..."` creates `workspace/{name}_{timestamp}/` directory
- [ ] PipelineRun.workspace_path is populated in DB
- [ ] `python -m src.cli list` shows past runs
- [ ] Two consecutive runs create separate workspace directories
- [ ] Tests updated for timestamped workspace paths

---

## Phase 3: Git Integration (3.2)

**Goal:** Auto-initialize git repo after successful pipeline run.

### 3a. Create git integration module

**File to create:** `src/utils/git_integration.py`

```python
import subprocess

def init_and_commit(workspace_path: str, project_name: str) -> dict:
    """Initialize git repo and create initial commit in workspace directory.
    Returns {"success": bool, "commit_hash": str | None, "error": str | None}
    """
    # subprocess.run(["git", "init"], cwd=workspace_path)
    # subprocess.run(["git", "add", "."], cwd=workspace_path)
    # subprocess.run(["git", "commit", "-m", f"Initial commit: {project_name}"], cwd=workspace_path)
    # Return commit hash from git rev-parse HEAD

def push_to_remote(workspace_path: str, remote_url: str) -> dict:
    """Optional: push to Gitea/GitLab if URL configured."""
    # Only if remote_url is provided
```

Use `subprocess.run` with `capture_output=True, text=True`. Do NOT use gitpython (unnecessary dependency).

### 3b. Add git fields to PipelineRun

**File:** `src/core/models.py`
```python
class PipelineRun:
    # ... existing ...
    git_commit_hash: Optional[str] = None
    git_remote_url: Optional[str] = None
```

### 3c. Hook into orchestrator

**File:** `src/agents/orchestrator.py` — After `_execute_documentation()` succeeds:

```python
if self._git_enabled:
    from ..utils.git_integration import init_and_commit
    result = init_and_commit(workspace_path, plan.get("project_name", "project"))
    if result["success"]:
        # Update PipelineRun.git_commit_hash
```

### 3d. Add --git CLI flag

**File:** `src/main.py` — Add `--git` argument
**File:** `src/api/schemas.py` — `CreatePipelineRequest.git: bool = False`

### Verification checklist
- [ ] `make run TASK="..." GIT=true` creates `.git/` in workspace output
- [ ] Git commit exists with all generated files
- [ ] PipelineRun.git_commit_hash is populated
- [ ] Without `--git`, no git operations happen
- [ ] Unit tests: mock subprocess, verify git commands called correctly

---

## Phase 4: Rust Crates — ollama_client + json_parser (3.4)

**Goal:** Complete the two Rust crates and wire through performance_bridge.py.

### 4a. Complete json_parser crate

**File:** `src/rust/json_parser/src/lib.rs`

Current stub has `parse_fast()` and `parse_json_c_ffi()`. Complete:
- Implement `parse_fast()` using `serde_json::from_str()` (simd-json is optional optimization)
- Ensure C FFI works: `parse_json_c_ffi(ptr, len) -> *mut u8` returns parsed+re-serialized JSON
- Add benchmarks: `benchmark_parse_iterations(n) -> f64` (nanoseconds per op)
- Add tests: roundtrip parse/serialize, malformed input, empty input, nested objects

### 4b. Complete ollama_client crate

**File:** `src/rust/ollama_client/Cargo.toml` — Add:
```toml
reqwest = { version = "0.12", features = ["json", "blocking"] }
tokio = { version = "1", features = ["rt", "macros"] }
```

**File:** `src/rust/ollama_client/src/lib.rs`

Implement `OllamaPool`:
```rust
impl OllamaPool {
    pub fn chat(&self, request: OllamaRequest) -> Result<OllamaResponse, String>
    // Uses reqwest::blocking::Client with connection pooling
    // POST to {base_url}/api/generate
}
```

Add C FFI:
```rust
#[no_mangle]
pub extern "C" fn ollama_chat(model: *const c_char, prompt: *const c_char) -> *mut c_char
#[no_mangle]
pub extern "C" fn ollama_free_string(ptr: *mut c_char)
```

**Important:** Use `reqwest::blocking` (not async) for C FFI simplicity. The Python side calls via ctypes which is inherently sync.

Add `crate-type = ["cdylib", "rlib"]` to Cargo.toml.

### 4c. Wire through performance_bridge.py

**File:** `src/utils/performance_bridge.py`

Add `RustJSONParser` class (same pattern as `RustASTParser`):
```python
class RustJSONParser:
    def parse(self, json_str: str) -> dict  # Falls back to json.loads()

class RustOllamaClient:
    def chat(self, model: str, prompt: str) -> str  # Falls back to ollama.chat()
```

Update `RustBridge.parse_json_fast()` to use Rust when available.

### 4d. Add benchmarks

**File:** `src/utils/performance_bridge.py` — `RustBridge._benchmark_json_parse()`

Compare Rust vs Python json.loads() for 10,000 iterations.

### Verification checklist
- [ ] `cd src/rust && cargo build --release` succeeds
- [ ] `cd src/rust && cargo test` — all crates pass
- [ ] `libollama_client.so` and `libjson_parser.so` exist in target/release/
- [ ] Python `RustBridge.parse_json_fast()` uses Rust lib when available
- [ ] Benchmark shows Rust speedup (or explains why not)
- [ ] Graceful fallback: everything works if Rust not compiled

---

## Phase 5: Plugin Architecture (3.5)

**Goal:** Define AgentPlugin protocol and enable loading custom agents.

### 5a. Define AgentPlugin protocol

**File to create:** `src/agents/plugin.py`

```python
from typing import Any, Protocol, runtime_checkable

@runtime_checkable
class AgentPlugin(Protocol):
    name: str
    role: str

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Execute the plugin with pipeline context.

        context keys: plan, execution_results, test_results, workspace_path
        Returns: {"status": "pass"|"fail", "findings": [...], ...}
        """
        ...
```

### 5b. Create plugin loader

**File to create:** `src/agents/plugin_loader.py`

```python
def discover_plugins(plugin_dir: str = "plugins") -> list[AgentPlugin]:
    """Discover and load plugins from directory.
    Each plugin is a .py file with a class implementing AgentPlugin.
    """
    # Walk plugin_dir, importlib.import_module each .py
    # Find classes that are AgentPlugin instances
    # Return instantiated list
```

### 5c. Create example plugin

**File to create:** `plugins/security_auditor.py`

```python
class SecurityAuditor:
    name = "SecurityAuditor"
    role = "security"

    def execute(self, context: dict) -> dict:
        # Check generated code for common vulnerabilities:
        # - hardcoded secrets (regex for API keys, passwords)
        # - SQL injection patterns
        # - eval/exec usage
        # - open() without proper path validation
        return {"status": "pass", "findings": [...]}
```

### 5d. Hook plugins into orchestrator

**File:** `src/agents/orchestrator.py`

After development phase, before documentation:
```python
# Run plugins (between testing and documentation)
plugins = discover_plugins()
for plugin in plugins:
    result = plugin.execute({
        "plan": self.plan,
        "execution_results": self.execution_results,
        "workspace_path": workspace_path,
    })
    self._log_to_db(plugin.name, "INFO", f"Plugin result: {result['status']}")
```

### Verification checklist
- [ ] `SecurityAuditor` plugin loads from `plugins/` directory
- [ ] Plugin execute() is called during pipeline run
- [ ] Plugin results logged to DB
- [ ] Pipeline works with no plugins directory (graceful skip)
- [ ] Unit tests: mock plugin, verify discovery and execution

---

## Phase 6: Tests & Final Verification (3.6)

**Goal:** E2E tests, load tests, 85% coverage.

### 6a. API endpoint tests

**File to create:** `tests/unit/test_api.py`

Test each endpoint with mocked orchestrator and in-memory DB:
- POST /pipeline/run returns 200 with run_id
- GET /pipeline/{id}/status returns correct data
- GET /pipeline/{id}/artifacts lists files
- GET /agents/metrics returns aggregated data

Use `from fastapi.testclient import TestClient`.

### 6b. WebSocket test

**File:** `tests/unit/test_api.py`

```python
def test_websocket_receives_events():
    with TestClient(app) as client:
        with client.websocket_connect(f"/pipeline/{run_id}/stream") as ws:
            # Trigger pipeline in background
            # Assert ws.receive_json() gets pipeline.started, phase events, pipeline.finished
```

### 6c. Git integration tests

**File to create:** `tests/unit/test_git_integration.py`

Mock `subprocess.run`, verify:
- `git init` called in workspace directory
- `git add .` called
- `git commit -m "..."` called
- Commit hash extracted correctly

### 6d. Plugin system tests

**File to create:** `tests/unit/test_plugins.py`

- Test plugin discovery from directory
- Test plugin execution with context
- Test graceful handling of no plugins directory
- Test invalid plugin (missing protocol methods)

### 6e. Integration test: full API pipeline

**File to create:** `tests/integration/test_api_pipeline.py`

Full flow: POST /pipeline/run -> poll GET /status -> GET /artifacts -> verify files exist.

### 6f. Coverage target

Run: `poetry run pytest tests/ --cov=src --cov=src/api --cov-report=term-missing`

Target: 85% on agents + core + api modules.

### Verification checklist
- [ ] All new tests pass
- [ ] Total test count >= 150
- [ ] Coverage >= 85% on agents + core + api
- [ ] `make lint` passes
- [ ] `make rust-build && make rust-test` passes
- [ ] `make test` passes (all Python tests)

---

## Dependency Graph

```
Phase 0: Doc discovery (this document) ─── DONE
    │
    ├── Phase 1: FastAPI backend (3.1)
    │       │
    │       ├── Phase 2: Project isolation (3.3)
    │       │       │
    │       │       └── Phase 3: Git integration (3.2) [needs workspace_path from Phase 2]
    │       │
    │       └── Phase 5: Plugin architecture (3.5) [needs API for plugin management]
    │
    ├── Phase 4: Rust crates (3.4) [independent, can parallel with 1-3]
    │
    └── Phase 6: Tests & verification (3.6) [after all other phases]
```

**Parallelizable:** Phase 4 (Rust) can run in parallel with Phases 1-3.

---

## Files to Create (New)

| File | Phase | Purpose |
|------|-------|---------|
| `src/api/__init__.py` | 1 | Package marker |
| `src/api/app.py` | 1 | FastAPI app factory |
| `src/api/routes.py` | 1 | REST endpoints |
| `src/api/websocket.py` | 1 | WebSocket streaming |
| `src/api/schemas.py` | 1 | Pydantic models |
| `src/utils/git_integration.py` | 3 | Git init/commit/push |
| `src/agents/plugin.py` | 5 | AgentPlugin protocol |
| `src/agents/plugin_loader.py` | 5 | Plugin discovery |
| `plugins/security_auditor.py` | 5 | Example plugin |
| `tests/unit/test_api.py` | 6 | API tests |
| `tests/unit/test_git_integration.py` | 6 | Git tests |
| `tests/unit/test_plugins.py` | 6 | Plugin tests |
| `tests/integration/test_api_pipeline.py` | 6 | E2E API test |

## Files to Modify (Existing)

| File | Phase | Change |
|------|-------|--------|
| `pyproject.toml` | 1 | Add fastapi, uvicorn deps |
| `Makefile` | 1 | Add `api` target |
| `src/core/models.py` | 2, 3 | Add workspace_path, git fields to PipelineRun |
| `src/core/database.py` | 2 | Export SessionDep type alias |
| `src/core/__init__.py` | 2 | Export new symbols |
| `src/agents/orchestrator.py` | 2, 3, 5 | Timestamped workspace, git hook, plugin hook |
| `src/main.py` | 3 | Add --git flag |
| `src/cli.py` | 2 | Add list/resume/status subcommands |
| `src/rust/ollama_client/` | 4 | Complete implementation |
| `src/rust/json_parser/` | 4 | Complete implementation |
| `src/utils/performance_bridge.py` | 4 | Wire new Rust crates |
| `CLAUDE.md` | 6 | Update architecture docs |
| `docs/SPRINT_PLAN.md` | 6 | Mark Sprint 3 deliverables complete |
