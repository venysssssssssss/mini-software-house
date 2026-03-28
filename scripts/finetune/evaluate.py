"""A/B evaluation: base models vs fine-tuned models.

Compares pipeline performance metrics between model configurations:
- First-pass success rate (tests pass without correction)
- JSON validity rate (planner)
- Correction loop count (average retries needed)
- Token efficiency (output tokens per successful generation)

Usage:
    python scripts/finetune/evaluate.py --config base --output results/eval_base.json
    python scripts/finetune/evaluate.py --config finetuned --output results/eval_ft.json
    python scripts/finetune/evaluate.py --compare results/eval_base.json results/eval_ft.json
"""

import argparse
import json
import sys
from pathlib import Path

from sqlmodel import Session, create_engine, func, select

_project_root = Path(__file__).resolve().parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from src.core.models import AgentLog, DPOTuple, PipelineRun, TaskStatus  # noqa: E402

# Standard evaluation tasks (diverse complexity)
EVAL_TASKS = [
    "Build a simple key-value store with a CLI interface",
    "Create a markdown link checker that reports broken URLs",
    "Build a CSV to JSON converter with validation",
    "Create a simple HTTP health check monitor",
    "Build a file deduplication tool using SHA256 hashes",
    "Create a stack-based calculator with undo support",
    "Build a log file analyzer that extracts error patterns",
    "Create a simple task scheduler with priority queue",
    "Build a text-based password generator with entropy check",
    "Create a directory tree visualizer with file size info",
]


def get_engine(db_path: str = "software_house.db"):
    """Create engine for the given database."""
    return create_engine(f"sqlite:///{db_path}", echo=False)


def collect_metrics(engine, run_ids: list[int] | None = None) -> dict:
    """Collect pipeline metrics from the database.

    If run_ids is provided, only consider those runs.
    Otherwise, consider all completed runs.
    """
    with Session(engine) as session:
        # Get completed runs
        query = select(PipelineRun).where(PipelineRun.status == TaskStatus.COMPLETED)
        if run_ids:
            query = query.where(PipelineRun.id.in_(run_ids))  # type: ignore[union-attr]
        runs = session.exec(query).all()

        if not runs:
            return {
                "total_runs": 0,
                "first_pass_success_rate": 0.0,
                "avg_corrections": 0.0,
                "avg_total_tokens": 0.0,
                "avg_latency_ms": 0.0,
                "avg_agent_calls": 0.0,
            }

        total_runs = len(runs)
        total_tokens = sum(r.total_prompt_tokens + r.total_response_tokens for r in runs)
        total_latency = sum(r.total_latency_ms for r in runs)
        total_agent_calls = sum(r.total_agent_calls for r in runs)

        # First-pass success: runs where no DPO correction tuple exists
        first_pass_success = 0
        total_corrections = 0
        for run in runs:
            correction_count = session.exec(
                select(func.count(DPOTuple.id)).where(
                    DPOTuple.pipeline_run_id == run.id,
                    DPOTuple.test_result != "pass",
                )
            ).one()
            if correction_count == 0:
                first_pass_success += 1
            total_corrections += correction_count

        # JSON validity from planner logs
        planner_total = 0
        planner_success = 0
        for run in runs:
            planner_logs = session.exec(
                select(AgentLog).where(
                    AgentLog.pipeline_run_id == run.id,
                    AgentLog.agent_name == "Planner",
                    AgentLog.message == "llm_call",
                )
            ).all()
            for log in planner_logs:
                planner_total += 1
                if log.success:
                    planner_success += 1

        return {
            "total_runs": total_runs,
            "first_pass_success_rate": first_pass_success / total_runs if total_runs else 0.0,
            "avg_corrections": total_corrections / total_runs if total_runs else 0.0,
            "avg_total_tokens": total_tokens / total_runs if total_runs else 0.0,
            "avg_latency_ms": total_latency / total_runs if total_runs else 0.0,
            "avg_agent_calls": total_agent_calls / total_runs if total_runs else 0.0,
            "json_validity_rate": (
                planner_success / planner_total if planner_total else 0.0
            ),
        }


def compare_results(base_path: str, ft_path: str) -> dict:
    """Compare two evaluation result files and compute deltas."""
    base = json.loads(Path(base_path).read_text())
    ft = json.loads(Path(ft_path).read_text())

    comparison = {}
    for key in base.get("metrics", base):
        base_metrics = base.get("metrics", base)
        ft_metrics = ft.get("metrics", ft)

        b_val = base_metrics.get(key, 0)
        f_val = ft_metrics.get(key, 0)

        if isinstance(b_val, (int, float)) and isinstance(f_val, (int, float)):
            delta = f_val - b_val
            pct = (delta / b_val * 100) if b_val != 0 else 0
            comparison[key] = {
                "base": b_val,
                "finetuned": f_val,
                "delta": round(delta, 4),
                "pct_change": round(pct, 2),
            }

    return comparison


def format_comparison(comparison: dict) -> str:
    """Format comparison dict as a human-readable table."""
    lines = [
        "Metric                        Base      FT        Delta     Change",
        "-" * 70,
    ]

    # Metrics where higher is better
    higher_better = {"first_pass_success_rate", "json_validity_rate", "total_runs"}
    # Metrics where lower is better
    lower_better = {"avg_corrections", "avg_total_tokens", "avg_latency_ms"}

    for key, vals in comparison.items():
        base = vals["base"]
        ft = vals["finetuned"]
        delta = vals["delta"]
        pct = vals["pct_change"]

        # Determine if change is positive
        if key in higher_better:
            indicator = "+" if delta > 0 else ("-" if delta < 0 else "=")
        elif key in lower_better:
            indicator = "+" if delta < 0 else ("-" if delta > 0 else "=")
        else:
            indicator = ""

        base_str = f"{base:.4f}" if isinstance(base, float) else str(base)
        ft_str = f"{ft:.4f}" if isinstance(ft, float) else str(ft)
        delta_str = f"{delta:+.4f}" if isinstance(delta, float) else f"{delta:+}"

        lines.append(
            f"{key:<30}{base_str:<10}{ft_str:<10}{delta_str:<10}{pct:+.1f}% {indicator}"
        )

    return "\n".join(lines)


def run_evaluation(config: str, output_path: str, db_path: str = "software_house.db"):
    """Run evaluation and save results.

    In 'base' config, uses existing runs (before fine-tuning deployment).
    In 'finetuned' config, uses runs made after fine-tuned models were deployed.
    """
    engine = get_engine(db_path)
    metrics = collect_metrics(engine)

    result = {
        "config": config,
        "metrics": metrics,
        "eval_tasks": EVAL_TASKS,
    }

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2))
    print(f"Evaluation saved to {output}")
    print(json.dumps(metrics, indent=2))

    return result


def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(description="A/B evaluation for fine-tuned models")
    parser.add_argument(
        "--config",
        choices=["base", "finetuned"],
        help="Model configuration to evaluate",
    )
    parser.add_argument("--output", help="Output JSON path for evaluation results")
    parser.add_argument("--db", default="software_house.db", help="Database path")
    parser.add_argument(
        "--compare",
        nargs=2,
        metavar=("BASE_JSON", "FT_JSON"),
        help="Compare two evaluation result files",
    )

    args = parser.parse_args(argv)

    if args.compare:
        comparison = compare_results(args.compare[0], args.compare[1])
        print(format_comparison(comparison))
        return comparison

    if not args.config or not args.output:
        parser.error("--config and --output are required when not using --compare")

    return run_evaluation(args.config, args.output, args.db)


if __name__ == "__main__":
    main()
