"""Integration test: full finetune data pipeline.

Validates the end-to-end flow:
  1. Seed DB with pipeline run data (simulating real pipeline runs)
  2. Export SFT + DPO data to JSONL
  3. Validate exported files
  4. Collect evaluation metrics
  5. Compare two evaluation result sets
  6. Verify model mapping toggle works
"""

import json

import pytest
from sqlmodel import Session, SQLModel, create_engine

from scripts.finetune.evaluate import collect_metrics, compare_results, run_evaluation
from scripts.finetune.export_training_data import (
    export_all,
    export_dpo_data,
    export_sft_data,
    validate_jsonl,
)
from scripts.finetune.train_sft import validate_data
from src.agents.base import BASE_MODELS, FINETUNED_MODELS, get_model_for_role
from src.core.models import AgentLog, DPOTuple, PipelineRun, Project, Task, TaskStatus


@pytest.fixture
def ft_engine(tmp_path):
    """Create a file-backed SQLite DB to simulate real pipeline state."""
    db_path = tmp_path / "finetune_test.db"
    engine = create_engine(f"sqlite:///{db_path}", echo=False)
    SQLModel.metadata.create_all(engine)
    return engine, str(db_path)


@pytest.fixture
def seeded_db(ft_engine):
    """Seed DB with diverse pipeline runs simulating real pipeline output."""
    engine, db_path = ft_engine

    with Session(engine) as session:
        project = Project(name="ft-eval-project", path="workspace")
        session.add(project)
        session.commit()
        session.refresh(project)

        task = Task(
            project_id=project.id,
            description="Multi-task evaluation",
            status=TaskStatus.COMPLETED,
        )
        session.add(task)
        session.commit()
        session.refresh(task)

        # Create 5 completed pipeline runs with varying metrics
        run_ids = []
        for i in range(5):
            run = PipelineRun(
                project_id=project.id,
                task_id=task.id,
                user_request=f"Build feature {i}",
                status=TaskStatus.COMPLETED,
                total_prompt_tokens=100 + i * 20,
                total_response_tokens=200 + i * 30,
                total_latency_ms=1000.0 + i * 200,
                total_agent_calls=4 + i,
            )
            session.add(run)
            session.commit()
            session.refresh(run)
            run_ids.append(run.id)

            # Agent logs for each run (all 4 agent types)
            for agent_name in ["Planner", "Executor", "Tester", "Documenter"]:
                log = AgentLog(
                    task_id=task.id,
                    pipeline_run_id=run.id,
                    agent_name=agent_name,
                    model=f"{agent_name.lower()}-model",
                    level="INFO",
                    message="llm_call",
                    prompt_tokens=25 + i * 5,
                    response_tokens=50 + i * 10,
                    latency_ms=250.0 + i * 50,
                    success=True,
                    structured_data=json.dumps(
                        {
                            "response": f"{agent_name} output for feature {i}",
                        }
                    ),
                )
                session.add(log)

        # DPO tuples: some passing, some with corrections
        # Run 0 and 1: first-pass success (no correction tuples)
        for i in range(2):
            dpo = DPOTuple(
                pipeline_run_id=run_ids[i],
                agent_name="executor",
                prompt=f"Build feature {i}",
                generated_code=f"def feature_{i}(): pass",
                test_result="pass",
            )
            session.add(dpo)

        # Run 2, 3, 4: needed corrections
        for i in range(2, 5):
            # Failed attempt
            dpo_fail = DPOTuple(
                pipeline_run_id=run_ids[i],
                agent_name="executor",
                prompt=f"Fix feature {i}",
                generated_code=f"import broken_{i}",
                test_result="ImportError",
                corrected_code=f"import fixed_{i}",
                error_type="ImportError",
                correction_successful=True,
            )
            session.add(dpo_fail)

        # Also add some tester DPO tuples (only for runs 3 and 4)
        for i in range(3, 5):
            dpo_test = DPOTuple(
                pipeline_run_id=run_ids[i],
                agent_name="tester",
                prompt=f"Write tests for feature {i}",
                generated_code=f"def test_bad_{i}(): assert False",
                test_result="AssertionError",
                corrected_code=f"def test_good_{i}(): assert True",
                error_type="AssertionError",
                correction_successful=True,
            )
            session.add(dpo_test)

        # 1 failed run (should be excluded from metrics)
        failed_run = PipelineRun(
            project_id=project.id,
            task_id=task.id,
            user_request="Failed build",
            status=TaskStatus.FAILED,
        )
        session.add(failed_run)

        session.commit()

    return engine, db_path


