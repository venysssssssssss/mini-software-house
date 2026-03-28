"""Tests for scripts/finetune/export_training_data.py — 100% coverage."""

import json

import pytest
from sqlmodel import Session, SQLModel, create_engine

from scripts.finetune.export_training_data import (
    AGENT_TO_ROLE,
    ALL_AGENTS,
    SYSTEM_PROMPTS,
    export_all,
    export_dpo_data,
    export_sft_data,
    get_engine,
    main,
    validate_jsonl,
)
from src.core.models import AgentLog, DPOTuple, PipelineRun, Project, Task, TaskStatus


@pytest.fixture
def db_engine():
    """Create an in-memory SQLite engine with all tables."""
    engine = create_engine("sqlite://", echo=False)
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture
def populated_db(db_engine):
    """Seed the database with sample pipeline data for export tests."""
    with Session(db_engine) as session:
        # Create project + task
        project = Project(name="test-project", path="workspace")
        session.add(project)
        session.commit()
        session.refresh(project)

        task = Task(
            project_id=project.id, description="Build a todo API", status=TaskStatus.COMPLETED
        )
        session.add(task)
        session.commit()
        session.refresh(task)

        # Create a completed pipeline run
        run = PipelineRun(
            project_id=project.id,
            task_id=task.id,
            user_request="Build a todo API",
            status=TaskStatus.COMPLETED,
        )
        session.add(run)
        session.commit()
        session.refresh(run)

        # Create agent logs (successful LLM calls)
        for agent_name in ["Planner", "Executor", "Tester", "Documenter"]:
            log = AgentLog(
                task_id=task.id,
                pipeline_run_id=run.id,
                agent_name=agent_name,
                model="test-model",
                level="INFO",
                message="llm_call",
                prompt_tokens=50,
                response_tokens=100,
                latency_ms=500.0,
                success=True,
                structured_data=json.dumps({"response": f"Response from {agent_name}"}),
            )
            session.add(log)

        # Create DPO tuples: one passing, one with successful correction
        dpo_pass = DPOTuple(
            pipeline_run_id=run.id,
            agent_name="executor",
            prompt="Build a todo API",
            generated_code="def hello(): pass",
            test_result="pass",
        )
        session.add(dpo_pass)

        dpo_corrected = DPOTuple(
            pipeline_run_id=run.id,
            agent_name="executor",
            prompt="Fix the imports",
            generated_code="import broken",
            test_result="ImportError",
            corrected_code="import flask",
            error_type="ImportError",
            correction_successful=True,
        )
        session.add(dpo_corrected)

        # DPO tuple with correction_successful=False (should NOT be exported as DPO)
        dpo_failed = DPOTuple(
            pipeline_run_id=run.id,
            agent_name="executor",
            prompt="Fix syntax",
            generated_code="bad code",
            test_result="SyntaxError",
            corrected_code="still bad",
            error_type="SyntaxError",
            correction_successful=False,
        )
        session.add(dpo_failed)

        # DPO tuple without corrected_code (should NOT be exported as DPO)
        dpo_no_correction = DPOTuple(
            pipeline_run_id=run.id,
            agent_name="tester",
            prompt="Write tests",
            generated_code="def test(): pass",
            test_result="FAILED",
            correction_successful=True,  # but no corrected_code
        )
        session.add(dpo_no_correction)

        session.commit()

    return db_engine


class TestSystemPrompts:
    def test_all_agents_have_prompts(self):
        for agent in ALL_AGENTS:
            assert agent in SYSTEM_PROMPTS
            assert len(SYSTEM_PROMPTS[agent]) > 0

    def test_agent_to_role_mapping(self):
        assert AGENT_TO_ROLE["Planner"] == "planner"
        assert AGENT_TO_ROLE["Executor"] == "executor"
        assert AGENT_TO_ROLE["Tester"] == "tester"
        assert AGENT_TO_ROLE["Documenter"] == "documenter"


