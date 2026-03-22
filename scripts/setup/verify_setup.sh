#!/bin/bash
# Verification script for Mini Software House - Rust workspace + optimization setup
# This script validates all components are correctly configured

set -e

echo "🔍 Mini Software House - Complete Setup Verification"
echo "===================================================="
echo ""

FAILED=0
WARNING=0

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

check_pass() {
    echo -e "${GREEN}✅${NC} $1"
}

check_warn() {
    echo -e "${YELLOW}⚠️${NC} $1"
    ((WARNING++))
}

check_fail() {
    echo -e "${RED}❌${NC} $1"
    ((FAILED++))
}

# 1️⃣ Check Python version
echo "1️⃣  Checking Python installation..."
if command -v python3 &> /dev/null; then
    python_version=$(python3 --version 2>&1 | awk '{print $2}')
    check_pass "Python $python_version"
else
    check_fail "Python 3 not found"
fi

# 2️⃣ Check Rust version
echo ""
echo "2️⃣  Checking Rust installation..."
if command -v rustc &> /dev/null; then
    rustc_version=$(rustc --version)
    check_pass "$rustc_version"
else
    check_fail "Rust not found. Install with: curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh"
fi

# 3️⃣ Check workspace structure
echo ""
echo "3️⃣  Checking project structure..."
if [ -f "pyproject.toml" ]; then
    check_pass "pyproject.toml found"
else
    check_fail "pyproject.toml missing"
fi

if [ -f "src/rust/Cargo.toml" ]; then
    check_pass "Rust workspace found"
else
    check_fail "Rust workspace missing"
fi

# 4️⃣ Check Rust modules
echo ""
echo "4️⃣  Checking Rust modules..."
modules=("performance_core" "json_parser" "docker_log_streamer" "fs_watcher" "ast_parser" "ollama_client")
for module in "${modules[@]}"; do
    if [ -f "src/rust/$module/Cargo.toml" ]; then
        check_pass "$module"
    else
        check_fail "$module missing"
    fi
done

# 5️⃣ Check core Python modules
echo ""
echo "5️⃣  Checking core Python modules..."
core_modules=("src/core/database.py" "src/core/models.py" "src/core/events.py" "src/core/logger.py")
for module in "${core_modules[@]}"; do
    if [ -f "$module" ]; then
        check_pass "$(basename $module)"
    else
        check_fail "$(basename $module) missing"
    fi
done

# 6️⃣ Check agents
echo ""
echo "6️⃣  Checking agents..."
agents=("base.py" "orchestrator.py" "planner.py" "executor.py" "tester.py" "documenter.py" "rag.py")
for agent in "${agents[@]}"; do
    if [ -f "src/agents/$agent" ]; then
        check_pass "$agent"
    else
        check_fail "$agent missing"
    fi
done

# 7️⃣ Check documentation structure
echo ""
echo "7️⃣  Checking documentation..."
doc_dirs=("docs/status" "docs/architecture" "docs/setup" "docs/quickstart")
for dir in "${doc_dirs[@]}"; do
    if [ -d "$dir" ]; then
        file_count=$(find "$dir" -type f -name "*.md" | wc -l)
        check_pass "$dir ($file_count files)"
    else
        check_fail "$dir missing"
    fi
done

# 8️⃣ Check Ollama
echo ""
echo "8️⃣  Checking Ollama..."
if command -v ollama &> /dev/null; then
    check_pass "Ollama installed"
    # Try to check if models are loaded - set timeout in case Ollama isn't running
    if timeout 5 ollama list 2>/dev/null | grep -q "qwen"; then
        model_count=$(ollama list 2>/dev/null | grep -c -E "qwen|deepseek|gemma|phi|nomic" || echo "0")
        check_pass "$model_count optimized models available"
    else
        check_warn "Ollama not running (models may still be available)"
    fi
else
    check_fail "Ollama not installed"
fi

# 9️⃣ Check Docker
echo ""
echo "9️⃣  Checking Docker..."
if command -v docker &> /dev/null; then
    check_pass "Docker installed"
    if [ -f "Dockerfile.sandbox" ]; then
        check_pass "Dockerfile.sandbox found"
    else
        check_warn "Dockerfile.sandbox missing"
    fi
else
    check_warn "Docker not installed (optional)"
fi

# 🔟 Check NVIDIA/GPU
echo ""
echo "🔟  Checking GPU..."
if command -v nvidia-smi &> /dev/null; then
    vram_mb=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits | head -1)
    vram_gb=$(echo "scale=2; $vram_mb / 1024" | bc)
    check_pass "NVIDIA GPU detected ($vram_gb GB VRAM)"
    
    if (( $(echo "$vram_gb < 4" | bc -l) )); then
        check_warn "VRAM less than 4GB - performance may be limited"
    fi
else
    check_warn "NVIDIA GPU not detected (CPU-only mode)"
fi

# Summary
echo ""
echo "===================================================="
if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ ALL CHECKS PASSED!${NC}"
    if [ $WARNING -gt 0 ]; then
        echo "($WARNING warnings - see above)"
    fi
    echo ""
    echo "🚀 Next steps:"
    echo "  1. Run: python src/main.py --task 'Your task here'"
    echo "  2. Monitor: streamlit run app.py"
    exit 0
else
    echo -e "${RED}❌ SETUP INCOMPLETE (${FAILED} failures, ${WARNING} warnings)${NC}"
    exit 1
fi
