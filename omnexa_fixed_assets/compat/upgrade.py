from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .logging import get_logger
from .scanner import CompatibilityScanner


@dataclass
class UpgradePlan:
    backup: bool = True
    validate: bool = True
    dependency_scan: bool = True
    compatibility_scan: bool = True
    migrate: bool = True
    build: bool = True
    clear_cache: bool = True
    restart_services: bool = False
    run_tests: bool = True
    steps: list[str] = field(default_factory=list)


class SafeUpgradePipeline:
    """Audited dry-run pipeline for upgrade orchestration.

    Commands that affect services or data are represented as planned steps.
    Production execution should be connected by deployment automation that
    provides backup and rollback guarantees for the target environment.
    """

    def __init__(self, plan: UpgradePlan | None = None) -> None:
        self.plan = plan or UpgradePlan()
        self.logger = get_logger("upgrade")

    def analyze(self) -> dict[str, Any]:
        report = CompatibilityScanner().scan()
        steps = [
            "backup",
            "validate",
            "dependency_scan",
            "compatibility_scan",
            "run_patches",
            "bench_migrate",
            "bench_build",
            "clear_cache",
            "rebuild_assets",
            "restart_workers",
            "restart_scheduler",
            "restart_socketio",
            "restart_nginx",
            "health_check",
            "unit_tests",
            "generate_report",
        ]
        self.plan.steps = steps
        payload = {"plan": self.plan.__dict__, "compatibility": report}
        self.logger.info("upgrade_plan_generated %s", payload)
        return payload


class SafeRollback:
    def plan(self) -> list[str]:
        return [
            "restore_database",
            "restore_site_config",
            "restore_assets",
            "restore_caches",
            "restore_installed_apps",
            "restore_patch_state",
            "restore_previous_compatibility_state",
        ]
