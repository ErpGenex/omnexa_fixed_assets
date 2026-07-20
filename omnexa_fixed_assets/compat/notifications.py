from __future__ import annotations

from typing import Any

from .scanner import CompatibilityScanner
from .version_manager import VersionManager


def frappe_version_changed(previous_version: str | None = None) -> dict[str, Any]:
    manager = VersionManager()
    current = str(manager.current())
    changed = bool(previous_version and previous_version != current)
    report = CompatibilityScanner().scan() if changed else {}
    return {
        "changed": changed,
        "title": "New Frappe version detected." if changed else "Frappe version unchanged.",
        "message": "Compatibility Analysis Complete." if changed else "No compatibility analysis required.",
        "previous_version": previous_version,
        "current_version": current,
        "report": report,
        "actions": ["Run migrate", "Run build", "Run patches", "Restart services"] if changed else [],
    }
