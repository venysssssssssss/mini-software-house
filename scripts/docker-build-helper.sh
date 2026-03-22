#!/bin/bash
# Docker build helper with progress feedback

set -e

echo "🐳 Mini Software House - Docker Build Helper"
echo "=============================================="
echo ""

# Check Docker availability
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed"
    exit 1
fi

echo "✓ Docker found: $(docker --version)"
echo ""

# Select build type
echo "Choose build option:"
echo ""
echo "1. Full GPU Support (CUDA 12.1) - ~5-10 minutes, ~3-4GB"
echo "   → Full acceleration with nvidia-smi monitoring"
echo "   → Requires NVIDIA Docker runtime"
echo ""
echo "2. Lightweight (CPU only) - ~2-3 minutes, ~1.2GB"
echo "   → Works on any system"
echo "   → GPU acceleration from local ollama if available"
echo ""
echo "3. Use existing Python environment (development)"
echo "   → Fastest (no Docker build)"
echo "   → Run: poetry run python -m src.cli"
echo ""

read -p "Select option (1/2/3) [1]: " choice
choice=${choice:-1}

case $choice in
    1)
        echo ""
        echo "🔨 Building FULL GPU-ACCELERATED image..."
        echo ""
        echo "This will:"
        echo "  • Download NVIDIA CUDA base image (~1.3GB)"
        echo "  • Install Python 3.12 and dependencies"
        echo "  • Install project packages"
        echo "  • Total size: ~3-4GB"
        echo "  • Build time: 5-10 minutes"
        echo ""
        echo "Running: docker build -t mini-software-house:latest -f Dockerfile ."
        echo ""
        
        # Run build with progress
        docker build \
            -t mini-software-house:latest \
            -f Dockerfile \
            --progress=plain \
            . 2>&1 | while IFS= read -r line; do
                if [[ $line == *"#"* ]] || [[ $line == *"Writing image"* ]] || [[ $line == *"Done"* ]]; then
                    echo "$line"
                fi
            done
        
        echo ""
        echo "✅ Full GPU build complete!"
        echo ""
        echo "Next: make docker-up"
        ;;
   
    2)
        echo ""
        echo "🔨 Building LIGHTWEIGHT image..."
        echo ""
        echo "This will:"
        echo "  • Use Python 3.12 slim base image"
        echo "  • Install project dependencies (CPU)"
        echo "  • Total size: ~1.2GB"
        echo "  • Build time: 2-3 minutes"
        echo ""
        echo "Running: docker build -t mini-software-house:lightweight -f Dockerfile.lightweight ."
        echo ""
        
        docker build \
            -t mini-software-house:lightweight \
            -f Dockerfile.lightweight \
            --progress=plain \
            . 2>&1 | while IFS= read -r line; do
                if [[ $line == *"#"* ]] || [[ $line == *"Writing image"* ]] || [[ $line == *"Done"* ]]; then
                    echo "$line"
                fi
            done
        
        echo ""
        echo "✅ Lightweight build complete!"
        echo ""
        echo "To use this image, update docker-compose.yml:"
        echo "  image: mini-software-house:lightweight"
        ;;
    
    3)
        echo ""
        echo "🐍 Using local Python environment"
        echo ""
        echo "Install dependencies:"
        echo "  poetry install"
        echo ""
        echo "Run directly:"
        echo "  poetry run python -m src.cli status"
        echo "  poetry run python -m src.cli create 'Build a REST API'"
        echo ""
        exit 0
        ;;
    
    *)
        echo "Invalid choice"
        exit 1
        ;;
esac

echo ""
echo "=============================================="
echo "Build Status: Complete ✅"
echo ""
echo "Next steps:"
echo "  1. Start services: make docker-up"
echo "  2. Create project: make docker-create DESC='...'"
echo "  3. Monitor GPU:   make docker-gpu"
echo ""
echo "For help: cat README.DOCKER.md"
echo "=============================================="
