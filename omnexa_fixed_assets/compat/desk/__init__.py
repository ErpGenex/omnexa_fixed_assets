
"""Compatibility namespace for desk concerns."""

from typing import Any

from ..wrappers import get_proxy

proxy = get_proxy('desk')


def __getattr__(attribute: str) -> Any:
    return getattr(proxy, attribute)


def get(attribute: str, default: Any = None) -> Any:
    try:
        return getattr(proxy, attribute)
    except Exception:
        return default


def call(attribute: str, *args: Any, **kwargs: Any) -> Any:
    return getattr(proxy, attribute)(*args, **kwargs)


__all__ = ["proxy", "get", "call"]
