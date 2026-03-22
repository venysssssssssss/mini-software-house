# Docker Build Guide - Options and Trade-offs

Your Mini Software House has **two Docker build options** to match your needs.

## 📊 Comparison Table

| Aspect | Full GPU (CUDA) | Lightweight (CPU) |
|--------|-----------------|-------------------|
| **Base Image** | nvidia/cuda:12.1.1 | python:3.12-slim |
| **Size** | ~3-4 GB | ~1.2 GB |
| **Build Time** | 5-10 minutes | 2-3 minutes |
| **GPU Support** | ✅ NVIDIA GPU exec | ⚠️ Via ollama only |
| **GPU Monitoring** | ✅ nvidia-smi works | ✅ Works if GPU available |
| **Best For** | Production, research | Development, testing |

## 🚀 Quick Start Options

### Option 1: Full GPU Support (Recommended for Production)

```bash
# Build with interactive helper
bash scripts/docker-build-helper.sh
# Choose option 1

# Or build directly
make docker-build
# Wait 5-10 minutes while CUDA base image downloads
```

**What you get:**
- ✅ Full NVIDIA GPU acceleration
- ✅ Real-time GPU monitoring (`nvidia-smi` inside container)
- ✅ All LLM inference on GPU
- ✅ Temperature and power monitoring
- ✅ Professional-grade setup

**Requirements:**
- 8+ GB free disk space
- NVIDIA Docker runtime installed
- NVIDIA GPU (optional but recommended)
- 10-15 minutes on first build

**Build output example:**
```
#4 [stage-1 1/8] FROM docker.io/nvidia/cuda:12.1.1-runtime-ubuntu22.04
#4 sha256:a14a8a8a... 1.33GB / 1.33GB downloading...
#4 extracting sha256:a14a8a8a... 66.6s
...
#8 [stage-1 8/8] RUN pip install packages...
#8 DONE in 2 minutes
Successfully tagged mini-software-house:latest
```

### Option 2: Lightweight Build (Recommend for Development)

```bash
# Build with interactive helper
bash scripts/docker-build-helper.sh
# Choose option 2

# Or build directly
make docker-build-lightweight
# Takes 2-3 minutes, ~1.2 GB size
```

**What you get:**
- ✅ Smaller image (~1.2 GB vs 3-4 GB)
- ✅ Faster builds (2-3 minutes)
- ✅ Works on any system (no CUDA needed)
- ✅ GPU monitoring if available
- ✅ Perfect for development and testing

**Requirements:**
- 3+ GB free disk space
- Any system - works on Mac, Windows, Linux
- 2-3 minutes on first build

**Build output example:**
```
#1 [internal] load .dockerignore
#2 [internal] load build context
#3 [base 1/5] FROM python:3.12-slim-ubuntu
#4 [base 2/5] RUN apt-get update && apt-get install...
#5 [base 3/5] RUN pip install packages...
Successfully tagged mini-software-house:lightweight
```

### Option 3: No Docker (Local Python)

```bash
# Skip Docker entirely, use local Python
poetry install
poetry run python -m src.cli create "Build a REST API"
```

**What you get:**
- ✅ Fastest - no build time
- ✅ Direct control of environment
- ✅ Better for development/debugging

**Requirements:**
- Python 3.12 installed
- 15+ GB RAM for LLM inference

---

## 🎯 Which Option Should I Choose?

### Choose **Full GPU Build** if:
- ✅ You have NVIDIA GPU and want to use it
- ✅ You're running inference on large models
- ✅ You need professional monitoring and performance
- ✅ You have 20+ minutes and 8+ GB disk space

### Choose **Lightweight Build** if:
- ✅ You're developing and testing
- ✅ You don't have much disk space (only 3 GB)
- ✅ You want faster builds and iterations
- ✅ You use CPU or access GPU via ollama

### Choose **No Docker** if:
- ✅ You're debugging or developing locally
- ✅ You don't want any build overhead
- ✅ You have all dependencies installed

---

## 📝 Step-by-Step: Full GPU Build

### Step 1: Validate Your System

```bash
python scripts/validate_docker_setup.py
```

Expected output:
```
✓ Docker: Docker version 28.4.0
✓ Docker Compose: Docker Compose version v2.39.1
✓ NVIDIA Docker Runtime: Available (or warning if not)
--READY TO USE--
```

### Step 2: Start the Build

```bash
# Option A: Interactive helper (recommended)
bash scripts/docker-build-helper.sh
# Choose option 1

# Option B: Direct build
make docker-build

# Option C: With detailed logging
docker build -t mini-software-house:latest --progress=plain .
```

