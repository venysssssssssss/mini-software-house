#!/usr/bin/env python3
"""Docker setup validation script"""

import subprocess
import json
import sys
from pathlib import Path
from typing import Tuple, Dict, Any

# Colors
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"


def run_command(cmd: str, check: bool = False) -> Tuple[int, str, str]:
    """Run shell command and return (code, stdout, stderr)"""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except subprocess.TimeoutExpired:
        return 1, "", "Command timed out"
    except Exception as e:
        return 1, "", str(e)


def check_prerequisites() -> Dict[str, bool]:
    """Check if all prerequisites are installed"""
    print(f"\n{BLUE}Checking Prerequisites...{RESET}")
    results = {}

    # Docker
    code, _, _ = run_command("docker --version")
    results["docker"] = code == 0
    status = f"{GREEN}✓{RESET}" if results["docker"] else f"{RED}✗{RESET}"
    print(f"  {status} Docker: {run_command('docker --version')[1]}")

    # Docker Compose
    code, _, _ = run_command("docker-compose --version")
    results["compose"] = code == 0
    status = f"{GREEN}✓{RESET}" if results["compose"] else f"{RED}✗{RESET}"
    print(f"  {status} Docker Compose: {run_command('docker-compose --version')[1]}")

    # NVIDIA Docker Runtime
    code, output, _ = run_command("docker run --rm --gpus all nvidia/cuda:12.1.1-runtime-ubuntu22.04 nvidia-smi -L")
    results["nvidia_docker"] = code == 0
    status = f"{GREEN}✓{RESET}" if results["nvidia_docker"] else f"{YELLOW}⚠{RESET}"
    msg = "Enabled" if results["nvidia_docker"] else "Not available (GPU disabled)"
    print(f"  {status} NVIDIA Docker Runtime: {msg}")

    # nvidia-smi
    code, _, _ = run_command("nvidia-smi -L")
    results["nvidia_smi"] = code == 0
    status = f"{GREEN}✓{RESET}" if results["nvidia_smi"] else f"{YELLOW}⚠{RESET}"
    print(f"  {status} NVIDIA GPU: {'Available' if results['nvidia_smi'] else 'Not available'}")

    return results


def check_docker_configuration() -> Dict[str, Any]:
    """Check Docker configuration"""
    print(f"\n{BLUE}Checking Docker Configuration...{RESET}")
    config = {}

    # Check if docker daemon is running
    code, _, _ = run_command("docker ps")
    config["daemon_running"] = code == 0
    status = f"{GREEN}✓{RESET}" if config["daemon_running"] else f"{RED}✗{RESET}"
    print(f"  {status} Docker daemon running: {config['daemon_running']}")

    # Check disk space
    code, output, _ = run_command("docker system df --format 'json'")
    if code == 0:
        try:
            data = json.loads(output)
            config["docker_disk_usage"] = data
            print(f"  {GREEN}✓{RESET} Docker disk usage: {data['Total']}")
        except:
            print(f"  {YELLOW}⚠{RESET} Could not parse disk usage")

    return config


def check_docker_images() -> Dict[str, bool]:
    """Check if required Docker images are available"""
    print(f"\n{BLUE}Checking Docker Images...{RESET}")
    images_needed = {
        "pytorch/pytorch:2.1.2-cuda12.1-runtime-ubuntu22.04": "PyTorch with CUDA",
        "ollama/ollama:latest": "Ollama LLM",
        "postgres:16-alpine": "PostgreSQL",
        "redis:7-alpine": "Redis",
    }

    results = {}
    for image, desc in images_needed.items():
        code, _, _ = run_command(f"docker image inspect {image}")
        exists = code == 0
        results[image] = exists

        if exists:
            print(f"  {GREEN}✓{RESET} {desc}: Found ({image})")
        else:
            print(f"  {YELLOW}⚠{RESET} {desc}: Not found (will pull on docker-compose up)")

    return results


def check_docker_files() -> Dict[str, bool]:
    """Check if required Docker files exist"""
    print(f"\n{BLUE}Checking Docker Configuration Files...{RESET}")
    files = {
        "Dockerfile": "Main application image",
        "docker-compose.yml": "Service orchestration",
        "docker-entrypoint.sh": "Container entrypoint",
        ".dockerignore": "Build optimization",
    }

    results = {}
    for filename, desc in files.items():
        path = Path(filename)
        exists = path.exists()
        results[filename] = exists
        status = f"{GREEN}✓{RESET}" if exists else f"{RED}✗{RESET}"
        print(f"  {status} {desc}: {filename}")

    return results


def check_cli_module() -> bool:
    """Check if CLI module exists"""
    print(f"\n{BLUE}Checking CLI Module...{RESET}")
    cli_path = Path("src/cli.py")
    gpu_path = Path("src/utils/gpu_monitor.py")

    cli_exists = cli_path.exists()
    gpu_exists = gpu_path.exists()

    print(f"  {'✓' if cli_exists else '✗'} CLI module: src/cli.py")
    print(f"  {'✓' if gpu_exists else '✗'} GPU monitor: src/utils/gpu_monitor.py")

    return cli_exists and gpu_exists


