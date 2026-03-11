import argparse
import sys
import os
import json
from .agents.executor import ExecutorAgent
from .agents.planner import PlannerAgent
from .agents.tester import TesterAgent
from .agents.documenter import DocumenterAgent
from colorama import init, Fore, Style

init(autoreset=True)

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

def main():
    parser = argparse.ArgumentParser(description="Mini Software House Orchestrator")
    parser.add_argument("--task", type=str, help="The programming task for the system")
    parser.add_argument("--max-retries", type=int, default=3, help="Max self-healing retries")
    parser.add_argument("--resume", action="store_true", help="Resume from last state")
    args = parser.parse_args()

    state = load_state() if args.resume else {"phase": 1, "plan": None, "retries": args.max_retries, "task": args.task}
    
    if not state.get("task"):
        print(Fore.RED + "Error: Task must be provided if not resuming.")
        sys.exit(1)

    print(Fore.BLUE + f"Starting Mini Software House Pipeline for task: {state['task']}")

    planner = PlannerAgent()
    executor = ExecutorAgent()
    tester = TesterAgent()
    documenter = DocumenterAgent()

    # Step 1: Planning
    if state["phase"] <= 1:
        print(Fore.CYAN + "\n--- Phase 1: Planning ---")
        plan = planner.plan_task(state["task"])
        if not plan:
            print(Fore.RED + "Failed to generate a valid plan. Exiting.")
            sys.exit(1)
        
        state["plan"] = plan
        state["phase"] = 2
        save_state(state)
        print(Fore.CYAN + "Plan generated successfully.")

    # Step 2: Execution
    if state["phase"] <= 2:
        print(Fore.GREEN + "\n--- Phase 2: Execution ---")
        plan = state["plan"]
        exec_task = f"User Request: {state['task']}\n\nPlan:\nArchitecture: {plan.get('architecture')}\nFiles to create: {plan.get('files_to_create')}\nSteps: {plan.get('logical_steps')}\n\nImplement the required files."
        response, saved_files = executor.execute_task(exec_task)
        
        if not saved_files:
            print(Fore.RED + "Executor failed to create any files. Exiting.")
            sys.exit(1)

        print(Fore.GREEN + f"Files created: {', '.join(saved_files)}")
        state["phase"] = 3
        save_state(state)

    # Step 3: Testing & Self-Healing
    if state["phase"] <= 3:
        print(Fore.YELLOW + "\n--- Phase 3: Testing & Self-Healing ---")
        tests_passed = False

        while state["retries"] > 0:
            print(Fore.YELLOW + f"Generating tests for workspace (Retries left: {state['retries']})...")
            tester.generate_tests()
            
            print(Fore.YELLOW + "Running tests...")
            test_result = tester.run_tests()
            exit_code = test_result.get("exit_code", -1)
            
            if exit_code == 0:
                print(Fore.GREEN + "Tests passed successfully!")
                tests_passed = True
                break
            else:
                print(Fore.RED + f"Tests failed with exit code {exit_code}.")
                error_output = tester.parse_error(test_result.get('output', 'Unknown error'))
                print(Fore.YELLOW + "Sending feedback to Executor...")
                
                feedback_task = f"The previous code failed the tests. Please fix the errors.\n\nError output:\n{error_output}"
                executor.execute_task(feedback_task)
                state["retries"] -= 1
                save_state(state)

        if not tests_passed:
            print(Fore.RED + "Max retries reached. Tests are still failing. Proceeding to documentation anyway.")
            
        state["phase"] = 4
        save_state(state)

    # Step 4: Documentation
    if state["phase"] <= 4:
        print(Fore.MAGENTA + "\n--- Phase 4: Documentation ---")
        documenter.generate_documentation()
        print(Fore.MAGENTA + "Documentation generated successfully.")
        
        state["phase"] = 5
        save_state(state)

    print(Fore.BLUE + "\nPipeline finished.")

if __name__ == "__main__":
    main()
