"""Security auditor plugin — scans generated code for common vulnerabilities."""

import os
import re


class SecurityAuditor:
    name = "SecurityAuditor"
    role = "security"

    # Patterns to detect potential security issues
    PATTERNS = [
        (r"\beval\s*\(", "eval() usage — potential code injection"),
        (r"\bexec\s*\(", "exec() usage — potential code injection"),
        (r"(?i)(api[_-]?key|secret|password|token)\s*=\s*['\"][^'\"]+['\"]", "Hardcoded secret"),
        (r"(?i)execute\s*\(\s*f['\"]", "Possible SQL injection via f-string in execute()"),
        (r"(?i)execute\s*\(\s*['\"].*%s", "Possible SQL injection via string formatting"),
        (r"\bopen\s*\(.*\+", "open() with concatenated path — possible path traversal"),
        (r"\bpickle\.loads?\s*\(", "pickle.load — potential deserialization attack"),
        (r"\byaml\.load\s*\((?!.*Loader)", "yaml.load without safe Loader"),
        (r"\bshell\s*=\s*True", "subprocess with shell=True"),
    ]

    def execute(self, context: dict) -> dict:
        workspace_path = context.get("workspace_path", "")
        findings = []

        if not workspace_path or not os.path.isdir(workspace_path):
            return {"status": "pass", "findings": []}

        for root, _dirs, files in os.walk(workspace_path):
            for fname in files:
                if not fname.endswith(".py"):
                    continue
                filepath = os.path.join(root, fname)
                try:
                    with open(filepath) as f:
                        content = f.read()
                except OSError:
                    continue

                for line_num, line in enumerate(content.splitlines(), 1):
                    for pattern, description in self.PATTERNS:
                        if re.search(pattern, line):
                            findings.append({
                                "file": os.path.relpath(filepath, workspace_path),
                                "line": line_num,
                                "issue": description,
                                "code": line.strip()[:120],
                            })

        status = "fail" if findings else "pass"
        return {"status": status, "findings": findings}
