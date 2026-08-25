# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

from omnexa_fixed_assets.utils.hotel_guard import enforce_hotel_feature_enabled
from omnexa_fixed_assets.utils.linen.loss_detection import create_linen_shortage_alert


class LinenIssueBatch(Document):
	def validate(self):
		enforce_hotel_feature_enabled()
		issued = int(self.issued_quantity or 0)
		returned = int(self.returned_quantity or 0)
		if returned > issued:
			frappe.throw(_("Returned quantity cannot exceed issued quantity."))
		self.missing_quantity = max(issued - returned, 0)

	def on_submit(self):
		if int(self.missing_quantity or 0) > 0:
			create_linen_shortage_alert(self)
