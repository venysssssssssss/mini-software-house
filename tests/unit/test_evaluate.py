"""Tests for scripts/finetune/evaluate.py — 100% coverage on testable code."""

import json

import pytest
from sqlmodel import Session, SQLModel, create_engine, select

from scripts.finetune.evaluate import (
    EVAL_TASKS,
    collect_metrics,
    compare_results,
    format_comparison,
    get_engine,
    main,
    run_evaluation,
)
from src.core.models import AgentLog, DPOTuple, PipelineRun, Project, Task, TaskStatus


@pytest.fixture
def db_engine():
    engine = create_engine("sqlite://", echo=False)
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture
def populated_db(db_engine):
    """Seed DB with 2 pipeline runs: 1 first-pass success, 1 with corrections."""
    with Session(db_engine) as session:
        project = Project(name="eval-test", path="workspace")
        session.add(project)
        session.commit()
        session.refresh(project)

        task = Task(project_id=project.id, description="t", status=TaskStatus.COMPLETED)
        session.add(task)
        session.commit()
        session.refresh(task)

        # Run 1: first-pass success (no correction DPO tuples)
        run1 = PipelineRun(
            project_id=project.id,
            task_id=task.id,
            user_request="Success task",
            status=TaskStatus.COMPLETED,
            total_prompt_tokens=100,
            total_response_tokens=200,
            total_latency_ms=1000.0,
            total_agent_calls=4,
        )
        session.add(run1)
        session.commit()
        session.refresh(run1)

        # Planner log for run1
        log1 = AgentLog(
            pipeline_run_id=run1.id,
            agent_name="Planner",
            level="INFO",
            message="llm_call",
            success=True,
        )
        session.add(log1)

        # Run 2: needed corrections
        run2 = PipelineRun(
            project_id=project.id,
            task_id=task.id,
            user_request="Correction task",
            status=TaskStatus.COMPLETED,
            total_prompt_tokens=200,
            total_response_tokens=400,
            total_latency_ms=2000.0,
            total_agent_calls=6,
        )
        session.add(run2)
        session.commit()
        session.refresh(run2)

        # DPO tuple for run2 (correction needed = NOT first-pass success)
        dpo = DPOTuple(
            pipeline_run_id=run2.id,
            agent_name="executor",
            prompt="fix",
            generated_code="broken",
            test_result="ImportError",
            corrected_code="fixed",
            correction_successful=True,
        )
        session.add(dpo)

        # Planner log for run2 (also successful)
        log2 = AgentLog(
            pipeline_run_id=run2.id,
            agent_name="Planner",
            level="INFO",
            message="llm_call",
            success=True,
        )
        session.add(log2)

        # A failed run (should be excluded from metrics)
        run_failed = PipelineRun(
            project_id=project.id,
            task_id=task.id,
            user_request="Failed task",
            status=TaskStatus.FAILED,
        )
        session.add(run_failed)

        session.commit()

    return db_engine


class TestEvalTasks:
    def test_has_ten_tasks(self):
        assert len(EVAL_TASKS) == 10

    def test_tasks_are_strings(self):
        for task in EVAL_TASKS:
            assert isinstance(task, str)
            assert len(task) > 10


class TestGetEngine:
    def test_creates_engine(self, tmp_path):
        engine = get_engine(str(tmp_path / "test.db"))
        assert engine is not None


class TestCollectMetrics:
    def test_collects_from_populated_db(self, populated_db):
        metrics = collect_metrics(populated_db)
        assert metrics["total_runs"] == 2
        assert metrics["first_pass_success_rate"] == 0.5  # 1 of 2
        assert metrics["avg_corrections"] == 0.5  # 1 correction / 2 runs
        assert metrics["avg_total_tokens"] == 450.0  # (300 + 600) / 2
        assert metrics["avg_latency_ms"] == 1500.0  # (1000 + 2000) / 2
        assert metrics["avg_agent_calls"] == 5.0  # (4 + 6) / 2
        assert metrics["json_validity_rate"] == 1.0  # 2/2 planner logs successful

    def test_empty_db_returns_zeros(self, db_engine):
        metrics = collect_metrics(db_engine)
        assert metrics["total_runs"] == 0
        assert metrics["first_pass_success_rate"] == 0.0
        assert metrics["avg_corrections"] == 0.0

    def test_filter_by_run_ids(self, populated_db):
        # Get only the first run
        with Session(populated_db) as session:
            runs = session.exec(
                select(PipelineRun).where(PipelineRun.status == TaskStatus.COMPLETED)
            ).all()
            first_run_id = runs[0].id

        metrics = collect_metrics(populated_db, run_ids=[first_run_id])
        assert metrics["total_runs"] == 1

    def test_excludes_failed_runs(self, populated_db):
        metrics = collect_metrics(populated_db)
        # Failed run should NOT be counted
        assert metrics["total_runs"] == 2  # not 3


