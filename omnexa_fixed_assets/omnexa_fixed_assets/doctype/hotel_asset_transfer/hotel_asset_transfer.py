# Copyright (c) 2026, Omnexa and contributors
# License: See license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime

from omnexa_fixed_assets.utils.hotel_guard import enforce_hotel_feature_enabled


class HotelAssetTransfer(Document):
	def validate(self):
		enforce_hotel_feature_enabled()
		if self.from_hotel_room and self.to_hotel_room and self.from_hotel_room == self.to_hotel_room:
			frappe.throw(_("From room and To room cannot be the same."), title=_("Validation"))

	def on_submit(self):
		if self.approval_status != "Approved":
			frappe.throw(_("Submit only after workflow status is Approved."), title=_("Validation"))
		asset = frappe.get_doc("Fixed Asset", self.fixed_asset)
		if self.to_hotel_property:
			asset.db_set("hotel_property", self.to_hotel_property, update_modified=False)
		if self.to_hotel_room:
			asset.db_set("hotel_room", self.to_hotel_room, update_modified=False)
		frappe.db.set_value(
			"Hotel Asset Transfer",
			self.name,
			"executed_at",
			now_datetime(),
			update_modified=False,
		)
