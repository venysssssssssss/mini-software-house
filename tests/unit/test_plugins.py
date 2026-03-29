"""Tests for plugin system."""

from src.agents.plugin import AgentPlugin
from src.agents.plugin_loader import discover_plugins


class TestAgentPluginProtocol:
    def test_valid_plugin_matches_protocol(self):
        class GoodPlugin:
            name = "TestPlugin"
            role = "test"

            def execute(self, context: dict) -> dict:
                return {"status": "pass", "findings": []}

        assert isinstance(GoodPlugin(), AgentPlugin)

    def test_missing_execute_not_plugin(self):
        class BadPlugin:
            name = "Bad"
            role = "test"

        assert not isinstance(BadPlugin(), AgentPlugin)


class TestPluginDiscovery:
    def test_discover_from_directory(self, tmp_path):
        plugin_dir = tmp_path / "plugins"
        plugin_dir.mkdir()

        # Write a valid plugin
        (plugin_dir / "my_plugin.py").write_text(
            """
class MyChecker:
    name = "MyChecker"
    role = "checker"

    def execute(self, context):
        return {"status": "pass", "findings": []}
"""
        )

        plugins = discover_plugins(str(plugin_dir))
        assert len(plugins) == 1
        assert plugins[0].name == "MyChecker"

    def test_discover_no_directory(self, tmp_path):
        plugins = discover_plugins(str(tmp_path / "nonexistent"))
        assert plugins == []

    def test_discover_skips_invalid(self, tmp_path):
        plugin_dir = tmp_path / "plugins"
        plugin_dir.mkdir()

        # Write a file with no valid plugin class
        (plugin_dir / "empty.py").write_text("x = 42\n")

        plugins = discover_plugins(str(plugin_dir))
        assert plugins == []

    def test_discover_skips_underscored_files(self, tmp_path):
        plugin_dir = tmp_path / "plugins"
        plugin_dir.mkdir()

        (plugin_dir / "_helper.py").write_text(
            """
class Helper:
    name = "Helper"
    role = "util"
    def execute(self, context):
        return {"status": "pass", "findings": []}
"""
        )

        plugins = discover_plugins(str(plugin_dir))
        assert plugins == []

    def test_discover_real_plugins_dir(self):
        plugins = discover_plugins("plugins")
        assert len(plugins) >= 1
        names = [p.name for p in plugins]
        assert "SecurityAuditor" in names


class TestSecurityAuditor:
    def test_clean_code(self, tmp_path):
        (tmp_path / "app.py").write_text("def main():\n    print('hello')\n")

        from plugins.security_auditor import SecurityAuditor

        auditor = SecurityAuditor()
        result = auditor.execute({"workspace_path": str(tmp_path)})
        assert result["status"] == "pass"
        assert result["findings"] == []

    def test_detects_eval(self, tmp_path):
        (tmp_path / "bad.py").write_text("result = eval(user_input)\n")

        from plugins.security_auditor import SecurityAuditor

        auditor = SecurityAuditor()
        result = auditor.execute({"workspace_path": str(tmp_path)})
        assert result["status"] == "fail"
        assert len(result["findings"]) >= 1
        assert "eval" in result["findings"][0]["issue"].lower()

    def test_detects_hardcoded_secret(self, tmp_path):
        (tmp_path / "config.py").write_text('API_KEY = "sk-1234567890abcdef"\n')

        from plugins.security_auditor import SecurityAuditor

        auditor = SecurityAuditor()
        result = auditor.execute({"workspace_path": str(tmp_path)})
        assert result["status"] == "fail"
        assert any(
            "secret" in f["issue"].lower() or "hardcoded" in f["issue"].lower()
            for f in result["findings"]
        )

    def test_no_workspace(self):
        from plugins.security_auditor import SecurityAuditor

        auditor = SecurityAuditor()
        result = auditor.execute({"workspace_path": ""})
        assert result["status"] == "pass"
