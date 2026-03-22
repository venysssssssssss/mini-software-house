# 🤖 Mini Software House

> **Autonomous Multi-Agent System for Full-Stack Software Development**

A local AI-powered "software house" that autonomously receives natural language requirements and executes a complete software development pipeline: planning → development → testing → documentation.

Optimized to run on consumer-grade GPUs (GTX 1050 Ti, 4GB VRAM).

---

## 🎯 Quick Start

### Prerequisites
- Python 3.12+
- Rust (for performance modules)
- 4GB+ VRAM (GPU recommended)
- Docker (optional, for sandboxing)

### 1. **Setup Environment**

```bash
# Run full setup (Python, Rust, Ollama models)
python scripts/setup/setup_environment.py

# Or check your current setup
bash scripts/setup/verify_setup.sh
```

### 2. **Download Models**

```bash
# Pull 7 optimized models for 4GB VRAM
bash scripts/setup/pull_models.sh
```

### 3. **Run Pipeline**

```bash
# Create a software house project
python src/main.py --task "Build a REST API for user management in Python with FastAPI"

# Resume from a previous state
python src/main.py --resume

# Monitor via dashboard
streamlit run app.py
```

---

## 📊 What It Does

### **5-Phase Pipeline**

1. **Planning** 🗓️  
   Breaks down requirements into architecture and specifications
   - Model: Qwen 2.5 3B
   - Output: Structured plan with tech stack

2. **Development** 💻  
   Generates complete source code (Python, Rust, frontend)
   - Models: Qwen Coder 3B (backend), 1.5B (frontend)
   - Output: Production-ready code with proper structure

3. **Testing** 🧪  
   Validates code, finds bugs, suggests fixes
   - Model: DeepSeek Coder 1.3B
   - Output: Passing test suite with coverage report

4. **Documentation** 📚  
   Auto-generates technical documentation
   - Model: Gemma 2 2B
   - Output: README, API docs, architecture diagrams

5. **Extras** ✨  
   Intelligent naming, portfolio generation, README enhancement
   - Portfolio HTML generation
   - Smart project naming engine
   - Live website static generation

---

## 🏗️ Project Structure

```
mini-software-house/
├── 📄 README.md (this file)
├── 📋 Makefile
├── 🔧 pyproject.toml & Cargo.toml
│
├── 📁 src/                          # Main application
│   ├── main.py                      # Entry point
│   ├── naming_engine.py             # Smart naming (450+ lines)
│   ├── html_generator.py            # Portfolio generator (500+ lines)
│   │
│   ├── 🤖 agents/                   # 6 specialized agents
│   │   ├── base.py                  # Base agent class
│   │   ├── orchestrator.py          # Central coordinator
│   │   ├── planner.py               # Requirement planner
│   │   ├── executor.py              # Code executor
│   │   ├── tester.py                # Test validator
│   │   ├── documenter.py            # Documentation
│   │   ├── rag.py                   # RAG engine
│   │   └── context_manager.py       # Context handling
│   │
│   ├── 🦀 rust/                     # Performance (6 modules)
│   │   ├── performance_core/        # Async executor
│   │   ├── json_parser/             # FFI parsing
│   │   ├── docker_log_streamer/     # Log filtering
│   │   ├── fs_watcher/              # File watcher
│   │   ├── ast_parser/              # AST analysis
│   │   └── ollama_client/           # Connection pooling
│   │
│   ├── 📦 core/                     # Infrastructure
│   │   ├── database.py              # SQLModel setup
│   │   ├── models.py                # Schema definitions
│   │   ├── events.py                # Event bus
│   │   └── logger.py                # Structured logging
│   │
│   └── 🔧 utils/
│       ├── docker_runner.py         # Container execution
│       └── __pycache__/
│
├── 📁 tests/                        # Test suite
│   ├── unit/                        # Unit tests
│   ├── integration/                 # Integration tests
│   └── conftest.py                  # Pytest fixtures
│
├── 📁 scripts/                      # Utilities
│   ├── benchmark.py                 # Performance testing
│   └── setup/                       # Setup scripts
│       ├── setup_environment.py     # Full environment setup
│       ├── pull_models.sh           # Download models
│       └── verify_setup.sh          # Validate installation
│
├── 📁 docs/                         # Documentation (organized by theme)
│   ├── INDEX.md                     # Navigation guide
│   ├── status/                      # Project status
│   ├── architecture/                # Design & roadmap
│   ├── setup/                       # Installation guides
│   ├── quickstart/                  # Quick reference
│   └── archive/                     # Legacy docs
│
├── 📁 workspace/                    # Build artifacts (gitignored)
│   ├── state.json                   # Pipeline state
│   ├── run.log                      # Execution logs
│   └── *.html                       # Generated portfolios
│
└── 🐋 Dockerfile.sandbox            # Container for sandboxing
```

For detailed structure breakdown, see [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md)

---

## ⚙️ Architecture

### **Stack**

