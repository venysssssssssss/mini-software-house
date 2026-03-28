"""DPO fine-tuning using SFT model as base.

Applies Direct Preference Optimization on top of an SFT adapter using
chosen/rejected pairs from the pipeline's self-healing corrections (DPOTuple table).

Usage:
    python scripts/finetune/train_dpo.py --agent executor \
        --sft-model models/finetune/executor/lora \
        --data data/finetune/dpo/executor.jsonl
"""

import argparse
import json
import sys
from pathlib import Path

# LoRA config for DPO (smaller rank — less data than SFT)
DPO_LORA_CONFIG = {
    "planner": {"r": 8, "lora_alpha": 8, "epochs": 2},
    "executor": {"r": 8, "lora_alpha": 8, "epochs": 2},
    "tester": {"r": 8, "lora_alpha": 8, "epochs": 2},
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

MINIMUM_DPO_PAIRS = 15


def validate_dpo_data(data_path: str) -> int:
    """Validate DPO JSONL training data. Returns number of pairs."""
    path = Path(data_path)
    if not path.exists():
        raise FileNotFoundError(f"DPO data not found: {data_path}")

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

            required = {"prompt", "chosen", "rejected"}
            missing = required - set(entry.keys())
            if missing:
                raise ValueError(f"Missing keys {missing} at line {i}")

            count += 1

    if count < MINIMUM_DPO_PAIRS:
        raise ValueError(
            f"Insufficient DPO pairs: {count} found, minimum {MINIMUM_DPO_PAIRS} required. "
            "Run more pipeline tasks to accumulate correction data."
        )

    return count


def get_dpo_training_args(agent_name: str, output_dir: str) -> dict:
    """Build DPO training arguments optimized for 4GB VRAM."""
    config = DPO_LORA_CONFIG[agent_name]

    return {
        "output_dir": output_dir,
        "per_device_train_batch_size": 1,
        "gradient_accumulation_steps": 4,
        "num_train_epochs": config["epochs"],
        "learning_rate": 5e-5,
        "fp16": True,
        "beta": 0.1,
        "logging_steps": 5,
        "save_strategy": "epoch",
        "optim": "adamw_8bit",
        "warmup_ratio": 0.1,
    }


def train_dpo(agent_name: str, sft_model_path: str, data_path: str, output_dir: str):
    """Run DPO training on top of an SFT-tuned model.

    Heavy ML dependencies imported only when called.
    """
    try:
        from unsloth import FastLanguageModel, PatchDPOTrainer
    except ImportError:
        print("ERROR: unsloth not installed. Install with:")
        print('  pip install "unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git"')
        sys.exit(1)

    try:
        from datasets import load_dataset
        from trl import DPOConfig, DPOTrainer
    except ImportError:
        print("ERROR: trl/datasets not installed. Install with:")
        print("  pip install trl datasets")
        sys.exit(1)

    config = DPO_LORA_CONFIG.get(agent_name)
    if config is None:
        print(f"ERROR: DPO not supported for agent '{agent_name}'")
        print(f"Supported agents: {list(DPO_LORA_CONFIG.keys())}")
        sys.exit(1)

    # Apply Unsloth DPO optimization
    PatchDPOTrainer()

    # Validate data
    num_pairs = validate_dpo_data(data_path)
    print(f"DPO training {agent_name} with {num_pairs} pairs from {data_path}")
    print(f"SFT base model: {sft_model_path}")

    # 1. Load SFT-tuned model
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=sft_model_path,
        max_seq_length=2048,
        load_in_4bit=True,
    )

    # 2. Apply fresh LoRA adapters for DPO
    model = FastLanguageModel.get_peft_model(
        model,
        r=config["r"],
        lora_alpha=config["lora_alpha"],
        target_modules=TARGET_MODULES,
        use_gradient_checkpointing="unsloth",
    )

    # 3. Load DPO dataset
    dataset = load_dataset("json", data_files=data_path, split="train")

    # 4. DPO training config
    dpo_args = get_dpo_training_args(agent_name, output_dir)
    dpo_config = DPOConfig(**dpo_args)

    # 5. Train with DPO
    trainer = DPOTrainer(
        model=model,
        ref_model=None,  # Unsloth handles reference model internally
        tokenizer=tokenizer,
        train_dataset=dataset,
        args=dpo_config,
    )

    trainer.train()

    # 6. Save adapter
    lora_path = f"{output_dir}/lora"
    model.save_pretrained(lora_path)
    tokenizer.save_pretrained(lora_path)

    print(f"DPO training complete for {agent_name}")
    print(f"  Adapter saved to: {lora_path}")

    return lora_path


def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(description="DPO fine-tuning on SFT base")
    parser.add_argument(
        "--agent",
        required=True,
        choices=list(DPO_LORA_CONFIG.keys()),
        help="Agent role to fine-tune",
    )
    parser.add_argument("--sft-model", required=True, help="Path to SFT LoRA adapter")
    parser.add_argument("--data", required=True, help="Path to DPO JSONL training data")
    parser.add_argument("--output", default="models/finetune", help="Output directory")
    args = parser.parse_args(argv)

    train_dpo(
        agent_name=args.agent,
        sft_model_path=args.sft_model,
        data_path=args.data,
        output_dir=f"{args.output}/{args.agent}_dpo",
    )


if __name__ == "__main__":
    main()
