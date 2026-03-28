"""Tests for PlannerAgent — JSON plan structure validation."""

import json
from unittest.mock import patch

import pytest

from src.agents.planner import PlannerAgent


@pytest.fixture
def planner():
    with patch("src.agents.base.ollama"):
        return PlannerAgent()


class TestPlanTask:
    @patch("src.agents.base.ollama")
    def test_valid_plan_returned(self, mock_ollama):
        plan_json = json.dumps(
            {
                "project_name": "build-task-api",
                "architecture": "FastAPI REST API",
                "files_to_create": ["main.py", "models.py"],
                "dependencies": ["fastapi", "uvicorn"],
                "logical_steps": ["Create models", "Create routes"],
            }
        )
        mock_ollama.chat.return_value = {"message": {"content": plan_json}}

        planner = PlannerAgent()
        result = planner.plan_task("Create a task API")

        assert result["architecture"] == "FastAPI REST API"
        assert "main.py" in result["files_to_create"]
        assert "fastapi" in result["dependencies"]
        assert len(result["logical_steps"]) == 2

    @patch("src.agents.base.ollama")
    def test_invalid_json_returns_empty(self, mock_ollama):
        mock_ollama.chat.return_value = {"message": {"content": "not json at all"}}

        planner = PlannerAgent()
        result = planner.plan_task("Do something")

        assert result == {}

    @patch("src.agents.base.ollama")
    def test_missing_keys_still_returns_data(self, mock_ollama):
        partial = json.dumps({"project_name": "partial-plan", "architecture": "monolith"})
        mock_ollama.chat.return_value = {"message": {"content": partial}}

        planner = PlannerAgent()
        result = planner.plan_task("Partial plan")

        assert result["architecture"] == "monolith"
        # Missing keys are logged as warning but data is returned
        assert "files_to_create" not in result


class TestKebabCaseValidation:
    def test_valid_kebab_case(self, planner):
        assert planner._is_valid_kebab_case("build-task-api") is True
        assert planner._is_valid_kebab_case("create-chat-app") is True
        assert planner._is_valid_kebab_case("a-b") is True

    def test_invalid_kebab_case(self, planner):
        assert planner._is_valid_kebab_case("") is False
        assert planner._is_valid_kebab_case("SingleWord") is False
        assert planner._is_valid_kebab_case("has spaces") is False
        assert planner._is_valid_kebab_case("has_underscores") is False
        assert planner._is_valid_kebab_case("UPPERCASE-BAD") is False
        assert planner._is_valid_kebab_case("no") is False  # needs at least one hyphen

    @patch("src.agents.base.ollama")
    def test_invalid_name_triggers_naming_engine(self, mock_ollama):
        plan_json = json.dumps(
            {
                "project_name": "BadName",
                "architecture": "REST",
                "files_to_create": ["main.py"],
                "dependencies": [],
                "logical_steps": ["step"],
            }
        )
        mock_ollama.chat.return_value = {"message": {"content": plan_json}}

        with patch("src.agents.planner.PlannerAgent._is_valid_kebab_case", return_value=False):
            with patch("src.naming_engine.NamingEngine") as MockNE:
                MockNE.return_value.generate_project_name_from_task.return_value = "fixed-name"
                planner = PlannerAgent()
                result = planner.plan_task("test")

        assert result["project_name"] == "fixed-name"
