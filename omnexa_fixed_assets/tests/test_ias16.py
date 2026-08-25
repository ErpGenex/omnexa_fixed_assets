# Copyright (c) 2026, Omnexa and contributors
# License: See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import flt, today

from omnexa_fixed_assets.api import run_auto_depreciation_policy_now, run_monthly_depreciation_batch
from omnexa_fixed_assets.tasks import run_month_end_depreciation_jobs
from omnexa_fixed_assets.utils.ias16 import depreciable_amount, monthly_straight_line, suggest_monthly_depreciation


class TestIAS16Helpers(FrappeTestCase):
	def test_depreciable_amount_and_sl_monthly(self):
		self.assertEqual(depreciable_amount(1000, 100), 900.0)
		self.assertEqual(monthly_straight_line(cost=1200, salvage=0, useful_life_months=12), 100.0)

	def test_suggest_matches_straight_line(self):
		s = suggest_monthly_depreciation(
			method="Straight Line",
			cost=6000,
			salvage=600,
			accumulated_depreciation=0,
			useful_life_months=60,
			annual_declining_rate_percent=None,
			total_estimated_units=None,
			units_this_period=None,
		)
		self.assertEqual(s, 90.0)


class TestIAS16Posting(FrappeTestCase):
	def setUp(self):
		super().setUp()
		self._ensure_geo()
		sfx = frappe.generate_hash(length=4)
		self.company = self._create_company(f"IF{sfx.upper()}")
		self.branch = self._create_branch(self.company, f"I{sfx[:3]}", f"Br {sfx}")
		frappe.defaults.set_user_default("Company", self.company)
		frappe.defaults.set_user_default("Branch", self.branch)
		self._gl_asset = self._gl(f"IF{sfx}1", f"IF Ast {sfx}")
		self._gl_accum = self._gl(f"IF{sfx}2", f"IF Acu {sfx}")
		self._gl_exp = self._gl(f"IF{sfx}3", f"IF Exp {sfx}")
		self._gl_cash = self._gl(f"IF{sfx}4", f"IF Csh {sfx}")
		self._gl_pl = self._gl(f"IF{sfx}5", f"IF PL {sfx}")
		self.category = frappe.get_doc(
			{
				"doctype": "Fixed Asset Category",
				"category_code": f"I{sfx
	}",
				"category_name": f"Cat {sfx
	}",
				"company": self.company,
				"is_group": 0,
				"asset_gl_account": self._gl_asset,
				"accumulated_depreciation_gl_account": self._gl_accum,
				"depreciation_expense_gl_account": self._gl_exp,
				"default_useful_life_months": 12,
				"default_depreciation_method": "Straight Line"
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
				"company_name": f"Co {abbr
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

	def _gl(self, number, name):
		d = frappe.new_doc("GL Account")
		d.company = self.company
		d.account_number = number
		d.account_name = name
		d.is_group = 0
		d.insert(ignore_permissions=True)
		return d.name

	def _capitalized_asset(self, amount: float):
		asset = frappe.get_doc(
			{
				"doctype": "Fixed Asset",
				"naming_series": "FA-.#####",
				"asset_name": "IFRS test asset",
				"company": self.company,
				"branch": self.branch,
				"category": self.category.name,
				"status": "draft",
				"depreciation_method": "Straight Line",
				"useful_life_months": 12,
				"depreciation_start_date": today()
	}
		).insert(ignore_permissions=True)
		acq = frappe.get_doc(
			{
				"doctype": "Fixed Asset Acquisition",
				"naming_series": "FAA-.#####",
				"company": self.company,
				"branch": self.branch,
				"posting_date": today(),
				"fixed_asset": asset.name,
				"capitalization_amount": amount,
				"credit_account": self._gl_cash
	}
		)
		acq.insert(ignore_permissions=True)
		acq.submit()
		asset.reload()
		return asset

	def test_depreciation_entry_posts_and_disposal_derecognizes(self):
		asset = self._capitalized_asset(12000.0)
		self.assertEqual(asset.status, "acquired")

		dep = frappe.get_doc(
			{
				"doctype": "Fixed Asset Depreciation Entry",
				"naming_series": "FADP-.#####",
				"company": self.company,
				"branch": self.branch,
				"posting_date": today(),
				"fixed_asset": asset.name,
				"depreciation_amount": 1000.0
	}
		)
		dep.insert(ignore_permissions=True)
		dep.submit()

		asset.reload()
		self.assertEqual(flt(asset.accumulated_depreciation), 1000.0)
		self.assertTrue(dep.journal_entry)

		dsp = frappe.get_doc(
			{
				"doctype": "Fixed Asset Disposal",
				"naming_series": "FADIS-.#####",
				"company": self.company,
				"branch": self.branch,
				"disposal_date": today(),
				"fixed_asset": asset.name,
				"proceeds": 5000.0,
				"cash_account": self._gl_cash,
				"gain_or_loss_account": self._gl_pl
	}
		)
		dsp.insert(ignore_permissions=True)
		dsp.submit()

		asset.reload()
		self.assertEqual(asset.status, "disposed")
		self.assertEqual(flt(asset.acquisition_cost), 0.0)
		self.assertEqual(flt(asset.accumulated_depreciation), 0.0)

		dsp.cancel()
		asset.reload()
		self.assertEqual(flt(asset.acquisition_cost), 12000.0)
		self.assertEqual(flt(asset.accumulated_depreciation), 1000.0)
		self.assertEqual(asset.status, "acquired")

	def test_monthly_depreciation_batch_is_idempotent_per_date(self):
		asset = self._capitalized_asset(1200.0)
		result_1 = run_monthly_depreciation_batch(
			company=self.company,
			branch=self.branch,
			posting_date=today(),
			submit_entries=1,
			limit=50,
		)
		self.assertEqual(result_1["created_count"], 1)
		self.assertEqual(result_1["submitted_count"], 1)
		asset.reload()
		self.assertEqual(flt(asset.accumulated_depreciation), 100.0)

		result_2 = run_monthly_depreciation_batch(
			company=self.company,
			branch=self.branch,
			posting_date=today(),
			submit_entries=1,
			limit=50,
		)
		self.assertEqual(result_2["created_count"], 0)

	def test_scheduled_monthly_job_uses_company_policy(self):
		asset = self._capitalized_asset(1200.0)
		frappe.get_doc(
			{
				"doctype": "Fixed Asset Auto Depreciation Policy",
				"company": self.company,
				"enabled": 1,
				"branch": self.branch,
				"submit_entries": 1,
				"max_assets_per_run": 100
	}
		).insert(ignore_permissions=True)

		run_month_end_depreciation_jobs(posting_date=today())
		asset.reload()
		self.assertEqual(flt(asset.accumulated_depreciation), 100.0)

	def test_policy_run_now_updates_audit_fields(self):
		asset = self._capitalized_asset(1200.0)
		policy = frappe.get_doc(
			{
				"doctype": "Fixed Asset Auto Depreciation Policy",
				"company": self.company,
				"enabled": 1,
				"branch": self.branch,
				"submit_entries": 1,
				"max_assets_per_run": 100
	}
		).insert(ignore_permissions=True)

		result = run_auto_depreciation_policy_now(policy.name, posting_date=today())
		self.assertEqual(result["created_count"], 1)

		policy.reload()
		asset.reload()
		self.assertEqual(policy.last_run_status, "Success")
		self.assertTrue(policy.last_run_at)
		self.assertEqual(flt(asset.accumulated_depreciation), 100.0)
