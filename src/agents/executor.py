import os
import re

from colorama import Fore

from .base import Agent, get_model_for_role
from .context_manager import get_code_summary


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

    def read_existing_files(self) -> dict[str, str]:
        """Read all Python files in workspace and return {filepath: content}."""
        files = {}
        for root, _, filenames in os.walk(self.workspace_dir):
            for fname in filenames:
                if fname.endswith((".py", ".html", ".css", ".js")):
                    full_path = os.path.join(root, fname)
                    rel_path = os.path.relpath(full_path, self.workspace_dir)
                    try:
                        with open(full_path, "r", encoding="utf-8") as f:
                            files[rel_path] = f.read()
                    except Exception:
                        pass
        return files


class ExecutorAgent(Agent):
    def __init__(self):
        system_prompt = (
            "You are an expert software developer. "
            "Write clean, efficient, and well-documented code. "
            "Always output the complete code. "
            "For every file you create or modify, wrap the code in a markdown block "
            "and ALWAYS put a comment on the VERY FIRST LINE inside the block "
            "specifying the relative filepath. "
            "Use the appropriate comment syntax for the language:\n"
            "- Python/CSS/JS: # filepath: filename.ext\n"
            "- HTML: <!-- filepath: filename.html -->\n\n"
            "Examples:\n"
            "```python\n"
            "# filepath: main.py\n"
            "print('Hello')\n"
            "```\n\n"
            "```html\n"
            "<!-- filepath: index.html -->\n"
            "<!DOCTYPE html>\n"
            "```\n\n"
            "```css\n"
            "/* filepath: styles.css */\n"
            "body { margin: 0; }\n"
            "```\n"
        )
        super().__init__(
            name="Executor",
            model=get_model_for_role("backend"),
            system_prompt=system_prompt,
            color=Fore.GREEN,
        )
        self.file_manager = FileManager()

    def _build_context_summary(self) -> str:
        """Build a summary of existing workspace files for multi-file context."""
        existing = self.file_manager.read_existing_files()
        if not existing:
            return ""

        parts = []
        for filepath, content in existing.items():
            if filepath.endswith(".py"):
                summary = get_code_summary(content)
                parts.append(f"--- {filepath} ---\n{summary}")
            else:
                # For non-Python files, include first 20 lines
                lines = content.split("\n")[:20]
                parts.append(f"--- {filepath} ---\n" + "\n".join(lines))

        return "\n\n".join(parts)

    def parse_and_save_code(self, llm_response: str):
        code_blocks = re.findall(r"```(\w*)\n(.*?)```", llm_response, re.DOTALL)

        saved_files = []
        for lang, content in code_blocks:
            lines = content.split("\n")
            filepath = None

            for i in range(min(5, len(lines))):
                # Match: # filepath: x, <!-- filepath: x -->, /* filepath: x */
                match = re.search(
                    r"(?:#|//|<!--|/\*)\s*filepath:\s*(.+?)(?:\s*-->|\s*\*/)?$",
                    lines[i],
                    re.IGNORECASE,
                )
                if match:
                    filepath = match.group(1).strip()
                    break

            # Fallback: infer filename from language if no filepath comment
            if not filepath and lang:
                ext_map = {
                    "python": "py",
                    "py": "py",
                    "html": "html",
                    "css": "css",
                    "javascript": "js",
                    "js": "js",
                    "json": "json",
                    "sh": "sh",
                    "bash": "sh",
                    "rust": "rs",
                    "sql": "sql",
                }
                ext = ext_map.get(lang.lower())
                if ext:
                    # Avoid overwriting: use counter for duplicates
                    base = "index" if ext == "html" else "styles" if ext == "css" else "main"
                    candidate = f"{base}.{ext}"
                    counter = 1
                    while candidate in saved_files:
                        candidate = f"{base}_{counter}.{ext}"
                        counter += 1
                    filepath = candidate
                    self.log_action(f"No filepath comment found, inferred: {filepath}")

            if filepath:
                self.file_manager.save_file(filepath, content.strip())
                saved_files.append(filepath)
                self.log_action(f"Saved file: {filepath}")
            else:
                self.log_action("Warning: Code block found but no filepath specified. Skipping.")

        return saved_files

    def execute_task(self, task: str, plan: dict | None = None):
        """Execute a file creation task with optional plan context and multi-file awareness.

        Args:
            task: The task description for the LLM.
            plan: Optional full plan dict with architecture, dependencies, etc.
        """
        self.log_action("Thinking about task...")

        # Build context-enriched prompt
        prompt_parts = []

        # Include plan context if available
        if plan:
            prompt_parts.append(
                f"Project: {plan.get('project_name', 'unknown')}\n"
                f"Architecture: {plan.get('architecture', 'N/A')}\n"
                f"Dependencies: {', '.join(plan.get('dependencies', []))}\n"
                f"All files in project: {', '.join(plan.get('files_to_create', []))}\n"
            )

        # Include summaries of already-created files
        context = self._build_context_summary()
        if context:
            prompt_parts.append(
                f"The following files already exist in the project:\n\n{context}\n\n"
                "Make sure your code is compatible with them."
            )

        prompt_parts.append(task)
        full_prompt = "\n\n".join(prompt_parts)

        response = self.generate_response(full_prompt)
        self.log_action("Response generated. Parsing code...")
        saved = self.parse_and_save_code(response)
        return response, saved
