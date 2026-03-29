import argparse
import json
import sys

from .agents.orchestrator import OrchestratorAgent
from .core.logger import get_logger

logger = get_logger("main")


def main():
    parser = argparse.ArgumentParser(description="Mini Software House Orchestrator")
    parser.add_argument("--task", type=str, help="The programming task for the system")
    parser.add_argument("--max-retries", type=int, default=3, help="Max self-healing retries")
    parser.add_argument("--resume", action="store_true", help="Resume from last state")
    parser.add_argument(
        "--git", action="store_true", help="Initialize git repo after successful run"
    )
    args = parser.parse_args()

    if not args.task and not args.resume:
        logger.error("no_task_provided")
        print("Error: --task is required (or use --resume)")
        sys.exit(1)

    task = args.task or "Resumed task"

    orchestrator = OrchestratorAgent(git_enabled=args.git)
    result = orchestrator.execute_pipeline(task)

    print("\n" + "=" * 60)
    print("PIPELINE RESULTS")
    print("=" * 60)
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
