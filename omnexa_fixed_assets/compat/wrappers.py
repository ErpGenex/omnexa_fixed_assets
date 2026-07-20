from __future__ import annotations

from typing import Any

from .imports import import_frappe
from .logging import log_event


class FrappeProxy:
    """Lazy proxy around a Frappe namespace.

    The proxy keeps imports lazy and centralizes API access so future Frappe
    changes can be mapped in one place.
    """

    def __init__(self, namespace: str | None = None) -> None:
        self.namespace = namespace

    def _target(self) -> Any:
        frappe = import_frappe()
        return getattr(frappe, self.namespace) if self.namespace else frappe

    def __getattr__(self, name: str) -> Any:
        target = self._target()
        value = getattr(target, name)
        log_event("compat_api_access", namespace=self.namespace or "frappe", attribute=name)
        return value


def get_proxy(namespace: str | None = None) -> FrappeProxy:
    return FrappeProxy(namespace)
