# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

import frappe
from frappe import _

from omnexa_core.omnexa_core.utils.report_charts import auto_chart_for_columns


def execute(filters=None):
	filters = frappe._dict(filters or {})
	if not filters.get("company"):
		frappe.throw(_("Company is required."), title=_("Filters"))

	conditions = ["ic.company = %(company)s", "ic.docstatus < 2"]
	params = {"company": filters.company}

	if filters.get("claim_status"):
		conditions.append("ic.claim_status = %(claim_status)s")
		params["claim_status"] = filters.claim_status

	data = frappe.db.sql(
		f"""
		SELECT
			ic.name AS insurance_claim,
			ic.claim_date,
			ic.claim_status,
			ic.claim_amount,
			ic.insurance_policy,
			ic.insurance_incident,
			ic.docstatus
		FROM `tabInsurance Claim` ic
		WHERE {' AND '.join(conditions)}
		ORDER BY ic.claim_date DESC, ic.name DESC
		""",
		params,
		as_dict=True,
	)
	columns = [
		{"label": _("Insurance Claim"), "fieldname": "insurance_claim", "fieldtype": "Link", "options": "Insurance Claim", "width": 160},
		{"label": _("Claim Date"), "fieldname": "claim_date", "fieldtype": "Date", "width": 110},
		{"label": _("Status"), "fieldname": "claim_status", "fieldtype": "Data", "width": 120},
		{"label": _("Claim Amount"), "fieldname": "claim_amount", "fieldtype": "Currency", "width": 130},
		{"label": _("Insurance Policy"), "fieldname": "insurance_policy", "fieldtype": "Link", "options": "Insurance Policy", "width": 160},
		{"label": _("Insurance Incident"), "fieldname": "insurance_incident", "fieldtype": "Link", "options": "Insurance Incident", "width": 160},
		{"label": _("Docstatus"), "fieldname": "docstatus", "fieldtype": "Int", "width": 80},
	]
	chart = auto_chart_for_columns(data, columns)
	return columns, data, None, chart