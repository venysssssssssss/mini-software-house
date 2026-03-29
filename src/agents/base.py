import os
import time
from dataclasses import dataclass

import ollama
from colorama import Fore, init

# Default timeout for Ollama LLM calls (seconds).
# Prevents the pipeline from hanging indefinitely if a model stalls.
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "120"))

from ..core.logger import get_logger

init(autoreset=True)

# Base models (original, pre-fine-tuning)
BASE_MODELS = {
    "planner": "qwen2.5:3b",
    "backend": "qwen2.5-coder:3b",
    "frontend": "qwen2.5-coder:1.5b",
    "tester": "qwen2.5-coder:3b",
    "documenter": "gemma2:2b",
    "rag": "phi3:mini",
}

# Fine-tuned model variants (created by Sprint FT pipeline)
FINETUNED_MODELS = {
    "planner": "planner-ft",
    "backend": "executor-ft",
    "tester": "tester-ft",
    "documenter": "documenter-ft",
}


def get_model_for_role(role: str) -> str:
    """Returns model for a given role, fitting within 4GB VRAM limit.

    When USE_FINETUNED_MODELS=true (default: false), returns fine-tuned
    variants for roles that have them. Falls back to base models otherwise.
    """
    use_ft = os.getenv("USE_FINETUNED_MODELS", "false").lower() == "true"
    if use_ft:
        ft_model = FINETUNED_MODELS.get(role)
        if ft_model:
            return ft_model
    return BASE_MODELS.get(role, "qwen2.5:3b")


@dataclass
class AgentCallMetrics:
    """Metrics captured from a single agent LLM call."""

    agent_name: str
    model: str
    prompt_tokens: int = 0
    response_tokens: int = 0
    latency_ms: float = 0.0
    success: bool = True
    error: str | None = None


class Agent:
    # Shared list to collect metrics across all agents within a pipeline run
    _metrics_collector: list[AgentCallMetrics] = []

    def __init__(self, name: str, model: str, system_prompt: str, color=Fore.WHITE):
        self.name = name
        self.model = model
        self.system_prompt = system_prompt
        self.chat_history = []
        self.color = color
        self.logger = get_logger(name)

    @classmethod
    def reset_metrics(cls):
        """Clear the shared metrics collector (call at start of each pipeline run)."""
        cls._metrics_collector = []

    @classmethod
    def get_collected_metrics(cls) -> list[AgentCallMetrics]:
        """Return all metrics collected since last reset."""
        return cls._metrics_collector.copy()

    def _add_to_history(self, role: str, content: str):
        self.chat_history.append({"role": role, "content": content})
        # Strict context management: keep only the last 10 messages (5 turns) to save VRAM
        if len(self.chat_history) > 10:
            self.chat_history = self.chat_history[-10:]

    def log_action(self, message: str):
        self.logger.info(message, agent=self.name)

    def generate_response(self, user_prompt: str, **kwargs) -> str:
        messages = [{"role": "system", "content": self.system_prompt}]
        self._add_to_history("user", user_prompt)
        messages.extend(self.chat_history)

        start_time = time.perf_counter()
        metrics = AgentCallMetrics(agent_name=self.name, model=self.model)

        try:
            self.log_action(f"Generating response using model {self.model}...")
            # Enforce keep_alive=0 to unload model immediately and save VRAM
            kwargs.setdefault("keep_alive", 0)
            # Use a client with timeout to prevent hanging if a model stalls
            client = ollama.Client(timeout=OLLAMA_TIMEOUT)
            response = client.chat(model=self.model, messages=messages, **kwargs)

            elapsed_ms = (time.perf_counter() - start_time) * 1000
            reply = response["message"]["content"]

            # Extract token counts from Ollama response
            metrics.prompt_tokens = response.get("prompt_eval_count", 0)
            metrics.response_tokens = response.get("eval_count", 0)
            metrics.latency_ms = elapsed_ms
            metrics.success = True

            self._add_to_history("assistant", reply)
            self._metrics_collector.append(metrics)

            self.logger.info(
                "llm_call_complete",
                agent=self.name,
                model=self.model,
                prompt_tokens=metrics.prompt_tokens,
                response_tokens=metrics.response_tokens,
                latency_ms=round(elapsed_ms, 1),
            )
            return reply
        except Exception as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            metrics.latency_ms = elapsed_ms
            metrics.success = False
            metrics.error = str(e)
            self._metrics_collector.append(metrics)

            self.logger.error("ollama_error", agent=self.name, error=str(e))
            return f"Error: {e}"
