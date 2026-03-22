# 📐 Project Structure

Detailed breakdown of Mini Software House project organization.

---

## Root Level

```
mini-software-house/
├── README.md                    # Main project README (start here!)
├── CONTRIBUTING.md             # Contribution guidelines
├── Makefile                     # Common development tasks
├── pyproject.toml              # Python project config (Poetry)
├── poetry.lock                 # Locked Dependencies
├── Cargo.toml                  # Rust workspace config (root)
├── Cargo.lock                  # Locked Rust dependencies
├── Dockerfile.sandbox          # Docker image for sandboxing
└── .gitignore                  # Git ignore rules
```

---

## `src/` - Main Application

The heart of the system. Contains all business logic, agents, and utilities.

```
src/
├── __init__.py                                # Package marker
├── main.py                                   # CLI Entry point
│   ├── Argument parsing (argparse)
│   ├── Pipeline orchestration
│   ├── State management (JSON)
│   └── Exit handlers
│
├── naming_engine.py                          # Smart project naming (450+ lines)
│   ├── Naming patterns engine
│   ├── Context-aware suggestions
│   └── Portfolio naming integration
│
├── html_generator.py                         # Portfolio HTML generation (500+ lines)
│   ├── Template rendering
│   ├── CSS styling generation
│   └── Asset management
│
├── demo.py                                   # Demo/example script
│
├── agents/                                   # 6 Specialized AI Agents
│   ├── __init__.py
│   ├── base.py                              # Base Agent class (core)
│   │   ├── Model router (get_model_for_role)
│   │   ├── Chat history
│   │   ├── Logging setup
│   │   ├── Message handling
│   │   └── VRAM optimization
│   │
│   ├── orchestrator.py                      # Central Coordinator (implements pipeline)
│   │   ├── Phase 1→5 execution
│   │   ├── Error handling & retries
│   │   ├── Agent lifecycle
│   │   └── State persistence
│   │
│   ├── planner.py                           # Planning Agent
│   │   ├── Task breakdown
│   │   ├── Architecture design
│   │   ├── Tech stack selection
│   │   └── Specification generation
│   │
│   ├── executor.py                          # Development Agent
│   │   ├── Code generation
│   │   ├── Multiple languages (Python, JS, Rust)
│   │   ├── Project structure creation
│   │   └── File writing
│   │
│   ├── tester.py                            # Testing Agent
│   │   ├── Test generation
│   │   ├── Test execution
│   │   ├── Coverage analysis
│   │   ├── Bug detection
│   │   └── Auto-correction
│   │
│   ├── documenter.py                        # Documentation Agent
│   │   ├── README generation
│   │   ├── API documentation
│   │   ├── Code comments
│   │   └── Architecture docs
│   │
│   ├── rag.py                               # RAG (Retrieval-Augmented Generation)
│   │   ├── ChromaDB integration
│   │   ├── Embedding generation
│   │   ├── Similarity search
│   │   ├── Context retrieval
│   │   └── Knowledge base management
│   │
│   ├── context_manager.py                   # Context Management
│   │   ├── AST parsing
│   │   ├── Code complexity analysis
│   │   ├── File context extraction
│   │   └── Memory optimization
│   │
│   ├── Cargo.toml                          # Rust interop config
│   └── main.rs                             # Rust integration point
│
├── rust/                                    # Performance Optimization Layer (6 modules)
│   ├── Cargo.toml                          # Workspace root (defines members)
│   ├── Cargo.lock                          # Locked dependencies
│   │
│   ├── performance_core/                   # Async task executor
│   │   ├── Cargo.toml
│   │   ├── src/lib.rs
│   │   └── Tokio-based async processing
│   │
│   ├── json_parser/                        # High-performance JSON parsing
│   │   ├── Cargo.toml
│   │   ├── src/lib.rs
│   │   └── C FFI bindings, serde
│   │
│   ├── docker_log_streamer/                # Log filtering & streaming
│   │   ├── Cargo.toml
│   │   ├── src/lib.rs
│   │   └── Regex-based log filtering
│   │
│   ├── fs_watcher/                         # File system watcher
│   │   ├── Cargo.toml
│   │   ├── src/lib.rs
│   │   └── Real-time file monitoring
│   │
│   ├── ast_parser/                         # Python AST analysis
│   │   ├── Cargo.toml
│   │   ├── src/lib.rs
│   │   └── Complexity estimation
│   │
│   ├── ollama_client/                      # Connection pooling
│   │   ├── Cargo.toml
│   │   ├── src/lib.rs
│   │   └── HTTP pooling to Ollama
│   │
│   └── target/                             # Build artifacts
│       ├── release/                        # Production binaries & .so files
│       ├── debug/                          # Debug builds
│       └── build/                          # Build metadata
│
├── core/                                    # Infrastructure & Database Layer
│   ├── __init__.py                         # Exports: init_db, get_session, etc.
│   │
│   ├── database.py                         # Database Setup
│   │   ├── SQLAlchemy engine creation
│   │   ├── Session factory
│   │   └── Migration helpers
│   │
│   ├── models.py                           # SQLModel Schemas
│   │   ├── Project model
│   │   ├── Task model (with status enum)
│   │   ├── AgentLog model
│   │   └── Relationships
│   │
│   ├── events.py                           # Pub/Sub Event Bus
│   │   ├── Event dataclass
│   │   ├── EventBus singleton
│   │   ├── Subscribe/publish methods
│   │   └── Event history
│   │
│   └── logger.py                           # Structured Logging
│       ├── Structlog configuration
│       ├── Console/JSON rendering
│       └── Logger factory
│
└── utils/                                   # Utilities
    ├── __init__.py
    ├── docker_runner.py                    # Docker container execution
    │   ├── Image building
    │   ├── Container lifecycle
    │   └── Output capturing
    │
    └── __pycache__/                        # Python cache (gitignored)
```