class TestFullExportPipeline:
    """Test the complete data export → validate → metrics collection flow."""

    def test_export_and_validate_all_agents(self, seeded_db, tmp_path):
        engine, db_path = seeded_db
        output_dir = tmp_path / "finetune_data"

        # Export all agent data
        summary = export_all(engine, output_dir)

        # Verify all agents got exported
        assert "Planner" in summary
        assert "Executor" in summary
        assert "Tester" in summary
        assert "Documenter" in summary

        # Executor should have both SFT and DPO data
        assert summary["Executor"]["sft_count"] >= 1
        assert summary["Executor"]["dpo_count"] >= 1

        # Validate all exported JSONL files
        for subdir in ["sft", "dpo"]:
            d = output_dir / subdir
            if d.exists():
                for jsonl_file in d.glob("*.jsonl"):
                    valid, count, err = validate_jsonl(jsonl_file)
                    assert valid, f"{jsonl_file}: {err}"
                    assert count >= 0

    def test_exported_sft_is_valid_training_format(self, seeded_db, tmp_path):
        """SFT output should be valid input for train_sft.py."""
        engine, db_path = seeded_db
        sft_dir = tmp_path / "sft"

        count = export_sft_data(engine, "Executor", sft_dir)
        assert count >= 1

        sft_file = sft_dir / "executor.jsonl"
        # Validate as SFT training data (used by train_sft.py)
        validated_count = validate_data(str(sft_file))
        assert validated_count == count

    def test_exported_dpo_has_correct_structure(self, seeded_db, tmp_path):
        """DPO output should have prompt/chosen/rejected keys."""
        engine, db_path = seeded_db
        dpo_dir = tmp_path / "dpo"

        count = export_dpo_data(engine, "Executor", dpo_dir)
        assert count >= 1

        dpo_file = dpo_dir / "executor.jsonl"
        with open(dpo_file) as f:
            for line in f:
                entry = json.loads(line.strip())
                assert "prompt" in entry
                assert "chosen" in entry
                assert "rejected" in entry
                assert entry["chosen"] != entry["rejected"]

    def test_metrics_collection_from_seeded_db(self, seeded_db):
        """Evaluation metrics should reflect the seeded pipeline runs."""
        engine, db_path = seeded_db

        metrics = collect_metrics(engine)
        assert metrics["total_runs"] == 5  # excludes the failed run
        assert metrics["first_pass_success_rate"] > 0  # at least some first-pass
        assert metrics["avg_corrections"] > 0  # some runs had corrections
        assert metrics["avg_total_tokens"] > 0
        assert metrics["avg_latency_ms"] > 0
        assert metrics["json_validity_rate"] == 1.0  # all planner logs successful

    def test_evaluation_roundtrip(self, seeded_db, tmp_path):
        """Export metrics, save to JSON, reload and compare."""
        engine, db_path = seeded_db

        # Save "base" evaluation
        base_path = tmp_path / "eval_base.json"
        base_result = run_evaluation("base", str(base_path), db_path)
        assert base_path.exists()
        assert base_result["config"] == "base"
        assert base_result["metrics"]["total_runs"] == 5

        # Save "finetuned" evaluation (same data for testing)
        ft_path = tmp_path / "eval_ft.json"
        run_evaluation("finetuned", str(ft_path), db_path)

        # Compare the two
        comparison = compare_results(str(base_path), str(ft_path))
        assert "total_runs" in comparison
        # Same data → delta should be 0
        assert comparison["total_runs"]["delta"] == 0


class TestModelMappingToggle:
    """Test that USE_FINETUNED_MODELS toggle works correctly end-to-end."""

    def test_base_models_default(self, monkeypatch):
        monkeypatch.delenv("USE_FINETUNED_MODELS", raising=False)

        for role, expected_model in BASE_MODELS.items():
            assert get_model_for_role(role) == expected_model

    def test_finetuned_models_enabled(self, monkeypatch):
        monkeypatch.setenv("USE_FINETUNED_MODELS", "true")

        for role, expected_ft_model in FINETUNED_MODELS.items():
            assert get_model_for_role(role) == expected_ft_model

        # Roles without FT models fall back to base
        assert get_model_for_role("frontend") == BASE_MODELS["frontend"]
        assert get_model_for_role("rag") == BASE_MODELS["rag"]

    def test_toggle_switch(self, monkeypatch):
        """Switching env var immediately changes model selection."""
        monkeypatch.setenv("USE_FINETUNED_MODELS", "true")
        assert get_model_for_role("planner") == "planner-ft"

        monkeypatch.setenv("USE_FINETUNED_MODELS", "false")
        assert get_model_for_role("planner") == "qwen2.5:3b"


class TestExportDPOForMultipleAgents:
    """Test that DPO export correctly filters by agent name."""

    def test_executor_and_tester_dpo_separate(self, seeded_db, tmp_path):
        engine, db_path = seeded_db

        exec_count = export_dpo_data(engine, "Executor", tmp_path / "dpo")
        test_count = export_dpo_data(engine, "Tester", tmp_path / "dpo_tester")

        # Both should have data (we seeded both)
        assert exec_count >= 1
        assert test_count >= 1

    def test_planner_has_no_dpo(self, seeded_db, tmp_path):
        engine, db_path = seeded_db
        count = export_dpo_data(engine, "Planner", tmp_path / "dpo")
        assert count == 0  # No planner DPO tuples were seeded
