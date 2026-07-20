# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from omnexa_fixed_assets.utils.hotel_guard import enforce_hotel_feature_enabled


class HotelFunctionalArea(Document):
	def validate(self):
		enforce_hotel_feature_enabled()
		branch_company = frappe.db.get_value("Branch", self.branch, "company")
		if not branch_company:
			frappe.throw(_("Branch {0} does not exist.").format(self.branch), title=_("Branch"))
		if branch_company != self.company:
			frappe.throw(_("Branch belongs to a different company."), title=_("Branch"))

		prop = frappe.db.get_value(
			"Hotel Property",
			self.hotel_property,
			["company", "branch"],
			as_dict=True,
		)
		if not prop:
			frappe.throw(_("Hotel Property does not exist."), title=_("Hotel Property"))
		if prop.company != self.company:
			frappe.throw(_("Hotel Property must belong to the same company."), title=_("Hotel Property"))
		if prop.branch != self.branch:
			frappe.throw(_("Hotel Property must use the same branch."), title=_("Branch"))

		code = (self.area_code or "").strip()
		if not code:
			return
		row = frappe.db.get_value(
			"Hotel Functional Area",
			{"hotel_property": self.hotel_property, "area_code": code},
			"name",
		)
		if row and (self.is_new() or row != self.name):
			frappe.throw(_("Area Code must be unique per hotel property."), title=_("Duplicate"))
