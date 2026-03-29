"""Git integration for auto-initializing repos after successful pipeline runs."""

import subprocess
from typing import Dict, Optional


def init_and_commit(workspace_path: str, project_name: str) -> Dict[str, Optional[str]]:
    """Initialize git repo and create initial commit in workspace directory.

    Returns {"success": bool, "commit_hash": str | None, "error": str | None}
    """
    try:
        subprocess.run(
            ["git", "init"],
            cwd=workspace_path,
            capture_output=True,
            text=True,
            check=True,
        )
        subprocess.run(
            ["git", "add", "."],
            cwd=workspace_path,
            capture_output=True,
            text=True,
            check=True,
        )
        subprocess.run(
            ["git", "commit", "-m", f"Initial commit: {project_name}"],
            cwd=workspace_path,
            capture_output=True,
            text=True,
            check=True,
        )
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=workspace_path,
            capture_output=True,
            text=True,
            check=True,
        )
        commit_hash = result.stdout.strip()
        return {"success": True, "commit_hash": commit_hash, "error": None}

    except subprocess.CalledProcessError as e:
        return {"success": False, "commit_hash": None, "error": e.stderr or str(e)}
    except FileNotFoundError:
        return {"success": False, "commit_hash": None, "error": "git not found on PATH"}


def push_to_remote(workspace_path: str, remote_url: str) -> Dict[str, Optional[str]]:
    """Push to a remote repository if URL is provided."""
    try:
        subprocess.run(
            ["git", "remote", "add", "origin", remote_url],
            cwd=workspace_path,
            capture_output=True,
            text=True,
            check=True,
        )
        subprocess.run(
            ["git", "push", "-u", "origin", "main"],
            cwd=workspace_path,
            capture_output=True,
            text=True,
            check=True,
        )
        return {"success": True, "error": None}

    except subprocess.CalledProcessError as e:
        return {"success": False, "error": e.stderr or str(e)}