class TestCompareResults:
    def test_basic_comparison(self, tmp_path):
        base = {"metrics": {"first_pass_success_rate": 0.6, "avg_corrections": 2.0}}
        ft = {"metrics": {"first_pass_success_rate": 0.8, "avg_corrections": 1.5}}

        base_path = tmp_path / "base.json"
        ft_path = tmp_path / "ft.json"
        base_path.write_text(json.dumps(base))
        ft_path.write_text(json.dumps(ft))

        comparison = compare_results(str(base_path), str(ft_path))

        assert comparison["first_pass_success_rate"]["delta"] == pytest.approx(0.2)
        assert comparison["avg_corrections"]["delta"] == pytest.approx(-0.5)

    def test_zero_base_value(self, tmp_path):
        base = {"metrics": {"total_runs": 0}}
        ft = {"metrics": {"total_runs": 5}}

        base_path = tmp_path / "base.json"
        ft_path = tmp_path / "ft.json"
        base_path.write_text(json.dumps(base))
        ft_path.write_text(json.dumps(ft))

        comparison = compare_results(str(base_path), str(ft_path))
        assert comparison["total_runs"]["pct_change"] == 0  # div by zero protection


class TestFormatComparison:
    def test_basic_formatting(self):
        comparison = {
            "first_pass_success_rate": {
                "base": 0.6,
                "finetuned": 0.8,
                "delta": 0.2,
                "pct_change": 33.33,
            },
            "avg_corrections": {
                "base": 2.0,
                "finetuned": 1.5,
                "delta": -0.5,
                "pct_change": -25.0,
            },
        }
        result = format_comparison(comparison)
        assert "first_pass_success_rate" in result
        assert "avg_corrections" in result
        assert "+" in result  # positive indicator

    def test_empty_comparison(self):
        result = format_comparison({})
        assert "Metric" in result  # header still present

    def test_integer_values(self):
        comparison = {
            "total_runs": {
                "base": 10,
                "finetuned": 15,
                "delta": 5,
                "pct_change": 50.0,
            },
        }
        result = format_comparison(comparison)
        assert "total_runs" in result


class TestRunEvaluation:
    def test_saves_results(self, populated_db, tmp_path, monkeypatch):
        db_file = tmp_path / "test.db"
        # Create a real DB file
        real_engine = create_engine(f"sqlite:///{db_file}", echo=False)
        SQLModel.metadata.create_all(real_engine)

        output = tmp_path / "results" / "eval.json"
        result = run_evaluation("base", str(output), str(db_file))

        assert output.exists()
        assert result["config"] == "base"
        assert "metrics" in result

    def test_creates_parent_dirs(self, tmp_path):
        db_file = tmp_path / "test.db"
        real_engine = create_engine(f"sqlite:///{db_file}", echo=False)
        SQLModel.metadata.create_all(real_engine)

        output = tmp_path / "deep" / "nested" / "eval.json"
        run_evaluation("finetuned", str(output), str(db_file))
        assert output.exists()


class TestMainCLI:
    def test_compare_mode(self, tmp_path):
        base = {"metrics": {"total_runs": 5, "first_pass_success_rate": 0.6}}
        ft = {"metrics": {"total_runs": 5, "first_pass_success_rate": 0.8}}

        base_path = tmp_path / "base.json"
        ft_path = tmp_path / "ft.json"
        base_path.write_text(json.dumps(base))
        ft_path.write_text(json.dumps(ft))

        result = main(["--compare", str(base_path), str(ft_path)])
        assert isinstance(result, dict)

    def test_config_mode(self, tmp_path):
        db_file = tmp_path / "test.db"
        real_engine = create_engine(f"sqlite:///{db_file}", echo=False)
        SQLModel.metadata.create_all(real_engine)

        output = tmp_path / "eval.json"
        result = main(["--config", "base", "--output", str(output), "--db", str(db_file)])
        assert result is not None

    def test_missing_output_in_config_mode(self):
        with pytest.raises(SystemExit):
            main(["--config", "base"])

    def test_no_args_help(self):
        """No --config and no --compare should error."""
        with pytest.raises(SystemExit):
            main(["--output", "/tmp/x.json"])