### Step 3: Wait for Completion

The build will download and cache the CUDA image (~1.3 GB).

Progress phases:
1. **Load metadata** (0-2 sec)
2. **Download base image** (Varies by connection)
3. **Extract base image** (20-70 sec)
4. **Install system packages** (30-60 sec)
5. **Install Python packages** (60-120 sec)
6. **Build complete** (✅ Image ready)

**Total time: 5-10 minutes**

### Step 4: Verify Build

```bash
docker images | grep mini-software-house
# Should show: mini-software-house   latest   3-4GB
```

### Step 5: Run Services

```bash
make docker-up
# Services will be ready in 30-60 seconds
```

---

## 📝 Step-by-Step: Lightweight Build

### Step 1: Build Image

```bash
# Option A: Interactive helper
bash scripts/docker-build-helper.sh
# Choose option 2

# Option B: Direct build
make docker-build-lightweight
```

### Step 2: Wait for Completion

Much faster! Only 2-3 minutes.

```
[1/4] FROM python:3.12-slim-ubuntu
[2/4] RUN apt-get update && apt-get install...
[3/4] COPY --chown=appuser:appuser . /app/
[4/4] RUN pip install packages...
```

### Step 3: Use in Docker Compose

Update `docker-compose.yml` if needed:

```yaml
services:
  app:
    image: mini-software-house:lightweight  # Changed from: latest
```

Then start:

```bash
make docker-up
```

---

## 🔧 Troubleshooting Builds

### Build hangs/stalls

Usually the CUDA base image download. Let it run - it can take 10+ minutes.

```bash
# If it seems stuck, check Docker logs
docker ps -a
# Should show a container named something like "build-xxx"
```

### Out of disk space

CUDA image is ~1.3 GB, build output ~3-4 GB total.

```bash
# Check disk space
df -h

# Clean up Docker (careful!)
docker system prune -a  # Removes ALL Docker resources
```

### Image not found

Make sure image name matches:
- Full GPU: `mini-software-house:latest`
- Lightweight: `mini-software-house:lightweight`

```bash
docker images | grep mini-software-house
```

### NVIDIA runtime not available

Install NVIDIA Docker:
```bash
# Ubuntu/Debian
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | \
  sudo tee /etc/apt/sources.list.d/nvidia-docker.list
sudo apt-get update && sudo apt-get install -y nvidia-docker2
```

---

## 💾 Build Outputs

### Full GPU Build (~3-4 GB)

```
mini-software-house:latest    3.2GB
```

Contains:
- NVIDIA CUDA 12.1 runtime (~1.3 GB)
- Ubuntu 22.04 base (~500 MB)
- Python 3.12 + packages (~1.4 GB)

### Lightweight Build (~1.2 GB)

```
mini-software-house:lightweight    1.2GB
```

Contains:
- Python 3.12 slim (~400 MB)
- Python packages (~800 MB)

---

## 🚀 After Build: What's Next?

Once your image is built:

```bash
# 1. Start services
make docker-up

# 2. Create a project
make docker-create DESC="Build a REST API"

# 3. Monitor GPU (if applicable)
make docker-gpu

# 4. View logs
make docker-logs

# 5. Stop services
make docker-down
```

---

## 📊 Performance Comparison

When creating a project (REST API example):

| Metric | Full GPU | Lightweight | Local Python |
|--------|----------|-------------|--------------|
| **Build time** | 5-10 min | 2-3 min | 0 min |
| **Startup** | 30-60 sec | 30-60 sec | ~5 sec |
| **Project creation** | 30-45 sec | 45-60 sec | 45-60 sec |
| **LLM inference** | Fast (GPU) | Medium (CPU) | Medium (CPU) |

---

## 🎓 Advanced: Custom Build

Create your own Dockerfile combining features:

```dockerfile
# Use specific CUDA version and add custom packages
FROM nvidia/cuda:12.1.1-runtime-ubuntu22.04
# ... your customizations ...
```

Build with custom Dockerfile:
```bash
docker build -t my-custom-image -f Dockerfile.custom .
```

---

## 📞 Quick Commands Reference

```bash
# Build options
make docker-build                  # Full GPU
make docker-build-lightweight      # Lightweight
bash scripts/docker-build-helper.sh # Interactive

# Check what was built
docker images | grep mini-software-house

# Use the built image
make docker-up                # Start services
make docker-create DESC="..."  # Create project
make docker-down              # Stop services

# Cleanup old builds
docker rmi mini-software-house:latest
docker system prune -a
```

---

**Recommendation:** Start with the interactive helper (`bash scripts/docker-build-helper.sh`) - it will guide you through the best option for your system!
