from __future__ import annotations

from typing import Any

try:
    import frappe  # type: ignore
except Exception:  # pragma: no cover
    frappe = None

from ..scanner import CompatibilityScanner


def get_context(context: Any) -> None:
    if context is not None:
        context.no_cache = 1
        context.report = CompatibilityScanner().scan()


def get_system_compatibility() -> dict[str, Any]:
    return CompatibilityScanner().scan()


if frappe:
    get_system_compatibility = frappe.whitelist()(get_system_compatibility)
