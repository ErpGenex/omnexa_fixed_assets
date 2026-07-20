from __future__ import annotations

from typing import Any

from .logging import log_event
from .scanner import CompatibilityScanner


def _run_hook(name: str, *args: Any, **kwargs: Any) -> dict[str, Any]:
    log_event(name, args=[str(arg) for arg in args], kwargs={key: str(value) for key, value in kwargs.items()})
    if name in {"before_migrate", "after_migrate", "before_tests"}:
        return CompatibilityScanner().scan()
    return {"status": "ok", "hook": name}


def before_install(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return _run_hook("before_install", *args, **kwargs)


def after_install(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return _run_hook("after_install", *args, **kwargs)


def before_migrate(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return _run_hook("before_migrate", *args, **kwargs)


def after_migrate(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return _run_hook("after_migrate", *args, **kwargs)


def before_uninstall(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return _run_hook("before_uninstall", *args, **kwargs)


def after_uninstall(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return _run_hook("after_uninstall", *args, **kwargs)


def before_tests(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return _run_hook("before_tests", *args, **kwargs)


def after_tests(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return _run_hook("after_tests", *args, **kwargs)


def before_scheduler(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return _run_hook("before_scheduler", *args, **kwargs)


def after_scheduler(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return _run_hook("after_scheduler", *args, **kwargs)
