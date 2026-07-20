# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

import frappe
from frappe import _

from omnexa_core.omnexa_core.utils.report_charts import auto_chart_for_columns

from omnexa_core.omnexa_core.report_print.report_query_filters import (
	get_all_filters,
	policy_version_filters,
	prepare_filters,
	sql_conditions,
)



def execute(filters=None):
	columns = [
		{"label": _("Fixed Asset"), "fieldname": "fixed_asset", "fieldtype": "Link", "options": "Fixed Asset", "width": 160},
		{"label": _("Last Seen Time"), "fieldname": "last_seen_time", "fieldtype": "Datetime", "width": 170},
		{"label": _("Last Location"), "fieldname": "last_location", "fieldtype": "Data", "width": 220},
		{"label": _("Reader"), "fieldname": "last_reader", "fieldtype": "Data", "width": 160},
	]
	filters = prepare_filters(filters)
	conditions, params = sql_conditions(filters, "RFID Scan Log", date_field="creation", company=True, branch=True)
	rows = frappe.db.sql(
		f"""
		SELECT
			r.fixed_asset,
			MAX(r.scan_time) AS last_seen_time,
			SUBSTRING_INDEX(
				GROUP_CONCAT(r.location_text ORDER BY r.scan_time DESC SEPARATOR '||'),
				'||',
				1
			) AS last_location,
			SUBSTRING_INDEX(
				GROUP_CONCAT(r.reader_device ORDER BY r.scan_time DESC SEPARATOR '||'),
				'||',
				1
			) AS last_reader
		FROM `tabRFID Scan Log`
		WHERE {' AND '.join(conditions)}
		GROUP BY r.fixed_asset
		ORDER BY r.scan_time DESC SEPARATOR '||'),
				'||',
				1
			) AS last_location,
			SUBSTRING_INDEX(
				GROUP_CONCAT(r.reader_device ORDER BY r.scan_time DESC SEPARATOR '||'),
				'||',
				1
			) AS last_reader
		FROM `tabRFID Scan Log` r
		WHERE r.company = %(company)s
		GROUP BY r.fixed_asset
		ORDER BY last_seen_time DESC
		""",
		params,
		as_dict=True,
	)
	chart = auto_chart_for_columns(rows, columns)
	return columns, rows, None, chart