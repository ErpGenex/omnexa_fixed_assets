# Copyright (c) 2026, Omnexa and contributors
# License: MIT

"""Merge desk navbar company/branch into fixed-assets Script Report filters."""

from __future__ import annotations

import frappe

from omnexa_core.omnexa_core.report_scope import resolve_report_filters


def merge_navbar_report_filters(filters=None) -> frappe._dict:
	return resolve_report_filters(filters)
