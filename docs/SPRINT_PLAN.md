# 3-Sprint Improvement Plan — Mini Software House

**Created:** 2026-03-28
**Status:** Planning
**Estimated Duration:** 3 sprints (~2 weeks each)

---

## Current State Assessment

| Area | Status | Gap |
|------|--------|-----|
| **Agent pipeline** | Functional, end-to-end works | Orchestrator ignores EventBus & DB (uses dicts + print) |
| **Core infra** (DB, EventBus, Logger) | Implemented but **not wired** | Orchestrator bypasses all of it |
| **Tests** | **0 unit, 0 integration** | conftest.py only; empty test dirs |
| **CI/CD** | None | No GitHub Actions, no automation |
| **Rust crates** | 6 defined, ast_parser has code, rest are stubs | performance_bridge.py falls back to Python for everything |
| **Dashboard** | 38-line Streamlit placeholder | Reads state.json, no real metrics |
| **Roadmap phases 4-5** | Not started | Data flywheel, FastAPI+WS, Git integration |

---

## Sprint 1 — "Wire It Up & Prove It Works" (Stability)

**Goal:** Connect the existing infrastructure that's built but unused, and add test coverage so refactoring is safe.

### 1.1 Wire Orchestrator to Core Infrastructure

- **Replace `print()` logging with `structlog`** — `logger.py` exists, orchestrator still uses `print()`+colorama
- **Emit events through EventBus** — `events.py` is implemented with pub/sub but orchestrator never publishes events. Add `pipeline.started`, `phase.completed`, `test.failed`, `pipeline.finished` events
- **Persist pipeline runs to SQLite** — `models.py` has `Project`, `Task`, `AgentLog` schemas that are never written to. Record each run, each phase result, each agent call

### 1.2 Unit Tests for Core Modules

- `tests/unit/test_events.py` — EventBus subscribe, publish, wildcard, history
- `tests/unit/test_models.py` — SQLModel schemas create/read/query
- `tests/unit/test_database.py` — Session lifecycle, concurrent access
- `tests/unit/test_logger.py` — Structlog output format, JSON mode

### 1.3 Unit Tests for Agents (mocked Ollama)

- `tests/unit/test_base_agent.py` — Chat history rotation (10-msg cap), model routing via `get_model_for_role()`
- `tests/unit/test_executor.py` — `parse_and_save_code()` with various markdown formats, filepath extraction, security check (path traversal)
- `tests/unit/test_planner.py` — JSON plan structure validation
- `tests/unit/test_tester.py` — `parse_error()`, Docker fallback behavior
- `tests/unit/test_context_manager.py` — AST extraction of function signatures

### 1.4 Integration Test

- `tests/integration/test_pipeline.py` — Full pipeline with a mock Ollama server returning canned responses. Validates: plan -> execute -> test -> document flow, state persistence, event emission

### 1.5 CI/CD

- `.github/workflows/ci.yml` — On push/PR: `make lint` -> `make test-unit` -> `make rust-build` -> `make rust-test`
- Add `pytest-cov` to dev deps, enforce minimum coverage threshold (60% for sprint 1)

### 1.6 Code Quality Baseline

- Run `ruff check --fix` and `ruff format` on all Python files
- Add `[tool.ruff]` config to `pyproject.toml` if missing
- Fix any lint violations currently in the codebase

**Deliverables:**

- [x] Orchestrator uses structlog, EventBus, and DB for every pipeline run
- [x] 76 unit tests + 6 integration tests, all green (82 total)
- [x] CI pipeline running on push (.github/workflows/ci.yml)
- [x] `make test` produces a coverage report

---

## Sprint 2 — "Make It Smart" (Quality & Observability)

**Goal:** Improve the output quality of generated code and build the data flywheel (Roadmap Phase 4).

### 2.1 Agent Metrics Collection (Data Flywheel)

- On every agent call, log to `AgentLog` table: `{agent_name, model, prompt_tokens, response_tokens, latency_ms, success}`
- Save DPO tuples: `{prompt, generated_code, test_result, corrected_code}` per Roadmap 4.1
- Add a `PipelineRun` model linking all artifacts for a single `make run` invocation

### 2.2 Streamlit Dashboard v2

- Replace the 38-line placeholder with real pages:
  - **Pipeline history** — list of runs from DB, status, duration, success rate
  - **Agent performance** — avg latency, first-pass success rate per agent, model used
  - **Error patterns** — most common test failures (parsed from `AgentLog`)
  - **Live run view** — subscribe to EventBus, show real-time phase progress

### 2.3 Executor Improvements

- **Multi-file context passing** — when generating file N, include summaries (via ContextManager) of files 1..N-1 so the LLM knows what already exists
- **Plan-aware prompts** — pass the full plan structure (architecture, dependencies) to each file generation call, not just a string description
- **Smarter fallback naming** — use plan's `project_name` for workspace subdir instead of flat `workspace/`

