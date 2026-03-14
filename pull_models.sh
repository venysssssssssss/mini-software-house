#!/bin/bash

echo "Pulling optimized models for 4GB VRAM..."

# Planner & Architect
ollama pull qwen2.5:3b

# Backend Developer
ollama pull qwen2.5-coder:3b

# Frontend Developer
ollama pull qwen2.5-coder:1.5b

# Tester / QA
ollama pull deepseek-coder:1.3b

# Documenter
ollama pull gemma2:2b

# RAG / Research
ollama pull phi3:mini

# Embeddings (Extremely lightweight)
ollama pull nomic-embed-text

echo "All models successfully pulled."
