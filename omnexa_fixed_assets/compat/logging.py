
from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any


LOG_NAMES = {
    "compatibility",
    "upgrade",
    "migration",
    "rollback",
    "scanner",
    "performance",
}


def bench_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "sites" / "apps.txt").exists():
            return parent
    return Path(__file__).resolve().parents[4]


def log_dir() -> Path:
    path = bench_root() / "logs" / "compatibility"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_logger(name: str = "compatibility") -> logging.Logger:
    safe_name = name if name in LOG_NAMES else "compatibility"
    logger = logging.getLogger(f"compat.{safe_name}")
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    handler = RotatingFileHandler(log_dir() / f"{safe_name}.log", maxBytes=2_000_000, backupCount=5)
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    logger.addHandler(handler)
    return logger


def log_event(event: str, **payload: Any) -> None:
    get_logger("compatibility").info("%s %s", event, payload)
