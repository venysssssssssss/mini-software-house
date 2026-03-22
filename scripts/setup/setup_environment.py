#!/usr/bin/env python3
"""
Setup script for Mini Software House optimized for GTX 1050 Ti (4GB VRAM).

This script configures the environment, installs dependencies, and validates the setup.

Usage:
    python scripts/setup/setup_environment.py [--check-only] [--skip-models]
"""

import subprocess
import sys
import os
import json
import argparse
from pathlib import Path


def run_command(cmd, description="", check=True):
    """Run a shell command and handle errors gracefully."""
    print(f"  🔧 {description or cmd}")
    
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            check=check,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            print(f"     ✅ Success")
            return True
        else:
            if result.stderr:
                print(f"     ⚠️  {result.stderr.strip()[:100]}")
            return False
    except Exception as e:
        print(f"     ❌ Error: {str(e)[:100]}")
        return False


def check_system_requirements():
    """Check if system meets minimum requirements."""
    print("\n📋 Checking System Requirements")
    print("-" * 50)
    
    checks = [
        ("python3", "Python 3.12+"),
        ("rustc", "Rust toolchain"),
        ("docker", "Docker (optional)"),
        ("nvidia-smi", "NVIDIA GPU (optional)"),
    ]
    
    for cmd, desc in checks:
        if run_command(f"command -v {cmd}", f"Checking {desc}", check=False):
            print(f"     ✓ {desc} installed")
        else:
            print(f"     ✗ {desc} NOT installed")
    
    return True


def setup_python_environment():
    """Setup Python virtual environment and dependencies."""
    print("\n🐍 Setting up Python Environment")
    print("-" * 50)
    
    # Check Poetry
    if not run_command("poetry --version", "Checking Poetry", check=False):
        print("     Installing Poetry...")
        run_command("pip install poetry", "Installing Poetry")
    
    # Install dependencies
    run_command("poetry install", "Installing project dependencies")
    
    print("     ✅ Python environment ready")
    return True


def setup_rust_environment():
    """Setup Rust workspace."""
    print("\n🦀 Setting up Rust Environment")
    print("-" * 50)
    
    if not os.path.exists("src/rust/Cargo.toml"):
        print("     ✗ Rust workspace not found")
        return False
    
    os.chdir("src/rust")
    
    # Build workspace
    success = run_command("cargo build --release", "Building Rust modules (this may take a while)")
    
    os.chdir("../..")
    
    if success:
        print("     ✅ Rust workspace built successfully")
    
    return success


def setup_ollama(skip=False):
    """Setup Ollama and download models."""
    print("\n🤖 Setting up Ollama")
    print("-" * 50)
    
    if skip:
        print("     Skipping Ollama setup")
        return True
    
    # Check if Ollama is installed
    if not run_command("ollama --version", "Checking Ollama", check=False):
        print("     ℹ️  Ollama not installed")
        print("     Install from: https://ollama.com/download")
        return False
    
    # Configure Ollama
    print("     Configuring Ollama for 4GB VRAM...")
    config_dir = Path.home() / ".ollama"
    config_dir.mkdir(exist_ok=True)
    
    ollama_config = {
        "OLLAMA_KEEP_ALIVE": "0",
        "OLLAMA_NUM_GPU": "1",
        "OLLAMA_MAX_LOADED_MODELS": "1",
        "OLLAMA_NUM_PARALLEL": "1",
    }
    
    config_file = config_dir / "config.json"
    with open(config_file, "w") as f:
        json.dump(ollama_config, f, indent=2)
    
    print("     ✅ Ollama configured")
    
    # Pull models
    models_to_pull = [
        "qwen2.5:3b",
        "qwen2.5-coder:3b",
        "qwen2.5-coder:1.5b",
        "deepseek-coder:1.3b",
        "gemma2:2b",
        "phi3:mini",
        "nomic-embed-text",
    ]
    
    print("     📥 Pulling models (this may take 30-60 minutes)...")
    for model in models_to_pull:
        run_command(f"ollama pull {model}", f"Pulling {model}")
    
    print("     ✅ Models setup complete")
    return True


def setup_docker():
    """Setup Docker sandbox."""
    print("\n🐋 Setting up Docker Sandbox")
    print("-" * 50)
    
    if not run_command("docker --version", "Checking Docker", check=False):
        print("     ℹ️  Docker not installed (optional)")
        return False
    
    if os.path.exists("Dockerfile.sandbox"):
        run_command(
            "docker build -t mini-sh-sandbox -f Dockerfile.sandbox .",
            "Building sandbox image"
        )
        print("     ✅ Docker sandbox ready")
    
    return True


def validate_setup():
    """Validate complete setup."""
    print("\n✨ Validating Setup")
    print("-" * 50)
    
    checks = [
        ("pyproject.toml", "Python project config"),
        ("src/rust/Cargo.toml", "Rust workspace"),
        ("src/main.py", "Main entry point"),
        ("src/agents/orchestrator.py", "Orchestrator agent"),
        ("src/core/database.py", "Database module"),
    ]
    
    all_good = True
    for filepath, desc in checks:
        if os.path.exists(filepath):
            print(f"     ✓ {desc}")
        else:
            print(f"     ✗ {desc} MISSING")
            all_good = False
    
    return all_good


def main():
    """Main setup orchestration."""
    parser = argparse.ArgumentParser(
        description="Setup Mini Software House environment"
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Only check requirements without installing",
    )
    parser.add_argument(
        "--skip-models",
        action="store_true",
        help="Skip downloading Ollama models",
    )
    
    args = parser.parse_args()
    
    print("\n" + "=" * 50)
    print("🏗️  Mini Software House - Setup Script")
    print("=" * 50)
    
    try:
        check_system_requirements()
        
        if args.check_only:
            print("\n✅ Check complete. Exiting.")
            return 0
        
        setup_python_environment()
        setup_rust_environment()
        setup_ollama(skip=args.skip_models)
        setup_docker()
        
        if validate_setup():
            print("\n" + "=" * 50)
            print("✅ SETUP COMPLETE!")
            print("=" * 50)
            print("\n🚀 Next steps:")
            print("  1. Activate Poetry shell: poetry shell")
            print("  2. Run pipeline: python src/main.py --task 'Your task'")
            print("  3. Monitor: streamlit run app.py")
            return 0
        else:
            print("\n⚠️  Setup completed with warnings")
            return 1
    
    except KeyboardInterrupt:
        print("\n\n❌ Setup cancelled by user")
        return 1
    except Exception as e:
        print(f"\n❌ Setup failed: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
