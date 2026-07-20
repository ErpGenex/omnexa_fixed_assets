from __future__ import annotations

import json
import platform
import re
import shutil
import subprocess
from dataclasses import dataclass
from functools import cached_property
from typing import Any


_VERSION_RE = re.compile(r"(\d+)(?:\.(\d+))?(?:\.(\d+))?")


@dataclass(frozen=True, order=True)
class SemanticVersion:
    major: int = 0
    minor: int = 0
    patch: int = 0
    raw: str = "0.0.0"

    @classmethod
    def parse(cls, value: Any) -> "SemanticVersion":
        raw = str(value or "0.0.0")
        match = _VERSION_RE.search(raw)
        if not match:
            return cls(raw=raw)
        major, minor, patch = match.groups(default="0")
        return cls(int(major), int(minor), int(patch), raw)

    def as_tuple(self) -> tuple[int, int, int]:
        return (self.major, self.minor, self.patch)

    def __str__(self) -> str:
        return self.raw


class VersionManager:
    """Detect Frappe, bench, runtime, and service versions lazily."""

    def __init__(self) -> None:
        self._frappe = None

    @cached_property
    def frappe_version(self) -> SemanticVersion:
        try:
            import frappe  # type: ignore

            self._frappe = frappe
            return SemanticVersion.parse(getattr(frappe, "__version__", "0.0.0"))
        except Exception:
            return SemanticVersion()

    @cached_property
    def bench_version(self) -> SemanticVersion:
        return SemanticVersion.parse(self._command_version(["bench", "--version"]))

    @cached_property
    def python_version(self) -> SemanticVersion:
        return SemanticVersion.parse(platform.python_version())

    @cached_property
    def node_version(self) -> SemanticVersion:
        return SemanticVersion.parse(self._command_version(["node", "--version"]))

    @cached_property
    def redis_version(self) -> SemanticVersion:
        return SemanticVersion.parse(self._command_version(["redis-server", "--version"]))

    @cached_property
    def mariadb_version(self) -> SemanticVersion:
        return SemanticVersion.parse(
            self._command_version(["mariadb", "--version"])
            or self._command_version(["mysql", "--version"])
        )

    @cached_property
    def yarn_version(self) -> SemanticVersion:
        return SemanticVersion.parse(self._command_version(["yarn", "--version"]))

    def current(self) -> SemanticVersion:
        return self.frappe_version

    def major(self) -> int:
        return self.current().major

    def minor(self) -> int:
        return self.current().minor

    def patch(self) -> int:
        return self.current().patch

    def is_v14(self) -> bool:
        return self.major() == 14

    def is_v15(self) -> bool:
        return self.major() == 15

    def is_v16(self) -> bool:
        return self.major() == 16

    def is_v17(self) -> bool:
        return self.major() == 17

    def is_ge(self, version: str) -> bool:
        return self.current().as_tuple() >= SemanticVersion.parse(version).as_tuple()

    def is_gt(self, version: str) -> bool:
        return self.current().as_tuple() > SemanticVersion.parse(version).as_tuple()

    def is_lt(self, version: str) -> bool:
        return self.current().as_tuple() < SemanticVersion.parse(version).as_tuple()

    def is_le(self, version: str) -> bool:
        return self.current().as_tuple() <= SemanticVersion.parse(version).as_tuple()

    def snapshot(self) -> dict[str, str]:
        return {
            "frappe": str(self.frappe_version),
            "bench": str(self.bench_version),
            "python": str(self.python_version),
            "node": str(self.node_version),
            "redis": str(self.redis_version),
            "mariadb": str(self.mariadb_version),
            "yarn": str(self.yarn_version)
	}

    def snapshot_json(self) -> str:
        return json.dumps(self.snapshot(), indent=2, sort_keys=True)

    @staticmethod
    def _command_version(command: list[str]) -> str:
        if not shutil.which(command[0]):
            return "0.0.0"
        try:
            result = subprocess.run(command, capture_output=True, text=True, check=False, timeout=5)
        except Exception:
            return "0.0.0"
        return (result.stdout or result.stderr or "0.0.0").strip()
