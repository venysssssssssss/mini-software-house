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
        response = self.generate_response(user_request)
        self.log_action("Plan generated. Parsing JSON...")
        
        # Advanced cleanup strategy for robust JSON extraction
        # 1. Strip Markdown code blocks
        response_clean = re.sub(r"```(?:json)?", "", response, flags=re.IGNORECASE)
        response_clean = re.sub(r"```", "", response_clean)
        
        # 2. Strip standard comments (// or #) which are invalid in standard JSON but models love adding
        response_clean = re.sub(r"^\s*//.*$", "", response_clean, flags=re.MULTILINE)
        response_clean = re.sub(r"^\s*#.*$", "", response_clean, flags=re.MULTILINE)
        
        try:
            start_idx = response_clean.find('{')
            end_idx = response_clean.rfind('}')
            
            if start_idx != -1 and end_idx != -1:
                json_str = response_clean[start_idx:end_idx+1]
                # Validate structure keys
                data = json.loads(json_str)
                required_keys = {"architecture", "files_to_create", "dependencies", "logical_steps"}
                if not required_keys.issubset(data.keys()):
                    missing = required_keys - data.keys()
                    raise ValueError(f"JSON missing required keys: {missing}")
                return data
            else:
                raise ValueError("No JSON found in response.")
        except json.JSONDecodeError as e:
            self.log_action(f"Error parsing JSON from Planner: {e}")
            self.log_action(f"Raw Planner response:\n{response}")
            return {}
        except Exception as e:
             self.log_action(f"Unexpected error parsing JSON: {e}")
             return {}
