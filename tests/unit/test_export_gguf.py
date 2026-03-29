"""Tests for scripts/finetune/export_gguf.py — 100% coverage on testable code."""

import pytest

from scripts.finetune.export_gguf import (
    SAFE_QUANT_METHODS,
    SUPPORTED_AGENTS,
    UNSAFE_QUANT_METHODS,
    main,
    validate_model_path,
    validate_quant_method,
)


class TestSupportedAgents:
    def test_all_four_agents(self):
        assert "planner" in SUPPORTED_AGENTS
        assert "executor" in SUPPORTED_AGENTS
        assert "tester" in SUPPORTED_AGENTS
        assert "documenter" in SUPPORTED_AGENTS

    def test_rag_not_supported(self):
        assert "rag" not in SUPPORTED_AGENTS


class TestQuantMethods:
    def test_safe_methods(self):
        assert "q4_k_m" in SAFE_QUANT_METHODS
        assert "q4_0" in SAFE_QUANT_METHODS

    def test_unsafe_methods(self):
        assert "q8_0" in UNSAFE_QUANT_METHODS
        assert "f16" in UNSAFE_QUANT_METHODS
        assert "f32" in UNSAFE_QUANT_METHODS


class TestValidateQuantMethod:
    def test_safe_method_passes(self):
        result = validate_quant_method("q4_k_m")
        assert result == "q4_k_m"

    def test_unsafe_method_raises(self):
        with pytest.raises(ValueError, match="too large for 4GB VRAM"):
            validate_quant_method("q8_0")

    def test_f16_raises(self):
        with pytest.raises(ValueError, match="too large"):
            validate_quant_method("f16")

    def test_f32_raises(self):
        with pytest.raises(ValueError, match="too large"):
            validate_quant_method("f32")

    def test_unknown_method_passes(self):
        # Unknown methods are allowed (might be new llama.cpp quantizations)
        result = validate_quant_method("q3_k_s")
        assert result == "q3_k_s"


class TestValidateModelPath:
    def test_valid_adapter_dir(self, tmp_path):
        adapter_dir = tmp_path / "lora"
        adapter_dir.mkdir()
        (adapter_dir / "adapter_config.json").write_text("{}")

        result = validate_model_path(str(adapter_dir))
        assert result == adapter_dir

    def test_parent_dir_with_lora_subdir(self, tmp_path):
        """If model_path/lora/adapter_config.json exists, return lora/ subdir."""
        lora_dir = tmp_path / "model" / "lora"
        lora_dir.mkdir(parents=True)
        (lora_dir / "adapter_config.json").write_text("{}")

        result = validate_model_path(str(tmp_path / "model"))
        assert result == lora_dir

    def test_nonexistent_path_raises(self):
        with pytest.raises(FileNotFoundError, match="not found"):
            validate_model_path("/nonexistent/path")

    def test_no_adapter_config_raises(self, tmp_path):
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        with pytest.raises(FileNotFoundError, match="adapter_config.json"):
            validate_model_path(str(empty_dir))

    def test_no_adapter_in_lora_subdir(self, tmp_path):
        """Dir exists and has lora/ subdir but no adapter_config.json inside."""
        model_dir = tmp_path / "model"
        model_dir.mkdir()
        lora_dir = model_dir / "lora"
        lora_dir.mkdir()
        # No adapter_config.json

        with pytest.raises(FileNotFoundError, match="adapter_config.json"):
            validate_model_path(str(model_dir))


class TestMainCLI:
    def test_missing_required_args(self):
        with pytest.raises(SystemExit):
            main([])

    def test_missing_model(self):
        with pytest.raises(SystemExit):
            main(["--agent", "planner"])

    def test_invalid_agent(self):
        with pytest.raises(SystemExit):
            main(["--agent", "rag", "--model", "x"])

    def test_unsafe_quant_in_cli(self, tmp_path):
        with pytest.raises(ValueError, match="too large"):
            main(["--agent", "planner", "--model", str(tmp_path), "--quant", "q8_0"])

    def test_valid_args_but_no_unsloth(self, tmp_path, monkeypatch):
        """When unsloth is not installed, export() should sys.exit(1)."""
        adapter_dir = tmp_path / "lora"
        adapter_dir.mkdir()
        (adapter_dir / "adapter_config.json").write_text("{}")

        import builtins

        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "unsloth":
                raise ImportError("no unsloth")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", mock_import)

        from scripts.finetune import export_gguf

        with pytest.raises(SystemExit):
            export_gguf.export(
                agent_name="planner",
                model_path=str(adapter_dir),
                output_dir=str(tmp_path / "out"),
            )


class TestExportWithMockedML:
    """Test export() with fully mocked unsloth."""

    def test_export_full_flow(self, tmp_path, monkeypatch):
        from unittest.mock import MagicMock

        from scripts.finetune import export_gguf

        adapter_dir = tmp_path / "lora"
        adapter_dir.mkdir()
        (adapter_dir / "adapter_config.json").write_text("{}")
        output_dir = str(tmp_path / "gguf_output")

        mock_flm = MagicMock()
        mock_model = MagicMock()
        mock_tokenizer = MagicMock()
        mock_flm.from_pretrained.return_value = (mock_model, mock_tokenizer)

        import builtins

        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "unsloth":
                return MagicMock(FastLanguageModel=mock_flm)
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", mock_import)

        result = export_gguf.export(
            agent_name="planner",
            model_path=str(adapter_dir),
            output_dir=output_dir,
        )

        assert "q4_k_m.gguf" in result
        mock_model.save_pretrained_gguf.assert_called_once()

    def test_export_custom_quant(self, tmp_path, monkeypatch):
        from unittest.mock import MagicMock

        from scripts.finetune import export_gguf

        adapter_dir = tmp_path / "lora"
        adapter_dir.mkdir()
        (adapter_dir / "adapter_config.json").write_text("{}")

        mock_flm = MagicMock()
        mock_model = MagicMock()
        mock_tokenizer = MagicMock()
        mock_flm.from_pretrained.return_value = (mock_model, mock_tokenizer)

        import builtins

        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "unsloth":
                return MagicMock(FastLanguageModel=mock_flm)
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", mock_import)

        result = export_gguf.export(
            agent_name="executor",
            model_path=str(adapter_dir),
            output_dir=str(tmp_path / "out"),
            quant="q4_0",
        )

        assert "q4_0.gguf" in result

    def test_main_calls_export(self, tmp_path, monkeypatch):
        from unittest.mock import MagicMock

        from scripts.finetune import export_gguf

        adapter_dir = tmp_path / "lora"
        adapter_dir.mkdir()
        (adapter_dir / "adapter_config.json").write_text("{}")

        mock_export = MagicMock()
        monkeypatch.setattr(export_gguf, "export", mock_export)

        export_gguf.main(
            [
                "--agent",
                "planner",
                "--model",
                str(adapter_dir),
                "--output",
                str(tmp_path / "gguf"),
            ]
        )

        mock_export.assert_called_once()
        call_kwargs = mock_export.call_args[1]
        assert call_kwargs["agent_name"] == "planner"
