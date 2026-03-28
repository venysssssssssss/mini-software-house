# Sprint FT — "Fine-Tune the Pipeline" (Model Specialization)

**Created:** 2026-03-28
**Status:** Complete
**Estimated Duration:** 2–3 weeks
**Prerequisite:** Sprint 2 complete (DPO data infrastructure, metrics collection)
**Hardware:** GTX 1050 Ti (4GB VRAM), CUDA 12.x

---

## Goal

Fine-tune each of the 6 Ollama models on task-specific data collected by the pipeline's data flywheel (DPOTuple, AgentLog). Measure improvement via first-pass success rate before/after. Deploy fine-tuned models back into the pipeline via Ollama Modelfiles without changing any Python code — only `get_model_for_role()` mappings change.

---

## Current Model Mapping

| Role | Base Model | Size | System Prompt Summary | Fine-Tune Priority |
|------|-----------|------|----------------------|-------------------|
| `planner` | `qwen2.5:3b` | 3B | Software Architect — JSON-only output with strict schema | **High** — JSON compliance is critical |
| `backend` (executor) | `qwen2.5-coder:3b` | 3B | Expert developer — multi-file code gen with filepath comments | **High** — code quality drives everything |
| `frontend` (executor) | `qwen2.5-coder:1.5b` | 1.5B | Same as backend but for frontend tasks | Medium |
| `tester` | `deepseek-coder:1.3b` | 1.3B | QA Engineer — pytest generation with filepath format | **High** — test quality enables self-healing |
| `documenter` | `gemma2:2b` | 2B | Technical Writer — markdown documentation | Low |
| `rag` | `phi3:mini` | 3.8B | Query engine for ChromaDB retrieval | Low (skip for now) |

**Priority order:** planner → executor (backend) → tester → executor (frontend) → documenter. RAG agent is skipped — it queries an embedding DB, not generating structured output.

---

## Phase 0 — Data Collection Baseline

**Goal:** Accumulate enough training data before fine-tuning begins.

### 0.1 Run Pipeline on Diverse Tasks

Run 30–50 pipeline invocations with varied prompts to populate the database:

```bash
# Example batch — run each as a separate pipeline invocation
make run TASK="Build a REST API for a todo list with Flask"
make run TASK="Create a CLI calculator with argparse"
make run TASK="Build a URL shortener with SQLite backend"
make run TASK="Create a markdown-to-HTML converter"
make run TASK="Build a simple chat server with websockets"
# ... (aim for 30-50 diverse tasks)
```

### 0.2 Minimum Data Thresholds

| Agent | SFT Examples Needed | DPO Pairs Needed | Source |
|-------|--------------------|--------------------|--------|
| Planner | 30+ (prompt → valid JSON plan) | 10+ (invalid JSON → corrected JSON) | `AgentLog` + `PipelineRun` |
| Executor | 30+ (task → working code) | 15+ (failed code → corrected code) | `DPOTuple` where `agent_name='Executor'` |
| Tester | 30+ (code → pytest tests) | 10+ (bad tests → fixed tests) | `DPOTuple` where `agent_name='Tester'` |
| Documenter | 20+ (code context → markdown) | — (SFT only) | `AgentLog` |

### 0.3 Verify Data Exists

```sql
-- Check DPO tuple counts per agent
SELECT agent_name, COUNT(*) as total,
       SUM(CASE WHEN correction_successful = 1 THEN 1 ELSE 0 END) as successful_corrections
FROM dpotuple
GROUP BY agent_name;

-- Check total pipeline runs
SELECT COUNT(*) FROM pipelinerun WHERE status = 'completed';
```

**Verification:** At least 30 completed pipeline runs and 15+ DPO tuples before proceeding to Phase 1.

---

## Phase 1 — Data Export Pipeline

**Goal:** Export SQLite training data to JSONL format suitable for Unsloth SFT and DPO training.

### 1.1 Create Export Script

Create `scripts/finetune/export_training_data.py`:

