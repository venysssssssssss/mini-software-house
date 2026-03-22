# 🐳 Docker Quick Start Guide

**Get started in 5 minutes with GPU-accelerated project creation**

## Prerequisites Check

```bash
# Validate Docker setup
python scripts/validate_docker_setup.py
```

Expected output:
```
✓ Docker: Docker version
✓ Docker Compose: Docker Compose version  
✓ NVIDIA Docker Runtime: Available
✓ NVIDIA GPU: Available
```

## 3-Step Quick Start

### Step 1: Build Docker Image (⏱️ 2-3 minutes first time)

```bash
make docker-build
```

or with docker-compose:

```bash
docker-compose build
```

**Output:**
```
Building Docker image: mini-software-house:latest
Successfully tagged mini-software-house:latest
✓ Build complete
```

### Step 2: Start Services

```bash
make docker-up
```

**What starts:**
- ✓ Ollama (LLM inference)
- ✓ PostgreSQL (database)
- ✓ Redis (caching)
- ✓ App Container (ready)

Check status:
```bash
make docker-ps
# or
docker-compose ps
```

### Step 3: Create Your First Project

```bash
make docker-create DESC="Build a REST API for user authentication"
```

**Real-time output:**
```
🚀 Starting project creation pipeline
📝 Description: Build a REST API for user authentication
📦 Project name: build-user-auth-api

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
[   1.2s] [STATUS] [PREP] Initializing agents... [████] 10%
[   2.5s] [STATUS] [PHASE 1] Planning architecture... [████████] 20%
...
[  15.0s] [SUCCESS] ✓ Project creation completed successfully!
```

**Project created at:** `workspace/build-user-auth-api/`

## Common Commands

### Monitor GPU in Real-time
```bash
make docker-gpu
```

Output:
```
🖥️  GPU 0: NVIDIA RTX 4090
   Memory: 42.5% (10432/24576 MB)
   Utilization: 75.3%
   Temperature: 68.5°C
   Power: 320.5W / 450W
```

### View All Logs
```bash
make docker-logs
```

### Open Container Shell
```bash
make docker-shell
```

### Check System Status
```bash
make docker-status
```

### Stop Everything
```bash
make docker-down
```

### Remove Everything (including data)
```bash
make docker-clean
```

## More Examples

### Create ML Project
```bash
make docker-create DESC="Create a neural network for image classification with PyTorch"
```

### Create Real-time Chat
```bash
make docker-create DESC="Build a real-time chat application with WebSocket support"
```

### Create ETL Pipeline
```bash
make docker-create DESC="Build an ETL pipeline for streaming data processing"
```

### Create with Custom Name
```bash
docker-compose run --rm app create "Your description" --name="my-project"
```

## Accessing Services

| Service | URL/Port | Credentials |
|---------|----------|-------------|
| Ollama | http://localhost:11434 | - |
| PostgreSQL | localhost:5432 | appuser / apppassword |
| Redis | localhost:6379 | - |
| Streamlit | http://localhost:8501 | - |

### Example: Direct PostgreSQL

```bash
docker exec -it mini-software-house-db psql -U appuser -d software_house
```

### Example: Direct Redis

```bash
docker exec -it mini-software-house-redis redis-cli
```

## Docker Project Output Structure

After creating a project, check the generated structure:

```
workspace/
├── build-user-auth-api/          # Your project directory
│   ├── src/
│   │   ├── models.py             # Database models
│   │   ├── routes.py             # API endpoints
│   │   ├── schemas.py            # Request/response schemas
│   │   └── main.py               # Application entry
│   ├── tests/
│   │   ├── test_api.py           # API tests
│   │   └── test_models.py        # Model tests
│   ├── requirements.txt          # Python dependencies
│   ├── docker-compose.yml        # Isolated compose file
│   ├── Dockerfile                # Project Dockerfile
│   ├── README.md                 # Project documentation
│   └── .env.example             # Environment template
├── state.json                    # Pipeline state
├── run.log                       # Execution log
└── metrics.json                  # GPU & performance metrics
```

## Troubleshooting

### Docker daemon not running
```bash
sudo systemctl start docker
```

### GPU not detected
```bash
docker run --rm --gpus all nvidia/cuda:12.1.1-runtime-ubuntu22.04 nvidia-smi
```

### Ollama service not ready
```bash
make docker-logs
# Check if ollama container is pulling models
```

### Out of memory
```bash
# Increase Docker memory limit in Docker Desktop settings
# or edit /etc/docker/daemon.json for Linux
```

### Want to use specific GPU?
```bash
# In docker-compose.yml, modify app service:
environment:
  - CUDA_VISIBLE_DEVICES=0  # Use GPU 0 only
```

## Performance Tips

1. **Use volume mount for workspace** (already done)
   ```yaml
   volumes:
     - ./workspace:/app/workspace
   ```

2. **GPU performance monitoring**
   ```bash
   watch -n 1 'make docker-gpu'
   ```

3. **Keep models cached** in ollama_data volume
   - Models persist between runs
   - Much faster on second runs

4. **Use resource limits**
   ```yaml
   deploy:
     resources:
      limits:
        memory: 32G
   ```

## Full Documentation

For detailed information, see [README.DOCKER.md](README.DOCKER.md)

## What's Next?

- ✅ Created projects in Docker
- 👉 View README in generated project folder
- 👉 Access project files in `workspace/project-name/`
- 👉 Deploy generated projects independently

---

**Tip:** Run `make help` to see all available commands at any time.
