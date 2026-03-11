import json
import re
from .base import Agent
from colorama import Fore

class PlannerAgent(Agent):
    def __init__(self):
        system_prompt = (
            "You are a Software Architect and Planner. "
            "You MUST respond ONLY with a valid, parsable JSON object. "
            "DO NOT include markdown formatting, DO NOT include backticks (```), "
            "and DO NOT add any explanatory text. \n"
            "If you need to include comments, verify strictly that the output remains valid JSON.\n"
            "The JSON must have exactly the following structure:\n"
            "{\n"
            '  "architecture": "brief description",\n'
            '  "files_to_create": ["file1.py", "file2.py"],\n'
            '  "dependencies": ["lib1", "lib2"],\n'
            '  "logical_steps": ["step 1", "step 2"]\n'
            "}"
        )
        super().__init__(
            name="Planner",
            model="phi3.5:latest",
            system_prompt=system_prompt,
            color=Fore.CYAN
        )

    def plan_task(self, user_request: str) -> dict:
        self.log_action(f"Planning task: {user_request}")
        
        # Utilizando Native JSON Mode do Ollama (Grammar-Based Sampling)
        # Isso garante que o modelo SÓ gere JSON válido, economizando tokens e evitando erros de parse.
        response = self.generate_response(user_request, format='json')
        self.log_action("Plan generated (JSON Mode).")
        
        try:
            data = json.loads(response)
            required_keys = {"architecture", "files_to_create", "dependencies", "logical_steps"}
            if not required_keys.issubset(data.keys()):
                missing = required_keys - data.keys()
                self.log_action(f"Warning: JSON missing keys: {missing}")
            return data
        except json.JSONDecodeError as e:
            self.log_action(f"Critical: Model failed to generate valid JSON even in JSON mode: {e}")
            return {}