```python
"""Export training data from SQLite to JSONL for fine-tuning."""

import json
from pathlib import Path
from sqlmodel import Session, create_engine, select
from src.core.models import AgentLog, DPOTuple, PipelineRun

def export_sft_data(agent_name: str, output_path: Path):
    """Export SFT data as chat-format JSONL.

    Format (Unsloth chat template):
    {"conversations": [
        {"from": "system", "value": "<system_prompt>"},
        {"from": "human", "value": "<user_request>"},
        {"from": "gpt", "value": "<agent_response>"}
    ]}
    """
    ...

def export_dpo_data(agent_name: str, output_path: Path):
    """Export DPO data as chosen/rejected pairs.

    Format:
    {"prompt": "<task>",
     "chosen": "<corrected_code>",
     "rejected": "<original_failed_code>"}
    """
    ...
```

### 1.2 SFT Data Format (per agent)

**Planner — JSON compliance training:**
```jsonl
{"conversations": [{"from": "system", "value": "You are a Software Architect and Planner. You MUST respond ONLY with a valid, parsable JSON object..."}, {"from": "human", "value": "Build a REST API for a todo list"}, {"from": "gpt", "value": "{\"project_name\": \"build-todo-api\", \"architecture\": \"Flask REST API\", \"files_to_create\": [\"app.py\", \"models.py\"], \"dependencies\": [\"flask\"], \"logical_steps\": [\"Create models\", \"Add routes\"]}"}]}
```

