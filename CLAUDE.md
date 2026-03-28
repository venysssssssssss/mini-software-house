# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

Mini Software House is an AI-powered software development pipeline that uses multiple specialized Ollama agents (planner, executor, tester, documenter, RAG) orchestrated to generate complete software projects. It targets GTX 1050 Ti (4GB VRAM) with small quantized models.

## Common Commands

<!-- AUTO-GENERATED: from Makefile -->

| Command | Description |
|---------|-------------|
| `make install` | Install Python deps (Poetry) |
| `make test` | Run all tests (unit + integration) with coverage |
| `make test-unit` | Unit tests only |
| `make test-integration` | Integration tests |
| `make lint` | Ruff check |
| `make format` | Ruff format + fix |
| `make rust-build` | Build Rust modules (release) |
| `make rust-test` | Test Rust modules |
| `make run TASK="desc"` | Run the pipeline with a task |
| `make resume` | Resume from last pipeline state |
| `make dashboard` | Start Streamlit UI (port 8501) |
| `make build-docker-sandbox` | Build Docker sandbox image |
| `make benchmark` | Run performance benchmarks |
| `make clean` | Clean temporary files and caches |
| `make clean-db` | Remove database |
| `make setup` | Full environment setup (Python, Rust, Ollama) |
| `make verify` | Verify setup completeness |
| `make finetune-export` | Export training data from DB to JSONL |
| `make finetune-train` | SFT fine-tune all priority agents |
| `make finetune-dpo` | DPO fine-tune agents with correction data |
| `make finetune-export-gguf` | Convert fine-tuned models to GGUF |
| `make finetune-deploy` | Register fine-tuned models in Ollama |
| `make finetune-eval` | Evaluate fine-tuned models (A/B comparison) |
| `make finetune-all` | Full fine-tuning pipeline (export -> train -> deploy -> eval) |

<!-- /AUTO-GENERATED -->

Run a single test: `poetry run pytest tests/unit/test_models.py -v -k "test_name"`

First-time setup: `python scripts/setup/setup_environment.py` (installs Python, Rust, pulls Ollama models). Verify with `bash scripts/setup/verify_setup.sh`.

## Architecture

**Entry points:** `src/main.py` (CLI with `--task`, `--resume`, `--max-retries` flags), `app.py` (Streamlit dashboard with 4 pages: Pipeline History, Agent Performance, Error Patterns, Live Run View)

**Agent pipeline** (`src/agents/`): The orchestrator (`orchestrator.py`) runs a 4-phase pipeline coordinating specialized agents. All agents inherit from `Agent` base class in `base.py`, which handles Ollama chat, logging, metrics collection, and model routing via `get_model_for_role()`. Each role maps to a specific small model (e.g., planner->qwen2.5:3b, backend->qwen2.5-coder:3b).

- `orchestrator.py` — Pipeline coordinator; creates PipelineRun in DB, flushes agent metrics per phase, saves DPO tuples for self-healing corrections
- `executor.py` — Code generation; multi-file context passing (includes AST summaries of prior files), plan-aware prompts, project subdirectory naming
- `tester.py` — Test generation and execution; error classification (ImportError, SyntaxError, etc.), targeted correction prompts, hallucination guard (>80% change rejection)
- `planner.py` — Task decomposition into architecture + file list (JSON mode)
- `documenter.py` — README/docs generation via RAG
- `context_manager.py` — AST-based code summarization (uses Rust tree-sitter when available, falls back to Python ast)
- `base.py` — Agent base class with `AgentCallMetrics` capturing prompt_tokens, response_tokens, latency_ms, success per LLM call

**Core infrastructure** (`src/core/`): Database (SQLModel/SQLAlchemy), ORM models (Project, Task, AgentLog, PipelineRun, DPOTuple), pub/sub EventBus, structured logging (structlog).

**Rust performance layer** (`src/rust/`): Six crates in a Cargo workspace. `ast_parser` is fully integrated with tree-sitter Python grammar and C FFI (`ast_summarize_python`, `ast_summarize_python_json`, `ast_free_string`). Other crates (`performance_core`, `json_parser`, `docker_log_streamer`, `fs_watcher`, `ollama_client`) are stubs for Sprint 3.