def check_makefile_targets() -> Dict[str, bool]:
    """Check if Makefile has Docker targets"""
    print(f"\n{BLUE}Checking Makefile Targets...{RESET}")

    makefile = Path("Makefile")
    if not makefile.exists():
        print(f"  {RED}✗{RESET} Makefile not found")
        return {}

    with open(makefile) as f:
        content = f.read()

    targets = [
        "docker-build",
        "docker-up",
        "docker-down",
        "docker-create",
        "docker-gpu",
    ]

    results = {}
    for target in targets:
        exists = f"docker-{target.split('-')[1]}" in content or target in content
        results[target] = exists
        status = f"{GREEN}✓{RESET}" if exists else f"{RED}✗{RESET}"
        print(f"  {status} {target}")

    return results


def test_build() -> bool:
    """Test building Docker image"""
    print(f"\n{BLUE}Testing Docker Build...{RESET}")
    print("  (This may take several minutes on first run)")

    code, stdout, stderr = run_command(
        "docker build -t mini-software-house:test .",
        check=True
    )

    if code == 0:
        print(f"  {GREEN}✓{RESET} Docker build successful")
        return True
    else:
        print(f"  {RED}✗{RESET} Docker build failed")
        if stderr:
            print(f"    Error: {stderr[:200]}")
        return False


def generate_report(results: Dict[str, Any]) -> str:
    """Generate a summary report"""
    report = f"\n{BLUE}{'='*60}{RESET}\n"
    report += f"{BLUE}Docker Setup Validation Report{RESET}\n"
    report += f"{BLUE}{'='*60}{RESET}\n\n"

    # Prerequisites
    prereqs = results.get("prerequisites", {})
    required = ["docker", "compose"]
    all_required = all(prereqs.get(k) for k in required)
    status = f"{GREEN}PASS{RESET}" if all_required else f"{RED}FAIL{RESET}"
    report += f"Prerequisites: {status}\n"

    # Files
    files = results.get("files", {})
    all_files = all(files.values())
    status = f"{GREEN}PASS{RESET}" if all_files else f"{YELLOW}WARNING{RESET}"
    report += f"Docker Files: {status}\n"

    # CLI Module
    cli_ok = results.get("cli_module", False)
    status = f"{GREEN}PASS{RESET}" if cli_ok else f"{RED}FAIL{RESET}"
    report += f"CLI Module: {status}\n"

    # Summary
    overall_ok = (
        all_required and all_files and cli_ok and
        results.get("docker_config", {}).get("daemon_running", False)
    )

    report += f"\n{BLUE}{'='*60}{RESET}\n"
    report += f"Overall Status: {f'{GREEN}✓ READY TO USE{RESET}' if overall_ok else f'{RED}✗ NEEDS SETUP{RESET}'}\n"
    report += f"{BLUE}{'='*60}{RESET}\n"

    return report


def main():
    """Main validation routine"""
    print(f"\n{BLUE}Mini Software House - Docker Setup Validator{RESET}")
    print(f"{BLUE}{'='*60}{RESET}")

    results = {}

    # Run checks
    results["prerequisites"] = check_prerequisites()
    results["docker_config"] = check_docker_configuration()
    results["docker_images"] = check_docker_images()
    results["files"] = check_docker_files()
    results["cli_module"] = check_cli_module()
    results["makefile"] = check_makefile_targets()

    # Generate report
    report = generate_report(results)
    print(report)

    # Recommendations
    print(f"\n{BLUE}Recommendations:{RESET}")

    prereqs = results.get("prerequisites", {})
    if not prereqs.get("docker"):
        print(f"  {YELLOW}→{RESET} Install Docker: https://docs.docker.com/get-docker/")

    if not prereqs.get("compose"):
        print(f"  {YELLOW}→{RESET} Install Docker Compose: https://docs.docker.com/compose/install/")

    if not prereqs.get("nvidia_docker"):
        print(f"  {YELLOW}→{RESET} Install NVIDIA Docker: https://github.com/NVIDIA/nvidia-docker")

    config = results.get("docker_config", {})
    if not config.get("daemon_running"):
        print(f"  {YELLOW}→{RESET} Start Docker daemon: `sudo systemctl start docker`")

    print(f"\n{BLUE}Next Steps:{RESET}")
    print(f"  1. {GREEN}make docker-build{RESET}     - Build Docker image")
    print(f"  2. {GREEN}make docker-up{RESET}         - Start services")
    print(f"  3. {GREEN}make docker-create DESC=\"...\"  - Create a project")
    print(f"\nDocumentation: {GREEN}cat README.DOCKER.md{RESET}\n")

    return 0 if (prereqs.get("docker") and config.get("daemon_running")) else 1


if __name__ == "__main__":
    sys.exit(main())
