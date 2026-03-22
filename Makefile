.PHONY: help install build test lint format clean rust-build rust-clean run setup verify

# Color output
BLUE=\033[0;34m
GREEN=\033[0;32m
YELLOW=\033[1;33m
NC=\033[0m # No Color

help: ## Show this help message
	@echo "$(BLUE)=== Mini Software House - Makefile ===$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(YELLOW)Examples:$(NC)"
	@echo "  make help          # Show this help"
	@echo "  make install       # Setup environment"
	@echo "  make test          # Run all tests"
	@echo "  make run TASK=\"...\" # Run pipeline with task"

# Setup & Installation
setup: ## Full environment setup (Python, Rust, Ollama)
	@echo "$(BLUE)Setting up environment...$(NC)"
	python scripts/setup/setup_environment.py

verify: ## Verify setup completeness
	@echo "$(BLUE)Verifying setup...$(NC)"
	bash scripts/setup/verify_setup.sh

pull-models: ## Download optimized Ollama models
	@echo "$(BLUE)Pulling models...$(NC)"
	bash scripts/setup/pull_models.sh

install: ## Install Python dependencies
	@echo "$(BLUE)Installing Python dependencies...$(NC)"
	poetry install

# Development
run: ## Run the pipeline (use: make run TASK="description")
	@if [ -z "$(TASK)" ]; then \
		echo "$(YELLOW)Error: TASK not specified$(NC)"; \
		echo "Usage: make run TASK=\"Your task description\""; \
		exit 1; \
	fi
	@echo "$(BLUE)Running pipeline: $(TASK)$(NC)"
	poetry run python src/main.py --task "$(TASK)"

resume: ## Resume from last pipeline state
	@echo "$(BLUE)Resuming pipeline...$(NC)"
	poetry run python src/main.py --resume

dashboard: ## Start Streamlit dashboard
	@echo "$(BLUE)Starting dashboard at http://localhost:8501$(NC)"
	streamlit run app.py

# Testing
test: ## Run all tests (unit + integration)
	@echo "$(BLUE)Running tests...$(NC)"
	poetry run pytest tests/ -v --tb=short

test-unit: ## Run unit tests only
	@echo "$(BLUE)Running unit tests...$(NC)"
	poetry run pytest tests/unit/ -v --tb=short

test-integration: ## Run integration tests
	@echo "$(BLUE)Running integration tests...$(NC)"
	poetry run pytest tests/integration/ -v --tb=short

test-watch: ## Run tests and watch for changes
	@echo "$(BLUE)Running tests in watch mode...$(NC)"
	poetry run ptw tests/ -v

# Code Quality
lint: ## Run linter (ruff check)
	@echo "$(BLUE)Linting code...$(NC)"
	poetry run ruff check src/ tests/ scripts/

format: ## Format code (ruff format + isort)
	@echo "$(BLUE)Formatting code...$(NC)"
	poetry run ruff format src/ tests/ scripts/
	poetry run ruff check --fix src/ tests/ scripts/

format-check: ## Check formatting without changing files
	@echo "$(BLUE)Checking format...$(NC)"
	poetry run ruff format --check src/ tests/ scripts/

# Rust Development
rust-build: ## Build Rust modules (release)
	@echo "$(BLUE)Building Rust modules...$(NC)"
	cd src/rust && cargo build --release
	@echo "$(GREEN)✓ Rust build complete$(NC)"

rust-build-debug: ## Build Rust modules (debug)
	@echo "$(BLUE)Building Rust modules (debug)...$(NC)"
	cd src/rust && cargo build
	@echo "$(GREEN)✓ Rust build complete$(NC)"

rust-test: ## Test Rust modules
	@echo "$(BLUE)Testing Rust modules...$(NC)"
	cd src/rust && cargo test --release
	@echo "$(GREEN)✓ Rust tests complete$(NC)"

rust-clean: ## Clean Rust build artifacts
	@echo "$(BLUE)Cleaning Rust artifacts...$(NC)"
	cd src/rust && cargo clean

rust-doc: ## Generate Rust documentation
	@echo "$(BLUE)Generating Rust documentation...$(NC)"
	cd src/rust && cargo doc --release --open

# Build
build: rust-build ## Build all components (Python + Rust)
	@echo "$(GREEN)✓ Build complete$(NC)"

build-docker-sandbox: ## Build Docker sandbox image
	@echo "$(BLUE)Building Docker sandbox...$(NC)"
	docker build -t mini-sh-sandbox -f Dockerfile.sandbox .
	@echo "$(GREEN)✓ Docker image built$(NC)"

# Benchmarking
benchmark: ## Run performance benchmarks
	@echo "$(BLUE)Running benchmarks...$(NC)"
	poetry run python scripts/benchmark.py

# Cleaning
clean: ## Clean temporary files and caches
	@echo "$(BLUE)Cleaning temporary files...$(NC)"
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete
	rm -rf workspace/state.json workspace/run.log 2>/dev/null || true
	@echo "$(GREEN)✓ Cleaned$(NC)"

clean-all: clean rust-clean ## Clean everything including build artifacts
	@echo "$(GREEN)✓ Full clean complete$(NC)"

clean-db: ## Remove database
	@echo "$(BLUE)Removing database...$(NC)"
	rm -f software_house.db
	@echo "$(GREEN)✓ Database removed$(NC)"

# Docker (Full Suite)
docker-build: ## Build Docker image with GPU support
	@echo "$(BLUE)Starting Docker build...$(NC)"
	@echo "Note: First build downloads ~1.3GB CUDA base image (5-10 minutes)"
	@echo ""
	docker build -t mini-software-house:latest .
	@echo "$(GREEN)✓ Build complete$(NC)"

docker-build-lightweight: ## Build lightweight Docker image (no GPU, faster)
	@echo "$(BLUE)Building lightweight image...$(NC)"
	docker build -t mini-software-house:lightweight -f Dockerfile.lightweight .
	@echo "$(GREEN)✓ Lightweight build complete$(NC)"

docker-build-helper: ## Interactive build helper (choose options)
	@bash scripts/docker-build-helper.sh

docker-up: ## Start all services (Ollama, PostgreSQL, Redis, App)
	@echo "$(BLUE)Starting services...$(NC)"
	docker-compose -f docker-compose.yml up -d
	@echo "$(GREEN)✓ Services started$(NC)"

docker-down: ## Stop all services
	@echo "$(BLUE)Stopping services...$(NC)"
	docker-compose -f docker-compose.yml down

docker-logs: ## Stream logs from all services
	@echo "$(BLUE)Streaming logs...$(NC)"
	docker-compose -f docker-compose.yml logs -f

docker-shell: ## Open shell in running app container
	@echo "$(BLUE)Opening shell...$(NC)"
	docker-compose -f docker-compose.yml exec app /bin/bash

docker-create: ## Create project in Docker (use: make docker-create DESC="...")
	@if [ -z "$(DESC)" ]; then \
		echo "$(YELLOW)Error: DESC not specified$(NC)"; \
		echo "Usage: make docker-create DESC=\"Your project description\""; \
		exit 1; \
	fi
	@echo "$(BLUE)Creating project: $(DESC)$(NC)"
	docker-compose -f docker-compose.yml run --rm app create "$(DESC)" --verbose

docker-status: ## Show system status and GPU info
	@echo "$(BLUE)System Status$(NC)"
	docker-compose -f docker-compose.yml run --rm app status

docker-gpu: ## Show real-time GPU metrics
	@echo "$(BLUE)GPU Metrics$(NC)"
	docker-compose -f docker-compose.yml run --rm app info

docker-test: ## Run tests in Docker
	@echo "$(BLUE)Running tests in Docker...$(NC)"
	docker-compose -f docker-compose.yml run --rm app python -m pytest tests/ -v

docker-clean: ## Remove all Docker containers and volumes
	@echo "$(BLUE)Cleaning Docker resources...$(NC)"
	docker-compose -f docker-compose.yml down -v
	@echo "$(GREEN)✓ Cleanup complete$(NC)"

docker-ps: ## List running Docker containers
	@echo "$(BLUE)Running containers:$(NC)"
	docker ps --filter "name=mini-software-house" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

docker-docs: ## Show Docker setup documentation
	@echo "$(BLUE)Docker Documentation:$(NC)"
	@cat README.DOCKER.md | head -100

# Legacy Docker
docker-shell-sandbox: ## Open shell in Docker sandbox (legacy)
	@echo "$(BLUE)Opening Docker shell...$(NC)"
	docker run -it mini-sh-sandbox bash

# Dependencies
update-deps: ## Update Poetry dependencies
	@echo "$(BLUE)Updating dependencies...$(NC)"
	poetry update

update-rust: ## Update Rust dependencies
	@echo "$(BLUE)Updating Rust dependencies...$(NC)"
	cd src/rust && cargo update

# Documentation
docs: ## Open documentation index
	@echo "$(BLUE)Opening documentation...$(NC)"
	@cat docs/INDEX.md

status: ## Show project status
	@echo "$(BLUE)=== Project Status ===$(NC)"
	@echo "Structure: ✓ Reorganized"
	@echo "Core modules: ✓ src/core/"
	@echo "Documentation: ✓ docs/ (organized)"
	@echo "Scripts: ✓ scripts/setup/"
	@echo "Tests: ✓ tests/ (configured)"

# Development utilities
shell: ## Enter Poetry shell
	@echo "$(BLUE)Entering Poetry shell...$(NC)"
	poetry shell

freeze: ## Export dependency requirements.txt
	@echo "$(BLUE)Exporting requirements...$(NC)"
	poetry export --output requirements.txt

# Info
info: ## Show system and project info
	@echo "$(BLUE)=== System Info ===$(NC)"
	python --version
	@echo ""
	@echo "$(BLUE)=== Project Info ===$(NC)"
	@echo "Python env: $$(poetry env info -p)"
	@echo "Rust: $$(rustc --version)"
	@echo ""
	@echo "$(BLUE)=== Directory Structure ===$(NC)"
	@ls -la | grep '^d'

# Default target
.DEFAULT_GOAL := help
