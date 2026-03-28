"""Tests for ExecutorAgent — parse_and_save_code with various formats."""

from unittest.mock import patch

import pytest

from src.agents.executor import ExecutorAgent, FileManager


@pytest.fixture
def file_manager(tmp_path):
    return FileManager(workspace_dir=str(tmp_path))


@pytest.fixture
def executor(tmp_path):
    with patch("src.agents.base.ollama"):
        agent = ExecutorAgent()
        agent.file_manager = FileManager(workspace_dir=str(tmp_path))
        return agent


class TestFileManager:
    def test_save_file(self, file_manager, tmp_path):
        file_manager.save_file("hello.py", "print('hi')")
        assert (tmp_path / "hello.py").read_text() == "print('hi')"

    def test_save_nested_file(self, file_manager, tmp_path):
        file_manager.save_file("sub/dir/app.py", "code")
        assert (tmp_path / "sub" / "dir" / "app.py").read_text() == "code"

    def test_path_traversal_blocked(self, file_manager):
        with pytest.raises(ValueError, match="Security error"):
            file_manager.save_file("../../etc/passwd", "hacked")

    def test_absolute_path_traversal_blocked(self, file_manager):
        with pytest.raises(ValueError, match="Security error"):
            file_manager.save_file("/tmp/evil.py", "hacked")


class TestParseAndSaveCode:
    def test_python_filepath_comment(self, executor, tmp_path):
        response = '```python\n# filepath: main.py\nprint("hello")\n```'
        saved = executor.parse_and_save_code(response)
        assert saved == ["main.py"]
        assert (tmp_path / "main.py").exists()

    def test_html_filepath_comment(self, executor, tmp_path):
        response = "```html\n<!-- filepath: index.html -->\n<h1>Hi</h1>\n```"
        saved = executor.parse_and_save_code(response)
        assert saved == ["index.html"]

    def test_css_filepath_comment(self, executor, tmp_path):
        response = "```css\n/* filepath: styles.css */\nbody { margin: 0; }\n```"
        saved = executor.parse_and_save_code(response)
        assert saved == ["styles.css"]

    def test_js_filepath_comment(self, executor, tmp_path):
        response = '```javascript\n// filepath: app.js\nconsole.log("hi");\n```'
        saved = executor.parse_and_save_code(response)
        assert saved == ["app.js"]

    def test_fallback_inferred_filename(self, executor, tmp_path):
        response = '```python\nprint("no filepath comment")\n```'
        saved = executor.parse_and_save_code(response)
        assert saved == ["main.py"]

    def test_fallback_html_inferred(self, executor, tmp_path):
        response = "```html\n<h1>No filepath</h1>\n```"
        saved = executor.parse_and_save_code(response)
        assert saved == ["index.html"]

    def test_multiple_code_blocks(self, executor, tmp_path):
        response = (
            "```python\n# filepath: app.py\nfrom flask import Flask\n```\n\n"
            "```python\n# filepath: models.py\nclass User: pass\n```"
        )
        saved = executor.parse_and_save_code(response)
        assert "app.py" in saved
        assert "models.py" in saved
        assert len(saved) == 2

    def test_no_code_blocks_returns_empty(self, executor):
        saved = executor.parse_and_save_code("Just some text, no code blocks.")
        assert saved == []

    def test_filepath_case_insensitive(self, executor, tmp_path):
        response = "```python\n# FILEPATH: upper.py\ncode\n```"
        saved = executor.parse_and_save_code(response)
        assert saved == ["upper.py"]

    def test_duplicate_fallback_names_get_counter(self, executor, tmp_path):
        response = '```python\nprint("a")\n```\n\n```python\nprint("b")\n```'
        saved = executor.parse_and_save_code(response)
        assert len(saved) == 2
        assert "main.py" in saved
        assert "main_1.py" in saved


# ---- Sprint 2: Executor Improvements ----


class TestFileManagerReadExisting:
    def test_reads_existing_files(self, tmp_path):
        fm = FileManager(workspace_dir=str(tmp_path))
        (tmp_path / "app.py").write_text("from flask import Flask")
        (tmp_path / "index.html").write_text("<h1>Hi</h1>")

        files = fm.read_existing_files()
        assert "app.py" in files
        assert "index.html" in files
        assert "Flask" in files["app.py"]

    def test_empty_workspace_returns_empty(self, tmp_path):
        fm = FileManager(workspace_dir=str(tmp_path))
        assert fm.read_existing_files() == {}

    def test_ignores_non_code_files(self, tmp_path):
        fm = FileManager(workspace_dir=str(tmp_path))
        (tmp_path / "readme.md").write_text("# Docs")
        (tmp_path / "data.csv").write_text("a,b,c")
        (tmp_path / "app.py").write_text("code")

        files = fm.read_existing_files()
        assert "app.py" in files
        assert "readme.md" not in files
        assert "data.csv" not in files


class TestContextSummary:
    @patch("src.agents.base.ollama")
    def test_build_context_with_existing_files(self, mock_ollama, tmp_path):
        executor = ExecutorAgent()
        executor.file_manager = FileManager(workspace_dir=str(tmp_path))
        (tmp_path / "models.py").write_text("class User:\n    def save(self):\n        pass\n")

        summary = executor._build_context_summary()
        assert "models.py" in summary
        assert "class User:" in summary

    @patch("src.agents.base.ollama")
    def test_build_context_empty_workspace(self, mock_ollama, tmp_path):
        executor = ExecutorAgent()
        executor.file_manager = FileManager(workspace_dir=str(tmp_path))

        summary = executor._build_context_summary()
        assert summary == ""


class TestExecuteTaskWithPlan:
    @patch("src.agents.base.ollama")
    def test_plan_context_included_in_prompt(self, mock_ollama, tmp_path):
        mock_ollama.chat.return_value = {
            "message": {"content": "```python\n# filepath: app.py\ncode\n```"},
            "prompt_eval_count": 10,
            "eval_count": 5,
        }

        executor = ExecutorAgent()
        executor.file_manager = FileManager(workspace_dir=str(tmp_path))

        plan = {
            "project_name": "my-api",
            "architecture": "Flask REST API",
            "dependencies": ["flask", "sqlalchemy"],
            "files_to_create": ["app.py", "models.py"],
        }

        executor.execute_task("Create app.py", plan=plan)

        # Verify the LLM was called with plan context
        call_args = mock_ollama.chat.call_args
        messages = call_args[1]["messages"]
        user_msg = messages[-1]["content"]  # last user message
        assert "Flask REST API" in user_msg
        assert "flask" in user_msg
        assert "my-api" in user_msg

    @patch("src.agents.base.ollama")
    def test_no_plan_still_works(self, mock_ollama, tmp_path):
        mock_ollama.chat.return_value = {
            "message": {"content": "```python\n# filepath: app.py\ncode\n```"},
        }

        executor = ExecutorAgent()
        executor.file_manager = FileManager(workspace_dir=str(tmp_path))

        response, saved = executor.execute_task("Create a simple app")
        assert saved == ["app.py"]
