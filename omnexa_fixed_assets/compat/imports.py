from __future__ import annotations

import importlib
from functools import lru_cache
from types import ModuleType
from typing import Any


class CompatibilityImportError(ImportError):
    pass


@lru_cache(maxsize=256)
def import_module(path: str) -> ModuleType:
    try:
        return importlib.import_module(path)
    except Exception as exc:
        raise CompatibilityImportError(f"Unable to import {path}: {exc}") from exc


def resolve_attr(*candidates: str) -> Any:
    last_error: Exception | None = None
    for candidate in candidates:
        module_name, _, attr = candidate.rpartition(".")
        try:
            module = import_module(module_name)
            return getattr(module, attr)
        except Exception as exc:
            last_error = exc
    raise CompatibilityImportError(f"No compatible import found for {candidates}: {last_error}")


def import_utils() -> ModuleType:
    return import_module("frappe.utils")


def import_frappe() -> ModuleType:
    return import_module("frappe")


def import_db() -> Any:
    return getattr(import_frappe(), "db", None)
