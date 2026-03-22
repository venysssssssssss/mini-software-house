import json
import re
from .base import Agent, get_model_for_role
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
            '  "project_name": "action-object-purpose-in-kebab-case",\n'
            '  "architecture": "brief description",\n'
            '  "files_to_create": ["file1.py", "file2.py"],\n'
            '  "dependencies": ["lib1", "lib2"],\n'
            '  "logical_steps": ["step 1", "step 2"]\n'
            "}\n"
            "IMPORTANT: project_name MUST be in kebab-case format (lowercase, hyphens, no spaces). "
            "Pattern: action-object-purpose (e.g., 'build-user-api', 'create-chat-app')"
        )
        super().__init__(
            name="Planner",
            model=get_model_for_role("planner"),
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
            
            # Validate and generate intelligent project name if needed
            project_name = data.get("project_name", "")
            
            # Check if project_name follows kebab-case pattern (lowercase, hyphens, no underscores/spaces)
            if not self._is_valid_kebab_case(project_name):
                from ..naming_engine import NamingEngine
                engine = NamingEngine()
                project_name = engine.generate_project_name_from_task(
                    task_description=user_request,
                    dependencies=data.get("dependencies", [])
                )
                data["project_name"] = project_name
                self.log_action(f"Generated intelligent project name (kebab-case): {project_name}")
            else:
                self.log_action(f"Using model-generated project name (kebab-case): {project_name}")
            
            required_keys = {"architecture", "files_to_create", "dependencies", "logical_steps"}
            if not required_keys.issubset(data.keys()):
                missing = required_keys - data.keys()
                self.log_action(f"Warning: JSON missing keys: {missing}")
            return data
        except json.JSONDecodeError as e:
            self.log_action(f"Critical: Model failed to generate valid JSON even in JSON mode: {e}")
            return {}
    
    def _is_valid_kebab_case(self, name: str) -> bool:
        """Validate if name follows kebab-case pattern (lowercase, hyphens, no spaces/underscores)"""
        if not name:
            return False
        # Pattern: lowercase letters, numbers, and hyphens only
        # Must have at least one hyphen to be kebab-case
        if not re.match(r'^[a-z0-9]+(-[a-z0-9]+)+$', name):
            return False
        return True
