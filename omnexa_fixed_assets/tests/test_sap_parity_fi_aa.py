# Copyright (c) 2026, ErpGenEx
import frappe
from frappe.tests.utils import FrappeTestCase


class TestSapParityFiAa(FrappeTestCase):
	def test_depreciation_book_field_in_meta(self):
		meta = frappe.get_meta("Fixed Asset")
		self.assertTrue(meta.has_field("accounting_depreciation_book"))
		field = meta.get_field("accounting_depreciation_book")
		self.assertEqual(field.default, "Local")

	def test_revaluation_validate_positive_amount(self):
		doc = frappe.get_doc(
			{
				"doctype": "Fixed Asset Revaluation",
				"company": "_Test Company",
				"branch": "_Test Branch",
				"fixed_asset": "_Test Asset",
				"revalued_amount": 0,
				"posting_date": "2026-05-20",
			}
		)
		with self.assertRaises(frappe.ValidationError):
			doc.validate()

	def test_impairment_preview(self):
		from omnexa_fixed_assets.fi_aa_parity import preview_impairment_adjustment

		out = preview_impairment_adjustment(100000, 85000)
		self.assertEqual(out["impairment_loss"], 15000)