---

## `tests/` - Test Suite

Properly organized testing structure following pytest conventions.

```
tests/
├── __init__.py                 # Test package marker
├── conftest.py                 # Pytest fixtures & configuration
│   ├── test_project_root fixture
│   ├── temp_workspace fixture
│   └── Path setup
│
├── unit/                       # Unit tests
│   ├── __init__.py
│   ├── test_agents.py          # Agent tests (unit)
│   ├── test_core.py            # Core module tests
│   ├── test_naming.py          # Naming engine tests
│   └── test_html.py            # HTML generator tests
│
└── integration/                # Integration tests
    ├── __init__.py
    ├── test_pipeline.py        # Full pipeline integration
    ├── test_agents_together.py # Multi-agent integration
    └── test_docker.py          # Docker sandbox tests
```

---

## `docs/` - Documentation

Centralized, well-organized documentation by category.

```
docs/
├── INDEX.md                    # Navigation guide (start here!)
│
├── status/                     # Project Status
│   ├── SYSTEM_STATUS.md        # Overall system status
│   ├── TIER1_COMPLETE.md       # Tier 1 completion status
│   ├── IMPLEMENTATION_COMPLETE.md  # Rust implementation
│   └── RUST_STATUS.md          # Rust module status
│
├── architecture/               # Design & Strategy
│   ├── PRODUCT_ROADMAP.md      # 4-phase development roadmap
│   ├── PERFORMANCE_OPTIMIZATION_PLAN.md  # Optimization strategy
│   └── OPTIMIZATION_SUMMARY.md # Summarized optimizations
│
├── setup/                      # Installation & Configuration
│   ├── CHECKLIST_SOFTWARE_HOUSE_1050TI.md  # Setup checklist
│   └── README_VRAM_OPTIMIZATION.md          # VRAM constraints
│
├── quickstart/                 # Quick Reference & Guides
│   ├── RUST_QUICK_START.md     # Rust 4-week roadmap
│   ├── WEBPAGE_QUICKSTART.md   # Portfolio generator guide
│   └── dev_plan.md             # Development phases
│
└── archive/                    # Legacy/Deprecated Docs
    └── (retired documentation)
```

---

## `scripts/` - Build & Utility Scripts

Automation and convenience scripts for development.

```
scripts/
├── benchmark.py                # Performance benchmarking
│   ├── Python vs Rust comparison
│   ├── Model loading speed
│   └── Results JSON export
│
└── setup/                      # Setup & Installation Scripts
    ├── setup_environment.py    # Full environment setup (refactored)
    │   ├── System requirements check
    │   ├── Python environment setup
    │   ├── Rust compilation
    │   ├── Ollama configuration
    │   └── Model downloading
    │
    ├── pull_models.sh          # Download optimized models (refactored)
    │   ├── 7 models for 4GB VRAM
    │   └── Progress tracking
    │
    └── verify_setup.sh         # Validation script (refactored)
        ├── Component verification
        ├── Module checking
        ├── Model validation
        └── Setup completeness report
```

---

## `workspace/` - Generated Build Artifacts

Dynamic directory created during pipeline execution (gitignored).

```
workspace/
├── state.json                  # Pipeline execution state
│   ├── current phase
│   ├── plan
│   ├── retries
│   └── metadata
│
├── run.log                     # Execution log file
│   ├── Agent operations
│   ├── Timestamps
│   └── Error traces
│
└── *.html                      # Generated portfolios
    ├── portfolio.html          # Master portfolio
    ├── api_python_db.html
    ├── javascript_dashboard.html
    ├── ml_engine.html
    ├── pipeline_python.html
    └── service_rust_async.html
```

---

## Key Files at Root

| File | Purpose |
|------|---------|
| `README.md` | Main project README (you should read this) |
| `Makefile` | Development tasks (make test, make lint, etc.) |
| `pyproject.toml` | Python dependencies & project metadata |
| `Cargo.toml` | Rust workspace configuration |
| `Dockerfile.sandbox` | Sandbox environment for code execution |
| `.gitignore` | Git ignore rules |

---

## Entry Points

### CLI
```bash
python src/main.py --task "Your task here"
```

### Web Dashboard
```bash
streamlit run app.py
```

### Rust Utilities
```bash
cd src/rust
cargo build --release
```

---

## Import Hierarchy

```
src/
├── main.py              (CLI entry, uses orchestrator)
├── app.py               (Dashboard, uses state.json)
├── agents/
│   ├── orchestrator     (coordinates agents)
│   ├── planner          (uses models from base)
│   ├── executor         ↓       (uses models from base)
│   ├── tester           ↓       (uses models from base)
│   ├── documenter       ↓       (uses models from base)
│   └── base             ←────── (core agent logic)
│
└── core/
    ├── database         (models)
    ├── models           ←── (defines ORM models)
    ├── events
    └── logger
```

---

## File Count Summary

- **Python files**: 20+
- **Rust files**: 12+ (6 modules)
- **Documentation**: 13 markdown files
- **Tests**: Structure ready (fixtures in place)
- **Total organized LOC**: ~5,000+

---

## Organization Principles

✅ **Separation of Concerns**: Agents, infrastructure, utils clearly separated
✅ **Scala bility**: New agents easily added to `src/agents/`
✅ **Testability**: Tests directory mirrors source structure
✅ **Documentation**: Centralized in `/docs` with clear navigation  
✅ **Setup**: All setup scripts consolidated in `/scripts/setup/`
✅ **Performance**: Rust modules isolated and cleanly integrated

