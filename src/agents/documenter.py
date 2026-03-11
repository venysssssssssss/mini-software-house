import os
from .base import Agent
from .executor import FileManager
from colorama import Fore

class DocumenterAgent(Agent):
    def __init__(self):
        system_prompt = (
            "You are a Technical Writer. "
            "Your task is to analyze the provided code base and write a comprehensive README.md file. "
            "Include an introduction, installation instructions, usage examples, and architecture details. "
            "Output the README markdown wrapped in a ```markdown block and "
            "start the block with the relative filepath: # filepath: README.md"
        )
        super().__init__(
            name="Documenter",
            model="gemma2:2b",
            system_prompt=system_prompt,
            color=Fore.MAGENTA
        )

    def generate_documentation(self, workspace_dir="workspace"):
        content = ""
        for root, _, files in os.walk(workspace_dir):
            for file in files:
                filepath = os.path.join(root, file)
                if not file.endswith(('.py', '.json', '.txt')):
                    continue
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                         content += f"--- {file} ---\n{f.read()}\n\n"
                except Exception as e:
                     self.log_action(f"Error reading file {file}: {e}")

        if not content:
            return "No valid files found to document."

        prompt = f"Write documentation for this project. Files content:\n\n{content}"
        self.log_action("Generating documentation...")
        
        response = self.generate_response(prompt)
        
        file_manager = FileManager(workspace_dir)
        import re
        code_blocks = re.findall(r"```(markdown)?\n(.*?)```", response, re.DOTALL)
        
        saved = False
        for lang, md_content in code_blocks:
            lines = md_content.split('\n')
            filepath = None
            
            for i in range(min(5, len(lines))):
                match = re.search(r"#\s*filepath:\s*(.+)", lines[i], re.IGNORECASE)
                if match:
                    filepath = match.group(1).strip()
                    break
            
            if filepath:
                file_manager.save_file(filepath, md_content.strip())
                saved = True
                self.log_action(f"Saved documentation to {filepath}")
                
        if not saved:
             self.log_action("Warning: No markdown block with filepath found. Writing to README.md by default.")
             file_manager.save_file("README.md", response)
        
        return response
