# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

"""Seed demo hotel fixed assets with capitalization + transfers (+ optional RFID).

Requires:
  - Company with Chart of Accounts (leaf GL for acquisition credit side).
  - At least one leaf ``Fixed Asset Category`` with asset / accumulated / expense GL accounts.
  - Hotel Asset Management enabled (Company ``Hotel Assets`` activity OR site_config flag).

Desk (recommended): open **Company**, menu group **أصول الفنادق — تجريبي** → **إنشاء 50 أصلًا…**
(System Manager only; company must have Hotel Assets activity or site flag.)

CLI::

	bench --site YOUR_SITE execute omnexa_fixed_assets.scripts.seed_hotel_asset_movements.run \\
	  --kwargs '{"company": "My Company"}'

Optional kwargs:
  count (int, default 50)
  property_name (str) — Hotel Property name / id
  with_transfer (bool, default True) — second movement via ``Hotel Asset Transfer``
  with_rfid (bool, default True) — one ``RFID Scan Log`` per asset + rfid_tag on asset
  commit (bool, default True)
"""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import flt, now_datetime


def _branch_for_company(company: str) -> str:
	branches = frappe.get_all(
		"Branch",
		filters={"company": company},
		pluck="name",
		order_by="name asc",
		limit=20,
	)
	if not branches:
		frappe.throw(_("Create at least one Branch for company {0}.").format(company))
	return branches[0]


def _leaf_category(company: str) -> str:
	row = frappe.db.sql(
		"""
		SELECT name FROM `tabFixed Asset Category`
		WHERE company = %(c)s AND IFNULL(is_group, 0) = 0
		  AND IFNULL(asset_gl_account, '') != ''
		  AND IFNULL(accumulated_depreciation_gl_account, '') != ''
		  AND IFNULL(depreciation_expense_gl_account, '') != ''
		ORDER BY name LIMIT 1
		""",
		{"c": company},
	)
	if not row:
		frappe.throw(
			_("No leaf Fixed Asset Category with GL accounts found for company {0}.").format(company)
		)
	return row[0][0]


_BAD_CREDIT_ACCOUNT_TYPES = frozenset(
	{
		"Fixed Asset",
		"Capital Work in Progress",
		"Accumulated Depreciation",
		"Depreciation",
	}
)


def _credit_account(company: str, *exclude: str) -> str:
	"""Pick a leaf credit (Cr) account for acquisition; never use category asset/dep GL rows."""
	excl = {x for x in exclude if x}

	def _first_match(filters: dict) -> str | None:
		for name in frappe.get_all(
			"GL Account",
			filters=filters,
			pluck="name",
			order_by="name asc",
			limit_page_length=200,
		):
			if name and name not in excl:
				return name
		return None

	for account_type in ("Bank", "Cash"):
		n = _first_match({"company": company, "account_type": account_type, "is_group": 0})
		if n:
			return n
	for account_type in ("Stock Received But Not Billed", "Payable", "Current Liability", "Equity"):
		n = _first_match({"company": company, "account_type": account_type, "is_group": 0})
		if n:
			return n
	for row in frappe.get_all(
		"GL Account",
		filters={"company": company, "is_group": 0},
		fields=["name", "account_type"],
		order_by="name asc",
		limit_page_length=500,
	):
		if not row.name or row.name in excl:
			continue
		if (row.account_type or "") in _BAD_CREDIT_ACCOUNT_TYPES:
			continue
		return row.name
	frappe.throw(_("No suitable leaf GL account for acquisition credit (exclude asset accounts) for company {0}.").format(company))


def _ensure_hotel_property(company: str, branch: str, property_name: str) -> str:
	if frappe.db.exists("Hotel Property", property_name):
		return property_name
	doc = frappe.get_doc(
		{
			"doctype": "Hotel Property",
			"company": company,
			"branch": branch,
			"property_name": property_name,
			"operational_status": "Operational",
			"is_active": 1,
			"total_rooms": 99,
		}
	)
	doc.insert(ignore_permissions=True)
	return doc.name


def _ensure_room(
	company: str,
	branch: str,
	hotel_property: str,
	room_number: str,
	room_type: str,
	floor_label: str | None = None,
) -> str:
	name_guess = f"{hotel_property}-{room_number}"
	if frappe.db.exists("Hotel Room", name_guess):
		return name_guess
	doc = frappe.get_doc(
		{
			"doctype": "Hotel Room",
			"company": company,
			"branch": branch,
			"hotel_property": hotel_property,
			"room_number": room_number,
			"room_type": room_type,
			"floor": floor_label or "",
			"status": "Available",
		}
	)
	doc.insert(ignore_permissions=True)
	return doc.name


def run(
	company: str | None = None,
	branch: str | None = None,
	count: int = 50,
	property_name: str = "فندق تجريبي — أصول",
	with_transfer: bool = True,
	with_rfid: bool = True,
	commit: bool = True,
):
	"""Create ``count`` demo assets distributed across admin zones and guest rooms."""
	from omnexa_fixed_assets.utils.feature_flags import is_hotel_vertical_active_for_company

	if not company:
		try:
			from omnexa_core.omnexa_core.branch_access import get_default_company

			company = get_default_company()
		except Exception:
			company = None
	if not company:
		cos = frappe.get_all("Company", pluck="name", limit=2)
		if len(cos) == 1:
			company = cos[0]
	if not company:
		frappe.throw(_("Pass company=\"...\" or set a default Company."))

	if not is_hotel_vertical_active_for_company(company):
		frappe.throw(
			_(
				"Hotel Asset Management is off for this company: set Business Activity / Industry to Hotel Assets "
				"or enable `enable_hotel_asset_management` in site_config."
			)
		)

	frappe.flags.omnexa_hotel_guard_company = company
	try:
		return _run_seed_body(
			company=company,
			branch=branch,
			count=count,
			property_name=property_name,
			with_transfer=with_transfer,
			with_rfid=with_rfid,
			commit=commit,
		)
	finally:
		frappe.flags.omnexa_hotel_guard_company = None


