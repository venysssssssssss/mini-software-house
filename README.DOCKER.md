# 🐳 Mini Software House - Docker Setup Guide

Complete Docker setup with GPU support, real-time streaming, and full orchestration.

## 📋 Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+
- NVIDIA Docker runtime (for GPU support)
- At least 8GB of disk space
- 16GB+ RAM recommended
- NVIDIA GPU (optional but recommended)

## 🚀 Quick Start

### 1. Build the Docker Image

```bash
make docker-build
# or
docker build -t mini-software-house:latest .
```

### 2. Start Services

```bash
make docker-up
# or
docker-compose up -d
```

This starts:
- **Ollama** (LLM inference) - http://localhost:11434
- **PostgreSQL** - localhost:5432
- **Redis** - localhost:6379
- **App Container** (ready for commands)

### 3. Create Your First Project

```bash
make docker-create DESC="Build a REST API for user authentication"
```

This will:
1. Show real-time progress with streaming status
2. Display GPU metrics continuously
3. Generate an intelligent project name (kebab-case)
4. Return project location and metrics

## 📊 Monitoring & Status

### View System Status
```bash
make docker-status
```

Shows GPU availability and configuration.

### View GPU Metrics
```bash
make docker-gpu
```

Real-time GPU utilization, memory, temperature, and power consumption.

### Stream Logs
```bash
make docker-logs
```

### Open Shell in Container
```bash
make docker-shell
```

## 🎯 Project Creation Examples

### REST API Project
```bash
docker-compose run --rm app create "Build a REST API for user management with PostgreSQL"
```

Output:
```
[  25.3s] [STATUS] [PHASE 1] Planning architecture and structure... [████████░░░░░░░░░░] 40%
[  25.5s] [INFO] GPU0: 45.2% util, 28.5% mem, 62.1°C
[  30.2s] [SUCCESS] ✓ Planning phase complete
[  30.3s] [STATUS] [PHASE 2] Executing and generating code... [██████████████░░░░░░] 60%
...
```

### Machine Learning Project
```bash
docker-compose run --rm app create "Create a neural network for image classification"
```

### Real-time Chat Application
```bash
docker-compose run --rm app create "Build a real-time chat application with WebSocket" --name="rtchat-app"
```

## 🐳 Docker Compose Services

### App Service
- **Image**: Built from Dockerfile
- **GPU Support**: NVIDIA runtime, all GPUs available
- **Volumes**: 
  - `./workspace` → `/app/workspace` (project output)
  - `./src` → `/app/src` (live code)
  - `/var/run/docker.sock` → Docker daemon access
- **Ports**: 8501 (Streamlit), 8000 (API)
- **Environment**: Connects to Ollama at http://ollama:11434

### Ollama Service
- **Image**: ollama/ollama:latest
- **GPU Support**: All GPUs available
- **Volume**: `ollama_data` (model storage - persistent)
- **Port**: 11434
- **Models**: Auto-pulled if specified

### PostgreSQL Service
- **Image**: postgres:16-alpine
- **Credentials**: appuser/apppassword
- **Database**: software_house
- **Port**: 5432
- **Volume**: `postgres_data` (persistent)

### Redis Service
- **Image**: redis:7-alpine
- **Port**: 6379
- **Volume**: `redis_data` (persistent)

## 🎛️ Configuration

### GPU Configuration

**All GPUs** (default):
```yaml
deploy:
  resources:
    reservations:
      devices:
        - driver: nvidia
          count: all
          capabilities: [gpu]
```

**Specific GPU**:
```yaml
environment:
  - CUDA_VISIBLE_DEVICES=0  # Use GPU 0 only
  # or
  - CUDA_VISIBLE_DEVICES=0,1  # Use GPUs 0 and 1
```

### Environment Variables

```bash
# In docker-compose.yml
environment:
  - OLLAMA_HOST=http://ollama:11434      # LLM service
  - CUDA_VISIBLE_DEVICES=0               # GPU selection
  - PYTHONUNBUFFERED=1                   # Real-time output
  - DEFAULT_MODEL=qwen2.5                # Auto-pull model
```

### Memory Limits

```yaml
deploy:
  resources:
    limits:
      memory: 32G                         # Max 32GB
    reservations:
      memory: 16G                         # Reserve 16GB
```

## 📈 Real-time Streaming Output Example

