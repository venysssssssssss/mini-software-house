import ast
import os
from typing import List

class CodeSummarizer(ast.NodeVisitor):
    """
    Parses Python code and extracts a structural summary (signatures of classes and functions).
    Used to save context window tokens by ignoring function bodies.
    """
    def __init__(self):
        self.summary = []
        self.indent_level = 0

    def visit_ClassDef(self, node):
        bases = [b.id for b in node.bases if isinstance(b, ast.Name)]
        base_str = f"({', '.join(bases)})" if bases else ""
        self.summary.append(f"{'    ' * self.indent_level}class {node.name}{base_str}:")
        
        self.indent_level += 1
        self.generic_visit(node)
        self.indent_level -= 1

    def visit_FunctionDef(self, node):
        args = [a.arg for a in node.args.args]
        if 'self' in args: args.remove('self')
        
        # Add return type hint if present
        ret_annotation = ""
        if node.returns:
            # Simplified handling for simple return types
            if isinstance(node.returns, ast.Name):
                ret_annotation = f" -> {node.returns.id}"
            elif isinstance(node.returns, ast.Constant):
                ret_annotation = f" -> {node.returns.value}"

        self.summary.append(f"{'    ' * self.indent_level}def {node.name}({', '.join(args)}){ret_annotation}: ...")
        # Important: We do NOT visit the body of the function to keep it summarized

def get_code_summary(code: str) -> str:
    try:
        tree = ast.parse(code)
        summarizer = CodeSummarizer()
        summarizer.visit(tree)
        return "\n".join(summarizer.summary)
    except SyntaxError:
        return "    (Syntax Error in file parsing)"