**Executor — Code generation with filepath format:**
```jsonl
{"conversations": [{"from": "system", "value": "You are an expert software developer. Write clean, efficient code. For every file, wrap code in a markdown block with filepath comment on the first line..."}, {"from": "human", "value": "Create app.py for a Flask todo API with CRUD routes"}, {"from": "gpt", "value": "```python\n# filepath: app.py\nfrom flask import Flask, jsonify, request\napp = Flask(__name__)\n...\n```"}]}
```

**Tester — Pytest generation:**
```jsonl
{"conversations": [{"from": "system", "value": "You are a Software QA and Test Engineer. Write pytest tests for the provided Python code..."}, {"from": "human", "value": "Write tests for this Flask app:\n<code>"}, {"from": "gpt", "value": "```python\n# filepath: test_app.py\nimport pytest\n...\n```"}]}
```

### 1.3 DPO Data Format

```jsonl
{"prompt": "Write tests for this code:\ndef add(a, b): return a + b", "chosen": "```python\n# filepath: test_math.py\ndef test_add():\n    assert add(2, 3) == 5\n```", "rejected": "```python\n# filepath: test_math.py\ndef test_add():\n    assert add(2, 3) == 6\n```"}
```

DPO pairs come from `DPOTuple` where `correction_successful = True`:
- `rejected` = `generated_code` (original, failed)
- `chosen` = `corrected_code` (fixed version that passed tests)

### 1.4 Deliverables

- [x] `scripts/finetune/export_training_data.py` — exports SFT + DPO JSONL per agent
- [x] `data/finetune/sft/{planner,executor,tester,documenter}.jsonl`
- [x] `data/finetune/dpo/{executor,tester,planner}.jsonl`
- [x] Validation: each JSONL line parses, conversations have correct roles

**Verification:**
```bash
# Every line must be valid JSON
python -c "import json; [json.loads(l) for l in open('data/finetune/sft/planner.jsonl')]"
# Check counts
wc -l data/finetune/sft/*.jsonl data/finetune/dpo/*.jsonl
```

---

## Phase 2 — SFT Training (Supervised Fine-Tuning)

**Goal:** Fine-tune each priority model using QLoRA on collected task-specific data.

### 2.1 Training Environment Setup

```bash
# Install Unsloth (optimized for consumer GPUs)
pip install "unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git"
pip install trl datasets

# Verify GPU is visible
python -c "import torch; print(torch.cuda.get_device_name(0), torch.cuda.get_device_properties(0).total_mem // 1024**2, 'MB')"
# Expected: NVIDIA GeForce GTX 1050 Ti 4096 MB
```

Add to `pyproject.toml` under `[tool.poetry.group.ml.dependencies]`:
```toml
trl = ">=0.12.0"
datasets = ">=3.0.0"
# unsloth installed separately via pip (git dependency)
```

### 2.2 Training Script Template

Create `scripts/finetune/train_sft.py`:

```python
"""SFT fine-tuning script using Unsloth QLoRA.

Optimized for GTX 1050 Ti (4GB VRAM):
- 4-bit quantization (load_in_4bit=True)
- Gradient checkpointing ("unsloth" mode — 30% less VRAM)
- Batch size 1 + gradient accumulation
- AdamW 8-bit optimizer
"""

from unsloth import FastLanguageModel
from trl import SFTTrainer
from transformers import TrainingArguments
from datasets import load_dataset
import argparse

def train(agent_name: str, base_model: str, data_path: str, output_dir: str):
    # 1. Load base model with 4-bit quantization
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=base_model,
        max_seq_length=2048,      # sufficient for code generation
        load_in_4bit=True,         # critical for 4GB VRAM
        dtype=None,                # auto-detect
    )

    # 2. Apply LoRA adapters
    model = FastLanguageModel.get_peft_model(
        model,
        r=16,                      # LoRA rank (16 is good for 3B models)
        lora_alpha=16,
        lora_dropout=0,            # Unsloth optimized — 0 is fine
        target_modules=[
            "q_proj", "k_proj", "v_proj", "o_proj",
            "gate_proj", "up_proj", "down_proj",
        ],
        use_gradient_checkpointing="unsloth",  # 30% less VRAM
    )

    # 3. Load dataset
    dataset = load_dataset("json", data_files=data_path, split="train")

    # 4. Training config (4GB VRAM safe)
    training_args = TrainingArguments(
        output_dir=output_dir,
        per_device_train_batch_size=1,       # must be 1 for 4GB
        gradient_accumulation_steps=4,        # effective batch = 4
        num_train_epochs=3,
        learning_rate=2e-4,
        fp16=True,                            # GTX 1050 Ti has no bf16
        logging_steps=10,
        save_strategy="epoch",
        optim="adamw_8bit",                   # 8-bit optimizer saves VRAM
        warmup_ratio=0.05,
        weight_decay=0.01,
        seed=42,
    )

    # 5. Train
    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=dataset,
        args=training_args,
        dataset_text_field="text",            # or use formatting_func
        max_seq_length=2048,
    )

    trainer.train()

    # 6. Save LoRA adapter
    model.save_pretrained(f"{output_dir}/lora")
    tokenizer.save_pretrained(f"{output_dir}/lora")

    print(f"✓ SFT training complete for {agent_name}")
    print(f"  Adapter saved to: {output_dir}/lora")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--agent", required=True, choices=["planner", "executor", "tester", "documenter"])
    parser.add_argument("--data", required=True, help="Path to SFT JSONL")
    parser.add_argument("--output", default="models/finetune")
    args = parser.parse_args()

    MODEL_MAP = {
        "planner":    "unsloth/Qwen2.5-3B-Instruct-bnb-4bit",
        "executor":   "unsloth/Qwen2.5-Coder-3B-Instruct-bnb-4bit",
        "tester":     "unsloth/deepseek-coder-1.3b-instruct-bnb-4bit",
        "documenter": "unsloth/gemma-2-2b-it-bnb-4bit",
    }

    train(
        agent_name=args.agent,
        base_model=MODEL_MAP[args.agent],
        data_path=args.data,
        output_dir=f"{args.output}/{args.agent}",
    )
```

### 2.3 Training Order and Parameters

Train one model at a time (only 4GB VRAM). Close Ollama before training:

```bash
# Stop Ollama to free VRAM
systemctl --user stop ollama  # or: ollama stop

# Train in priority order
python scripts/finetune/train_sft.py --agent planner    --data data/finetune/sft/planner.jsonl
python scripts/finetune/train_sft.py --agent executor    --data data/finetune/sft/executor.jsonl
python scripts/finetune/train_sft.py --agent tester      --data data/finetune/sft/tester.jsonl
python scripts/finetune/train_sft.py --agent documenter  --data data/finetune/sft/documenter.jsonl
```

| Agent | Base Model (Unsloth) | LoRA r | Epochs | Est. Time (4GB) |
|-------|---------------------|--------|--------|-----------------|
| planner | Qwen2.5-3B-Instruct-bnb-4bit | 16 | 3 | ~20 min (30 samples) |
| executor | Qwen2.5-Coder-3B-Instruct-bnb-4bit | 16 | 3 | ~25 min (30 samples) |
| tester | deepseek-coder-1.3b-instruct-bnb-4bit | 16 | 3 | ~15 min (30 samples) |
| documenter | gemma-2-2b-it-bnb-4bit | 8 | 2 | ~10 min (20 samples) |

### 2.4 Deliverables

- [x] `scripts/finetune/train_sft.py` — parameterized SFT training script
- [ ] `models/finetune/{planner,executor,tester,documenter}/lora/` — LoRA adapters (requires GPU training)
- [ ] Training logs showing loss convergence (requires GPU training)

**Verification:**
```bash
# Check adapter files exist
ls models/finetune/planner/lora/adapter_config.json
ls models/finetune/executor/lora/adapter_config.json
# Check training logs show decreasing loss
grep "loss" models/finetune/planner/checkpoint-*/trainer_state.json
```

---

## Phase 3 — DPO Training (Direct Preference Optimization)

**Goal:** Further align models using chosen/rejected pairs from the self-healing loop.

### 3.1 DPO Training Script

Create `scripts/finetune/train_dpo.py`:

```python
"""DPO fine-tuning using SFT model as base.

Applies DPO on top of the SFT adapter using chosen/rejected pairs
from the pipeline's self-healing corrections (DPOTuple table).
"""

