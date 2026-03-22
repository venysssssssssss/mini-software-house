#!/usr/bin/env python3
"""Test full pipeline naming engine integration"""

import sys
import os
import subprocess
import json
import time
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def run_pipeline_test(task_description: str, test_name: str):
    """Run a single pipeline test"""
    print(f"\n{'='*60}")
    print(f"🧪 TEST: {test_name}")
    print(f"{'='*60}")
    print(f"Task: {task_description}\n")
    
    # Clean state
    workspace_dir = Path(__file__).parent.parent / "workspace"
    state_file = workspace_dir / "state.json"
    log_file = workspace_dir / "run.log"
    
    if state_file.exists():
        state_file.unlink()
    if log_file.exists():
        log_file.unlink()
    
    # Run pipeline
    cmd = [
        "python", "-m", "src.main",
        "--task", task_description
    ]
    
    # Run with timeout
    try:
        result = subprocess.run(
            cmd,
            cwd=str(workspace_dir.parent),
            timeout=25,
            capture_output=True,
            text=True
        )
    except subprocess.TimeoutExpired:
        print("⏱️  Pipeline timeout (expected - waiting for LLM)")
    
    # Check result
    if state_file.exists():
        with open(state_file) as f:
            state = json.load(f)
            project_name = state.get("plan", {}).get("project_name", "NOT SET")
            
            # Validate kebab-case
            import re
            is_valid = bool(re.match(r'^[a-z0-9]+(-[a-z0-9]+)+$', project_name))
            
            status = "✅" if is_valid else "❌"
            print(f"{status} Project Name: {project_name}")
            print(f"   Valid Kebab-Case: {is_valid}")
            
            return project_name, is_valid
    else:
        print("⚠️  State file not created (LLM possibly too slow)")
        return None, False

# Test cases
tests = [
    ("Build a REST API for user authentication", "REST API"),
    ("Create a real-time chat application", "Chat App"),
    ("Develop machine learning pipeline", "ML Pipeline"),
    ("Build ETL data processing system", "ETL System"),
]

print("\n" + "="*60)
print("🚀 FULL PIPELINE NAMING ENGINE TESTS")
print("="*60)

results = []
for task, name in tests:
    project_name, is_valid = run_pipeline_test(task, name)
    results.append((name, project_name, is_valid))

# Summary
print(f"\n" + "="*60)
print("📊 SUMMARY")
print("="*60)

passed = sum(1 for _, _, is_valid in results if is_valid)
total = len(results)

for name, project_name, is_valid in results:
    status = "✅" if is_valid else "❌"
    print(f"{status} {name}: {project_name}")

print(f"\n✨ Results: {passed}/{total} tests passed (kebab-case)")
