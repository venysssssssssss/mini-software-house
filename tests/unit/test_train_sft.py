"""Tests for scripts/finetune/train_sft.py — 100% coverage on testable code.

ML training (unsloth, trl, torch) is mocked since it requires GPU.
All configuration, validation, and CLI logic is tested directly.
"""

import json

import pytest

from scripts.finetune.train_sft import (
    LORA_CONFIG,
    MODEL_MAP,
    TARGET_MODULES,
    get_training_args,
    main,
    validate_data,
)


class TestModelMap:
    def test_all_agents_have_models(self):
        assert "planner" in MODEL_MAP
        assert "executor" in MODEL_MAP
        assert "tester" in MODEL_MAP
        assert "documenter" in MODEL_MAP

    def test_models_are_unsloth_4bit(self):
        for model in MODEL_MAP.values():
            assert "unsloth/" in model
            assert "bnb-4bit" in model or "instruct" in model.lower()


class TestLoRAConfig:
    def test_all_agents_have_config(self):
        for agent in MODEL_MAP:
            assert agent in LORA_CONFIG
            assert "r" in LORA_CONFIG[agent]
            assert "lora_alpha" in LORA_CONFIG[agent]
            assert "epochs" in LORA_CONFIG[agent]

    def test_documenter_has_smaller_config(self):
        assert LORA_CONFIG["documenter"]["r"] <= LORA_CONFIG["planner"]["r"]


class TestTargetModules:
    def test_contains_attention_projections(self):
        assert "q_proj" in TARGET_MODULES
        assert "k_proj" in TARGET_MODULES
        assert "v_proj" in TARGET_MODULES
        assert "o_proj" in TARGET_MODULES

    def test_contains_mlp_projections(self):
        assert "gate_proj" in TARGET_MODULES
        assert "up_proj" in TARGET_MODULES
        assert "down_proj" in TARGET_MODULES


class TestValidateData:
    def test_valid_data(self, tmp_path):
        data_file = tmp_path / "train.jsonl"
        data_file.write_text(
            json.dumps(
                {
                    "conversations": [
                        {"from": "system", "value": "sys"},
                        {"from": "human", "value": "hello"},
                        {"from": "gpt", "value": "hi"},
                    ]
                }
            )
            + "\n"
        )
        count = validate_data(str(data_file))
        assert count == 1

    def test_multiple_examples(self, tmp_path):
        data_file = tmp_path / "train.jsonl"
        lines = []
        for i in range(5):
            lines.append(
                json.dumps(
                    {
                        "conversations": [
                            {"from": "system", "value": "sys"},
                            {"from": "human", "value": f"q{i}"},
                            {"from": "gpt", "value": f"a{i}"},
                        ]
                    }
                )
            )
        data_file.write_text("\n".join(lines) + "\n")
        count = validate_data(str(data_file))
        assert count == 5

    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError, match="not found"):
            validate_data("/nonexistent/path.jsonl")

    def test_invalid_json(self, tmp_path):
        data_file = tmp_path / "bad.jsonl"
        data_file.write_text("not json\n")
        with pytest.raises(ValueError, match="Invalid JSON at line 1"):
            validate_data(str(data_file))

    def test_missing_conversations_key(self, tmp_path):
        data_file = tmp_path / "no_conv.jsonl"
        data_file.write_text('{"data": "something"}\n')
        with pytest.raises(ValueError, match="Missing 'conversations'"):
            validate_data(str(data_file))

    def test_too_few_turns(self, tmp_path):
        data_file = tmp_path / "short.jsonl"
        entry = {"conversations": [{"from": "system", "value": "s"}]}
        data_file.write_text(json.dumps(entry) + "\n")
        with pytest.raises(ValueError, match=">= 2 turns"):
            validate_data(str(data_file))

    def test_empty_file(self, tmp_path):
        data_file = tmp_path / "empty.jsonl"
        data_file.write_text("")
        with pytest.raises(ValueError, match="No training examples"):
            validate_data(str(data_file))

    def test_skips_blank_lines(self, tmp_path):
        data_file = tmp_path / "blanks.jsonl"
        entry = json.dumps(
            {
                "conversations": [
                    {"from": "system", "value": "s"},
                    {"from": "human", "value": "h"},
                ]
            }
        )
        data_file.write_text(f"\n{entry}\n\n{entry}\n")
        count = validate_data(str(data_file))
        assert count == 2

    def test_conversations_not_a_list(self, tmp_path):
        data_file = tmp_path / "bad_type.jsonl"
        data_file.write_text(json.dumps({"conversations": "not a list"}) + "\n")
        with pytest.raises(ValueError, match=">= 2 turns"):
            validate_data(str(data_file))