from unsloth import FastLanguageModel, PatchDPOTrainer
from trl import DPOTrainer, DPOConfig
from datasets import load_dataset

PatchDPOTrainer()  # Unsloth optimization

def train_dpo(agent_name: str, sft_model_path: str, data_path: str, output_dir: str):
    # Load SFT-tuned model (from Phase 2 output)
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=sft_model_path,
        max_seq_length=2048,
        load_in_4bit=True,
    )

    model = FastLanguageModel.get_peft_model(
        model,
        r=8,                       # smaller rank for DPO (less data)
        lora_alpha=8,
        target_modules=[
            "q_proj", "k_proj", "v_proj", "o_proj",
            "gate_proj", "up_proj", "down_proj",
        ],
        use_gradient_checkpointing="unsloth",
    )

    # DPO dataset: {"prompt": ..., "chosen": ..., "rejected": ...}
    dataset = load_dataset("json", data_files=data_path, split="train")

    dpo_config = DPOConfig(
        output_dir=output_dir,
        per_device_train_batch_size=1,
        gradient_accumulation_steps=4,
        num_train_epochs=2,
        learning_rate=5e-5,           # lower LR for DPO
        fp16=True,
        beta=0.1,                     # DPO temperature
        logging_steps=5,
        save_strategy="epoch",
        optim="adamw_8bit",
        warmup_ratio=0.1,
    )

    trainer = DPOTrainer(
        model=model,
        ref_model=None,               # Unsloth handles this internally
        tokenizer=tokenizer,
        train_dataset=dataset,
        args=dpo_config,
    )

    trainer.train()
    model.save_pretrained(f"{output_dir}/lora")
    tokenizer.save_pretrained(f"{output_dir}/lora")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--agent", required=True)
    parser.add_argument("--sft-model", required=True, help="Path to SFT LoRA adapter")
    parser.add_argument("--data", required=True, help="Path to DPO JSONL")
    parser.add_argument("--output", default="models/finetune")
    args = parser.parse_args()

    train_dpo(
        agent_name=args.agent,
        sft_model_path=args.sft_model,
        data_path=args.data,
        output_dir=f"{args.output}/{args.agent}_dpo",
    )
