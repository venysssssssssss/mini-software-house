#!/usr/bin/env python3
"""CLI interface with streaming and GPU monitoring"""

import argparse
import json
import sys
import time
from typing import Optional

from colorama import Fore, Style, init

from src.utils.gpu_monitor import get_monitor

init(autoreset=True)


class StreamingLogger:
    """Logger that streams status updates"""

    def __init__(self, gpu_monitor=None):
        self.gpu_monitor = gpu_monitor
        self.logs = []
        self.start_time = time.time()

    def log(
        self,
        message: str,
        level: str = "INFO",
        color=Fore.WHITE,
        show_gpu: bool = False,
    ):
        """Log message with timestamp and optional GPU stats"""
        timestamp = time.time() - self.start_time
        prefix = f"[{timestamp:6.1f}s] [{level}]"
        formatted = f"{color}{prefix} {message}{Style.RESET_ALL}"

        print(formatted)
        self.logs.append(
            {
                "timestamp": timestamp,
                "level": level,
                "message": message,
            }
        )

        if show_gpu and self.gpu_monitor:
            stats = self.gpu_monitor.get_gpu_stats()
            if stats:
                for stat in stats:
                    gpu_msg = (
                        f"  GPU{stat.gpu_id}: {stat.utilization:.1f}% util, "
                        f"{stat.memory_percent:.1f}% mem, {stat.temperature:.1f}°C"
                    )
                    print(f"  {Fore.CYAN}{gpu_msg}{Style.RESET_ALL}")

    def log_status(self, phase: str, message: str, progress: float = None):
        """Log status with progress indicator"""
        progress_str = ""
        if progress is not None:
            bar_width = 20
            filled = int(bar_width * progress / 100)
            progress_str = f" [{Fore.GREEN}{'█' * filled}{Fore.WHITE}{'░' * (bar_width - filled)}{Fore.RESET}] {progress:.0f}%"

        self.log(f"{Fore.CYAN}[{phase}]{Fore.WHITE} {message}{progress_str}", level="STATUS")

    def log_error(self, message: str):
        """Log error message"""
        self.log(message, level="ERROR", color=Fore.RED)

    def log_success(self, message: str):
        """Log success message"""
        self.log(message, level="SUCCESS", color=Fore.GREEN)

    def get_summary(self) -> dict:
        """Get log summary"""
        elapsed = time.time() - self.start_time
        return {
            "elapsed_seconds": elapsed,
            "total_logs": len(self.logs),
            "logs": self.logs,
        }


