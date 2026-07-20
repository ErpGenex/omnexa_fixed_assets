# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

"""One-off draft Core Work Order rows from submitted Asset Work Order (historical bridge).

Creates **Draft** Core Work Orders only — operators submit after reviewing materials/stock settings.
"""

import frappe

FIXED_ASSET_DOCTYPE = "Fixed Asset"

WO_TYPE_MAP = {
	"Corrective": "Corrective",
	"Preventive": "Preventive",
	"Predictive": "Predictive",
	"Inspection-Triggered": "Inspection",
	"Emergency": "Emergency"
	}

STATUS_MAP = {
	"Draft": "Draft",
	"Planned": "Planned",
	"Assigned": "Planned",
	"In Progress": "In Progress",
	"Completed": "Completed",
	"Cancelled": "Cancelled"
	}


def execute():
	if not frappe.db.exists("DocType", "Core Work Order"):
		return
	if not frappe.db.exists("DocType", "Asset Work Order"):
		return

	aw_names = frappe.get_all(
		"Asset Work Order",
		filters={"docstatus": 1
	},
		pluck="name",
		order_by="creation asc",
	)

	for aw_name in aw_names:
		if frappe.db.exists("Core Work Order", {"legacy_asset_work_order": aw_name
	}):
			continue

		aw = frappe.get_doc("Asset Work Order", aw_name)

		cwo = frappe.new_doc("Core Work Order")
		cwo.naming_series = "CWO-.####"
		cwo.company = aw.company
		cwo.branch = aw.branch
		cwo.status = STATUS_MAP.get(aw.status or "", "Draft")
		cwo.work_order_type = WO_TYPE_MAP.get(aw.work_order_type or "", "Corrective")
		cwo.priority = aw.priority or "Medium"
		cwo.planned_start = aw.planned_start
		cwo.planned_end = aw.planned_end
		cwo.completion_date = aw.completion_date
		cwo.assigned_to = aw.assigned_to
		cwo.estimated_cost = aw.estimated_cost
		cwo.legacy_asset_work_order = aw.name

		desc_parts = ["[Migrated from Asset Work Order {0}]".format(aw.name)]
		if aw.description:
			desc_parts.append(aw.description)
		cwo.description = "\n\n".join(desc_parts)
		cwo.resolution_notes = aw.resolution_notes

		if aw.asset and frappe.db.exists(FIXED_ASSET_DOCTYPE, aw.asset):
			cwo.subject_doctype = FIXED_ASSET_DOCTYPE
			cwo.subject_name = aw.asset

		cwo.insert(ignore_permissions=True)