```

### 3.2 Training Order

DPO is only applied to agents that have sufficient correction data (15+ pairs):

```bash
# Only train DPO for agents with enough correction data
python scripts/finetune/train_dpo.py \
    --agent executor \
    --sft-model models/finetune/executor/lora \
    --data data/finetune/dpo/executor.jsonl

python scripts/finetune/train_dpo.py \
    --agent tester \
    --sft-model models/finetune/tester/lora \
    --data data/finetune/dpo/tester.jsonl

python scripts/finetune/train_dpo.py \
    --agent planner \
    --sft-model models/finetune/planner/lora \
    --data data/finetune/dpo/planner.jsonl
```

### 3.3 Deliverables

- [x] `scripts/finetune/train_dpo.py` — DPO training script
- [ ] `models/finetune/{executor,tester,planner}_dpo/lora/` — DPO-tuned adapters (requires GPU training)
- [x] Only agents with 15+ DPO pairs get DPO training; others use SFT-only

**Verification:**
```bash
# DPO loss should be lower than random (< 0.693)
grep "loss" models/finetune/executor_dpo/checkpoint-*/trainer_state.json
```

---

## Phase 4 — GGUF Conversion & Ollama Deployment

**Goal:** Convert fine-tuned models to GGUF Q4_K_M format and load into Ollama.

### 4.1 GGUF Export Script

Create `scripts/finetune/export_gguf.py`:

```python
"""Merge LoRA adapter + export to GGUF for Ollama."""

from unsloth import FastLanguageModel

def export(agent_name: str, model_path: str, output_dir: str, quant: str = "q4_k_m"):
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=model_path,
        max_seq_length=2048,
        load_in_4bit=True,
    )

    # Merge LoRA into base and export as GGUF
    model.save_pretrained_gguf(
        output_dir,
        tokenizer,
        quantization_method=quant,  # Q4_K_M: good quality/size balance
    )
    print(f"✓ Exported {agent_name} to {output_dir}/{quant}.gguf")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--agent", required=True)
    parser.add_argument("--model", required=True, help="Path to final LoRA adapter")
    parser.add_argument("--output", default="models/gguf")
    parser.add_argument("--quant", default="q4_k_m")
    args = parser.parse_args()

    export(args.agent, args.model, f"{args.output}/{args.agent}", args.quant)
```

```bash
# Export each fine-tuned model
# Use DPO model if available, otherwise SFT model
python scripts/finetune/export_gguf.py --agent planner    --model models/finetune/planner_dpo/lora
python scripts/finetune/export_gguf.py --agent executor   --model models/finetune/executor_dpo/lora
python scripts/finetune/export_gguf.py --agent tester     --model models/finetune/tester_dpo/lora
python scripts/finetune/export_gguf.py --agent documenter --model models/finetune/documenter/lora
```

### 4.2 Ollama Modelfiles

Create `modelfiles/` directory with one Modelfile per agent:

**`modelfiles/Modelfile.planner-ft`**
```dockerfile
FROM ./models/gguf/planner/q4_k_m.gguf

PARAMETER temperature 0.3
PARAMETER top_p 0.9
PARAMETER num_ctx 2048
PARAMETER stop "<|endoftext|>"
PARAMETER stop "<|im_end|>"

SYSTEM """You are a Software Architect and Planner. You MUST respond ONLY with a valid, parsable JSON object. DO NOT include markdown formatting, DO NOT include backticks (```), and DO NOT add any explanatory text.
The JSON must have exactly the following structure:
{
  "project_name": "action-object-purpose-in-kebab-case",
  "architecture": "brief description",
  "files_to_create": ["file1.py", "file2.py"],
  "dependencies": ["lib1", "lib2"],
  "logical_steps": ["step 1", "step 2"]
}
IMPORTANT: project_name MUST be in kebab-case format (lowercase, hyphens, no spaces). Pattern: action-object-purpose (e.g., 'build-user-api', 'create-chat-app')"""
```

**`modelfiles/Modelfile.executor-ft`**
```dockerfile
FROM ./models/gguf/executor/q4_k_m.gguf