class TestGetEngine:
    def test_creates_engine(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        engine = get_engine(db_path)
        assert engine is not None


class TestExportSFTData:
    def test_exports_sft_from_agent_logs(self, populated_db, tmp_path):
        count = export_sft_data(populated_db, "Planner", tmp_path / "sft")
        assert count >= 1

        output = tmp_path / "sft" / "planner.jsonl"
        assert output.exists()

        with open(output) as f:
            lines = [json.loads(line) for line in f if line.strip()]
        assert len(lines) >= 1
        assert lines[0]["conversations"][0]["from"] == "system"
        assert lines[0]["conversations"][1]["from"] == "human"
        assert lines[0]["conversations"][2]["from"] == "gpt"

    def test_exports_passing_dpo_as_sft(self, populated_db, tmp_path):
        count = export_sft_data(populated_db, "Executor", tmp_path / "sft")
        # Should include both: AgentLog entries AND passing DPOTuples
        assert count >= 2

        output = tmp_path / "sft" / "executor.jsonl"
        with open(output) as f:
            lines = [json.loads(line) for line in f if line.strip()]
        # At least one from DPOTuple (test_result == "pass")
        assert any("hello" in entry["conversations"][2]["value"] for entry in lines)

    def test_empty_db_returns_zero(self, db_engine, tmp_path):
        count = export_sft_data(db_engine, "Planner", tmp_path / "sft")
        assert count == 0

    def test_creates_output_dir(self, populated_db, tmp_path):
        output_dir = tmp_path / "nested" / "sft"
        assert not output_dir.exists()
        export_sft_data(populated_db, "Planner", output_dir)
        assert output_dir.exists()

    def test_agent_with_no_logs(self, populated_db, tmp_path):
        """Agent that has logs but also DPO passing tuples with lowercase name."""
        # Documenter has no DPO tuples, only AgentLog entries
        count = export_sft_data(populated_db, "Documenter", tmp_path / "sft")
        assert count >= 1

    def test_handles_structured_data_none(self, db_engine, tmp_path):
        """AgentLog with no structured_data should still export."""
        with Session(db_engine) as session:
            project = Project(name="p", path="w")
            session.add(project)
            session.commit()
            session.refresh(project)

            task = Task(project_id=project.id, description="t", status=TaskStatus.COMPLETED)
            session.add(task)
            session.commit()
            session.refresh(task)

            run = PipelineRun(
                project_id=project.id,
                task_id=task.id,
                user_request="test request",
                status=TaskStatus.COMPLETED,
            )
            session.add(run)
            session.commit()
            session.refresh(run)

            log = AgentLog(
                task_id=task.id,
                pipeline_run_id=run.id,
                agent_name="Planner",
                level="INFO",
                message="llm_call",
                success=True,
                structured_data=None,  # No structured data
            )
            session.add(log)
            session.commit()

        count = export_sft_data(db_engine, "Planner", tmp_path / "sft")
        assert count == 1

    def test_handles_invalid_structured_data_json(self, db_engine, tmp_path):
        """AgentLog with invalid JSON in structured_data should not crash."""
        with Session(db_engine) as session:
            project = Project(name="p", path="w")
            session.add(project)
            session.commit()
            session.refresh(project)

            task = Task(project_id=project.id, description="t", status=TaskStatus.COMPLETED)
            session.add(task)
            session.commit()
            session.refresh(task)

            run = PipelineRun(
                project_id=project.id,
                task_id=task.id,
                user_request="bad json test",
                status=TaskStatus.COMPLETED,
            )
            session.add(run)
            session.commit()
            session.refresh(run)

            log = AgentLog(
                task_id=task.id,
                pipeline_run_id=run.id,
                agent_name="Planner",
                level="INFO",
                message="llm_call",
                success=True,
                structured_data="not valid json {{{",
            )
            session.add(log)
            session.commit()

        count = export_sft_data(db_engine, "Planner", tmp_path / "sft")
        assert count == 1


class TestExportDPOData:
    def test_exports_successful_corrections(self, populated_db, tmp_path):
        count = export_dpo_data(populated_db, "Executor", tmp_path / "dpo")
        assert count == 1  # Only the one with correction_successful=True AND corrected_code

        output = tmp_path / "dpo" / "executor.jsonl"
        with open(output) as f:
            line = json.loads(f.readline())
        assert line["chosen"] == "import flask"
        assert line["rejected"] == "import broken"
        assert line["prompt"] == "Fix the imports"

    def test_excludes_failed_corrections(self, populated_db, tmp_path):
        export_dpo_data(populated_db, "Executor", tmp_path / "dpo")
        # Should NOT include the dpo_failed entry (correction_successful=False)
        output = tmp_path / "dpo" / "executor.jsonl"
        with open(output) as f:
            lines = [json.loads(line) for line in f if line.strip()]
        assert all(entry["rejected"] != "bad code" for entry in lines)

    def test_excludes_no_corrected_code(self, populated_db, tmp_path):
        count = export_dpo_data(populated_db, "Tester", tmp_path / "dpo")
        # Tester DPO tuple has correction_successful=True but corrected_code=None
        assert count == 0

    def test_empty_db_returns_zero(self, db_engine, tmp_path):
        count = export_dpo_data(db_engine, "Planner", tmp_path / "dpo")
        assert count == 0

    def test_creates_output_dir(self, populated_db, tmp_path):
        output_dir = tmp_path / "nested" / "dpo"
        export_dpo_data(populated_db, "Executor", output_dir)
        assert output_dir.exists()

    def test_unknown_agent_returns_zero(self, populated_db, tmp_path):
        count = export_dpo_data(populated_db, "NonExistent", tmp_path / "dpo")
        assert count == 0


class TestValidateJSONL:
    def test_valid_file(self, tmp_path):
        path = tmp_path / "valid.jsonl"
        path.write_text('{"a": 1}\n{"b": 2}\n')
        valid, count, err = validate_jsonl(path)
        assert valid is True
        assert count == 2
        assert err == ""

    def test_invalid_json_line(self, tmp_path):
        path = tmp_path / "invalid.jsonl"
        path.write_text('{"a": 1}\nnot json\n')
        valid, count, err = validate_jsonl(path)
        assert valid is False
        assert "Invalid JSON at line 2" in err

    def test_file_not_found(self, tmp_path):
        valid, count, err = validate_jsonl(tmp_path / "missing.jsonl")
        assert valid is False
        assert "not found" in err

    def test_empty_file(self, tmp_path):
        path = tmp_path / "empty.jsonl"
        path.write_text("")
        valid, count, err = validate_jsonl(path)
        assert valid is True
        assert count == 0

    def test_skips_blank_lines(self, tmp_path):
        path = tmp_path / "blanks.jsonl"
        path.write_text('{"a": 1}\n\n{"b": 2}\n\n')
        valid, count, err = validate_jsonl(path)
        assert valid is True
        assert count == 2


class TestExportAll:
    def test_exports_all_agents(self, populated_db, tmp_path):
        summary = export_all(populated_db, tmp_path)
        assert "Planner" in summary
        assert "Executor" in summary
        assert "Tester" in summary
        assert "Documenter" in summary
        assert summary["Executor"]["sft_count"] >= 1
        assert summary["Executor"]["dpo_count"] >= 1

    def test_exports_specific_agents(self, populated_db, tmp_path):
        summary = export_all(populated_db, tmp_path, agents=["Planner"])
        assert "Planner" in summary
        assert "Executor" not in summary


class TestMainCLI:
    def test_all_flag(self, populated_db, tmp_path, monkeypatch):
        db_file = tmp_path / "test.db"
        # Create a real DB file by copying schema
        real_engine = create_engine(f"sqlite:///{db_file}", echo=False)
        SQLModel.metadata.create_all(real_engine)

        main(["--all", "--output", str(tmp_path / "out"), "--db", str(db_file)])

    def test_agent_flag(self, tmp_path):
        db_file = tmp_path / "test.db"
        real_engine = create_engine(f"sqlite:///{db_file}", echo=False)
        SQLModel.metadata.create_all(real_engine)

        main(["--agent", "planner", "--output", str(tmp_path / "out"), "--db", str(db_file)])

    def test_validate_flag(self, tmp_path, capsys):
        out_dir = tmp_path / "out" / "sft"
        out_dir.mkdir(parents=True)
        (out_dir / "planner.jsonl").write_text('{"a": 1}\n')

        main(["--validate", "--output", str(tmp_path / "out")])
        captured = capsys.readouterr()
        assert "OK" in captured.out

    def test_validate_missing_dir(self, tmp_path, capsys):
        main(["--validate", "--output", str(tmp_path / "nonexistent")])
        captured = capsys.readouterr()
        assert "not found" in captured.out

    def test_no_flags_errors(self, tmp_path):
        with pytest.raises(SystemExit):
            main(["--output", str(tmp_path)])
