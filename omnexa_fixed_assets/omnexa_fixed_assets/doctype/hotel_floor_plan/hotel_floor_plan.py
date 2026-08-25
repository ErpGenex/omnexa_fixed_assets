# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from omnexa_fixed_assets.utils.hotel_guard import enforce_hotel_feature_enabled


class HotelFloorPlan(Document):
	def validate(self):
		enforce_hotel_feature_enabled()
		if not (self.svg_content or "").strip() and not self.attach_image:
			frappe.msgprint(_("Provide SVG content or attach a floor plan image."), indicator="orange")
