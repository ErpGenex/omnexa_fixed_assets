# Copyright (c) 2026, Omnexa and contributors
# License: See license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from omnexa_fixed_assets.utils.hotel_guard import enforce_hotel_feature_enabled


class HotelRoom(Document):
	def validate(self):
		enforce_hotel_feature_enabled()
		branch_company = frappe.db.get_value("Branch", self.branch, "company")
		if not branch_company:
			frappe.throw(_("Branch {0} does not exist.").format(self.branch), title=_("Branch"))
		if branch_company != self.company:
			frappe.throw(_("Branch belongs to a different company."), title=_("Branch"))

		prop = frappe.db.get_value("Hotel Property", self.hotel_property, ["company", "branch"], as_dict=True)
		if not prop:
			frappe.throw(_("Hotel Property does not exist."), title=_("Hotel Property"))
		if prop.company != self.company:
			frappe.throw(_("Hotel Property must belong to the same company."), title=_("Hotel Property"))
		if self.hotel_functional_area:
			fa_prop = frappe.db.get_value("Hotel Functional Area", self.hotel_functional_area, "hotel_property")
			if fa_prop and fa_prop != self.hotel_property:
				frappe.throw(
					_("Functional Area must belong to the same hotel property."),
					title=_("Hotel Room"),
				)
