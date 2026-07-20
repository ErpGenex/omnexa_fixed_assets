from __future__ import annotations

from pathlib import Path

from ..scanner import CompatibilityScanner
from ..version_manager import SemanticVersion, VersionManager


def test_semantic_version_parse():
    assert SemanticVersion.parse("15.2.1").as_tuple() == (15, 2, 1)


def test_version_manager_helpers():
    manager = VersionManager()
    assert isinstance(manager.major(), int)


def test_scanner_report_shape():
    report = CompatibilityScanner(package_root=Path(__file__).resolve().parents[2]).scan()
    assert "score" in report
    assert "findings" in report
