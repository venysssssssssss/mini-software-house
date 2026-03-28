"""Tests for TesterAgent — parse_error and Docker fallback."""

from unittest.mock import MagicMock, patch

import pytest

from src.agents.tester import TesterAgent


@pytest.fixture
def tester():
    with (
        patch("src.agents.base.ollama"),
        patch("src.agents.tester.DockerRunner", side_effect=Exception("no docker")),
    ):
        return TesterAgent()


class TestParseError:
    def test_extracts_failure_lines(self, tester):
        output = (
            "collected 3 items\n\n"
            "FAILED test_main.py::test_add - AssertionError\n"
            "expected 4 but got 5\n\n"
            "FAILED test_main.py::test_sub - TypeError\n"
            "bad operand\n\n"
            "2 failed"
        )
        result = tester.parse_error(output)
        assert "FAILED test_main.py::test_add" in result
        assert "FAILED test_main.py::test_sub" in result

    def test_no_failures_returns_tail(self, tester):
        output = "some output " * 200  # long output
        result = tester.parse_error(output)
        assert len(result) <= 1000

    def test_empty_output(self, tester):
        result = tester.parse_error("")
        assert result == ""


class TestDockerFallback:
    def test_no_docker_returns_fake_success(self, tester):
        assert tester.docker_runner is None
        result = tester.run_tests()
        assert result["exit_code"] == 0
        assert "Docker not available" in result["output"]

    @patch("src.agents.base.ollama")
    def test_docker_available_runs_tests(self, mock_ollama):
        mock_runner = MagicMock()
        mock_runner.run_command.return_value = {"exit_code": 1, "output": "FAILED test_x"}

        with patch("src.agents.tester.DockerRunner", return_value=mock_runner):
            tester = TesterAgent()

        result = tester.run_tests()
        assert result["exit_code"] == 1
        mock_runner.run_command.assert_called_once_with("pytest -v")


class TestClassifyError:
    def test_import_error(self, tester):
        output = "ImportError: No module named 'flask'"
        assert tester.classify_error(output) == "ImportError"

    def test_syntax_error(self, tester):
        output = "SyntaxError: invalid syntax (app.py, line 5)"
        assert tester.classify_error(output) == "SyntaxError"

    def test_name_error(self, tester):
        output = "NameError: name 'undefined_var' is not defined"
        assert tester.classify_error(output) == "NameError"

    def test_type_error(self, tester):
        output = "TypeError: func() takes 1 positional argument but 2 were given"
        assert tester.classify_error(output) == "TypeError"

    def test_attribute_error(self, tester):
        output = "AttributeError: 'NoneType' object has no attribute 'get'"
        assert tester.classify_error(output) == "AttributeError"

    def test_indentation_error(self, tester):
        output = "IndentationError: unexpected indent"
        assert tester.classify_error(output) == "IndentationError"

    def test_module_not_found(self, tester):
        output = "ModuleNotFoundError: No module named 'nonexistent'"
        assert tester.classify_error(output) == "ModuleNotFoundError"

    def test_unknown_error(self, tester):
        output = "some generic failure output"
        assert tester.classify_error(output) is None

    def test_multiple_errors_returns_first_match(self, tester):
        output = "ImportError: ... followed by NameError: ..."
        assert tester.classify_error(output) == "ImportError"


class TestBuildCorrectionPrompt:
    def test_known_error_type(self, tester):
        prompt = tester.build_correction_prompt("FAILED test_x", "ImportError")
        assert "ImportError" in prompt
        assert "import path" in prompt
        assert "minimal changes" in prompt.lower()

    def test_unknown_error_type(self, tester):
        prompt = tester.build_correction_prompt("FAILED test_x", None)
        assert "fix the code" in prompt.lower()
        assert "minimal changes" in prompt.lower()

    def test_syntax_error_prompt(self, tester):
        prompt = tester.build_correction_prompt("SyntaxError: line 5", "SyntaxError")
        assert "SyntaxError" in prompt
        assert "syntax" in prompt.lower()


class TestHallucinationGuard:
    def test_small_change_is_ok(self):
        old = "def hello():\n    print('hello')\n"
        new = "def hello():\n    print('hello world')\n"
        assert TesterAgent.check_hallucination(old, new) is False

    def test_complete_rewrite_detected(self):
        old = "def hello():\n    print('hello')\n    return True\n"
        new = (
            "class Server:\n    def run(self):\n"
            "        import flask\n        app = flask.Flask(__name__)\n"
        )
        assert TesterAgent.check_hallucination(old, new) is True

    def test_empty_old_code_is_ok(self):
        assert TesterAgent.check_hallucination("", "new code") is False

    def test_identical_code_is_ok(self):
        code = "def f(): pass\n"
        assert TesterAgent.check_hallucination(code, code) is False

    def test_custom_threshold(self):
        old = "line1\nline2\nline3\n"
        new = "line1\nchanged2\nchanged3\n"
        # With strict threshold, more changes are flagged
        assert TesterAgent.check_hallucination(old, new, threshold=0.3) is True
        # With lenient threshold, they're ok
        assert TesterAgent.check_hallucination(old, new, threshold=0.95) is False


class TestReadWorkspace:
    def test_reads_python_files(self, tester, tmp_path):
        (tmp_path / "app.py").write_text("def hello(): pass")
        (tmp_path / "test_app.py").write_text("def test_hello(): pass")  # should be skipped
        (tmp_path / "readme.md").write_text("# docs")  # should be skipped

        content = tester.read_workspace_files(str(tmp_path))
        assert "app.py" in content
        assert "test_app" not in content
        assert "readme" not in content

    def test_empty_workspace(self, tester, tmp_path):
        content = tester.read_workspace_files(str(tmp_path))
        assert content == ""

    def test_summarizes_code(self, tester, tmp_path):
        code = "class MyClass:\n    def method(self):\n        pass\n"
        (tmp_path / "module.py").write_text(code)

        content = tester.read_workspace_files(str(tmp_path))
        assert "Summary" in content
        assert "class MyClass" in content
