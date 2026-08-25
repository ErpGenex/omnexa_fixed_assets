# Copyright (c) 2026, Omnexa and contributors
# License: See license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate

from omnexa_fixed_assets.utils.ias16 import depreciable_amount
from omnexa_accounting.utils.enterprise_codes import ensure_simple_doc_name


class FixedAsset(Document):
	def autoname(self):
		ensure_simple_doc_name(self, prefix="AST-", digits=5)

	def validate(self):
		# Keep internal_code stable and aligned with auto-numbered name
		if self.name:
			if not self.internal_code:
				self.internal_code = self.name
			elif (self.internal_code or "").strip() != (self.name or "").strip():
				# Do not allow tampering with internal_code (must equal auto-numbered name)
				frappe.throw(_("Internal Code must match the Asset ID."), title=_("Identification"))
		self._sync_auto_identifiers()
		self._validate_branch_company_match()
		self._validate_category()
		self._validate_parent_asset_hierarchy()
		self._validate_tracking_identifiers()
		self._sync_default_accounts_from_category()
		self._sync_depreciation_defaults_from_category()
		self._validate_gl_accounts()
		self._validate_ifrs_cost_and_depreciation()
		self._sync_depreciable_and_carrying_amount()
		self._sync_asset_hierarchy_fields()
		self._sync_eam_cost_intelligence_fields()
		self._sync_media_and_ops_rollups()
		self._sync_fully_depreciated_status()

	def after_insert(self):
		# Name is final here; persist identifiers so Barcode / QR render on first load after save.
		code = (self.name or "").strip()
		if not code:
			return
		updates = {}
		if not (self.internal_code or "").strip():
			updates["internal_code"] = code
		if not (self.qr_payload or "").strip():
			updates["qr_payload"] = code
		if not (self.barcode or "").strip():
			updates["barcode"] = code
		if updates:
			self.db_set(updates, update_modified=False)
			for k, v in updates.items():
				setattr(self, k, v)

	def _sync_auto_identifiers(self):
		"""Default QR payload and barcode from asset code when left blank (non-destructive)."""
		code = (self.internal_code or self.name or "").strip()
		if not code:
			return
		if not (self.qr_payload or "").strip():
			self.qr_payload = code
		if not (self.barcode or "").strip():
			self.barcode = code

	def _validate_branch_company_match(self):
		branch_company = frappe.db.get_value("Branch", self.branch, "company")
		if not branch_company:
			frappe.throw(_("Branch {0} does not exist.").format(self.branch), title=_("Branch"))
		if branch_company != self.company:
			frappe.throw(_("Branch belongs to a different company."), title=_("Branch"))

	def _validate_category(self):
		cat = frappe.db.get_value(
			"Fixed Asset Category",
			self.category,
			["company", "is_group"],
			as_dict=True,
		)
		if not cat:
			frappe.throw(_("Category does not exist."), title=_("Category"))
		if cat.company != self.company:
			frappe.throw(_("Category must belong to the same company."), title=_("Category"))
		if cat.is_group:
			frappe.throw(_("Select a leaf category with GL accounts."), title=_("Category"))

	def _sync_default_accounts_from_category(self):
		cat = frappe.get_cached_doc("Fixed Asset Category", self.category)
		if not self.asset_gl_account and cat.asset_gl_account:
			self.asset_gl_account = cat.asset_gl_account
		if not self.accumulated_depreciation_gl_account and cat.accumulated_depreciation_gl_account:
			self.accumulated_depreciation_gl_account = cat.accumulated_depreciation_gl_account
		if not self.depreciation_expense_gl_account and cat.depreciation_expense_gl_account:
			self.depreciation_expense_gl_account = cat.depreciation_expense_gl_account

	def _sync_depreciation_defaults_from_category(self):
		if not self.category:
			return
		cat = frappe.get_cached_doc("Fixed Asset Category", self.category)
		if cat.is_group:
			return
		if not self.useful_life_months and getattr(cat, "default_useful_life_months", None):
			self.useful_life_months = cat.default_useful_life_months
		if getattr(cat, "default_depreciation_method", None) and (not self.depreciation_method or self.depreciation_method == "None"):
			self.depreciation_method = cat.default_depreciation_method
		method = (self.depreciation_method or "").strip()
		if method == "Declining Balance" and not flt(self.declining_balance_rate_annual):
			if flt(getattr(cat, "default_declining_balance_rate", None)):
				self.declining_balance_rate_annual = cat.default_declining_balance_rate
		if method == "Units of Production" and not self.total_estimated_units:
			if getattr(cat, "default_total_estimated_units", None):
				self.total_estimated_units = cat.default_total_estimated_units

	def _validate_gl_accounts(self):
		for field, label in (
			("asset_gl_account", _("Asset account")),
			("accumulated_depreciation_gl_account", _("Accumulated depreciation")),
			("depreciation_expense_gl_account", _("Depreciation expense")),
		):
			acc = self.get(field)
			if not acc:
				frappe.throw(_("Set {0} on the asset or category.").format(label), title=_("GL"))
			row = frappe.db.get_value(
				"GL Account",
				acc,
				["company", "is_group"],
				as_dict=True,
			)
			if not row or row.company != self.company:
				frappe.throw(_("{0}: invalid account for company.").format(label), title=_("GL"))
			if row.is_group:
				frappe.throw(_("{0}: must be a leaf account.").format(label), title=_("GL"))

	def _validate_ifrs_cost_and_depreciation(self):
		cost = flt(self.acquisition_cost)
		salvage = flt(self.salvage_value)
		if cost > 0 and salvage > cost:
			frappe.throw(_("Residual value cannot exceed acquisition cost."), title=_("IAS 16"))
		method = (self.depreciation_method or "").strip()
		if self.status in ("disposed", "draft"):
			return
		if not cost or self.measurement_model != "Cost Model":
			return
		if method in ("", "None"):
			return
		if method == "Straight Line":
			if not self.useful_life_months or int(self.useful_life_months) < 1:
				frappe.throw(
					_("Useful life in months is required for straight-line depreciation."),
					title=_("IAS 16"),
				)
		if method == "Declining Balance":
			if not flt(self.declining_balance_rate_annual) or flt(self.declining_balance_rate_annual) <= 0:
				frappe.throw(
					_("Set a positive annual rate for declining balance depreciation."),
					title=_("IAS 16"),
				)
		if method == "Units of Production":
			if not self.total_estimated_units or int(self.total_estimated_units) < 1:
				frappe.throw(
					_("Total estimated units is required for units-of-production depreciation."),
					title=_("IAS 16"),
				)
		if self.depreciation_start_date and self.capitalization_date:
			if getdate(self.depreciation_start_date) < getdate(self.capitalization_date):
				frappe.throw(
					_("Depreciation start date cannot be before capitalization date."),
					title=_("IAS 16"),
				)

	def _validate_tracking_identifiers(self):
		for fieldname, label in (
			("barcode", _("Barcode")),
			("qr_payload", _("QR payload")),
			("rfid_tag", _("RFID Tag")),
		):
			value = (self.get(fieldname) or "").strip()
			if not value:
				continue
			existing = frappe.db.get_value(
				"Fixed Asset",
				{fieldname: value, "name": ["!=", self.name or ""]},
				"name",
			)
			if existing:
				frappe.throw(
					_("{0} must be unique. Existing asset: {1}").format(label, existing),
					title=_("Tracking"),
				)

	def _sync_depreciable_and_carrying_amount(self):
		self.depreciable_amount = depreciable_amount(self.acquisition_cost, self.salvage_value)
		self.net_book_value = flt(self.acquisition_cost) - flt(self.accumulated_depreciation)

	def _sync_fully_depreciated_status(self):
		if self.status == "disposed":
			return
		rem = depreciable_amount(self.acquisition_cost, self.salvage_value) - flt(self.accumulated_depreciation)
		if flt(self.acquisition_cost) > 0 and rem <= 0.005 and self.depreciation_method not in ("", "None"):
			if self.status != "fully_depreciated":
				self.status = "fully_depreciated"

	def _validate_parent_asset_hierarchy(self):
		if not self.parent_asset:
			return
		if self.parent_asset == self.name:
			frappe.throw(_("Parent asset cannot be the same asset."), title=_("Hierarchy"))
		parent = frappe.db.get_value("Fixed Asset", self.parent_asset, ["company", "branch"], as_dict=True)
		if not parent:
			frappe.throw(_("Parent asset does not exist."), title=_("Hierarchy"))
		if parent.company != self.company:
			frappe.throw(_("Parent asset must belong to the same company."), title=_("Hierarchy"))

	def _sync_asset_hierarchy_fields(self):
		if not self.parent_asset:
			self.asset_level = 0
			self.asset_path = self.name or self.asset_name
			return
		parent = frappe.db.get_value("Fixed Asset", self.parent_asset, ["asset_level", "asset_path"], as_dict=True)
		parent_level = int((parent or {}).get("asset_level") or 0)
		parent_path = ((parent or {}).get("asset_path") or self.parent_asset).strip("/")
		this_node = self.name or (self.asset_name or "asset").replace("/", "-")
		self.asset_level = parent_level + 1
		self.asset_path = f"{parent_path}/{this_node}".strip("/")

	def _get_maintenance_cost_column(self) -> str:
		"""Support older schemas where maintenance cost field was named `cost`."""
		if frappe.db.has_column("Fixed Asset Maintenance", "cost_amount"):
			return "cost_amount"
		if frappe.db.has_column("Fixed Asset Maintenance", "cost"):
			return "cost"
		# Fallback; query will return 0 using IFNULL on a constant.
		return ""

	def _sync_eam_cost_intelligence_fields(self):
		# Conservative, deterministic derived defaults from existing accounting-maintenance data.
		cost_col = self._get_maintenance_cost_column()
		# cost_col is a whitelisted column name only (cost_amount | cost); safe to embed.
		cost_expr = f"sum(`{cost_col}`)" if cost_col else "0"
		maint_total = flt(
			frappe.db.sql(
				f"""
				select ifnull({cost_expr}, 0)
				from `tabFixed Asset Maintenance`
				where fixed_asset=%s and docstatus < 2
				""",
				(self.name,),
			)[0][0]
			or 0
		)
		lifecycle_cost = flt(self.acquisition_cost) + maint_total
		self.lifecycle_cost = lifecycle_cost
		self.maintenance_burden = (maint_total / lifecycle_cost * 100.0) if lifecycle_cost else 0.0
		self.repair_efficiency = max(0.0, min(100.0, 100.0 - self.maintenance_burden))
		nbv_ratio = (flt(self.net_book_value) / flt(self.acquisition_cost) * 100.0) if flt(self.acquisition_cost) else 0.0
		self.capital_risk = max(0.0, min(100.0, flt(self.maintenance_burden) * 0.7 + (100.0 - nbv_ratio) * 0.3))
		self.replacement_projection = max(flt(self.net_book_value), flt(self.acquisition_cost) * 0.85)

	def _sync_media_and_ops_rollups(self):
		media_rows = list(self.get("asset_media_attachments") or [])
		image_count = 0
		for row in media_rows:
			if not row.get("uploaded_by"):
				row.uploaded_by = frappe.session.user
			if (row.get("media_type") or "").strip() == "Image":
				image_count += 1

		self.image_count = image_count
		self.attachment_count = len(media_rows)

		if not self.name:
			self.maintenance_cost_to_date = 0
			self.maintenance_event_count = 0
			self.inventory_scan_count = 0
			self.last_inventory_scan_at = None
			return

		cost_col = self._get_maintenance_cost_column()
		cost_expr = f"sum(`{cost_col}`)" if cost_col else "0"
		maint = frappe.db.sql(
			f"""
			select ifnull({cost_expr}, 0) as total_cost, count(*) as event_count
			from `tabFixed Asset Maintenance`
			where fixed_asset=%s and docstatus < 2
			""",
			(self.name,),
			as_dict=True,
		)
		maint_row = maint[0] if maint else {}
		self.maintenance_cost_to_date = flt((maint_row or {}).get("total_cost"))
		self.maintenance_event_count = int((maint_row or {}).get("event_count") or 0)

		inv = frappe.db.sql(
			"""
			select count(*) as scan_count, max(scan_time) as last_scan
			from `tabRFID Scan Log`
			where fixed_asset=%s
			""",
			(self.name,),
			as_dict=True,
		)
		inv_row = inv[0] if inv else {}
		self.inventory_scan_count = int((inv_row or {}).get("scan_count") or 0)
		self.last_inventory_scan_at = (inv_row or {}).get("last_scan")
