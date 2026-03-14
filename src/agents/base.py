import ollama
import logging
from typing import Dict, Any
from colorama import init, Fore, Style

init(autoreset=True)

def get_model_for_role(role: str) -> str:
    """
    Returns an optimized model for a given role, fitting within 4GB VRAM limit.
    """
    models = {
        "planner": "qwen2.5:3b",
        "backend": "qwen2.5-coder:3b",
        "frontend": "qwen2.5-coder:1.5b",
        "tester": "deepseek-coder:1.3b",
        "documenter": "gemma2:2b",
        "rag": "phi3:mini"
    }
    return models.get(role, "qwen2.5:3b")

class Agent:
    def __init__(self, name: str, model: str, system_prompt: str, color=Fore.WHITE):
        self.name = name
        self.model = model
        self.system_prompt = system_prompt
        self.chat_history = []
        self.color = color

        # Setup file logger
        self.logger = logging.getLogger(self.name)
        if not self.logger.handlers:
            self.logger.setLevel(logging.INFO)
            import os
            os.makedirs("workspace", exist_ok=True)
            fh = logging.FileHandler('workspace/run.log')
            fh.setLevel(logging.INFO)
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            fh.setFormatter(formatter)
            self.logger.addHandler(fh)

    def _add_to_history(self, role: str, content: str):
        self.chat_history.append({"role": role, "content": content})
        # Strict context management: keep only the last 10 messages (5 turns) to save VRAM
        if len(self.chat_history) > 10:
            self.chat_history = self.chat_history[-10:]

    def log_action(self, message: str):
        print(f"{self.color}[{self.name}] {message}{Style.RESET_ALL}")
        self.logger.info(message)

    def generate_response(self, user_prompt: str, **kwargs) -> str:
        messages = [{"role": "system", "content": self.system_prompt}]
        self._add_to_history("user", user_prompt)
        messages.extend(self.chat_history)

        try:
            self.log_action(f"Generating response using model {self.model}...")
            # Enforce keep_alive=0 to unload model immediately and save VRAM
            kwargs.setdefault('keep_alive', 0)
            response = ollama.chat(model=self.model, messages=messages, **kwargs)
            reply = response['message']['content']
            self._add_to_history("assistant", reply)
            return reply
        except Exception as e:
            self.log_action(f"Error communicating with Ollama: {e}")
            return f"Error: {e}"