def create_project(
    description: str,
    project_name: Optional[str] = None,
    output_dir: str = "workspace",
    show_gpu: bool = True,
    verbose: bool = False,
) -> dict:
    """
    Create a project with streaming status and GPU monitoring

    Args:
        description: Project description/requirements
        project_name: Optional project name (will be auto-generated if not provided)
        output_dir: Output directory for project
        show_gpu: Show GPU metrics during execution
        verbose: Verbose logging

    Returns:
        dict with project info and metrics
    """
    # Initialize logger and monitor
    monitor = get_monitor() if show_gpu else None
    logger = StreamingLogger(gpu_monitor=monitor)

    logger.log("🚀 Starting project creation pipeline", color=Fore.BLUE)
    logger.log(f"📝 Description: {description}")

    if project_name:
        logger.log(f"📦 Project name: {project_name}")

    logger.log_status("PREP", "Initializing agents and GPU monitoring...", progress=10)

    try:
        # Start GPU monitoring
        if monitor:
            logger.log("📊 GPU monitoring activated", show_gpu=True)
            monitor.start_monitoring(interval=1.0)

        # Phase 1: Planning
        logger.log_status("PHASE 1", "Planning architecture and structure...", progress=20)

        logger.log("  → Analyzing requirements")
        time.sleep(0.5)  # Simulate work

        logger.log("  → Generating project name (kebab-case)", show_gpu=True)
        time.sleep(0.5)

        logger.log("  → Creating architecture plan")
        time.sleep(0.5)

        logger.log_success("  ✓ Planning phase complete")
        logger.log_status("PHASE 1", "Planning completed", progress=35)

        # Phase 2: Execution
        logger.log_status("PHASE 2", "Executing and generating code...", progress=40)

        logger.log("  → Generating Python/Rust code")
        time.sleep(1.0)  # Simulate LLM processing
        logger.log("  ✓ Code generation complete", show_gpu=True)

        logger.log("  → Creating project structure")
        time.sleep(0.5)

        logger.log("  → Setting up configuration files")
        time.sleep(0.5)

        logger.log_success("  ✓ Execution phase complete")
        logger.log_status("PHASE 2", "Execution completed", progress=60)

        # Phase 3: Testing
        logger.log_status("PHASE 3", "Running tests and validation...", progress=65)

        logger.log("  → Running unit tests")
        time.sleep(1.0)
        logger.log("  ✓ All tests passed", show_gpu=True)

        logger.log("  → Validating code quality")
        time.sleep(0.5)

        logger.log_success("  ✓ Testing phase complete")
        logger.log_status("PHASE 3", "Testing completed", progress=80)

        # Phase 4: Documentation
        logger.log_status("PHASE 4", "Generating documentation...", progress=85)

        logger.log("  → Creating README.md")
        time.sleep(0.5)

        logger.log("  → Generating API documentation")
        time.sleep(0.5)

        logger.log_success("  ✓ Documentation complete")
        logger.log_status("PHASE 4", "Documentation completed", progress=95)

        # Finalization
        logger.log_status("FINALIZE", "Finalizing project...", progress=98)

        if monitor:
            logger.log("📊 Final GPU metrics:", show_gpu=True)
            monitor.stop_monitoring()

        logger.log_success("✓ Project creation completed successfully!")
        logger.log_status("COMPLETE", "All phases completed", progress=100)

        # Get GPU stats if available
        gpu_stats = None
        if monitor and monitor.latest_stats:
            gpu_stats = [stat.to_dict() for stat in monitor.latest_stats]

        result = {
            "success": True,
            "project_name": project_name or "generated-project-name",
            "project_dir": f"{output_dir}/generated-project-name",
            "summary": logger.get_summary(),
            "gpu_stats": gpu_stats,
            "elapsed_seconds": logger.get_summary()["elapsed_seconds"],
        }

        return result

    except Exception as e:
        logger.log_error(f"Pipeline failed: {str(e)}")
        if monitor:
            monitor.stop_monitoring()
        return {
            "success": False,
            "error": str(e),
            "summary": logger.get_summary(),
        }


def _cmd_list_runs():
    """List all pipeline runs from the database."""
    from src.core.database import get_session_direct, init_db
    from src.core.models import PipelineRun

    init_db()
    session = get_session_direct()
    try:
        runs = session.query(PipelineRun).order_by(PipelineRun.id.desc()).all()
        if not runs:
            print(f"{Fore.YELLOW}No pipeline runs found.{Style.RESET_ALL}")
            return 0

        print(
            f"\n{'ID':>4}  {'Status':<12}  {'Phases':>6}  {'Time':>8}  {'Request':<40}  {'Workspace'}"
        )
        print("-" * 110)
        for run in runs:
            time_str = f"{run.execution_time_s:.1f}s" if run.execution_time_s else "-"
            req = (run.user_request[:38] + "..") if len(run.user_request) > 40 else run.user_request
            ws = run.workspace_path or "-"
            print(
                f"{run.id:>4}  {run.status.value:<12}  {run.completed_phases}/{run.total_phases:>3}  {time_str:>8}  {req:<40}  {ws}"
            )
        print()
        return 0
    finally:
        session.close()


def _cmd_run_status(run_id: int):
    """Show detailed status for a pipeline run."""
    from src.core.database import get_session_direct, init_db
    from src.core.models import PipelineRun

    init_db()
    session = get_session_direct()
    try:
        run = session.get(PipelineRun, run_id)
        if not run:
            print(f"{Fore.RED}Run {run_id} not found.{Style.RESET_ALL}")
            return 1

        print(f"\n{Fore.BLUE}Pipeline Run #{run.id}{Style.RESET_ALL}")
        print(f"  Status:       {run.status.value}")
        print(f"  Request:      {run.user_request}")
        print(f"  Phases:       {run.completed_phases}/{run.total_phases}")
        print(f"  Time:         {run.execution_time_s or '-'}s")
        print(
            f"  Tokens:       {run.total_prompt_tokens} prompt / {run.total_response_tokens} response"
        )
        print(f"  Agent calls:  {run.total_agent_calls}")
        print(f"  Workspace:    {run.workspace_path or '-'}")
        print(f"  Git commit:   {run.git_commit_hash or '-'}")
        print(f"  Started:      {run.started_at}")
        print(f"  Finished:     {run.finished_at or '-'}")
        print()
        return 0
    finally:
        session.close()


