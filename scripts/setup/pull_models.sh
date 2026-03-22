#!/bin/bash
# Setup script for Mini Software House - Download optimized models
# Models are configured for 4GB VRAM on GTX 1050 Ti

set -e

echo "📥 Pulling optimized models for 4GB VRAM..."
echo ""

# Planner & Architect - 3B parameters
echo "⬇️  Pulling Qwen 2.5 3B (Planner/Architect)..."
ollama pull qwen2.5:3b

# Backend Developer - 3B parameters
echo "⬇️  Pulling Qwen 2.5 Coder 3B (Backend Developer)..."
ollama pull qwen2.5-coder:3b

# Frontend Developer - 1.5B parameters
echo "⬇️  Pulling Qwen 2.5 Coder 1.5B (Frontend Developer)..."
ollama pull qwen2.5-coder:1.5b

# Tester / QA - 1.3B parameters
echo "⬇️  Pulling DeepSeek Coder 1.3B (Tester/QA)..."
ollama pull deepseek-coder:1.3b

# Documenter - 2B parameters
echo "⬇️  Pulling Gemma 2 2B (Documenter)..."
ollama pull gemma2:2b

# RAG / Research - Mini version
echo "⬇️  Pulling Phi-3 Mini (RAG/Research)..."
ollama pull phi3:mini

# Embeddings (Extremely lightweight - 137M parameters)
echo "⬇️  Pulling Nomic Embed Text (Embeddings)..."
ollama pull nomic-embed-text

echo ""
echo "✅ All models successfully pulled!"
echo ""
echo "📊 Total models configured: 7"
echo "💾 Total VRAM requirement: ~3.8GB"
echo ""
echo "Next: Run 'python scripts/setup/verify_setup.py'"