| Layer | Technologies |
|-------|---|
| **Orchestration** | Python 3.12, FastAPI, Structlog |
| **LLM Backend** | Ollama (local), 7 models, 4GB optimized |
| **Database** | SQLite + SQLModel ORM |
| **Performance** | Rust (async/FFI), Tokio, PyO3 |
| **Sandbox** | Docker for code execution |
| **Dashboard** | Streamlit web UI |

### **Agent Types**

| Agent | Model | Purpose | VRAM |
|-------|-------|---------|------|
| **Planner** | Qwen 2.5 3B | Architecture design | 800MB |
| **Backend Dev** | Qwen Coder 3B | Python/API code | 800MB |
| **Frontend Dev** | Qwen Coder 1.5B | UI/Web generation | 500MB |
| **Tester** | DeepSeek 1.3B | Test generation | 450MB |
| **Documenter** | Gemma 2 2B | Docs/README | 600MB |
| **RAG** | Phi-3 Mini | Context retrieval | 500MB |

**Total: ~3.8GB VRAM** (fits in 4GB with optimizations)

---

## 📚 Documentation

Navigate documentation by use case:

| Need | Read |
|------|------|
| **First time?** | [docs/quickstart/README.md](docs/quickstart/RUST_QUICK_START.md) |
| **System status?** | [docs/status/SYSTEM_STATUS.md](docs/status/SYSTEM_STATUS.md) |
| **Setup guide?** | [docs/setup/CHECKLIST_SOFTWARE_HOUSE_1050TI.md](docs/setup/CHECKLIST_SOFTWARE_HOUSE_1050TI.md) |
| **Architecture?** | [docs/architecture/PRODUCT_ROADMAP.md](docs/architecture/PRODUCT_ROADMAP.md) |
| **Rust development?** | [docs/quickstart/RUST_QUICK_START.md](docs/quickstart/RUST_QUICK_START.md) |
| **All docs index** | [docs/INDEX.md](docs/INDEX.md) |

---

## 🚀 Common Tasks

### Run the Full Pipeline

```bash
python src/main.py --task "Build a Todo API with FastAPI and SQLAlchemy"
```

### Monitor Execution

```bash
streamlit run app.py
```

### Build Rust Modules

```bash
cd src/rust
cargo build --release
```

### Run Tests

```bash
make test
```

### Format Code

```bash
make format
```

### Benchmark Performance

```bash
python scripts/benchmark.py
```

---

## 🛠️ Development

### Setup Development Environment

```bash
# Clone repository
git clone <repo>
cd mini-software-house

# Run setup
python scripts/setup/setup_environment.py

# Enter Poetry shell
poetry shell

# Run tests
make test
```

### Development Workflow

```bash
# Make your changes to src/

# Format code
make format

# Run linter
make lint

# Test your changes
make test

# Commit
git add .
git commit -m "feat: description"
```

---

## 📊 Performance

### Optimization Techniques

- **4-bit quantization** - Reduce model size by 75%
- **VRAM caching** - Keep only active model in memory
- **Rust FFI** - 50-70% faster JSON parsing
- **Async I/O** - Non-blocking Ollama requests
- **Streaming** - Real-time output for logs

### Benchmarks

- JSON Parsing: **60-70% faster** (Rust vs Python)
- Docker log streaming: **50-60% faster** (Rust regex)
- Connection pooling: **30-40% throughput improvement**

See [docs/architecture/OPTIMIZATION_SUMMARY.md](docs/architecture/OPTIMIZATION_SUMMARY.md)

---

## 🐛 Troubleshooting

### Models not loading?

```bash
# Check Ollama status
ollama list

# Diagnose setup
bash scripts/setup/verify_setup.sh

# Manually pull a model
ollama pull qwen2.5:3b
```

### Out of memory errors?

```bash
# Check VRAM usage
nvidia-smi

# Reduce model size (edit src/agents/base.py)
# Use smaller models with : suffix (e.g., qwen2.5:1.5b)
```

### Docker errors?

```bash
# Build sandbox manually
docker build -t mini-sh-sandbox -f Dockerfile.sandbox .

# Test execution
docker run -it mini-sh-sandbox python --version
```

---

## 📝 Configuration

### Environment Variables

```bash
# .env (create in root)
OLLAMA_NUM_GPU=1
OLLAMA_KEEP_ALIVE=0
OLLAMA_MAX_LOADED_MODELS=1
OLLAMA_NUM_PARALLEL=1
SQLITE_DATABASE=software_house.db
```

### Model Selection

Edit `src/agents/base.py` `get_model_for_role()`:

```python
models = {
    "planner": "qwen2.5:3b",          # Change here
    "backend": "qwen2.5-coder:3b",    # Or here
    # ...
}
```

---

## 📄 License

This project is part of the Mini Software House research initiative.

---

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## 📞 Support

- **Status**: See [docs/status/](docs/status/)
- **Roadmap**: [docs/architecture/PRODUCT_ROADMAP.md](docs/architecture/PRODUCT_ROADMAP.md)
- **Issues**: GitHub Issues

---

**Last Updated**: March 2026  
**Tier 1 Status**: ✅ Complete  
**Tier 2 Status**: 🏗️ In Progress