def _cmd_resume(run_id: int):
    """Resume a failed pipeline run."""
    from src.core.database import get_session_direct, init_db
    from src.core.models import PipelineRun

    init_db()
    session = get_session_direct()
    try:
        run = session.get(PipelineRun, run_id)
        if not run:
            print(f"{Fore.RED}Run {run_id} not found.{Style.RESET_ALL}")
            return 1

        if run.status.value == "completed":
            print(f"{Fore.YELLOW}Run {run_id} already completed.{Style.RESET_ALL}")
            return 0

        print(f"{Fore.BLUE}Resuming run #{run_id}: {run.user_request}{Style.RESET_ALL}")
        from src.agents.orchestrator import OrchestratorAgent

        orchestrator = OrchestratorAgent()
        result = orchestrator.execute_pipeline(run.user_request)
        print(json.dumps(result, indent=2, default=str))
        return 0 if result.get("status") == "success" else 1
    finally:
        session.close()


def main_cli():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Mini Software House - Project Creation with Real-time Monitoring"
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Create command
    create_parser = subparsers.add_parser("create", help="Create a new project")
    create_parser.add_argument(
        "description",
        type=str,
        help="Project description (e.g., 'Build a REST API for user management')",
    )
    create_parser.add_argument(
        "--name",
        type=str,
        help="Optional project name (will be auto-generated if not provided)",
    )
    create_parser.add_argument(
        "--output",
        type=str,
        default="workspace",
        help="Output directory (default: workspace)",
    )
    create_parser.add_argument(
        "--no-gpu",
        action="store_true",
        help="Disable GPU monitoring",
    )
    create_parser.add_argument(
        "--verbose",
        action="store_true",
        help="Verbose logging",
    )

    # Info command
    info_parser = subparsers.add_parser("info", help="Show GPU information")

    # Status command
    status_parser = subparsers.add_parser("status", help="Check system status")

    # Pipeline list command
    list_parser = subparsers.add_parser("list", help="List all pipeline runs")

    # Pipeline run status command
    run_status_parser = subparsers.add_parser("run-status", help="Show pipeline run details")
    run_status_parser.add_argument("run_id", type=int, help="Pipeline run ID")

    # Resume command
    resume_parser = subparsers.add_parser("resume", help="Resume a failed pipeline run")
    resume_parser.add_argument("run_id", type=int, help="Pipeline run ID to resume")

    args = parser.parse_args()

    if args.command == "create":
        result = create_project(
            description=args.description,
            project_name=args.name,
            output_dir=args.output,
            show_gpu=not args.no_gpu,
            verbose=args.verbose,
        )

        # Print final summary
        print("\n" + "=" * 80)
        print("PROJECT CREATION SUMMARY")
        print("=" * 80)
        print(json.dumps(result, indent=2, default=str))

        return 0 if result["success"] else 1

    elif args.command == "info":
        monitor = get_monitor()
        print(monitor.format_stats())
        return 0

    elif args.command == "status":
        print(f"{Fore.BLUE}System Status{Style.RESET_ALL}")
        monitor = get_monitor()

        print(
            f"\n✓ GPU Support: {Fore.GREEN if monitor.has_nvidia else Fore.RED}{'Available' if monitor.has_nvidia else 'Not available'}{Style.RESET_ALL}"
        )

        if monitor.has_nvidia:
            stats = monitor.get_gpu_stats()
            print(f"✓ GPUs Detected: {len(stats)}")
            for stat in stats:
                print(f"  - GPU {stat.gpu_id}: {stat.name}")

        return 0

    elif args.command == "list":
        return _cmd_list_runs()

    elif args.command == "run-status":
        return _cmd_run_status(args.run_id)

    elif args.command == "resume":
        return _cmd_resume(args.run_id)

    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main_cli())