```
🚀 Starting project creation pipeline
📝 Description: Build a REST API for user authentication
📦 Project name: build-user-auth-api

============================================================
GPU METRICS (Real-time)
============================================================

🖥️  GPU 0: NVIDIA RTX 4090
   Memory: [████████░░░░░░░░░░░░] 40%/24576 MB (65.2%)
   Utilization: [██████████████░░░░░░] 75.3%
   Temperature: 68.5°C
   Power: 320.5W / 450W

============================================================

[   0.5s] [INFO] 🚀 Starting project creation pipeline
[   0.6s] [STATUS] [PREP] Initializing agents and GPU monitoring... [██] 10%
[   1.2s] [INFO] 📊 GPU monitoring activated
[   1.5s] [STATUS] [PHASE 1] Planning architecture and structure... [████] 20%
[   2.0s] [INFO]   → Analyzing requirements
[   2.5s] [INFO]   → Generating project name (kebab-case)
[   3.0s] [INFO]     GPU0: 75.3% util, 65.2% mem, 68.5°C
[   3.5s] [INFO]   ✓ Planning phase complete
[   4.0s] [STATUS] [PHASE 1] Planning completed [████████] 35%
...
[  15.0s] [SUCCESS] ✓ Project creation completed successfully!
```

## 🔧 Advanced Commands

### Execute Custom Command
```bash
make docker-exec CMD="python -m src.cli status"
```

### Rebuild All Services (Fresh)
```bash
make docker-rebuild-services
```

### Run Tests
```bash
make docker-test
```

### Check Running Containers
```bash
make docker-ps
```

### Access PostgreSQL
```bash
docker exec -it mini-software-house-db psql -U appuser -d software_house
```

### Access Redis
```bash
docker exec -it mini-software-house-redis redis-cli
```

## 🧹 Cleanup

### Stop Services
```bash
make docker-down
# or
docker-compose down
```

### Remove Everything (including volumes)
```bash
make docker-clean
# or
docker-compose down -v
```

### Prune Unused Resources
```bash
make docker-prune
```

## 🐛 Troubleshooting

### NVIDIA GPU Not Detected
```bash
# Verify NVIDIA Docker runtime
docker run --rm --gpus all nvidia/cuda:12.1.1-runtime-ubuntu22.04 nvidia-smi

# Install NVIDIA Container Runtime
# https://github.com/NVIDIA/nvidia-docker
```

### Ollama Service Not Starting
```bash
# Check Ollama logs
docker-compose logs ollama

# Ensure model is pulled
docker exec mini-software-house-ollama ollama pull qwen2.5:3b
```

### Out of Memory
```bash
# Check resource usage
docker stats

# Increase Docker memory limits
# Edit Docker Desktop settings or daemon.json
```

### Permission Denied (Docker Socket)
```bash
# Fix docker.sock permissions in container
sudo chmod 666 /var/run/docker.sock
```

## 📦 Project Output

After running `docker-compose run --rm app create "..."`, the following appears in `workspace/`:

```
workspace/
├── state.json                 # Pipeline state and metadata
├── run.log                    # Execution log
├── build-user-auth-api/       # Generated project (kebab-case name)
│   ├── src/
│   │   ├── models.py
│   │   ├── routes.py
│   │   └── __init__.py
│   ├── tests/
│   │   └── test_api.py
│   ├── requirements.txt
│   ├── README.md
│   └── docker-compose.yml
└── metrics.json               # GPU and performance metrics
```

## 🚀 Deployment

### Docker Registry Push
```bash
docker tag mini-software-house:latest your-registry/mini-software-house:latest
docker push your-registry/mini-software-house:latest
```

### Kubernetes Deployment
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mini-software-house
spec:
  replicas: 1
  template:
    spec:
      containers:
      - name: app
        image: mini-software-house:latest
        resources:
          requests:
            nvidia.com/gpu: 1
          limits:
            nvidia.com/gpu: 1
```

## 📝 Makefile Commands Summary

```bash
make docker-build           # Build image
make docker-up              # Start services
make docker-down            # Stop services
make docker-create DESC="..." # Create project
make docker-shell           # Interactive shell
make docker-logs            # Stream logs
make docker-status          # System status
make docker-gpu             # GPU metrics
make docker-clean           # Remove everything
```

## 🎓 Best Practices

1. **Use persistent volumes** for data and models
2. **Monitor GPU usage** during long tasks
3. **Set resource limits** to prevent runaway processes
4. **Keep Ollama models** in a shared volume for reuse
5. **Use environment variables** for configuration
6. **Run tests** in Docker to catch issues early
7. **Stream logs** to debug issues in real-time

## 📞 Support

For issues, check:
- Docker logs: `make docker-logs`
- GPU status: `make docker-gpu`
- System status: `make docker-status`
- Application logs: `workspace/run.log`

---

**Last Updated**: March 2026  
**Version**: 1.0.0  
**Maintainer**: Mini Software House Team
