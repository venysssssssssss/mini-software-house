"""AgentPlugin protocol definition."""

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class AgentPlugin(Protocol):
    """Protocol for pipeline plugins.

    Plugins are executed between the testing and documentation phases.
    Each plugin receives pipeline context and returns findings.
    """

    name: str
    role: str

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Execute the plugin with pipeline context.

        Args:
            context: Dict with keys: plan, execution_results, test_results, workspace_path

        Returns:
            Dict with keys: status ("pass"|"fail"), findings (list), and any extras.
        """
        ...