### 2.4 Tester Self-Healing Improvements

- Parse specific error types (ImportError, SyntaxError, NameError) and generate targeted correction prompts instead of dumping the entire error
- Track correction success rate in DB — which error types self-heal vs which always exhaust retries
- Add a validation step: after correction, diff the old and new code and reject if >80% changed (hallucination guard)

### 2.5 Rust: Complete ast_parser + Python FFI

- Finish the `ast_parser` crate using tree-sitter (it already has partial implementation)
- Wire it through `performance_bridge.py` so `ContextManager` uses Rust AST parsing when available
- Benchmark: Python `ast` module vs Rust tree-sitter on the generated workspace files
- Add Rust unit tests (`cargo test`) for ast_parser

### 2.6 Tests

- Unit tests for all new metrics/collection code
- Unit tests for improved executor context passing
- Integration test: run pipeline, then query dashboard endpoints and verify data
- Target: 75% coverage

**Deliverables:**

- [x] Every pipeline run produces structured data in SQLite
- [x] Dashboard shows actionable metrics from real runs
- [x] Executor produces better code (multi-file awareness)
- [x] Rust ast_parser integrated and benchmarked
- [x] Test coverage at 75%+ (83% on agents+core)

---

## Sprint 3 — "Developer Experience" (Roadmap Phase 5)

**Goal:** Make the system usable as a real tool — real-time UI, Git integration, and project isolation.

### 3.1 FastAPI Backend

- New `src/api/` module with FastAPI app
- REST endpoints: `POST /pipeline/run`, `GET /pipeline/{id}/status`, `GET /pipeline/{id}/artifacts`, `GET /agents/metrics`
- WebSocket endpoint: `WS /pipeline/{id}/stream` — push EventBus events to connected clients in real-time
- Replace Streamlit as the primary UI backend (keep Streamlit as optional read-only dashboard)

### 3.2 Git Integration for Generated Projects

- Per Roadmap 5.2: after pipeline completes, initialize a git repo in the workspace output
- Create an initial commit with all generated files
- Optional: if a Gitea/GitLab URL is configured, push and create a PR
- Add `--git` flag to CLI: `make run TASK="..." GIT=true`

### 3.3 Project Isolation

- Each pipeline run gets its own workspace subdirectory: `workspace/{project_name}_{timestamp}/`
- Separate state.json per project (or just use DB, remove state.json entirely)
- List/resume past projects: `python -m src.cli list`, `python -m src.cli resume <project-id>`

### 3.4 Rust: Complete ollama_client + json_parser

- **ollama_client**: Connection pooling with reqwest, expose via FFI so Python agents can optionally use it for faster inference calls
- **json_parser**: simd-json based parsing for LLM responses, wire through performance_bridge.py
- Benchmark both against pure Python equivalents
- Graceful fallback remains (Python works if Rust isn't compiled)

### 3.5 Plugin Architecture for Agents

- Define an `AgentPlugin` protocol/ABC with `name`, `role`, `execute(context) -> result`
- Allow loading custom agents from a `plugins/` directory or via config
- Example: a `SecurityAuditor` agent that runs after executor, checks for common vulnerabilities in generated code

### 3.6 Tests & Documentation

- E2E test: API -> pipeline -> WebSocket events -> artifacts -> Git repo
- Load test: 3 concurrent pipeline runs (verify no VRAM contention, proper queuing)
- Update all docs to reflect new API, CLI flags, and architecture
- Target: 85% coverage

**Deliverables:**

- [ ] FastAPI server with WebSocket real-time streaming
- [ ] Generated projects auto-committed to Git
- [ ] Isolated project workspaces with history
- [ ] 2 more Rust crates integrated and benchmarked
- [ ] Plugin system for custom agents
- [ ] 85%+ test coverage

---

## Sprint Summary

| Sprint | Theme | Key Outcome | Coverage Target |
|--------|-------|-------------|-----------------|
| **S1** | Stability | Core infra wired, tests exist, CI runs | 60% |
| **S2** | Intelligence | Data flywheel, better code gen, metrics dashboard | 75% |
| **S3** | Experience | Real-time API, Git integration, project isolation | 85% |

### Dependencies Between Sprints

```
S1: Tests + CI + Wiring
 └── S2: Metrics + Dashboard + Executor improvements (needs DB/EventBus from S1)
      └── S3: FastAPI + Git + Plugins (needs metrics/API patterns from S2)
```

S1 is non-negotiable — everything after it depends on having tests and the core infrastructure actually connected. S2 and S3 can have items shuffled between them based on priorities.

---

## Relationship to Existing Roadmap

| Roadmap Phase | Sprint Coverage |
|---------------|-----------------|
| Phase 1-3 (done) | S1 finishes wiring what was built |
| Phase 4: Data Flywheel | S2 (metrics collection, DPO tuples, dashboard) |
| Phase 5: Developer Experience | S3 (FastAPI+WS, Git integration) |
