from __future__ import annotations

import ast
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .logging import get_logger
from .version_manager import VersionManager


@dataclass
class Finding:
    severity: str
    category: str
    path: str
    message: str
    recommendation: str


class CompatibilityScanner:
    """Static and runtime scanner for compatibility risks."""

    def __init__(self, app_name: str | None = None, package_root: Path | None = None) -> None:
        self.package_root = package_root or Path(__file__).resolve().parents[1]
        self.app_name = app_name or self.package_root.name
        self.version_manager = VersionManager()
        self.findings: list[Finding] = []
        self.logger = get_logger("scanner")

    def scan(self) -> dict[str, Any]:
        self.findings = []
        self._scan_python_imports()
        self._scan_hooks()
        self._scan_workspace_json()
        report = self.report()
        self.logger.info("compatibility_scan_complete %s", report)
        return report

    def report(self) -> dict[str, Any]:
        score = max(0, 100 - len([f for f in self.findings if f.severity in {"error", "warning"}]) * 5)
        return {
            "app": self.app_name,
            "score": score,
            "versions": self.version_manager.snapshot(),
            "findings": [asdict(finding) for finding in self.findings]
	}

    def write_report(self, output: Path | None = None) -> Path:
        output = output or self.package_root / "compat" / "compatibility_report.json"
        output.write_text(json.dumps(self.report(), indent=2, sort_keys=True), encoding="utf-8")
        return output

    def _scan_python_imports(self) -> None:
        for path in self.package_root.rglob("*.py"):
            if "__pycache__" in path.parts or "/compat/" in str(path):
                continue
            try:
                tree = ast.parse(path.read_text(encoding="utf-8"))
            except Exception as exc:
                self.findings.append(Finding("warning", "python", str(path), f"Unable to parse: {exc}", "Inspect the file manually."))
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("frappe."):
                    self.findings.append(
                        Finding(
                            "info",
                            "dynamic_imports",
                            str(path),
                            f"Direct import from {node.module}",
                            "Prefer compat.imports or compat resolver for new code.",
                        )
                    )

    def _scan_hooks(self) -> None:
        hooks = self.package_root / "hooks.py"
        if not hooks.exists():
            self.findings.append(Finding("warning", "hooks", str(hooks), "hooks.py is missing.", "Confirm the app is intentionally hookless."))

    def _scan_workspace_json(self) -> None:
        for path in self.package_root.rglob("*.json"):
            if "workspace" not in [part.lower() for part in path.parts]:
                continue
            try:
                json.loads(path.read_text(encoding="utf-8"))
            except Exception as exc:
                self.findings.append(Finding("warning", "workspace", str(path), f"Invalid workspace JSON: {exc}", "Repair JSON before migration."))