def _run_seed_body(
	company: str,
	count: int,
	property_name: str,
	with_transfer: bool,
	with_rfid: bool,
	commit: bool,
	branch: str | None = None,
):
	count = max(1, min(int(count), 500))
	if not branch:
		branch = _branch_for_company(company)
	category = _leaf_category(company)
	cat_gl = frappe.db.get_value(
		"Fixed Asset Category",
		category,
		["asset_gl_account", "accumulated_depreciation_gl_account", "depreciation_expense_gl_account"],
		as_dict=True,
	)
	forbid_gl = {v for v in (cat_gl or {}).values() if v}
	credit_gl = _credit_account(company, *forbid_gl)
	hp = _ensure_hotel_property(company, branch, property_name)

	# Five administrative / service "zones" + five guest rooms → spread 50 assets across 10 locations.
	admin_specs: list[tuple[str, str, str]] = [
		("ADM-01", "Service Area", "منطقة إدارية — مالية"),
		("ADM-02", "Service Area", "منطقة إدارية — موارد بشرية"),
		("ADM-03", "Service Area", "منطقة إدارية — مشتريات"),
		("ADM-04", "Service Area", "منطقة إدارية — تقنية معلومات"),
		("ADM-05", "Service Area", "منطقة إدارية — أمن"),
	]
	guest_specs: list[tuple[str, str, str]] = [
		("101", "Standard", "ضيوف — طابق 1"),
		("102", "Standard", "ضيوف — طابق 1"),
		("103", "Deluxe", "ضيوف — طابق 1"),
		("201", "Deluxe", "ضيوف — طابق 2"),
		("202", "Suite", "ضيوف — طابق 2"),
	]
	n_admin = len(admin_specs)

	room_names: list[str] = []
	for num, rtype, _floor in admin_specs:
		room_names.append(_ensure_room(company, branch, hp, num, rtype))
	for num, rtype, _floor in guest_specs:
		room_names.append(_ensure_room(company, branch, hp, num, rtype))

	n_locs = len(room_names)
	results = {"company": company, "hotel_property": hp, "assets": [], "errors": []}

	for i in range(count):
		idx = i % n_locs
		initial_room = room_names[idx]
		zone_label = admin_specs[idx][2] if idx < n_admin else guest_specs[idx - n_admin][2]

		transfer_target = room_names[(idx + 7) % n_locs]
		try:
			fa = frappe.get_doc(
				{
					"doctype": "Fixed Asset",
					"company": company,
					"branch": branch,
					"asset_name": f"أصل تجريبي فندقي {i + 1}",
					"category": category,
					"status": "draft",
					"measurement_model": "Cost Model",
					"hotel_property": hp,
					"hotel_room": initial_room,
					"hotel_zone": zone_label,
				}
			)
			fa.insert(ignore_permissions=True)

			faa = frappe.get_doc(
				{
					"doctype": "Fixed Asset Acquisition",
					"company": company,
					"branch": branch,
					"posting_date": frappe.utils.today(),
					"fixed_asset": fa.name,
					"capitalization_amount": flt(5000 + (i % 40) * 250),
					"credit_account": credit_gl,
					"remarks": "Demo seed — hotel capitalisation",
				}
			)
			faa.insert(ignore_permissions=True)
			faa.submit()

			frappe.db.set_value("Fixed Asset", fa.name, "status", "in_use", update_modified=False)

			if with_rfid:
				tag = f"DEMO-EPC-{i+1:05d}"
				frappe.db.set_value("Fixed Asset", fa.name, "rfid_tag", tag, update_modified=False)
				scan = frappe.get_doc(
					{
						"doctype": "RFID Scan Log",
						"company": company,
						"branch": branch,
						"fixed_asset": fa.name,
						"rfid_tag": tag,
						"scan_time": now_datetime(),
						"reader_device": "DEMO-GATE-01",
						"location_text": initial_room,
						"scan_result": "Seen",
						"notes": "Seed RFID scan",
					}
				)
				scan.insert(ignore_permissions=True)

			if with_transfer and transfer_target != initial_room:
				hat = frappe.get_doc(
					{
						"doctype": "Hotel Asset Transfer",
						"company": company,
						"branch": branch,
						"posting_date": frappe.utils.today(),
						"fixed_asset": fa.name,
						"from_hotel_property": hp,
						"from_hotel_room": initial_room,
						"to_hotel_property": hp,
						"to_hotel_room": transfer_target,
						"approval_status": "Approved",
						"notes": "Demo seed — transfer between admin zone / guest room",
					}
				)
				hat.insert(ignore_permissions=True)
				hat.submit()

			results["assets"].append(fa.name)
		except Exception as e:
			results["errors"].append({"index": i + 1, "error": str(e)})
			frappe.log_error(title="Hotel seed row failed", message=frappe.get_traceback())

	if results["errors"]:
		frappe.db.rollback()
		frappe.throw(frappe.as_json(results["errors"][:5], indent=2))

	if commit:
		frappe.db.commit()

	return results
