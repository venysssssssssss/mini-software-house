"""Export training data from SQLite to JSONL for fine-tuning.

Reads AgentLog and DPOTuple tables, produces:
- SFT data: chat-format JSONL per agent (system/human/gpt turns)
- DPO data: chosen/rejected pairs per agent from correction cycles

Usage:
    python scripts/finetune/export_training_data.py --all --output data/finetune
    python scripts/finetune/export_training_data.py --agent planner --output data/finetune
"""

import argparse
import json
import sys
from pathlib import Path

from sqlmodel import Session, col, create_engine, select

# Add project root to path so we can import src.*
_project_root = Path(__file__).resolve().parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from src.core.models import AgentLog, DPOTuple, PipelineRun, TaskStatus  # noqa: E402

# System prompts per agent role (must match src/agents/*.py)
SYSTEM_PROMPTS = {
    "Planner": (
        "You are a Software Architect and Planner. "
        "You MUST respond ONLY with a valid, parsable JSON object. "
        "DO NOT include markdown formatting, DO NOT include backticks (```), "
        "and DO NOT add any explanatory text.\n"
        "The JSON must have exactly the following structure:\n"
        "{\n"
        '  "project_name": "action-object-purpose-in-kebab-case",\n'
        '  "architecture": "brief description",\n'
        '  "files_to_create": ["file1.py", "file2.py"],\n'
        '  "dependencies": ["lib1", "lib2"],\n'
        '  "logical_steps": ["step 1", "step 2"]\n'
        "}\n"
        "IMPORTANT: project_name MUST be in kebab-case format."
    ),
    "Executor": (
        "You are an expert software developer. "
        "Write clean, efficient, and well-documented code. "
        "Always output the complete code. "
        "For every file you create or modify, wrap the code in a markdown block "
        "and ALWAYS put a comment on the VERY FIRST LINE inside the block "
        "specifying the relative filepath."
    ),
    "Tester": (
        "You are a Software QA and Test Engineer. "
        "Write pytest tests for the provided Python code. "
        "Focus on testing the core logic. "
        "Always wrap the test code in a markdown block starting with ```python\n"
        "and ALWAYS put a comment on the VERY FIRST LINE specifying "
        "the relative filepath as '# filepath: test_<filename>.py'."
    ),
    "Documenter": (
        "You are a Technical Writer. Write clear, comprehensive markdown documentation. "
        "Use the provided code context to explain how the system works."
    ),
}

# Map agent names to fine-tuning role names
AGENT_TO_ROLE = {
    "Planner": "planner",
    "Executor": "executor",
    "Tester": "tester",
    "Documenter": "documenter",
}

ALL_AGENTS = list(AGENT_TO_ROLE.keys())


def get_engine(db_path: str = "software_house.db"):
    """Create a SQLModel engine for the given database path."""
    return create_engine(f"sqlite:///{db_path}", echo=False)


