# Mini Software House - GTX 1050 Ti (4GB VRAM) Optimization Guide

This guide documents the optimizations implemented for running a multi-agent software house on limited hardware (GTX 1050 Ti with 4GB VRAM).

## 🎯 Optimization Strategy

Due to VRAM limitations, the architecture uses **sequential model execution** instead of parallel processing:

1. **Single Model at a Time**: Only one LLM is loaded in VRAM at any moment
2. **Immediate Unloading**: Models are unloaded immediately after use (`OLLAMA_KEEP_ALIVE=0`)
3. **Context Management**: Strict token limits (~4096 tokens) to prevent VRAM overflow
4. **Lightweight Models**: All models are 4-bit quantized and under 3.5GB

## 📋 Hardware Requirements

- **GPU**: GTX 1050 Ti (4GB VRAM) or equivalent
- **RAM**: 8GB+ system memory
- **Storage**: 10GB+ free space for models
- **OS**: Linux (Ubuntu 20.04+) or Windows with WSL2

## 🚀 Quick Start

### 1. Environment Setup

```bash
# Run the automated setup script
python setup_environment.py

# Or manually:
./pull_models.sh
docker build -t mini-sh-sandbox -f Dockerfile.sandbox .
```

### 2. Configure Ollama

Create `~/.ollama/config.json`:
```json
{
  "OLLAMA_KEEP_ALIVE": "0",
  "OLLAMA_NUM_GPU": "1", 
  "OLLAMA_MAX_LOADED_MODELS": "1",
  "OLLAMA_NUM_PARALLEL": "1"
}
```

### 3. Run a Task

```bash
python main_pipeline.py --task "Create a todo list API with FastAPI" --interactive
```

## 🏗️ Architecture Overview

```
User Request
     ↓
[Planner Agent] (Qwen2.5-3B)
     ↓ (JSON Plan)
[Executor Agent] (Qwen2.5-Coder-3B/1.5B)
     ↓ (Generated Code)
[Docker Sandbox] (Isolated Testing)
     ↓ (Test Results)
[Tester Agent] (DeepSeek-Coder-1.3B)
     ↓ (Error Analysis)
[Auto-Correction Loop]
     ↓ (Fixed Code)
[Documenter Agent] (Gemma2-2B)
     ↓ (Documentation)
Final Output
```

## 📊 Model Selection

| Agent | Model | Size | VRAM Usage | Purpose |
|-------|-------|------|------------|---------|
| Planner | Qwen2.5-3B | ~2.1GB | ~2.5GB | Task analysis & planning |
| Backend Dev | Qwen2.5-Coder-3B | ~2.3GB | ~2.8GB | Python/FastAPI development |
| Frontend Dev | Qwen2.5-Coder-1.5B | ~1.2GB | ~1.5GB | HTML/CSS/JS generation |
| Tester | DeepSeek-Coder-1.3B | ~1.0GB | ~1.2GB | Test generation & analysis |
| Documenter | Gemma2-2B | ~1.5GB | ~1.8GB | Documentation generation |
| RAG | Phi-3-mini | ~0.8GB | ~1.0GB | Context retrieval |

## 🔧 Key Optimizations

### 1. Context Management (`context_manager.py`)
- **AST Summarization**: Only send function signatures, not full code
- **Token Limiting**: Keep chat history under 4096 tokens
- **Selective Context**: Send only relevant code sections

### 2. Docker Sandbox (`docker_runner.py`)
- **Resource Limits**: 512MB RAM, single CPU core
- **Security**: No network access, PID limits
- **Timeout**: 30-second execution limit

### 3. Model Routing (`base.py`)
```python
def get_model_for_role(role: str) -> str:
    models = {
        "planner": "qwen2.5:3b",
        "backend": "qwen2.5-coder:3b", 
        "frontend": "qwen2.5-coder:1.5b",
        "tester": "deepseek-coder:1.3b",
        "documenter": "gemma2:2b"
    }
    return models.get(role, "qwen2.5:3b")
```

### 4. Sequential Pipeline (`orchestrator.py`)
- **Phase-by-Phase**: One agent at a time
- **State Management**: Track progress through pipeline
- **Auto-Correction**: 3 attempts to fix failing tests

## 🧪 Testing Strategy

### Docker Sandbox Configuration
```dockerfile
FROM python:3.11-slim

# Pre-install heavy dependencies
RUN pip install --no-cache-dir \
    pytest \
    fastapi \
    uvicorn \
    requests

# Resource limits enforced at runtime
```

### Test Execution Flow
1. Generate tests with Tester Agent
2. Execute in Docker with timeout
3. Parse failures and extract error details
4. Feed errors back to Executor Agent
5. Repeat up to 3 times (auto-correction)

## 📈 Performance Metrics

### VRAM Usage (Approximate)
- **Idle**: ~200MB
- **Single Model**: 1.2-2.8GB (depending on model)
- **Peak Usage**: ~3.5GB (with overhead)

### Execution Times (GTX 1050 Ti)
- **Planning**: 15-30 seconds
- **Code Generation**: 30-60 seconds per file
- **Testing**: 10-20 seconds
- **Documentation**: 20-40 seconds

### Throughput
- **Simple Tasks**: 3-5 minutes total
- **Complex Tasks**: 10-20 minutes total
- **Concurrent Tasks**: 1 at a time (VRAM limitation)

## ⚠️ Limitations & Workarounds

### VRAM Limitations
- **Cannot run multiple agents simultaneously**
- **Large context windows cause slowdowns**
- **Complex models may need CPU offloading**

### Performance Trade-offs
- **Sequential processing increases total time**
- **Smaller models may be less capable**
- **4-bit quantization reduces precision**

### Workarounds
- **Use AST summarization for large codebases**
- **Implement aggressive context pruning**
- **Optimize Docker resource allocation**

## 🔍 Monitoring & Debugging

### VRAM Monitoring
```bash
# Monitor VRAM usage
watch -n 1 nvidia-smi

# Check model loading
ollama list
```

### Pipeline Monitoring
```bash
# Run with detailed output
python main_pipeline.py --task "..." --interactive

# Save detailed logs
python main_pipeline.py --task "..." --output results.json
```

### Error Handling
- **Model Loading Failures**: Automatic fallback to smaller models
- **Docker Timeouts**: Code execution limits prevent hanging
- **Test Failures**: Auto-correction with up to 3 retry attempts

## 🚀 Future Optimizations

### Potential Improvements
1. **Model Caching**: Smart caching of frequently used models
2. **Context Compression**: Advanced summarization techniques
3. **Hybrid CPU/GPU**: Offload layers to CPU when needed
4. **Model Quantization**: Explore 3-bit or 2-bit quantization

### Hardware Upgrades
- **8GB VRAM**: Enable 2-3 concurrent models
- **NVMe Storage**: Faster model loading
- **More RAM**: Better Docker performance

## 📚 Additional Resources

- [Ollama Documentation](https://ollama.com/)
- [4-bit Quantization Guide](https://huggingface.co/docs/transformers/main/en/main_classes/quantization)
- [Docker Security Best Practices](https://docs.docker.com/develop/security-best-practices/)
- [CUDA Optimization Guide](https://docs.nvidia.com/cuda/)

## 🤝 Contributing

When contributing optimizations for VRAM-limited systems:

1. **Test on GTX 1050 Ti** or equivalent hardware
2. **Measure VRAM usage** before and after changes
3. **Document performance impact** in pull requests
4. **Consider backward compatibility** with larger systems

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.