"""Tests for scripts/finetune/train_dpo.py — 100% coverage on testable code.

ML training is mocked since it requires GPU.
"""

import json

import pytest

from scripts.finetune.train_dpo import (
    DPO_LORA_CONFIG,
    MINIMUM_DPO_PAIRS,
    TARGET_MODULES,
    get_dpo_training_args,
    main,
    validate_dpo_data,
)


class TestDPOLoRAConfig:
    def test_all_supported_agents(self):
        assert "planner" in DPO_LORA_CONFIG
        assert "executor" in DPO_LORA_CONFIG
        assert "tester" in DPO_LORA_CONFIG

    def test_documenter_not_in_dpo(self):
        # Documenter doesn't have enough correction data for DPO
        assert "documenter" not in DPO_LORA_CONFIG

    def test_config_has_required_keys(self):
        for agent, config in DPO_LORA_CONFIG.items():
            assert "r" in config
            assert "lora_alpha" in config
            assert "epochs" in config

    def test_dpo_rank_smaller_than_sft(self):
        # DPO uses smaller rank since less data
        for config in DPO_LORA_CONFIG.values():
            assert config["r"] <= 16


class TestTargetModules:
    def test_same_as_sft(self):
        from scripts.finetune.train_sft import TARGET_MODULES as SFT_MODULES

        assert set(TARGET_MODULES) == set(SFT_MODULES)


class TestValidateDPOData:
    def _make_dpo_file(self, tmp_path, count):
        """Helper to create a valid DPO JSONL file with N pairs."""
        data_file = tmp_path / "dpo.jsonl"
        lines = []
        for i in range(count):
            lines.append(json.dumps({
                "prompt": f"Fix error {i}",
                "chosen": f"correct code {i}",
                "rejected": f"broken code {i}",
            }))
        data_file.write_text("\n".join(lines) + "\n")
        return str(data_file)

    def test_valid_data_above_minimum(self, tmp_path):
        path = self._make_dpo_file(tmp_path, MINIMUM_DPO_PAIRS)
        count = validate_dpo_data(path)
        assert count == MINIMUM_DPO_PAIRS

    def test_below_minimum_raises(self, tmp_path):
        path = self._make_dpo_file(tmp_path, MINIMUM_DPO_PAIRS - 1)
        with pytest.raises(ValueError, match="Insufficient DPO pairs"):
            validate_dpo_data(path)

    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError, match="not found"):
            validate_dpo_data("/nonexistent.jsonl")

    def test_invalid_json(self, tmp_path):
        data_file = tmp_path / "bad.jsonl"
        data_file.write_text("not json\n")
        with pytest.raises(ValueError, match="Invalid JSON at line 1"):
            validate_dpo_data(str(data_file))

    def test_missing_keys(self, tmp_path):
        data_file = tmp_path / "missing.jsonl"
        data_file.write_text(json.dumps({"prompt": "x"}) + "\n")
        with pytest.raises(ValueError, match="Missing keys"):
            validate_dpo_data(str(data_file))

    def test_skips_blank_lines(self, tmp_path):
        lines = []
        for i in range(MINIMUM_DPO_PAIRS):
            lines.append(json.dumps({
                "prompt": f"p{i}",
                "chosen": f"c{i}",
                "rejected": f"r{i}",
            }))
        data_file = tmp_path / "blanks.jsonl"
        data_file.write_text("\n".join(lines) + "\n\n")
        count = validate_dpo_data(str(data_file))
        assert count == MINIMUM_DPO_PAIRS


class TestGetDPOTrainingArgs:
    def test_executor_args(self):
        args = get_dpo_training_args("executor", "/tmp/out")
        assert args["per_device_train_batch_size"] == 1
        assert args["fp16"] is True
        assert args["optim"] == "adamw_8bit"
        assert args["beta"] == 0.1
        assert args["learning_rate"] == 5e-5

    def test_lower_lr_than_sft(self):
        from scripts.finetune.train_sft import get_training_args

        dpo_args = get_dpo_training_args("executor", "/tmp/out")
        sft_args = get_training_args("executor", "/tmp/out")
        assert dpo_args["learning_rate"] < sft_args["learning_rate"]

    def test_all_agents_have_valid_args(self):
        for agent in DPO_LORA_CONFIG:
            args = get_dpo_training_args(agent, "/tmp/out")
            assert args["warmup_ratio"] == 0.1
            assert args["logging_steps"] == 5


