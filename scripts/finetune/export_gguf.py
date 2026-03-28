"""Merge LoRA adapter + export to GGUF for Ollama.

Converts a fine-tuned LoRA adapter into a standalone GGUF file
that can be loaded by Ollama via a Modelfile.

Usage:
    python scripts/finetune/export_gguf.py --agent planner --model models/finetune/planner_dpo/lora
    python scripts/finetune/export_gguf.py --agent executor \
        --model models/finetune/executor/lora --quant q4_k_m
"""

import argparse
import sys
from pathlib import Path

# Quantization methods safe for 4GB VRAM
SAFE_QUANT_METHODS = {"q4_0", "q4_k_m", "q5_k_m", "q4_k_s"}

# Quantization methods that are too large for 4GB VRAM with 3B models
UNSAFE_QUANT_METHODS = {"q8_0", "f16", "f32"}

SUPPORTED_AGENTS = ["planner", "executor", "tester", "documenter"]


def validate_model_path(model_path: str) -> Path:
    """Validate that the model path exists and contains adapter files."""
    path = Path(model_path)
    if not path.exists():
        raise FileNotFoundError(f"Model path not found: {model_path}")

    # Check for adapter_config.json (LoRA adapter marker)
    adapter_config = path / "adapter_config.json"
    if not adapter_config.exists():
        # Could be a directory containing the lora/ subdirectory
        lora_subdir = path / "lora"
        if lora_subdir.exists() and (lora_subdir / "adapter_config.json").exists():
            return lora_subdir
        raise FileNotFoundError(
            f"No adapter_config.json found in {model_path}. "
            "Expected a LoRA adapter directory from train_sft.py or train_dpo.py."
        )

    return path


def validate_quant_method(quant: str) -> str:
    """Validate quantization method is safe for 4GB VRAM."""
    if quant in UNSAFE_QUANT_METHODS:
        raise ValueError(
            f"Quantization '{quant}' is too large for 4GB VRAM with 3B models. "
            f"Use one of: {sorted(SAFE_QUANT_METHODS)}"
        )
    return quant


def export(agent_name: str, model_path: str, output_dir: str, quant: str = "q4_k_m"):
    """Merge LoRA into base model and export as GGUF.

    Heavy ML dependencies imported only when called.
    """
    try:
        from unsloth import FastLanguageModel
    except ImportError:
        print("ERROR: unsloth not installed. Install with:")
        print('  pip install "unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git"')
        sys.exit(1)

    # Validate inputs
    validated_path = validate_model_path(model_path)
    validate_quant_method(quant)

    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    print(f"Exporting {agent_name} from {validated_path}")
    print(f"  Quantization: {quant}")
    print(f"  Output: {output_dir}")

    # Load model with LoRA adapter
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=str(validated_path),
        max_seq_length=2048,
        load_in_4bit=True,
    )

    # Merge LoRA into base and export as GGUF
    model.save_pretrained_gguf(
        str(output),
        tokenizer,
        quantization_method=quant,
    )

    gguf_file = output / f"{quant}.gguf"
    print(f"Exported {agent_name} to {gguf_file}")

    return str(gguf_file)


def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(description="Export fine-tuned model to GGUF for Ollama")
    parser.add_argument(
        "--agent",
        required=True,
        choices=SUPPORTED_AGENTS,
        help="Agent role",
    )
    parser.add_argument("--model", required=True, help="Path to final LoRA adapter")
    parser.add_argument("--output", default="models/gguf", help="Output directory for GGUF files")
    parser.add_argument("--quant", default="q4_k_m", help="Quantization method (default: q4_k_m)")
    args = parser.parse_args(argv)

    validate_quant_method(args.quant)

    export(
        agent_name=args.agent,
        model_path=args.model,
        output_dir=f"{args.output}/{args.agent}",
        quant=args.quant,
    )


if __name__ == "__main__":
    main()
