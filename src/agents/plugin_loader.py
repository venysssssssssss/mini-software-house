"""Plugin discovery and loading."""

import importlib.util
import os
from typing import List

from ..core.logger import get_logger
from .plugin import AgentPlugin

logger = get_logger("plugin_loader")


def discover_plugins(plugin_dir: str = "plugins") -> List[AgentPlugin]:
    """Discover and load plugins from a directory.

    Each plugin is a .py file containing a class that implements AgentPlugin.
    """
    plugins: List[AgentPlugin] = []

    if not os.path.isdir(plugin_dir):
        logger.info("no_plugin_dir", dir=plugin_dir)
        return plugins

    for filename in sorted(os.listdir(plugin_dir)):
        if not filename.endswith(".py") or filename.startswith("_"):
            continue

        filepath = os.path.join(plugin_dir, filename)
        module_name = filename[:-3]

        try:
            spec = importlib.util.spec_from_file_location(module_name, filepath)
            if spec is None or spec.loader is None:
                continue
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Find classes that implement AgentPlugin
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (
                    isinstance(attr, type)
                    and attr_name != "AgentPlugin"
                    and hasattr(attr, "name")
                    and hasattr(attr, "role")
                    and hasattr(attr, "execute")
                ):
                    instance = attr()
                    if isinstance(instance, AgentPlugin):
                        plugins.append(instance)
                        logger.info("plugin_loaded", name=instance.name, role=instance.role)

        except Exception as e:
            logger.warning("plugin_load_failed", file=filename, error=str(e))

    return plugins
