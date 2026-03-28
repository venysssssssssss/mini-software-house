import argparse
import json
import os
import sys

from .agents.documenter import DocumenterAgent
from .agents.executor import ExecutorAgent
from .agents.planner import PlannerAgent
from .agents.tester import TesterAgent
from .core.database import get_session_direct, init_db
from .core.events import EventBus
from .core.logger import get_logger
from .core.models import AgentLog, Project, Task, TaskStatus

logger = get_logger("main")

STATE_FILE = "workspace/state.json"


def save_state(state):
    os.makedirs("workspace", exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=4)


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"phase": 1, "plan": None, "retries": 0}


def _log_to_db(task_id, agent_name, level, message, data=None):
    session = get_session_direct()
    try:
        entry = AgentLog(
            task_id=task_id,
            agent_name=agent_name,
            level=level,
            message=message,
            structured_data=json.dumps(data) if data else None,
        )
        session.add(entry)
        session.commit()
    finally:
        session.close()


def main():
    parser = argparse.ArgumentParser(description="Mini Software House Orchestrator")
    parser.add_argument("--task", type=str, help="The programming task for the system")
    parser.add_argument("--max-retries", type=int, default=3, help="Max self-healing retries")
    parser.add_argument("--resume", action="store_true", help="Resume from last state")
    args = parser.parse_args()

    state = (
        load_state()
        if args.resume
        else {"phase": 1, "plan": None, "retries": args.max_retries, "task": args.task}
    )

    if not state.get("task"):
        logger.error("no_task_provided")
        sys.exit(1)

    # Initialize DB
    init_db()

    # Create DB records
    session = get_session_direct()
    try:
        project = Project(name=state["task"][:120], path="workspace")
        session.add(project)
        session.commit()
        session.refresh(project)

        db_task = Task(
            project_id=project.id,
            description=state["task"],
            status=TaskStatus.IN_PROGRESS,
        )
        session.add(db_task)
        session.commit()
        session.refresh(db_task)
        task_id = db_task.id
    finally:
        session.close()

    logger.info("pipeline.starting", task=state["task"])
    EventBus.publish("pipeline.started", {"request": state["task"]})

    planner = PlannerAgent()
    executor = ExecutorAgent()
    tester = TesterAgent()
    documenter = DocumenterAgent()

    # Step 1: Planning
    if state["phase"] <= 1:
        logger.info("phase.starting", phase="planning")
        EventBus.publish("phase.started", {"phase": "planning"})
        plan = planner.plan_task(state["task"])
        if not plan:
            logger.error("planning.failed")
            _log_to_db(task_id, "planner", "ERROR", "Failed to generate plan")
            sys.exit(1)

        state["plan"] = plan
        state["phase"] = 2
        save_state(state)
        logger.info("phase.completed", phase="planning")
        EventBus.publish("phase.completed", {"phase": "planning"})
        _log_to_db(task_id, "planner", "INFO", "Plan generated", plan)

    # Step 2: Execution
    if state["phase"] <= 2:
        logger.info("phase.starting", phase="execution")
        EventBus.publish("phase.started", {"phase": "development"})
        plan = state["plan"]
        exec_task = (
            f"User Request: {state['task']}\n\n"
            f"Plan:\nArchitecture: {plan.get('architecture')}\n"
            f"Files to create: {plan.get('files_to_create')}\n"
            f"Steps: {plan.get('logical_steps')}\n\nImplement the required files."
        )
        response, saved_files = executor.execute_task(exec_task)

        if not saved_files:
            logger.error("execution.no_files_created")
            _log_to_db(task_id, "executor", "ERROR", "No files created")
            sys.exit(1)

        logger.info("execution.files_created", files=saved_files)
        _log_to_db(task_id, "executor", "INFO", "Files created", {"files": saved_files})
        EventBus.publish("phase.completed", {"phase": "development"})
        state["phase"] = 3
        save_state(state)

    # Step 3: Testing & Self-Healing
    if state["phase"] <= 3:
        logger.info("phase.starting", phase="testing")
        EventBus.publish("phase.started", {"phase": "testing"})
        tests_passed = False

        while state["retries"] > 0:
            logger.info("testing.attempt", retries_left=state["retries"])
            tester.generate_tests()

            test_result = tester.run_tests()
            exit_code = test_result.get("exit_code", -1)

            if exit_code == 0:
                logger.info("testing.passed")
                _log_to_db(task_id, "tester", "INFO", "Tests passed")
                tests_passed = True
                break
            else:
                logger.warning("testing.failed", exit_code=exit_code)
                EventBus.publish(
                    "test.failed",
                    {"exit_code": exit_code, "retries_left": state["retries"]},
                )
                error_output = tester.parse_error(test_result.get("output", "Unknown error"))
                _log_to_db(
                    task_id,
                    "tester",
                    "WARNING",
                    "Tests failed",
                    {"error": error_output[:500]},
                )

                feedback_task = (
                    "The previous code failed the tests. "
                    f"Please fix the errors.\n\nError output:\n{error_output}"
                )
                executor.execute_task(feedback_task)
                state["retries"] -= 1
                save_state(state)

        if not tests_passed:
            logger.error("testing.max_retries_exhausted")
            _log_to_db(task_id, "tester", "ERROR", "Max retries reached, tests still failing")

        EventBus.publish("phase.completed", {"phase": "testing"})
        state["phase"] = 4
        save_state(state)

    # Step 4: Documentation
    if state["phase"] <= 4:
        logger.info("phase.starting", phase="documentation")
        EventBus.publish("phase.started", {"phase": "documentation"})
        documenter.generate_documentation()
        logger.info("phase.completed", phase="documentation")
        EventBus.publish("phase.completed", {"phase": "documentation"})
        _log_to_db(task_id, "documenter", "INFO", "Documentation generated")

        state["phase"] = 5
        save_state(state)

    # Mark DB task complete
    session = get_session_direct()
    try:
        db_task = session.get(Task, task_id)
        if db_task:
            db_task.status = TaskStatus.COMPLETED
            session.add(db_task)
            session.commit()
    finally:
        session.close()

    logger.info("pipeline.finished")
    EventBus.publish("pipeline.finished", {"status": "success"})


if __name__ == "__main__":
    main()