PARAMETER temperature 0.4
PARAMETER top_p 0.95
PARAMETER num_ctx 2048
PARAMETER stop "<|endoftext|>"
PARAMETER stop "<|im_end|>"

SYSTEM """You are an expert software developer. Write clean, efficient, and well-documented code. Always output the complete code. For every file you create or modify, wrap the code in a markdown block and ALWAYS put a comment on the VERY FIRST LINE inside the block specifying the relative filepath.
Use the appropriate comment syntax for the language:
- Python/CSS/JS: # filepath: filename.ext
- HTML: <!-- filepath: filename.html -->"""
```

**`modelfiles/Modelfile.tester-ft`**
```dockerfile
FROM ./models/gguf/tester/q4_k_m.gguf

PARAMETER temperature 0.2
PARAMETER top_p 0.9
PARAMETER num_ctx 2048
PARAMETER stop "<|endoftext|>"

SYSTEM """You are a Software QA and Test Engineer. Write pytest tests for the provided Python code. Focus on testing the core logic. Always wrap the test code in a markdown block starting with ```python and ALWAYS put a comment on the VERY FIRST LINE specifying the relative filepath as '# filepath: test_<filename>.py'."""
```

**`modelfiles/Modelfile.documenter-ft`**
```dockerfile
FROM ./models/gguf/documenter/q4_k_m.gguf

PARAMETER temperature 0.5
PARAMETER top_p 0.95
PARAMETER num_ctx 2048

SYSTEM """You are a Technical Writer. Write clear, comprehensive markdown documentation. Use the provided code context to explain how the system works."""
```

### 4.3 Register in Ollama

```bash
# Create fine-tuned models in Ollama
ollama create planner-ft    -f modelfiles/Modelfile.planner-ft
ollama create executor-ft   -f modelfiles/Modelfile.executor-ft
ollama create tester-ft     -f modelfiles/Modelfile.tester-ft
ollama create documenter-ft -f modelfiles/Modelfile.documenter-ft

# Verify they load
ollama run planner-ft '{"test": true}' --format json
ollama run executor-ft 'Write a hello world Python script'
```

### 4.4 Update Model Mapping

Update `src/agents/base.py` `get_model_for_role()`:

```python
def get_model_for_role(role: str) -> str:
    """Returns model for role. Uses fine-tuned variants when available."""
    models = {
        "planner": "planner-ft",           # was: qwen2.5:3b
        "backend": "executor-ft",          # was: qwen2.5-coder:3b
        "frontend": "qwen2.5-coder:1.5b", # no FT yet (low priority)
        "tester": "tester-ft",             # was: deepseek-coder:1.3b
        "documenter": "documenter-ft",     # was: gemma2:2b
        "rag": "phi3:mini",                # no FT (embedding queries)
    }
    return models.get(role, "qwen2.5:3b")
```

### 4.5 Deliverables

- [x] `scripts/finetune/export_gguf.py` — GGUF export script
- [x] `modelfiles/Modelfile.{planner,executor,tester,documenter}-ft` — Ollama Modelfiles
- [ ] All 4 models registered in Ollama (`ollama list` shows them) (requires GGUF files from training)
- [x] `get_model_for_role()` updated to use `-ft` variants via `USE_FINETUNED_MODELS` env var
- [x] Fallback: if FT model not found, original model still works

**Anti-patterns:**
- Do NOT change system prompts in Python code — they're baked into the Modelfile
- Do NOT use Q8_0 quantization — too large for 4GB VRAM with 3B models
- Do NOT load multiple fine-tuned models simultaneously — keep `OLLAMA_MAX_LOADED_MODELS=1`

---

## Phase 5 — Evaluation & A/B Testing

**Goal:** Measure whether fine-tuned models actually improve pipeline output.

### 5.1 Evaluation Script

Create `scripts/finetune/evaluate.py`:

```python
"""A/B evaluation: base models vs fine-tuned models.

Runs the same set of tasks with both model configs and compares:
- First-pass success rate (tests pass without correction)
- JSON validity rate (planner)
- Correction loop count (how many retries needed)
- Token efficiency (output tokens per successful generation)
"""

