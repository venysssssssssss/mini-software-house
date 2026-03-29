# Mini Software House - Full Guide

Complete guide to set up and run the AI-powered software development pipeline.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Installation](#installation)
3. [Pulling Ollama Models](#pulling-ollama-models)
4. [Building Projects via CLI](#building-projects-via-cli)
5. [Building Projects via API](#building-projects-via-api)
6. [Building Projects via Dashboard](#building-projects-via-dashboard)
7. [Managing Pipeline Runs](#managing-pipeline-runs)
8. [Git Integration](#git-integration)
9. [Plugins](#plugins)
10. [Rust Performance Layer](#rust-performance-layer)
11. [Fine-Tuning Your Models](#fine-tuning-your-models)
12. [Docker Deployment](#docker-deployment)
13. [Configuration Reference](#configuration-reference)
14. [Troubleshooting](#troubleshooting)

---

## Prerequisites

| Requirement | Minimum | Recommended |
|------------|---------|-------------|
| Python | 3.12+ | 3.12 |
| Rust | 1.70+ | latest stable |
| GPU VRAM | 4 GB (GTX 1050 Ti) | 8 GB+ |
| RAM | 8 GB | 16 GB |
| Disk | 10 GB (models) | 20 GB |
| Ollama | 0.1+ | latest |
| Docker | optional | 24.0+ |

**OS:** Linux (tested on Kali/Ubuntu). macOS works with minor adjustments. Windows requires WSL2.

---

## Installation

### Option A: Automated Setup

```bash
git clone <repo-url>
cd mini-software-house

# Full setup: installs Python deps, builds Rust, checks Ollama
python scripts/setup/setup_environment.py

# Verify everything
bash scripts/setup/verify_setup.sh
```

### Option B: Step-by-Step

```bash
# 1. Install Python dependencies
poetry install

# 2. Build Rust performance modules (optional but recommended)
cd src/rust && cargo build --release && cd ../..

# 3. Initialize the database
poetry run python -c "from src.core.database import init_db; init_db()"
```

### Verify Installation

```bash
make verify
```

Expected output: all checks green for Python, Rust, and Ollama.

---

## Pulling Ollama Models

The pipeline uses 6 specialized models optimized for 4 GB VRAM. Only one model is loaded at a time.

```bash
# Pull all models at once
bash scripts/setup/pull_models.sh

# Or pull individually
ollama pull qwen2.5:3b           # Planner (architecture design)
ollama pull qwen2.5-coder:3b     # Backend development
ollama pull qwen2.5-coder:1.5b   # Frontend development
ollama pull deepseek-coder:1.3b  # Test generation
ollama pull gemma2:2b             # Documentation
ollama pull phi3:mini             # RAG context retrieval
```

Verify models are available:

```bash
ollama list
```

---

## Building Projects via CLI

### Basic Usage

```bash
# Run the full pipeline with a task description
make run TASK="Build a REST API for user management with FastAPI"

# Or directly
poetry run python -m src.main --task "Build a todo app with Flask and SQLite"
```

The pipeline runs 4 phases sequentially:

1. **Planning** - Generates architecture, file list, dependencies
2. **Development** - Creates each file with full project context
3. **Testing** - Runs tests, auto-corrects failures (up to 3 attempts)
4. **Documentation** - Generates README and API docs

Output goes to `workspace/{project-name}_{timestamp}/`.

### Examples

```bash
# Web API
make run TASK="Build a REST API for a bookstore with CRUD operations using Flask"

# CLI tool
make run TASK="Build a Python CLI tool that converts CSV files to JSON"

# Full-stack
make run TASK="Build a task management app with FastAPI backend and HTML frontend"

# Data processing
make run TASK="Build a Python script that scrapes weather data and stores it in SQLite"
```

### With Git Auto-Init

```bash
# Initialize a git repo in the output directory after successful run
make run TASK="Build a calculator API" GIT=true

# Or directly
poetry run python -m src.main --task "Build a calculator API" --git
```

This creates a `.git/` directory in the workspace output with an initial commit containing all generated files.

### Resume a Failed Run

```bash
make resume
# Or
poetry run python -m src.main --resume
```

---

## Building Projects via API

Sprint 3 added a FastAPI server for programmatic access.

### Start the API Server

```bash
make api
# Server runs at http://localhost:8000
# Auto-reloads on code changes
```

### Endpoints

#### Start a Pipeline

```bash
curl -X POST http://localhost:8000/pipeline/run \
  -H "Content-Type: application/json" \
  -d '{"task": "Build a todo API with Flask", "git": false}'
```

Response:
```json
{"id": 1, "status": "pending"}
```

The pipeline runs in the background. Use the returned `id` to check status.

#### Check Pipeline Status

```bash
curl http://localhost:8000/pipeline/1/status
```

Response:
```json
{
  "id": 1,
  "status": "completed",
  "user_request": "Build a todo API with Flask",
  "completed_phases": 4,
  "total_phases": 4,
  "execution_time_s": 45.2,
  "workspace_path": "/path/to/workspace/build-todo-api_20260329_120000",
  "total_prompt_tokens": 1200,
  "total_response_tokens": 3400,
  "total_agent_calls": 6
}
```

#### List Generated Files

```bash
curl http://localhost:8000/pipeline/1/artifacts
```

Response:
```json
{
  "run_id": 1,
  "files": ["app.py", "requirements.txt", "README.md", "tests/test_app.py"]
}
```

#### View Agent Metrics

```bash
curl http://localhost:8000/agents/metrics
```

Response:
```json
[
  {
    "agent_name": "planner",
    "model": "qwen2.5:3b",
    "total_calls": 5,
    "success_rate": 1.0,
    "avg_latency_ms": 2100.5,
    "total_prompt_tokens": 500,
    "total_response_tokens": 1200
  }
]
```

#### Real-Time Streaming (WebSocket)

```python
import asyncio
import websockets
import json

async def stream():
    async with websockets.connect("ws://localhost:8000/pipeline/1/stream") as ws:
        while True:
            msg = await ws.recv()
            event = json.loads(msg)
            print(f"[{event['type']}] {event['payload']}")
            if event["type"] == "pipeline.finished":
                break

asyncio.run(stream())
```

Events emitted: `pipeline.started`, `phase.started`, `phase.completed`, `test.failed`, `pipeline.finished`.

#### Download Generated Files

Generated workspace files are served as static files:

```
http://localhost:8000/artifacts/{project-name}_{timestamp}/app.py
```

---

## Building Projects via Dashboard

The Streamlit dashboard provides a visual interface for monitoring.

```bash
make dashboard
# Opens at http://localhost:8501
```

Pages:
- **Pipeline History** - Browse all past runs with status, timing, token usage
- **Agent Performance** - Charts for latency, success rate, token efficiency
- **Error Patterns** - Analyze failure types and correction rates
- **Live Run View** - Watch a pipeline execute in real-time

---

## Managing Pipeline Runs

### List All Runs

```bash
poetry run python -m src.cli list
```

Output:
```
  ID  Status        Phases     Time  Request                                   Workspace
--------------------------------------------------------------------------------------------------------------
   3  completed        4/  4    12.5s  Build a todo API with Flask                workspace/build-todo-api_20260329_120000
   2  failed           2/  4       -   Build a chat app                          workspace/build-chat-app_20260329_110000
   1  completed        4/  4     8.2s  Build a calculator                        workspace/build-calculator_20260329_100000
```

### View Run Details

```bash
poetry run python -m src.cli run-status 3
```

Output:
```
Pipeline Run #3
  Status:       completed
  Request:      Build a todo API with Flask
  Phases:       4/4
  Time:         12.5s
  Tokens:       1200 prompt / 3400 response
  Agent calls:  6
  Workspace:    workspace/build-todo-api_20260329_120000
  Git commit:   abc123def456
  Started:      2026-03-29 12:00:00
  Finished:     2026-03-29 12:00:12
```

### Resume a Failed Run

```bash
poetry run python -m src.cli resume 2
```

### Other CLI Commands

```bash
poetry run python -m src.cli info      # Show GPU information
poetry run python -m src.cli status    # Check system status (GPU, drivers)
poetry run python -m src.cli create "Build a REST API" --verbose  # Create with GPU monitoring
```

---

## Git Integration

When `--git` is passed (or `"git": true` in the API), the pipeline automatically:

1. Runs `git init` in the workspace output directory
2. Stages all generated files with `git add .`
3. Creates an initial commit: `Initial commit: {project-name}`
4. Stores the commit hash in the database (`PipelineRun.git_commit_hash`)

```bash
# CLI
make run TASK="Build an API" GIT=true

# API
curl -X POST http://localhost:8000/pipeline/run \
  -d '{"task": "Build an API", "git": true}'
```

Without `--git`, no git operations are performed.

---

## Plugins

Plugins run between the testing and documentation phases. They receive the full pipeline context and can audit or transform the generated code.

### Built-in Plugin: Security Auditor

The `plugins/security_auditor.py` plugin scans generated code for:
- `eval()` / `exec()` usage
- Hardcoded secrets (API keys, passwords, tokens)
- SQL injection patterns
- `pickle.load` deserialization risks
- `subprocess` with `shell=True`
- `yaml.load` without safe Loader
- Path traversal in `open()` calls

### Creating a Custom Plugin

Create a `.py` file in the `plugins/` directory:

```python
# plugins/my_linter.py
class MyLinter:
    name = "MyLinter"
    role = "quality"

    def execute(self, context: dict) -> dict:
        workspace_path = context["workspace_path"]
        plan = context["plan"]
        # ... your logic here ...
        return {"status": "pass", "findings": []}
```

Requirements:
- Class must have `name: str`, `role: str` attributes
- Class must have an `execute(self, context: dict) -> dict` method
- Context keys: `plan`, `execution_results`, `test_results`, `workspace_path`
- Return dict must have `status` ("pass" or "fail") and `findings` (list)

Plugins are auto-discovered on each pipeline run. No registration needed.

---

## Rust Performance Layer

Optional Rust modules provide faster JSON parsing, AST analysis, and Ollama connection pooling.

### Build

```bash
make rust-build    # Release build
make rust-test     # Run 31 Rust tests
```

### What It Accelerates

| Module | Purpose | Shared Lib |
|--------|---------|-----------|
| `ast_parser` | Python AST summarization via tree-sitter (~2.6x faster) | `libast_parser.so` |
| `json_parser` | JSON parse/serialize via serde_json | `libjson_parser.so` |
| `ollama_client` | HTTP connection pooling via reqwest | `libollama_client.so` |

### Graceful Fallback

If Rust modules are not compiled, everything falls back to pure Python automatically. No configuration needed.

### Verify Rust Integration

```bash
poetry run python -c "
from src.utils.performance_bridge import RustBridge
b = RustBridge()
print('Libraries:', list(b.lib_cache.keys()))
print(b.benchmark_modules())
"
```

---

## Fine-Tuning Your Models

After running several pipeline tasks, you can fine-tune the models on your own data.

```bash
# Full pipeline: export data -> train SFT -> train DPO -> export GGUF -> deploy -> evaluate
make finetune-all

# Or step by step:
make finetune-export     # Export training data from DB
make finetune-train      # SFT fine-tune (stop Ollama first!)
make finetune-dpo        # DPO training on correction data
make finetune-deploy     # Register in Ollama
make finetune-eval       # A/B comparison
```

Enable fine-tuned models:
```bash
export USE_FINETUNED_MODELS=true
make run TASK="Build a REST API"
```

---

## Docker Deployment

### Quick Start with Docker

```bash
# Build GPU-enabled image
make docker-build

# Start all services (Ollama + App)
make docker-up

# Create a project
make docker-create DESC="Build a REST API for user management"

# View logs
make docker-logs

# Stop
make docker-down
```

### Lightweight (No GPU)

```bash
make docker-build-lightweight
```

### Sandbox for Code Execution

```bash
make build-docker-sandbox
```

The tester agent runs generated code inside this sandbox for isolation.

---

## Configuration Reference

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_NUM_GPU` | `1` | Number of GPU layers |
| `OLLAMA_KEEP_ALIVE` | `0` | Model keep-alive (0 = unload immediately) |
| `OLLAMA_MAX_LOADED_MODELS` | `1` | Max models in VRAM simultaneously |
| `OLLAMA_NUM_PARALLEL` | `1` | Parallel request handling |
| `USE_FINETUNED_MODELS` | `false` | Use fine-tuned model variants |

### Model Roles

Edit `src/agents/base.py` to change model assignments:

| Role | Default Model | VRAM |
|------|--------------|------|
| `planner` | `qwen2.5:3b` | ~800 MB |
| `backend` | `qwen2.5-coder:3b` | ~800 MB |
| `frontend` | `qwen2.5-coder:1.5b` | ~500 MB |
| `tester` | `deepseek-coder:1.3b` | ~450 MB |
| `documenter` | `gemma2:2b` | ~600 MB |
| `rag` | `phi3:mini` | ~500 MB |

Only one model is loaded at a time. Total VRAM never exceeds ~800 MB.

### Database

SQLite at `software_house.db` (project root). Reset with:

```bash
make clean-db
```

### Workspace Output

Generated projects go to `workspace/{project-name}_{YYYYMMDD_HHMMSS}/`. Each run gets its own timestamped directory. Workspace is gitignored.

---

## Troubleshooting

### Ollama not running

```bash
# Check if Ollama is running
ollama list

# Start Ollama service
systemctl --user start ollama
# Or
ollama serve
```

### Out of VRAM

```bash
# Check current usage
nvidia-smi

# Set environment to minimize VRAM
export OLLAMA_KEEP_ALIVE=0
export OLLAMA_MAX_LOADED_MODELS=1

# Use smaller models in src/agents/base.py
# e.g., change "qwen2.5:3b" to "qwen2.5:1.5b"
```

### Pipeline stuck or slow

The pipeline runs models sequentially. Each phase waits for the previous one. Typical timing:
- Planning: 5-15 seconds
- Development: 10-60 seconds (depends on file count)
- Testing: 5-30 seconds (up to 3 correction attempts)
- Documentation: 5-15 seconds

### Tests failing

```bash
# Run with verbose output
make test

# Run a specific test
poetry run pytest tests/unit/test_api.py -v -k "test_name"

# Check Rust tests separately
make rust-test
```

### Rust modules not loading

```bash
# Rebuild
make rust-build

# Check shared libraries exist
ls -la src/rust/target/release/lib*.so

# Test Python bridge
poetry run python -c "from src.utils.performance_bridge import RustBridge; b = RustBridge(); print(b.lib_cache)"
```

### Database issues

```bash
# Reset database
make clean-db

# Re-initialize
poetry run python -c "from src.core.database import init_db; init_db()"
```

---

## Makefile Quick Reference

```bash
make help              # Show all available commands
make setup             # Full environment setup
make run TASK="..."    # Run pipeline
make run TASK="..." GIT=true  # Run with git init
make api               # Start FastAPI server (port 8000)
make dashboard         # Start Streamlit UI (port 8501)
make test              # Run all tests
make lint              # Check code quality
make format            # Auto-format code
make rust-build        # Build Rust modules
make rust-test         # Test Rust modules
make clean             # Clean temp files
make clean-db          # Reset database
```