def export_sft_data(
    engine,
    agent_name: str,
    output_dir: Path,
) -> int:
    """Export SFT data as chat-format JSONL.

    For each successful pipeline run, extracts the agent's prompt/response pair
    and formats it as a conversation with system/human/gpt roles.

    Returns the number of examples exported.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    role = AGENT_TO_ROLE.get(agent_name, agent_name.lower())
    output_path = output_dir / f"{role}.jsonl"
    system_prompt = SYSTEM_PROMPTS.get(agent_name, "")

    count = 0
    with Session(engine) as session:
        # Get successful pipeline runs
        runs = session.exec(
            select(PipelineRun).where(PipelineRun.status == TaskStatus.COMPLETED)
        ).all()

        for run in runs:
            # Get agent logs for this run that are successful LLM calls
            logs = session.exec(
                select(AgentLog).where(
                    AgentLog.pipeline_run_id == run.id,
                    AgentLog.agent_name == agent_name,
                    AgentLog.message == "llm_call",
                    AgentLog.success == True,  # noqa: E712
                )
            ).all()

            for log in logs:
                # Extract structured data if available
                extra = {}
                if log.structured_data:
                    try:
                        extra = json.loads(log.structured_data)
                    except json.JSONDecodeError:
                        pass

                # Build conversation entry
                entry = {
                    "conversations": [
                        {"from": "system", "value": system_prompt},
                        {"from": "human", "value": run.user_request},
                        {"from": "gpt", "value": extra.get("response", run.user_request)},
                    ]
                }
                count += 1
                with open(output_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(entry, ensure_ascii=False) + "\n")

        # Also include DPO tuples where the original code passed (first-pass success)
        passing_tuples = session.exec(
            select(DPOTuple).where(
                DPOTuple.agent_name == agent_name.lower(),
                DPOTuple.test_result == "pass",
            )
        ).all()

        for t in passing_tuples:
            entry = {
                "conversations": [
                    {"from": "system", "value": system_prompt},
                    {"from": "human", "value": t.prompt},
                    {"from": "gpt", "value": t.generated_code},
                ]
            }
            count += 1
            with open(output_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    return count


def export_dpo_data(
    engine,
    agent_name: str,
    output_dir: Path,
) -> int:
    """Export DPO data as chosen/rejected pairs.

    DPO pairs come from DPOTuple where correction_successful is True:
    - rejected = generated_code (original, failed)
    - chosen = corrected_code (fixed version that passed tests)

    Returns the number of pairs exported.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    role = AGENT_TO_ROLE.get(agent_name, agent_name.lower())
    output_path = output_dir / f"{role}.jsonl"

    count = 0
    with Session(engine) as session:
        tuples = session.exec(
            select(DPOTuple).where(
                DPOTuple.agent_name == agent_name.lower(),
                DPOTuple.correction_successful == True,  # noqa: E712
                col(DPOTuple.corrected_code).is_not(None),
            )
        ).all()

        for t in tuples:
            entry = {
                "prompt": t.prompt,
                "chosen": t.corrected_code,
                "rejected": t.generated_code,
            }
            count += 1
            with open(output_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    return count


def validate_jsonl(path: Path) -> tuple[bool, int, str]:
    """Validate that every line in a JSONL file is valid JSON.

    Returns (is_valid, line_count, error_message).
    """
    if not path.exists():
        return False, 0, f"File not found: {path}"

    line_count = 0
    with open(path, encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                json.loads(line)
                line_count += 1
            except json.JSONDecodeError as e:
                return False, i, f"Invalid JSON at line {i}: {e}"

    return True, line_count, ""


def export_all(engine, output_base: Path, agents: list[str] | None = None) -> dict:
    """Export SFT and DPO data for all (or specified) agents.

    Returns a summary dict: {agent: {sft_count, dpo_count}}.
    """
    if agents is None:
        agents = ALL_AGENTS

    sft_dir = output_base / "sft"
    dpo_dir = output_base / "dpo"

    summary = {}
    for agent_name in agents:
        sft_count = export_sft_data(engine, agent_name, sft_dir)
        dpo_count = export_dpo_data(engine, agent_name, dpo_dir)
        summary[agent_name] = {"sft_count": sft_count, "dpo_count": dpo_count}

    return summary


def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(description="Export training data for fine-tuning")
    parser.add_argument("--all", action="store_true", help="Export for all agents")
    parser.add_argument(
        "--agent",
        choices=["planner", "executor", "tester", "documenter"],
        help="Export for a specific agent",
    )
    parser.add_argument("--output", default="data/finetune", help="Output directory")
    parser.add_argument("--db", default="software_house.db", help="Database path")
    parser.add_argument("--validate", action="store_true", help="Validate existing JSONL files")

    args = parser.parse_args(argv)
    output = Path(args.output)
    engine = get_engine(args.db)

    if args.validate:
        for subdir in ["sft", "dpo"]:
            d = output / subdir
            if not d.exists():
                print(f"Directory not found: {d}")
                continue
            for jsonl_file in sorted(d.glob("*.jsonl")):
                valid, count, err = validate_jsonl(jsonl_file)
                status = "OK" if valid else "FAIL"
                print(f"  [{status}] {jsonl_file} — {count} entries" + (f" ({err})" if err else ""))
        return

    if not args.all and not args.agent:
        parser.error("Specify --all or --agent <name>")

    if args.all:
        agents = None  # all agents
    else:
        # Map CLI role name to agent class name
        role_to_agent = {v: k for k, v in AGENT_TO_ROLE.items()}
        agents = [role_to_agent[args.agent]]

    summary = export_all(engine, output, agents)

    print("\nExport Summary")
    print("-" * 40)
    for agent, counts in summary.items():
        role = AGENT_TO_ROLE.get(agent, agent)
        print(f"  {role}: {counts['sft_count']} SFT, {counts['dpo_count']} DPO")
    print(f"\nOutput: {output.resolve()}")


if __name__ == "__main__":
    main()
