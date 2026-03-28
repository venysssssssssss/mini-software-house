"""SFT fine-tuning script using Unsloth QLoRA.

Optimized for GTX 1050 Ti (4GB VRAM):
- 4-bit quantization (load_in_4bit=True)
- Gradient checkpointing ("unsloth" mode — 30% less VRAM)
- Batch size 1 + gradient accumulation
- AdamW 8-bit optimizer

Usage:
    python scripts/finetune/train_sft.py --agent planner --data data/finetune/sft/planner.jsonl
    python scripts/finetune/train_sft.py --agent executor --data data/finetune/sft/executor.jsonl
"""

import argparse
import json
import sys
from pathlib import Path

# Map agent role to Unsloth-optimized model identifier
MODEL_MAP = {
    "planner": "unsloth/Qwen2.5-3B-Instruct-bnb-4bit",
    "executor": "unsloth/Qwen2.5-Coder-3B-Instruct-bnb-4bit",
    "tester": "unsloth/deepseek-coder-1.3b-instruct-bnb-4bit",
    "documenter": "unsloth/gemma-2-2b-it-bnb-4bit",
}

# LoRA configuration per agent (smaller models get smaller rank)
LORA_CONFIG = {
    "planner": {"r": 16, "lora_alpha": 16, "epochs": 3},
    "executor": {"r": 16, "lora_alpha": 16, "epochs": 3},
    "tester": {"r": 16, "lora_alpha": 16, "epochs": 3},
    "documenter": {"r": 8, "lora_alpha": 8, "epochs": 2},
}

TARGET_MODULES = [
    "q_proj",
    "k_proj",
    "v_proj",
    "o_proj",
    "gate_proj",
    "up_proj",
    "down_proj",
]


def validate_data(data_path: str) -> int:
    """Validate JSONL training data. Returns number of examples."""
    path = Path(data_path)
    if not path.exists():
        raise FileNotFoundError(f"Training data not found: {data_path}")

    count = 0
    with open(path, encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON at line {i}: {e}")

            if "conversations" not in entry:
                raise ValueError(f"Missing 'conversations' key at line {i}")

            convs = entry["conversations"]
            if not isinstance(convs, list) or len(convs) < 2:
                raise ValueError(f"conversations must have >= 2 turns at line {i}")

            count += 1

    if count == 0:
        raise ValueError(f"No training examples found in {data_path}")

    return count


def get_training_args(agent_name: str, output_dir: str):
    """Build training arguments optimized for 4GB VRAM."""
    config = LORA_CONFIG[agent_name]

    return {
        "output_dir": output_dir,
        "per_device_train_batch_size": 1,
        "gradient_accumulation_steps": 4,
        "num_train_epochs": config["epochs"],
        "learning_rate": 2e-4,
        "fp16": True,
        "logging_steps": 10,
        "save_strategy": "epoch",
        "optim": "adamw_8bit",
        "warmup_ratio": 0.05,
        "weight_decay": 0.01,
        "seed": 42,
    }


def train(agent_name: str, base_model: str, data_path: str, output_dir: str):
    """Run SFT training with Unsloth QLoRA.

    This function imports heavy ML dependencies (torch, unsloth, trl)
    only when actually called, so the module can be imported and tested
    without GPU/ML dependencies installed.
    """
    try:
        from unsloth import FastLanguageModel
    except ImportError:
        print("ERROR: unsloth not installed. Install with:")
        print('  pip install "unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git"')
        sys.exit(1)

    try:
        from datasets import load_dataset
        from transformers import TrainingArguments
        from trl import SFTTrainer
    except ImportError:
        print("ERROR: trl/datasets not installed. Install with:")
        print("  pip install trl datasets")
        sys.exit(1)

    config = LORA_CONFIG[agent_name]

    # Validate data first
    num_examples = validate_data(data_path)
    print(f"Training {agent_name} with {num_examples} examples from {data_path}")

    # 1. Load base model with 4-bit quantization
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=base_model,
        max_seq_length=2048,
        load_in_4bit=True,
        dtype=None,
    )

    # 2. Apply LoRA adapters
    model = FastLanguageModel.get_peft_model(
        model,
        r=config["r"],
        lora_alpha=config["lora_alpha"],
        lora_dropout=0,
        target_modules=TARGET_MODULES,
        use_gradient_checkpointing="unsloth",
    )

    # 3. Load dataset
    dataset = load_dataset("json", data_files=data_path, split="train")

    # 4. Training arguments
    training_args = TrainingArguments(**get_training_args(agent_name, output_dir))

    # 5. Train
    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=dataset,
        args=training_args,
        dataset_text_field="text",
        max_seq_length=2048,
    )

    trainer.train()

    # 6. Save LoRA adapter
    lora_path = f"{output_dir}/lora"
    model.save_pretrained(lora_path)
    tokenizer.save_pretrained(lora_path)

    print(f"SFT training complete for {agent_name}")
    print(f"  Adapter saved to: {lora_path}")

    return lora_path


def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(description="SFT fine-tuning with Unsloth QLoRA")
    parser.add_argument(
        "--agent",
        required=True,
        choices=list(MODEL_MAP.keys()),
        help="Agent role to fine-tune",
    )
    parser.add_argument("--data", required=True, help="Path to SFT JSONL training data")
    parser.add_argument("--output", default="models/finetune", help="Output directory")
    args = parser.parse_args(argv)

    base_model = MODEL_MAP[args.agent]
    output_dir = f"{args.output}/{args.agent}"

    train(
        agent_name=args.agent,
        base_model=base_model,
        data_path=args.data,
        output_dir=output_dir,
    )


if __name__ == "__main__":
    main()