**Performance bridge** (`src/utils/performance_bridge.py`): Python FFI wrapper for Rust crates. `RustASTParser` loads `libast_parser.so` via ctypes. `ContextManager` uses Rust AST when available (~2.6x faster than Python ast).

**Fine-tuning pipeline** (`scripts/finetune/`): Data flywheel that exports pipeline data, fine-tunes models, and deploys them back into Ollama. Scripts: `export_training_data.py` (SQLite → SFT/DPO JSONL), `train_sft.py` (QLoRA SFT via Unsloth), `train_dpo.py` (DPO on SFT adapters), `export_gguf.py` (LoRA merge + GGUF Q4_K_M export), `evaluate.py` (A/B metrics comparison). Ollama Modelfiles in `modelfiles/`. Toggle via `USE_FINETUNED_MODELS=true` env var.

**Pipeline output** goes to `workspace/{project_name}/` (gitignored) — state.json, logs, and generated code.

## Database Models

| Model | Purpose |
|-------|---------|
| `Project` | Groups pipeline runs by name/path |
| `Task` | Tracks individual pipeline tasks (PENDING -> IN_PROGRESS -> COMPLETED/FAILED) |
| `PipelineRun` | One row per `make run` — links project+task, tracks token totals, phase progress, timing |
| `AgentLog` | Per-LLM-call metrics: agent_name, model, prompt_tokens, response_tokens, latency_ms, success |
| `DPOTuple` | Data flywheel: prompt, generated_code, test_result, corrected_code, error_type, correction_successful |

## Key Constraints

- All model selections are optimized for 4GB VRAM — do not swap in larger models without checking `get_model_for_role()` in `src/agents/base.py`
- Rust crates are built from `src/rust/` (not repo root) — the root `Cargo.toml` is a workspace pointer
- Python managed by Poetry; Rust managed by Cargo — these are independent build systems
- Docker setup supports GPU passthrough via `docker-compose.gpu.yml`
- Tests use `conftest.py` which adds `src/` to `sys.path` — imports in source use relative imports (e.g., `from .agents.executor import ExecutorAgent`)
- Environment variables for Ollama tuning: `OLLAMA_NUM_GPU=1`, `OLLAMA_KEEP_ALIVE=0`, `OLLAMA_MAX_LOADED_MODELS=1`, `OLLAMA_NUM_PARALLEL=1`
- Database: SQLite at `software_house.db` (gitignored); pipeline state at `workspace/state.json`
- Executor creates workspace subdirectories using the plan's `project_name` (e.g., `workspace/build-todo-api/`)
- Tester hallucination guard rejects code corrections that change >80% of the original file
- `USE_FINETUNED_MODELS=true` enables fine-tuned model variants (planner-ft, executor-ft, tester-ft, documenter-ft); default is `false` (base models)
- Fine-tuning scripts lazy-import ML deps (unsloth, trl, torch) — they are not required at module level

## Test Suite

- **252 Python tests** (unit + integration), all passing
- **9 Rust tests** (ast_parser crate), all passing
- **98% coverage** on finetune modules; 83% on agents + core
- Run: `make test` (all), `make test-unit`, `make test-integration`, `make rust-test`
- Key test patterns: mocked Ollama via `@patch("src.agents.base.ollama")`, in-memory SQLite for DB isolation, `tmp_path` for workspace files, mocked ML imports via `builtins.__import__` monkeypatching for GPU-dependent code

## Sprint Status

- **Sprint 1** (Stability): Complete -- core infra wired, 82 tests, CI
- **Sprint 2** (Intelligence): Complete -- metrics, dashboard v2, executor improvements, tester self-healing, Rust ast_parser FFI, 120 tests
- **Sprint FT** (Fine-Tuning): Complete -- data export pipeline, SFT/DPO training scripts, GGUF export, Ollama Modelfiles, evaluation harness, Makefile automation, 252 tests
- **Sprint 3** (Experience): Not started -- FastAPI, Git integration, project isolation, plugins
