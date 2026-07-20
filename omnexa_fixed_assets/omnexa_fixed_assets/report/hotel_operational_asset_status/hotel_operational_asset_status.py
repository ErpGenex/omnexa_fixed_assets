# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

import frappe
from frappe import _

from omnexa_core.omnexa_core.utils.report_charts import auto_chart_for_columns

from omnexa_fixed_assets.utils.hotel_guard import enforce_hotel_feature_enabled


def execute(filters=None):
	enforce_hotel_feature_enabled()
	filters = frappe._dict(filters or {})
	if not filters.get("company"):
		frappe.throw(_("Company is required."), title=_("Filters"))

	fa_cols = set(frappe.db.get_table_columns("Fixed Asset") or [])
	has_hotel = "hotel_property" in fa_cols
	has_scan = "scan_status" in fa_cols
	has_hk = "housekeeping_status" in fa_cols
	has_eng = "engineering_status" in fa_cols

	params = {"company": filters.company
	}
	conditions = ["fa.company = %(company)s"]
	if has_hotel:
		conditions.append("IFNULL(fa.hotel_property, '') != ''")
	if filters.get("hotel_property") and has_hotel:
		params["hotel_property"] = filters.hotel_property
		conditions.append("fa.hotel_property = %(hotel_property)s")

	select_bits = ["COUNT(*) AS total_assets"]
	if has_hotel:
		select_bits.insert(0, "fa.hotel_property")
	else:
		select_bits.insert(0, "'' AS hotel_property")

	group_by = "fa.hotel_property" if has_hotel else ""

	if has_scan:
		select_bits.extend(
			[
				"SUM(IF(IFNULL(fa.scan_status,'') = 'Missing', 1, 0)) AS missing_scan",
				"SUM(IF(IFNULL(fa.scan_status,'') = 'Mismatch', 1, 0)) AS scan_mismatch",
			]
		)
	else:
		select_bits.extend(["0 AS missing_scan", "0 AS scan_mismatch"])

	if has_hk:
		select_bits.append(
			"SUM(IF(IFNULL(fa.housekeeping_status,'') IN ('Dirty', 'Out of Service'), 1, 0)) AS housekeeping_attention"
		)
	else:
		select_bits.append("0 AS housekeeping_attention")

	if has_eng:
		select_bits.append(
			"SUM(IF(IFNULL(fa.engineering_status,'') IN ('Open Work Order', 'Critical'), 1, 0)) AS engineering_attention"
		)
	else:
		select_bits.append("0 AS engineering_attention")

	if group_by:
		sql = f"""
			SELECT {', '.join(select_bits)}
			FROM `tabFixed Asset` fa
			WHERE {' AND '.join(conditions)} AND fa.docstatus < 2
			GROUP BY {group_by}
			ORDER BY fa.hotel_property
		"""
	else:
		sql = f"""
			SELECT {', '.join(select_bits)}
			FROM `tabFixed Asset` fa
			WHERE {' AND '.join(conditions)} AND fa.docstatus < 2
		"""

	data = frappe.db.sql(sql, params, as_dict=True)

	columns = [
		{"label": _("Hotel Property"), "fieldname": "hotel_property", "fieldtype": "Link", "options": "Hotel Property", "width": 200
	},
		{"label": _("Total Assets"), "fieldname": "total_assets", "fieldtype": "Int", "width": 120
	},
		{"label": _("Missing Scan"), "fieldname": "missing_scan", "fieldtype": "Int", "width": 120
	},
		{"label": _("Scan Mismatch"), "fieldname": "scan_mismatch", "fieldtype": "Int", "width": 120
	},
		{"label": _("Housekeeping Attention"), "fieldname": "housekeeping_attention", "fieldtype": "Int", "width": 160
	},
		{"label": _("Engineering Attention"), "fieldname": "engineering_attention", "fieldtype": "Int", "width": 160
	},
	]
	chart = auto_chart_for_columns(data, columns)
	return columns, data, None, chart