# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

"""IAS 16 — asset-level disclosure schedule (cost, depreciation, NBV)."""

from __future__ import annotations

import frappe
from frappe import _

from omnexa_core.omnexa_core.utils.report_charts import auto_chart_for_columns
from frappe.utils import flt

from omnexa_core.omnexa_core.branch_access import get_allowed_branches
from omnexa_fixed_assets.utils.report_filters import merge_navbar_report_filters


def execute(filters=None):
	filters = merge_navbar_report_filters(filters)
	if not filters.get("company"):
		frappe.throw(_("Company is required"))

	conditions = ["fa.company = %(company)s"]
	if filters.get("branch"):
		conditions.append("fa.branch = %(branch)s")
	if filters.get("category"):
		conditions.append("fa.category = %(category)s")
	if filters.get("status"):
		conditions.append("fa.status = %(status)s")

	allowed = get_allowed_branches(company=filters.company)
	if allowed is not None:
		if not allowed:
			return _columns(), []
		filters.allowed_branches = tuple(allowed)
		conditions.append("fa.branch in %(allowed_branches)s")

	data = frappe.db.sql(
		f"""
		SELECT
			fa.name,
			fa.asset_name,
			fa.category,
			fa.branch,
			fa.status,
			fa.capitalization_date AS acquisition_date,
			COALESCE(fa.acquisition_cost, 0) AS acquisition_cost,
			COALESCE(fa.accumulated_depreciation, 0) AS accumulated_depreciation,
			COALESCE(fa.net_book_value, 0) AS net_book_value
		FROM `tabFixed Asset` fa
		WHERE {' AND '.join(conditions)}
		ORDER BY fa.category, fa.asset_name
		""",
		filters,
		as_dict=True,
	)
	for row in data:
		for f in ("acquisition_cost", "accumulated_depreciation", "net_book_value"):
			row[f] = flt(row[f])
	columns = _columns()
	chart = auto_chart_for_columns(data, columns)
	return columns, data, None, chart


def _columns():
	return [
		{"label": _("Asset"), "fieldname": "name", "fieldtype": "Link", "options": "Fixed Asset", "width": 120
	},
		{"label": _("Asset Name"), "fieldname": "asset_name", "fieldtype": "Data", "width": 160
	},
		{"label": _("Category"), "fieldname": "category", "fieldtype": "Link", "options": "Fixed Asset Category", "width": 130
	},
		{"label": _("Branch"), "fieldname": "branch", "fieldtype": "Link", "options": "Branch", "width": 110
	},
		{"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 100
	},
		{"label": _("Acquisition Date"), "fieldname": "acquisition_date", "fieldtype": "Date", "width": 110
	},
		{"label": _("Cost"), "fieldname": "acquisition_cost", "fieldtype": "Currency", "width": 120
	},
		{"label": _("Accum. Depreciation"), "fieldname": "accumulated_depreciation", "fieldtype": "Currency", "width": 140
	},
		{"label": _("NBV"), "fieldname": "net_book_value", "fieldtype": "Currency", "width": 120
	},
	]
