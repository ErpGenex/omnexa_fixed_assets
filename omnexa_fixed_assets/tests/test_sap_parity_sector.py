# Copyright (c) 2026, ErpGenEx
import frappe
from frappe.tests.utils import FrappeTestCase


class TestSapParityFixedAssets(FrappeTestCase):
	def test_fixed_asset_depreciation_book_meta(self):
		meta = frappe.get_meta("Fixed Asset")
		self.assertTrue(meta.has_field("accounting_depreciation_book"))
