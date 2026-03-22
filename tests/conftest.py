"""Pytest configuration and fixtures for mini-software-house tests."""

import pytest
import sys
from pathlib import Path

# Add src to path for imports
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))


@pytest.fixture
def test_project_root():
    """Provide path to project root."""
    return Path(__file__).parent.parent


@pytest.fixture
def temp_workspace(tmp_path):
    """Provide temporary workspace directory."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    return workspace
