from colorama import Fore

from .base import Agent, get_model_for_role
from .rag import RAGEngine


class DocumenterAgent(Agent):
    def __init__(self):
        system_prompt = (
            "You are a Technical Writer. Write clear, comprehensive markdown documentation. "
            "Use the provided code context to explain how the system works."
        )
        super().__init__(
            name="Documenter",
            model=get_model_for_role("documenter"),  # Lightweight model for docs
            system_prompt=system_prompt,
            color=Fore.MAGENTA,
        )
        self.rag = RAGEngine()

    def generate_documentation(self) -> str:
        self.log_action("Indexing workspace for RAG...")
        self.rag.index_workspace()

        # Phase 1: High level overview
        overview_query = "What is the main purpose of this application? What are the main classes?"
        overview_context = self.rag.query(overview_query)
        prompt = (
            "Based on this context, write a README.md "
            f"Introduction and Architecture Overview:\n{overview_context}"
        )

        self.log_action("Generating overview...")
        overview = self.generate_response(prompt)

        # Phase 2: Usage
        usage_query = "How to run the application? CLI arguments? Main entry point?"
        usage_context = self.rag.query(usage_query)
        prompt_usage = (
            f"Based on this context, write a 'Usage' section for the README:\n{usage_context}"
        )

        self.log_action("Generating usage guide...")
        usage = self.generate_response(prompt_usage)

        full_docs = f"# Project Documentation\n\n{overview}\n\n{usage}"

        with open("workspace/README_GENERATED.md", "w") as f:
            f.write(full_docs)

        return full_docs