EVAL_TASKS = [
    "Build a simple key-value store with a CLI interface",
    "Create a markdown link checker that reports broken URLs",
    "Build a CSV to JSON converter with validation",
    "Create a simple HTTP health check monitor",
    "Build a file deduplication tool using SHA256 hashes",
    # ... 10 total, covering different complexity levels
]

def evaluate(model_config: str, tasks: list[str]) -> dict:
    """Run pipeline with given model config, return metrics."""
    results = {
        "first_pass_success": 0,
        "total_corrections": 0,
        "json_valid_rate": 0,  # planner only
        "total_tokens": 0,
        "avg_latency_ms": 0,
    }
    # ... run each task, aggregate metrics from DB
    return results
```

### 5.2 Metrics to Compare

| Metric | Definition | Target Improvement |
|--------|-----------|-------------------|
| **First-pass success rate** | % of files that pass tests without correction | +20% (e.g., 60% → 80%) |
| **JSON validity rate** | % of planner responses that parse as valid JSON | +15% (e.g., 85% → 100%) |
| **Correction loops** | Average retries per failed file | -30% (e.g., 2.1 → 1.5) |
| **Format compliance** | % of executor outputs with correct `# filepath:` header | +10% |
| **Token efficiency** | Average response tokens per successful generation | -10% (more focused output) |

### 5.3 Evaluation Process

```bash
# 1. Run evaluation with BASE models (restore original get_model_for_role)
python scripts/finetune/evaluate.py --config base --output results/eval_base.json

# 2. Run evaluation with FINE-TUNED models
python scripts/finetune/evaluate.py --config finetuned --output results/eval_ft.json

# 3. Compare
python scripts/finetune/evaluate.py --compare results/eval_base.json results/eval_ft.json
```

### 5.4 Rollback Criteria

If fine-tuned models perform worse, rollback is trivial:

```python
# Revert get_model_for_role() to original mappings
# OR keep both and use environment variable:
import os
USE_FINETUNED = os.getenv("USE_FINETUNED_MODELS", "true").lower() == "true"

def get_model_for_role(role: str) -> str:
    if USE_FINETUNED:
        ft_models = {"planner": "planner-ft", "backend": "executor-ft", ...}
        model = ft_models.get(role)
        if model:
            return model
    # Fallback to base models
    base_models = {"planner": "qwen2.5:3b", "backend": "qwen2.5-coder:3b", ...}
    return base_models.get(role, "qwen2.5:3b")
```

### 5.5 Deliverables

- [x] `scripts/finetune/evaluate.py` — A/B evaluation harness
- [ ] `results/eval_base.json` and `results/eval_ft.json` — comparison data (requires pipeline runs)
- [ ] Documented improvement (or regression) per metric per agent (requires pipeline runs)
- [x] Environment variable toggle: `USE_FINETUNED_MODELS=true|false`

---

## Phase 6 — Continuous Improvement Loop

**Goal:** Automate the data collection → fine-tune → evaluate cycle.

### 6.1 Makefile Targets

Add to `Makefile`:

```makefile
# Fine-tuning pipeline
finetune-export:
	python scripts/finetune/export_training_data.py --all --output data/finetune

finetune-train: finetune-export
	@echo "Training SFT models (one at a time to fit 4GB VRAM)..."
	python scripts/finetune/train_sft.py --agent planner  --data data/finetune/sft/planner.jsonl
	python scripts/finetune/train_sft.py --agent executor  --data data/finetune/sft/executor.jsonl
	python scripts/finetune/train_sft.py --agent tester    --data data/finetune/sft/tester.jsonl

finetune-dpo: finetune-train
	@echo "Training DPO models..."
	python scripts/finetune/train_dpo.py --agent executor --sft-model models/finetune/executor/lora --data data/finetune/dpo/executor.jsonl
	python scripts/finetune/train_dpo.py --agent tester   --sft-model models/finetune/tester/lora   --data data/finetune/dpo/tester.jsonl

finetune-export-gguf: finetune-dpo
	python scripts/finetune/export_gguf.py --agent planner    --model models/finetune/planner/lora
	python scripts/finetune/export_gguf.py --agent executor   --model models/finetune/executor_dpo/lora
	python scripts/finetune/export_gguf.py --agent tester     --model models/finetune/tester_dpo/lora

finetune-deploy: finetune-export-gguf
	ollama create planner-ft    -f modelfiles/Modelfile.planner-ft
	ollama create executor-ft   -f modelfiles/Modelfile.executor-ft
	ollama create tester-ft     -f modelfiles/Modelfile.tester-ft

finetune-eval:
	python scripts/finetune/evaluate.py --config finetuned --output results/eval_ft.json

finetune-all: finetune-deploy finetune-eval
	@echo "Fine-tuning pipeline complete!"
```