class TestMainCLI:
    def test_missing_required_args(self):
        with pytest.raises(SystemExit):
            main([])

    def test_missing_sft_model(self):
        with pytest.raises(SystemExit):
            main(["--agent", "executor", "--data", "x.jsonl"])

    def test_invalid_agent(self):
        with pytest.raises(SystemExit):
            main(["--agent", "documenter", "--sft-model", "x", "--data", "x.jsonl"])

    def test_valid_args_but_no_unsloth(self, tmp_path, monkeypatch):
        """When unsloth is not installed, train_dpo() should sys.exit(1)."""
        lines = []
        for i in range(MINIMUM_DPO_PAIRS):
            lines.append(json.dumps({
                "prompt": f"p{i}", "chosen": f"c{i}", "rejected": f"r{i}",
            }))
        data_file = tmp_path / "dpo.jsonl"
        data_file.write_text("\n".join(lines) + "\n")

        import builtins
        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "unsloth":
                raise ImportError("no unsloth")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", mock_import)

        from scripts.finetune import train_dpo

        with pytest.raises(SystemExit):
            train_dpo.train_dpo(
                agent_name="executor",
                sft_model_path=str(tmp_path),
                data_path=str(data_file),
                output_dir=str(tmp_path / "out"),
            )


class TestTrainDPOWithMockedML:
    """Test train_dpo() with fully mocked ML dependencies."""

    def _make_dpo_data(self, tmp_path):
        lines = []
        for i in range(MINIMUM_DPO_PAIRS):
            lines.append(json.dumps({
                "prompt": f"p{i}", "chosen": f"c{i}", "rejected": f"r{i}",
            }))
        data_file = tmp_path / "dpo.jsonl"
        data_file.write_text("\n".join(lines) + "\n")
        return str(data_file)

    def test_train_dpo_full_flow(self, tmp_path, monkeypatch):
        from unittest.mock import MagicMock

        from scripts.finetune import train_dpo

        data_path = self._make_dpo_data(tmp_path)
        output_dir = str(tmp_path / "output")

        mock_flm = MagicMock()
        mock_model = MagicMock()
        mock_tokenizer = MagicMock()
        mock_flm.from_pretrained.return_value = (mock_model, mock_tokenizer)
        mock_flm.get_peft_model.return_value = mock_model
        mock_patch_dpo = MagicMock()

        mock_dataset = MagicMock()
        mock_load_dataset = MagicMock(return_value=mock_dataset)
        mock_dpo_config_cls = MagicMock()
        mock_dpo_trainer_cls = MagicMock()
        mock_trainer = MagicMock()
        mock_dpo_trainer_cls.return_value = mock_trainer

        import builtins
        real_import = builtins.__import__
        mock_modules = {
            "unsloth": MagicMock(
                FastLanguageModel=mock_flm,
                PatchDPOTrainer=mock_patch_dpo,
            ),
            "datasets": MagicMock(load_dataset=mock_load_dataset),
            "trl": MagicMock(
                DPOConfig=mock_dpo_config_cls,
                DPOTrainer=mock_dpo_trainer_cls,
            ),
        }

        def mock_import(name, *args, **kwargs):
            if name in mock_modules:
                return mock_modules[name]
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", mock_import)

        result = train_dpo.train_dpo(
            agent_name="executor",
            sft_model_path=str(tmp_path),
            data_path=data_path,
            output_dir=output_dir,
        )

        assert result == f"{output_dir}/lora"
        mock_trainer.train.assert_called_once()

    def test_train_dpo_trl_import_error(self, tmp_path, monkeypatch):
        from unittest.mock import MagicMock

        from scripts.finetune import train_dpo

        data_path = self._make_dpo_data(tmp_path)

        import builtins
        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "unsloth":
                return MagicMock()
            if name in ("datasets", "trl"):
                raise ImportError(f"no {name}")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", mock_import)

        with pytest.raises(SystemExit):
            train_dpo.train_dpo("executor", str(tmp_path), data_path, str(tmp_path / "out"))

    def test_unsupported_agent_exits(self, tmp_path, monkeypatch):
        from unittest.mock import MagicMock

        from scripts.finetune import train_dpo

        data_path = self._make_dpo_data(tmp_path)

        import builtins
        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "unsloth":
                return MagicMock()
            if name in ("datasets", "trl"):
                return MagicMock()
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", mock_import)

        with pytest.raises(SystemExit):
            train_dpo.train_dpo("documenter", str(tmp_path), data_path, str(tmp_path / "out"))

    def test_main_calls_train_dpo(self, tmp_path, monkeypatch):
        from unittest.mock import MagicMock

        from scripts.finetune import train_dpo

        data_path = self._make_dpo_data(tmp_path)
        mock_train = MagicMock()
        monkeypatch.setattr(train_dpo, "train_dpo", mock_train)

        train_dpo.main([
            "--agent", "executor",
            "--sft-model", str(tmp_path),
            "--data", data_path,
            "--output", str(tmp_path / "out"),
        ])

        mock_train.assert_called_once_with(
            agent_name="executor",
            sft_model_path=str(tmp_path),
            data_path=data_path,
            output_dir=f"{tmp_path / 'out'}/executor_dpo",
        )
