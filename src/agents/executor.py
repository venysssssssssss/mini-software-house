import re
import os
from .base import Agent, get_model_for_role
from colorama import Fore

class FileManager:
    def __init__(self, workspace_dir: str = "workspace"):
        self.workspace_dir = os.path.abspath(workspace_dir)
        os.makedirs(self.workspace_dir, exist_ok=True)

    def save_file(self, filepath: str, content: str):
        full_path = os.path.abspath(os.path.join(self.workspace_dir, filepath))
        
        if not full_path.startswith(self.workspace_dir):
            raise ValueError(f"Security error: Attempted to write outside workspace: {filepath}")

        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)

class ExecutorAgent(Agent):
    def __init__(self):
        system_prompt = (
            "You are an expert Python coder. "
            "Write clean, efficient, and well-documented code. "
            "Always output the complete code. "
            "For every file you create or modify, wrap the code in a markdown block "
            "and ALWAYS put a comment on the VERY FIRST LINE inside the block specifying the relative filepath. "
            "Example:\n"
            "```python\n"
            "# filepath: main.py\n"
            "print('Hello')\n"
            "```\n"
        )
        super().__init__(
            name="Executor",
            model=get_model_for_role("backend"),
            system_prompt=system_prompt,
            color=Fore.GREEN
        )
        self.file_manager = FileManager()

    def parse_and_save_code(self, llm_response: str):
        code_blocks = re.findall(r"```(\w*)\n(.*?)```", llm_response, re.DOTALL)
        
        saved_files = []
        for lang, content in code_blocks:
            lines = content.split('\n')
            filepath = None
            
            for i in range(min(5, len(lines))):
                match = re.search(r"#\s*filepath:\s*(.+)", lines[i], re.IGNORECASE)
                if match:
                    filepath = match.group(1).strip()
                    break
            
            if filepath:
                self.file_manager.save_file(filepath, content.strip())
                saved_files.append(filepath)
                self.log_action(f"Saved file: {filepath}")
            else:
                self.log_action(f"Warning: Code block found but no filepath specified. Skipping.")
                
        return saved_files

    def execute_task(self, task: str):
        self.log_action(f"Thinking about task...")
        response = self.generate_response(task)
        self.log_action(f"Response generated. Parsing code...")
        saved = self.parse_and_save_code(response)
        return response, saved
