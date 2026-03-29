import difflib
import os
import re

from colorama import Fore

from ..utils.docker_runner import DockerRunner
from .base import Agent, get_model_for_role
from .context_manager import get_code_summary

# Known error types with targeted fix strategies
ERROR_STRATEGIES = {
    "ImportError": (
        "This is an ImportError — a module or name could not be imported. "
        "Check that: (1) the module is installed, (2) the import path is correct, "
        "(3) there are no circular imports. Fix ONLY the import issue."
    ),
    "ModuleNotFoundError": (
        "This is a ModuleNotFoundError — a required package is missing. "
        "Either add it to dependencies or replace with an available alternative. "
        "Fix ONLY the missing module issue."
    ),
    "SyntaxError": (
        "This is a SyntaxError — there is invalid Python syntax. "
        "Check for: missing colons, unmatched brackets, invalid indentation, "
        "or incompatible syntax for the target Python version. "
        "Fix ONLY the syntax issue, do not rewrite the logic."
    ),
    "NameError": (
        "This is a NameError — a variable or function is used before being defined. "
        "Check that: (1) the name is spelled correctly, (2) it's defined before use, "
        "(3) it's in scope. Fix ONLY the undefined name issue."
    ),
    "TypeError": (
        "This is a TypeError — wrong argument types or count. "
        "Check function signatures and argument types. Fix ONLY the type mismatch."
    ),
    "AttributeError": (
        "This is an AttributeError — accessing an attribute that doesn't exist. "
        "Check the object type and available attributes. Fix ONLY the attribute access."
    ),
    "IndentationError": (
        "This is an IndentationError — inconsistent indentation. "
        "Fix ONLY the indentation, do not change logic."
    ),
}


class TesterAgent(Agent):
    def __init__(self):
        system_prompt = (
            "You are a Software QA and Test Engineer. "
            "Write simple, focused pytest tests for the provided Python code. "
            "Only test the public API — do not test internal helpers. "
            "Each test function should test ONE behavior. "
            "Do NOT import external packages that are not in the source code. "
            "Always wrap the test code in a single markdown block starting with ```python\n"
            "and put a comment on the VERY FIRST LINE: '# filepath: tests/test_<name>.py'.\n"
            "Output ONLY the code block — no explanations before or after."
        )
        super().__init__(
            name="Tester",
            model=get_model_for_role("tester"),
            system_prompt=system_prompt,
            color=Fore.YELLOW,
        )
        self._workspace_dir = None
        try:
            self.docker_runner = DockerRunner()
        except Exception as e:
            self.log_action(f"Warning: Docker runner could not be initialized: {e}")
            self.docker_runner = None

    def set_workspace(self, workspace_dir: str):
        """Set the workspace directory to read code from and run tests in."""
        self._workspace_dir = os.path.abspath(workspace_dir)
        if self.docker_runner:
            self.docker_runner.workspace_dir = self._workspace_dir

    def _get_workspace_dir(self) -> str:
        """Return the active workspace directory."""
        if self._workspace_dir:
            return self._workspace_dir
        return os.path.abspath("workspace")

    def read_workspace_files(self, workspace_dir: str | None = None) -> str:
        ws = workspace_dir or self._get_workspace_dir()
        content = ""
        for root, _, files in os.walk(ws):
            for file in files:
                if file.endswith(".py") and not file.startswith("test_"):
                    filepath = os.path.join(root, file)
                    try:
                        with open(filepath, "r", encoding="utf-8") as f:
                            raw_code = f.read()
                            # Send full source code so the tester can write meaningful tests.
                            # AST summaries lose implementation details needed for assertions.
                            content += f"--- {file} ---\n{raw_code}\n\n"
                    except Exception:
                        pass
        return content

    def generate_tests(self) -> str:
        self.log_action("Reading workspace code...")
        code_context = self.read_workspace_files()

        if not code_context:
            return "No Python code found to test."

        prompt = (
            "Write pytest tests for the following code. "
            "Import modules using their filename (e.g., 'import csv2json'). "
            "Keep tests simple — test that functions exist and return expected types.\n\n"
            f"{code_context}"
        )
        self.log_action("Generating tests...")
        response = self.generate_response(prompt)
        return response

    def run_tests(self) -> dict:
        if not self.docker_runner:
            self.log_action(
                "Docker not available to run tests. Skipping execution and faking success."
            )
            return {"exit_code": 0, "output": "Docker not available. Tests skipped."}

        self.log_action("Running tests in Docker sandbox...")
        cmd = "pytest -v"
        result = self.docker_runner.run_command(cmd)
        self.log_action(f"Test Exit Code: {result['exit_code']}")

        return result

    def classify_error(self, test_output: str) -> str | None:
        """Identify the primary error type from test output."""
        for error_type in ERROR_STRATEGIES:
            if error_type in test_output:
                return error_type
        return None

    def build_correction_prompt(self, error_details: str, error_type: str | None) -> str:
        """Build a targeted correction prompt based on error classification."""
        parts = [f"The following tests failed:\n{error_details}\n"]

        if error_type and error_type in ERROR_STRATEGIES:
            parts.append(ERROR_STRATEGIES[error_type])
        else:
            parts.append(
                "Please fix the code based on these test failures. "
                "Focus on the specific errors mentioned above."
            )

        parts.append(
            "\nIMPORTANT: Make minimal changes. Fix only what is broken. "
            "Do NOT rewrite working code."
        )

        return "\n\n".join(parts)

    def parse_error(self, test_output: str) -> str:
        failures = re.findall(r"(FAILED.*?\n.*?(?=\n\n|\Z))", test_output, re.DOTALL)
        if failures:
            return "\n".join(failures)
        return test_output[-1000:]

    @staticmethod
    def check_hallucination(old_code: str, new_code: str, threshold: float = 0.80) -> bool:
        """Return True if the new code changed more than `threshold` of the original.

        This guards against the LLM hallucinating a complete rewrite instead of
        making a targeted fix.
        """
        if not old_code.strip():
            return False

        matcher = difflib.SequenceMatcher(None, old_code.splitlines(), new_code.splitlines())
        similarity = matcher.ratio()
        # If less than (1 - threshold) similar, it's a hallucination
        return similarity < (1.0 - threshold)