class TestGetTrainingArgs:
    def test_planner_args(self):
        args = get_training_args("planner", "/tmp/out")
        assert args["per_device_train_batch_size"] == 1
        assert args["fp16"] is True
        assert args["optim"] == "adamw_8bit"
        assert args["output_dir"] == "/tmp/out"
        assert args["num_train_epochs"] == LORA_CONFIG["planner"]["epochs"]

    def test_documenter_fewer_epochs(self):
        args = get_training_args("documenter", "/tmp/out")
        assert args["num_train_epochs"] == 2

    def test_gradient_accumulation(self):
        args = get_training_args("executor", "/tmp/out")
        assert args["gradient_accumulation_steps"] == 4

    def test_all_agents_have_valid_args(self):
        for agent in LORA_CONFIG:
            args = get_training_args(agent, "/tmp/out")
            assert args["learning_rate"] == 2e-4
            assert args["warmup_ratio"] == 0.05


class TestMainCLI:
    def test_missing_required_args(self):
        with pytest.raises(SystemExit):
            main([])

    def test_missing_data_arg(self):
        with pytest.raises(SystemExit):
            main(["--agent", "planner"])

    def test_invalid_agent(self):
        with pytest.raises(SystemExit):
            main(["--agent", "nonexistent", "--data", "x.jsonl"])

    def test_valid_args_but_no_unsloth(self, tmp_path, monkeypatch):
        """When unsloth is not installed, train() should sys.exit(1)."""
        data_file = tmp_path / "train.jsonl"
        data_file.write_text(
            json.dumps(
                {
                    "conversations": [
                        {"from": "system", "value": "s"},
                        {"from": "human", "value": "h"},
                        {"from": "gpt", "value": "g"},
                    ]
                }
            )
            + "\n"
        )

        import builtins

        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "unsloth":
                raise ImportError("no unsloth")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", mock_import)

        from scripts.finetune import train_sft

        with pytest.raises(SystemExit):
            train_sft.train(
                agent_name="planner",
                base_model="unsloth/test",
                data_path=str(data_file),
                output_dir=str(tmp_path / "out"),
            )


class TestTrainWithMockedML:
    """Test train() function with fully mocked ML dependencies."""

    def _make_training_data(self, tmp_path):
        data_file = tmp_path / "train.jsonl"
        data_file.write_text(
            json.dumps(
                {
                    "conversations": [
                        {"from": "system", "value": "s"},
                        {"from": "human", "value": "h"},
                        {"from": "gpt", "value": "g"},
                    ]
                }
            )
            + "\n"
        )
        return str(data_file)

    def test_train_full_flow_mocked(self, tmp_path, monkeypatch):
        """Test the full train() flow with all ML deps mocked."""
        from unittest.mock import MagicMock

        from scripts.finetune import train_sft

        data_path = self._make_training_data(tmp_path)
        output_dir = str(tmp_path / "output")

        # Mock unsloth
        mock_flm = MagicMock()
        mock_model = MagicMock()
        mock_tokenizer = MagicMock()
        mock_flm.from_pretrained.return_value = (mock_model, mock_tokenizer)
        mock_flm.get_peft_model.return_value = mock_model

        # Mock trl/datasets/transformers
        mock_dataset = MagicMock()
        mock_load_dataset = MagicMock(return_value=mock_dataset)
        mock_training_args_cls = MagicMock()
        mock_trainer_cls = MagicMock()
        mock_trainer = MagicMock()
        mock_trainer_cls.return_value = mock_trainer

        import builtins

        real_import = builtins.__import__
        mock_modules = {
            "unsloth": MagicMock(FastLanguageModel=mock_flm),
            "datasets": MagicMock(load_dataset=mock_load_dataset),
            "transformers": MagicMock(TrainingArguments=mock_training_args_cls),
            "trl": MagicMock(SFTTrainer=mock_trainer_cls),
        }

        def mock_import(name, *args, **kwargs):
            if name in mock_modules:
                return mock_modules[name]
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", mock_import)

        result = train_sft.train(
            agent_name="planner",
            base_model="unsloth/test-model",
            data_path=data_path,
            output_dir=output_dir,
        )

        assert result == f"{output_dir}/lora"
        mock_trainer.train.assert_called_once()
        mock_model.save_pretrained.assert_called_once()
        mock_tokenizer.save_pretrained.assert_called_once()

    def test_train_trl_import_error(self, tmp_path, monkeypatch):
        """When trl is not installed but unsloth is, should sys.exit(1)."""
        from unittest.mock import MagicMock

        from scripts.finetune import train_sft

        data_path = self._make_training_data(tmp_path)

        import builtins

        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "unsloth":
                return MagicMock()
            if name in ("datasets", "transformers", "trl"):
                raise ImportError(f"no {name}")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", mock_import)

        with pytest.raises(SystemExit):
            train_sft.train("planner", "model", data_path, str(tmp_path / "out"))

    def test_main_calls_train(self, tmp_path, monkeypatch):
        """Test that main() correctly wires CLI args to train()."""
        from unittest.mock import MagicMock

        from scripts.finetune import train_sft

        data_path = self._make_training_data(tmp_path)

        mock_train = MagicMock()
        monkeypatch.setattr(train_sft, "train", mock_train)

        train_sft.main(["--agent", "planner", "--data", data_path, "--output", str(tmp_path)])

        mock_train.assert_called_once_with(
            agent_name="planner",
            base_model=MODEL_MAP["planner"],
            data_path=data_path,
            output_dir=f"{tmp_path}/planner",
        )
