# Copyright (c) 2026, Omnexa and contributors
# License: See license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from omnexa_fixed_assets.utils.hotel_guard import enforce_hotel_feature_enabled


class RFIDScanLog(Document):
	def validate(self):
		enforce_hotel_feature_enabled()
		asset = frappe.db.get_value("Fixed Asset", self.fixed_asset, ["company", "branch"], as_dict=True)
		if not asset:
			frappe.throw(_("Fixed Asset does not exist."), title=_("Fixed Asset"))
		if asset.company != self.company:
			frappe.throw(_("Fixed Asset must belong to the same company."), title=_("Company"))
