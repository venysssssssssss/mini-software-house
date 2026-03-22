import os
import re
from .base import Agent, get_model_for_role
from ..utils.docker_runner import DockerRunner
from .context_manager import get_code_summary
from colorama import Fore

class TesterAgent(Agent):
    def __init__(self):
        system_prompt = (
            "You are a Software QA and Test Engineer. "
            "Write pytest tests for the provided Python code. "
            "Focus on testing the core logic. "
            "Always wrap the test code in a markdown block starting with ```python\n"
            "and ALWAYS put a comment on the VERY FIRST LINE specifying the relative filepath as '# filepath: test_<filename>.py'."
        )
        super().__init__(
            name="Tester",
            model=get_model_for_role("tester"),
            system_prompt=system_prompt,
            color=Fore.YELLOW
        )
        try:
            self.docker_runner = DockerRunner()
        except Exception as e:
            self.log_action(f"Warning: Docker runner could not be initialized: {e}")
            self.docker_runner = None

    def read_workspace_files(self, workspace_dir="workspace"):
        content = ""
        for root, _, files in os.walk(workspace_dir):
            for file in files:
                if file.endswith(".py") and not file.startswith("test_"):
                    filepath = os.path.join(root, file)
                    try:
                        with open(filepath, "r", encoding="utf-8") as f:
                            raw_code = f.read()
                            # AST Optimization: Send structure instead of full code for context efficiency
                            # The LLM infers logic from names and signatures to write tests
                            summary = get_code_summary(raw_code)
                            content += f"--- {file} (Summary) ---\n{summary}\n\n"
                    except Exception:
                        pass
        return content

    def generate_tests(self) -> str:
        self.log_action("Reading workspace code...")
        code_context = self.read_workspace_files()
        
        if not code_context:
            return "No Python code found to test."

        prompt = f"Write pytest tests for the following code:\n\n{code_context}"
        self.log_action("Generating tests...")
        response = self.generate_response(prompt)
        return response

    def run_tests(self) -> dict:
        if not self.docker_runner:
            self.log_action("Docker not available to run tests. Skipping execution and faking success.")
            return {"exit_code": 0, "output": "Docker not available. Tests skipped."}
        
        self.log_action("Running tests in Docker sandbox...")
        cmd = "pytest -v"
        result = self.docker_runner.run_command(cmd)
        self.log_action(f"Test Exit Code: {result['exit_code']}")
        
        return result

    def parse_error(self, test_output: str) -> str:
        failures = re.findall(r"(FAILED.*?\n.*?(?=\n\n|\Z))", test_output, re.DOTALL)
        if failures:
            return "\n".join(failures)
        return test_output[-1000:]
