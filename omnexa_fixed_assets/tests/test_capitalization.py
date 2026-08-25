# Copyright (c) 2026, Omnexa and contributors
# License: See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import flt, today


class TestFixedAssetCapitalization(FrappeTestCase):
	def setUp(self):
		super().setUp()
		self._ensure_geo()
		sfx = frappe.generate_hash(length=4)
		self.company = self._create_company(f"FA{sfx.upper()}")
		self.branch = self._create_branch(self.company, f"B{sfx[:3]}", f"Branch {sfx}")
		frappe.defaults.set_user_default("Company", self.company)
		frappe.defaults.set_user_default("Branch", self.branch)
		self._gl_asset = self._gl(f"FA{sfx}1", f"FA Asset {sfx}", company=self.company)
		self._gl_accum = self._gl(f"FA{sfx}2", f"FA Accum {sfx}", company=self.company)
		self._gl_exp = self._gl(f"FA{sfx}3", f"FA Exp {sfx}", company=self.company)
		self._gl_cash = self._gl(f"FA{sfx}4", f"FA Cash {sfx}", company=self.company)
		self.category = frappe.get_doc(
			{
				"doctype": "Fixed Asset Category",
				"category_code": f"C{sfx
	}",
				"category_name": f"Category {sfx
	}",
				"company": self.company,
				"is_group": 0,
				"asset_gl_account": self._gl_asset,
				"accumulated_depreciation_gl_account": self._gl_accum,
				"depreciation_expense_gl_account": self._gl_exp
	}
		).insert(ignore_permissions=True)

	def _ensure_geo(self):
		if not frappe.db.exists("Currency", "EGP"):
			frappe.get_doc(
				{"doctype": "Currency", "currency_name": "EGP", "symbol": "E£", "enabled": 1
	}
			).insert(ignore_permissions=True)
		if not frappe.db.exists("Country", "Egypt"):
			frappe.get_doc(
				{"doctype": "Country", "country_name": "Egypt", "code": "EG"
	}
			).insert(ignore_permissions=True)

	def _create_company(self, abbr: str):
		doc = frappe.get_doc(
			{
				"doctype": "Company",
				"company_name": f"Test Co {abbr
	}",
				"abbr": abbr[:10],
				"default_currency": "EGP",
				"country": "Egypt",
				"status": "Active"
	}
		)
		doc.insert(ignore_permissions=True)
		return doc.name

	def _create_branch(self, company: str, code: str, name: str):
		doc = frappe.get_doc(
			{
				"doctype": "Branch",
				"company": company,
				"branch_name": name,
				"branch_code": code,
				"status": "Active"
	}
		)
		doc.insert(ignore_permissions=True)
		return doc.name

	def _gl(self, number, name, company=None):
		d = frappe.new_doc("GL Account")
		d.company = company or self.company
		d.account_number = number
		d.account_name = name
		d.is_group = 0
		d.insert(ignore_permissions=True)
		return d.name

	def _make_asset(self):
		return frappe.get_doc(
			{
				"doctype": "Fixed Asset",
				"naming_series": "FA-.#####",
				"asset_name": "Test laptop",
				"company": self.company,
				"branch": self.branch,
				"category": self.category.name,
				"status": "draft"
	}
		).insert(ignore_permissions=True)

	def test_acquisition_posts_journal_and_updates_asset(self):
		asset = self._make_asset()
		acq = frappe.get_doc(
			{
				"doctype": "Fixed Asset Acquisition",
				"naming_series": "FAA-.#####",
				"company": self.company,
				"branch": self.branch,
				"posting_date": today(),
				"fixed_asset": asset.name,
				"capitalization_amount": 1500,
				"credit_account": self._gl_cash
	}
		)
		acq.insert(ignore_permissions=True)
		acq.submit()

		acq.reload()
		asset.reload()
		self.assertTrue(acq.journal_entry)
		self.assertEqual(asset.status, "acquired")
		self.assertEqual(flt(asset.acquisition_cost), 1500.0)
		self.assertEqual(asset.capitalization_journal_entry, acq.journal_entry)

		je = frappe.get_doc("Journal Entry", acq.journal_entry)
		self.assertEqual(je.docstatus, 1)
		self.assertEqual(je.company, self.company)
		self.assertEqual(je.branch, self.branch)
		debit = sum(flt(r.debit) for r in je.accounts)
		credit = sum(flt(r.credit) for r in je.accounts)
		self.assertEqual(debit, credit)
		self.assertEqual(debit, 1500.0)

	def test_acquisition_cancel_reverts_asset(self):
		asset = self._make_asset()
		acq = frappe.get_doc(
			{
				"doctype": "Fixed Asset Acquisition",
				"naming_series": "FAA-.#####",
				"company": self.company,
				"branch": self.branch,
				"posting_date": today(),
				"fixed_asset": asset.name,
				"capitalization_amount": 800,
				"credit_account": self._gl_cash
	}
		)
		acq.insert(ignore_permissions=True)
		acq.submit()
		acq.cancel()

		acq.reload()
		asset.reload()
		self.assertEqual(acq.docstatus, 2)
		self.assertFalse(acq.journal_entry)
		self.assertEqual(asset.status, "draft")
		self.assertEqual(flt(asset.acquisition_cost), 0.0)
		self.assertFalse(asset.capitalization_journal_entry)
