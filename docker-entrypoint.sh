#!/bin/bash
# Docker entrypoint script

set -e

echo "🚀 Mini Software House - Docker Startup"
echo "========================================"

# Wait for Ollama to be ready
if [ ! -z "$OLLAMA_HOST" ]; then
    echo "⏳ Waiting for Ollama service..."
    max_attempts=30
    attempt=0
    
    while ! curl -s -f "$OLLAMA_HOST/api/version" > /dev/null 2>&1; do
        attempt=$((attempt + 1))
        if [ $attempt -ge $max_attempts ]; then
            echo "❌ Ollama service unavailable after $max_attempts attempts"
            exit 1
        fi
        echo "  Attempt $attempt/$max_attempts..."
        sleep 2
    done
    
    echo "✓ Ollama service is ready"
    
    # Pull default model if needed
    if [ ! -z "$DEFAULT_MODEL" ]; then
        echo "📥 Pulling Ollama model: $DEFAULT_MODEL"
        ollama pull $DEFAULT_MODEL || echo "⚠️  Could not pull model (may be pre-loaded)"
    fi
fi

# Check GPU availability
echo ""
echo "🖥️  System Information:"
if command -v nvidia-smi &> /dev/null; then
    echo "✓ NVIDIA GPU detected:"
    nvidia-smi --query-gpu=name,index --format=csv,noheader | sed 's/^/  /'
    echo ""
fi

# Display Python info
python3 --version

echo ""
echo "========================================"
echo "🎯 Ready to process commands"
echo "========================================"
echo ""

# Execute the command passed to the container
exec "$@"
