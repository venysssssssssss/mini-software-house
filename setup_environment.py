#!/usr/bin/env python3
"""
Setup script for Mini Software House optimized for GTX 1050 Ti (4GB VRAM)
This script configures the environment, installs dependencies, and validates the setup.
"""

import subprocess
import sys
import os
import json
from pathlib import Path

def run_command(cmd, description=""):
    """Run a shell command and handle errors."""
    print(f"Running: {cmd}")
    if description:
        print(f"Description: {description}")
    
    try:
        result = subprocess.run(cmd, shell=True, check=True, 
                              capture_output=True, text=True)
        print(f"✓ Success: {result.stdout.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Error: {e.stderr.strip()}")
        return False

def check_nvidia_setup():
    """Check if NVIDIA drivers and CUDA are properly configured."""
    print("\n=== Checking NVIDIA/CUDA Setup ===")
    
    # Check nvidia-smi
    if not run_command("nvidia-smi", "Checking NVIDIA driver"):
        print("Warning: NVIDIA driver not detected. GPU acceleration may not work.")
        return False
    
    # Check CUDA
    if not run_command("nvcc --version", "Checking CUDA toolkit"):
        print("Warning: CUDA toolkit not found. GPU acceleration may be limited.")
        return False
    
    # Check VRAM
    try:
        result = subprocess.run("nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits", 
                              shell=True, capture_output=True, text=True)
        vram_mb = int(result.stdout.strip().split('\n')[0])
        print(f"Detected VRAM: {vram_mb}MB")
        
        if vram_mb < 4000:
            print("Warning: VRAM less than 4GB detected. Performance may be severely limited.")
            return False
    except:
        print("Warning: Could not determine VRAM size.")
    
    return True

def setup_ollama():
    """Setup Ollama with optimized configuration for 4GB VRAM."""
    print("\n=== Setting up Ollama ===")
    
    # Install Ollama if not present
    if not run_command("ollama --version", "Checking Ollama installation"):
        print("Installing Ollama...")
        if not run_command("curl -fsSL https://ollama.com/install.sh | sh", 
                          "Downloading Ollama installer"):
            return False
    
    # Configure Ollama for 4GB VRAM
    ollama_config = {
        "OLLAMA_KEEP_ALIVE": "0",  # Unload models immediately
        "OLLAMA_NUM_GPU": "1",     # Use GPU
        "OLLAMA_MAX_LOADED_MODELS": "1",  # Only one model at a time
        "OLLAMA_NUM_PARALLEL": "1"        # Sequential processing
    }
    
    # Create Ollama config file
    config_dir = Path.home() / ".ollama"
    config_dir.mkdir(exist_ok=True)
    
    with open(config_dir / "config.json", "w") as f:
        json.dump(ollama_config, f, indent=2)
    
    print("✓ Ollama configured for 4GB VRAM optimization")
    return True

def install_dependencies():
    """Install Python dependencies with poetry."""
    print("\n=== Installing Python Dependencies ===")
    
    # Check if poetry is installed
    if not run_command("poetry --version", "Checking Poetry installation"):
        print("Installing Poetry...")
        if not run_command("pip install poetry", "Installing Poetry"):
            return False
    
    # Install dependencies
    if not run_command("poetry install", "Installing project dependencies"):
        return False
    
    # Install additional VRAM-optimized dependencies
    additional_deps = [
        "litellm",  # Lightweight LLM orchestration
        "accelerate",  # HuggingFace optimization
        "bitsandbytes",  # 4-bit quantization
    ]
    
    for dep in additional_deps:
        if not run_command(f"poetry add {dep}", f"Installing {dep}"):
            print(f"Warning: Could not install {dep}")
    
    return True

def pull_models():
    """Pull optimized models for 4GB VRAM."""
    print("\n=== Pulling Optimized Models ===")
    
    models = [
        "qwen2.5:3b",           # Planner
        "qwen2.5-coder:3b",     # Backend Developer  
        "qwen2.5-coder:1.5b",   # Frontend Developer
        "deepseek-coder:1.3b",  # Tester
        "gemma2:2b",           # Documenter
        "phi3:mini",           # RAG
        "nomic-embed-text"     # Embeddings
    ]
    
    for model in models:
        if not run_command(f"ollama pull {model}", f"Pulling {model}"):
            print(f"Warning: Could not pull {model}")
    
    return True

def setup_docker():
    """Setup Docker sandbox environment."""
    print("\n=== Setting up Docker Sandbox ===")
    
    # Check Docker
    if not run_command("docker --version", "Checking Docker installation"):
        print("Warning: Docker not found. Sandbox functionality will be limited.")
        return False
    
    # Build sandbox image
    if not run_command("docker build -t mini-sh-sandbox -f Dockerfile.sandbox .", 
                      "Building sandbox Docker image"):
        return False
    
    return True

def validate_setup():
    """Validate the complete setup."""
    print("\n=== Validation ===")
    
    checks = [
        ("Python 3.12+", "python --version", lambda x: "3.12" in x),
        ("Poetry", "poetry --version", lambda x: "Poetry" in x),
        ("Ollama", "ollama --version", lambda x: "ollama" in x.lower()),
        ("Docker", "docker --version", lambda x: "Docker" in x),
        ("NVIDIA GPU", "nvidia-smi", lambda x: "NVIDIA" in x),
    ]
    
    all_passed = True
    for name, cmd, validator in checks:
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if validator(result.stdout):
                print(f"✓ {name}: OK")
            else:
                print(f"✗ {name}: FAILED")
                all_passed = False
        except:
            print(f"✗ {name}: ERROR")
            all_passed = False
    
    return all_passed

def main():
    """Main setup function."""
    print("🚀 Mini Software House Setup for GTX 1050 Ti (4GB VRAM)")
    print("=" * 60)
    
    steps = [
        ("NVIDIA/CUDA Setup", check_nvidia_setup),
        ("Ollama Configuration", setup_ollama),
        ("Python Dependencies", install_dependencies),
        ("Model Download", pull_models),
        ("Docker Sandbox", setup_docker),
    ]
    
    results = []
    for step_name, step_func in steps:
        print(f"\n🔧 {step_name}")
        try:
            result = step_func()
            results.append((step_name, result))
        except Exception as e:
            print(f"✗ {step_name}: ERROR - {e}")
            results.append((step_name, False))
    
    # Final validation
    print(f"\n🔧 Final Validation")
    validation_passed = validate_setup()
    results.append(("Validation", validation_passed))
    
    # Summary
    print("\n" + "=" * 60)
    print("📋 SETUP SUMMARY")
    print("=" * 60)
    
    for step_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status} {step_name}")
    
    all_passed = all(result for _, result in results)
    
    if all_passed:
        print("\n🎉 Setup completed successfully!")
        print("Your Mini Software House is ready for GTX 1050 Ti (4GB VRAM)")
    else:
        print("\n⚠️  Setup completed with warnings/errors.")
        print("Some features may not work optimally.")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)