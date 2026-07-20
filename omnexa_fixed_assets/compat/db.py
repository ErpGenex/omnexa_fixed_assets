from __future__ import annotations

from typing import Any

from .imports import import_frappe, import_module
from .wrappers import get_proxy


proxy = get_proxy('db')


def __getattr__(name: str) -> Any:
    return getattr(proxy, name)


def get(name: str, default: Any = None) -> Any:
    try:
        return getattr(proxy, name)
    except Exception:
        return default


def call(name: str, *args: Any, **kwargs: Any) -> Any:
    return getattr(proxy, name)(*args, **kwargs)
