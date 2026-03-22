#!/usr/bin/env python3
"""
Docker integration demo - shows how to use the Docker setup
with GPU monitoring and streaming status
"""

import subprocess
import sys
from pathlib import Path


def print_section(title: str):
    """Print a formatted section header"""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")


def run_command(cmd: str, description: str = ""):
    """Run and display command output"""
    if description:
        print(f"\n→ {description}")
    print(f"  Command: {cmd}\n")

    result = subprocess.run(cmd, shell=True)
    return result.returncode == 0


def main():
    print_section("Mini Software House - Docker Integration Demo")

    print("""
This demo shows you how to use the fully Dockerized setup with:
  ✓ GPU acceleration (all models run on GPU)
  ✓ Real-time streaming status updates
  ✓ GPU metrics monitoring
  ✓ Complete orchestration (Ollama + PostgreSQL + Redis + App)

""")

    # Step 1: Validation
    print_section("Step 1: Validate Docker Setup")

    print("\nValidating your Docker environment...")
    success = run_command(
        "python scripts/validate_docker_setup.py",
        "Running validation script"
    )

    if not success:
        print("\n❌ Docker validation failed. Please fix issues above.")
        sys.exit(1)

    # Step 2: Build
    print_section("Step 2: Build Docker Image")

    print("""
The Docker image includes:
  • Python 3.12 + PyTorch with CUDA support
  • All dependencies from pyproject.toml
  • GPU monitoring tools (nvidia-smi)
  • CLI with streaming support

First-time build takes 2-3 minutes. Subsequent builds are much faster.
You can now build with:

  make docker-build
  or
  docker build -t mini-software-house:latest .
""")

    # Step 3: Start services
    print_section("Step 3: Start Services")

    print("""
Start all services (Ollama, PostgreSQL, Redis) with:

  make docker-up
  or
  docker-compose up -d

What starts:
  • Ollama (LLM service) on http://localhost:11434
  • PostgreSQL on localhost:5432
  • Redis on localhost:6379
  • App Container (ready for commands)

Check status:
  make docker-ps
""")

    # Step 4: Create project
    print_section("Step 4: Create Your First Project")

    print("""
Create a project with real-time streaming and GPU monitoring:

  make docker-create DESC="Build a REST API for user authentication"

This will:
  1. Show real-time progress updates
  2. Display GPU metrics continuously
     - GPU utilization percentage
     - Memory usage and temperature
     - Power consumption
  3. Generate intelligent kebab-case project name
  4. Create complete project structure

Example output:

  🚀 Starting project creation pipeline
  📝 Description: Build a REST API for user authentication
  
  ============================================================
  GPU METRICS (Real-time)
  ============================================================
  
  🖥️  GPU 0: NVIDIA RTX 4090
     Memory: [████████░░░░░░░░░░░░] 42.5%/24576 MB (65.2%)
     Utilization: [██████████████░░░░░░] 75.3%
     Temperature: 68.5°C
     Power: 320.5W / 450W
  
  ============================================================
  
  [   0.5s] [INFO] 🚀 Starting project creation pipeline
  [   1.2s] [STATUS] [PREP] Initializing... [████] 10%
  [   2.5s] [INFO]   → Analyzing requirements
  [   3.0s] [INFO]   → Generating project name (kebab-case)
  [   3.2s] [INFO]     GPU0: 75.3% util, 65.2% mem, 68.5°C
  ...
  [  15.0s] [SUCCESS] ✓ Project created: build-user-auth-api
""")

    # Step 5: Monitoring
    print_section("Step 5: Monitor GPU Metrics")

    print("""
View real-time GPU metrics anytime:

  make docker-gpu

Shows:
  • GPU name and index
  • Memory usage (MB and percentage)
  • Utilization percentage
  • Temperature in Celsius
  • Power draw (W) and limit

View all service logs:

  make docker-logs

Open shell in container:

  make docker-shell
""")

    # Step 6: Examples
    print_section("Project Creation Examples")

    examples = [
        ("REST API", "Build a REST API for user authentication"),
        ("Chat App", "Create a real-time chat application with WebSocket"),
        ("ML Model", "Train a neural network for image classification"),
        ("ETL Pipeline", "Build an ETL system for data streaming"),
        ("Microservices", "Create a microservices architecture with gRPC"),
    ]

    print("\nTry these examples:\n")

    for name, desc in examples:
        print(f'  make docker-create DESC="{desc}"')

    # Step 7: Advanced
    print_section("Advanced Usage")

    print("""
View system status:
  make docker-status

Run tests in Docker:
  make docker-test

Execute custom command:
  make docker-exec CMD="python -m src.cli info"

Stop all services:
  make docker-down

Clean everything (remove volumes):
  make docker-clean
""")

    # Step 8: Documentation
    print_section("Full Documentation")

    print("""
For complete documentation:

  cat README.DOCKER.md              # Docker setup guide
  cat docs/quickstart/DOCKER_QUICKSTART.md  # Quick reference
  make docker-docs                  # Show docs in make

Structure of generated projects:

  workspace/
  ├── project-name/                # Your generated project
  │   ├── src/                     # Application code
  │   ├── tests/                   # Test suite
  │   ├── Dockerfile               # Project Dockerfile
  │   ├── docker-compose.yml       # Project services
  │   ├── requirements.txt         # Dependencies
  │   └── README.md                # Documentation
  ├── state.json                   # Pipeline state
  └── run.log                      # Logs
""")

    # Final
    print_section("Ready to Start!")

    print("""
Now that you understand the setup, start with:

  1. make docker-build
     → Build the Docker image

  2. make docker-up
     → Start all services

  3. make docker-create DESC="Your project description"
     → Create your first project with GPU monitoring

That's it! Your projects will be created with:
  ✓ Real-time streaming status
  ✓ GPU metrics displayed in real-time
  ✓ Intelligent project naming (kebab-case)
  ✓ Complete infrastructure setup

Questions? Check the docs or run: make help
""")

    print("\n" + "="*70 + "\n")


if __name__ == "__main__":
    main()