### 6.2 Re-training Schedule

After accumulating 50+ new pipeline runs, re-export data and retrain. The DPOTuple table grows automatically with every self-healing correction — no manual data labeling needed.

```
Pipeline runs → DPOTuple/AgentLog → export JSONL → SFT → DPO → GGUF → Ollama → Pipeline runs
       ↑_________________________________________________________________________↓
                              Continuous improvement loop
```

### 6.3 Deliverables

- [x] Makefile targets: `finetune-export`, `finetune-train`, `finetune-dpo`, `finetune-deploy`, `finetune-eval`, `finetune-all`
- [x] Documentation on when to retrain (50+ new runs threshold)

---

## Summary

| Phase | What | Output | Est. Time |
|-------|------|--------|-----------|
| **0** | Data collection | 30+ pipeline runs in DB | ~2 hours (running tasks) |
| **1** | Export to JSONL | `data/finetune/{sft,dpo}/*.jsonl` | 1 hour |
| **2** | SFT training | LoRA adapters (4 models) | ~1.5 hours |
| **3** | DPO training | DPO adapters (3 models) | ~1 hour |
| **4** | GGUF + Ollama | 4 fine-tuned models in Ollama | 30 min |
| **5** | Evaluation | A/B comparison report | ~2 hours |
| **6** | Automation | Makefile targets, retrain loop | 30 min |

**Total estimated time:** ~8–9 hours (mostly training + evaluation compute)

### Dependencies

```
Phase 0: Data Collection (30+ pipeline runs)
 └── Phase 1: Export (JSONL files)
      └── Phase 2: SFT Training
           └── Phase 3: DPO Training (optional, needs 15+ pairs)
                └── Phase 4: GGUF + Ollama Deployment
                     └── Phase 5: Evaluation (A/B test)
Phase 6: Automation (can start after Phase 4)
```

### Anti-Pattern Guards

| Don't | Why | Do Instead |
|-------|-----|-----------|
| Train on <20 examples | Overfitting, memorization | Wait for more pipeline runs |
| Use Q8_0 quantization | Won't fit in 4GB VRAM with 3B models | Use Q4_K_M |
| Load 2+ models simultaneously | OOM on GTX 1050 Ti | `OLLAMA_MAX_LOADED_MODELS=1` |
| Skip SFT and go straight to DPO | DPO needs a competent base to work | Always SFT first |
| Change system prompts in Python after FT | Prompts are baked into Modelfile | Update Modelfile, re-create in Ollama |
| Fine-tune RAG/phi3:mini | It does embedding queries, not generation | Skip, use base model |
| Train with bf16 | GTX 1050 Ti doesn't support bf16 | Use fp16 |
| Use batch_size > 1 | OOM on 4GB VRAM | batch_size=1 + gradient_accumulation |

### Relationship to Sprint Plan

| Sprint | How It Connects |
|--------|----------------|
| Sprint 2 (Intelligence) | Provides the data infrastructure: DPOTuple, AgentLog, PipelineRun |
| Sprint FT (this) | Consumes Sprint 2 data, produces better models |
| Sprint 3 (Experience) | Benefits from improved models; FastAPI can trigger retrain |
