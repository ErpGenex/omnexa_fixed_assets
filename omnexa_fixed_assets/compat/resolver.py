from __future__ import annotations

from collections.abc import Callable
from functools import lru_cache
from typing import Any

from .imports import import_frappe, resolve_attr


API_MAP: dict[str, tuple[str, ...]] = {
    "enqueue": ("frappe.enqueue", "frappe.utils.background_jobs.enqueue"),
    "publish_realtime": ("frappe.publish_realtime", "frappe.realtime.publish_realtime"),
    "get_cached_doc": ("frappe.get_cached_doc", "frappe.get_doc"),
    "get_all": ("frappe.get_all",),
    "get_list": ("frappe.get_list",)}

MODULE_MAP: dict[str, str] = {}


@lru_cache(maxsize=256)
def resolve_api(name: str) -> Callable[..., Any]:
    candidates = API_MAP.get(name, (name,))
    return resolve_attr(*candidates)


def resolve_module(name: str) -> str:
    return MODULE_MAP.get(name, name)


def call(name: str, *args: Any, **kwargs: Any) -> Any:
    return resolve_api(name)(*args, **kwargs)


def frappe_call(name: str, *args: Any, **kwargs: Any) -> Any:
    return getattr(import_frappe(), name)(*args, **kwargs)
