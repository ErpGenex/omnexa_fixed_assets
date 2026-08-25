# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

"""Seed demo hotel fixed assets with full property layout (rooms, kitchen, zones).

Creates:
  - Hotel Functional Areas (lobby, kitchen, restaurant, spa, engineering, …)
  - Guest rooms across multiple floors (default 6 × 20 = 120)
  - Back-of-house placement units (kitchen, laundry, storage, admin, …)
  - Fixed assets linked to ``hotel_property``, ``hotel_room``, ``hotel_functional_area``

CLI::

	bench --site YOUR_SITE execute omnexa_fixed_assets.scripts.seed_hotel_asset_movements.run \\
	  --kwargs '{"company": "My Company", "branch": "Head Office", "count": 200}'
"""

from __future__ import annotations

from dataclasses import dataclass

import frappe
from frappe import _
from frappe.utils import flt, now_datetime


@dataclass(frozen=True)
class FunctionalAreaSpec:
	code: str
	name_ar: str
	area_type: str


@dataclass(frozen=True)
class LocationSpec:
	room_number: str
	room_type: str
	zone_label: str
	functional_area_code: str
	floor: str = ""
	wing: str = ""


# Master functional areas for a complete hotel asset demo.
FUNCTIONAL_AREA_SPECS: tuple[FunctionalAreaSpec, ...] = (
	FunctionalAreaSpec("LOBBY", "البهو والاستقبال", "Lobby"),
	FunctionalAreaSpec("GUEST", "غرف الضيوف", "Guest Rooms"),
	FunctionalAreaSpec("REST", "المطعم الرئيسي", "Restaurant"),
	FunctionalAreaSpec("KITCHEN", "المطبخ الرئيسي", "Back of House"),
	FunctionalAreaSpec("KITCHEN2", "مطبخ الحلويات والمعجنات", "Back of House"),
	FunctionalAreaSpec("LAUNDRY", "المغسلة والتنظيف", "Back of House"),
	FunctionalAreaSpec("STORAGE", "المخازن والتموين", "Back of House"),
	FunctionalAreaSpec("SPA", "السبا والعناية", "Spa"),
	FunctionalAreaSpec("POOL", "المسبح ومرافق الترفيه", "Swimming Pool"),
	FunctionalAreaSpec("ENG", "الورشة الهندسية", "Engineering Zone"),
	FunctionalAreaSpec("PARK", "المواقف والمرآب", "Parking"),
	FunctionalAreaSpec("ADMIN", "الإدارة والمكاتب", "Service Area"),
)

# Back-of-house and public-area placement units (Hotel Room records).
SERVICE_LOCATION_SPECS: tuple[LocationSpec, ...] = (
	LocationSpec("KITCHEN-MAIN", "Service Area", "المطبخ الرئيسي — خط ساخن", "KITCHEN", "0", "BOH"),
	LocationSpec("KITCHEN-COLD", "Service Area", "المطبخ — التحضير البارد", "KITCHEN", "0", "BOH"),
	LocationSpec("KITCHEN-PASTRY", "Service Area", "مطبخ الحلويات والمعجنات", "KITCHEN2", "0", "BOH"),
	LocationSpec("REST-DINING", "Service Area", "قاعة الطعام الرئيسية", "REST", "0", "F&B"),
	LocationSpec("REST-BUFFET", "Service Area", "بوفيه الإفطار", "REST", "0", "F&B"),
	LocationSpec("LOBBY-MAIN", "Service Area", "البهو الرئيسي", "LOBBY", "0", "Public"),
	LocationSpec("LOBBY-RECEP", "Service Area", "مكتب الاستقبال", "LOBBY", "0", "Public"),
	LocationSpec("LAUNDRY-01", "Service Area", "غرفة الغسيل المركزية", "LAUNDRY", "0", "BOH"),
	LocationSpec("STORAGE-01", "Service Area", "مخزن التموين الجاف", "STORAGE", "0", "BOH"),
	LocationSpec("STORAGE-02", "Service Area", "مخزن المفروشات", "STORAGE", "0", "BOH"),
	LocationSpec("ENG-BOILER", "Service Area", "غرفة الغلايات", "ENG", "0", "BOH"),
	LocationSpec("ENG-HVAC", "Service Area", "غرفة التكييف المركزي", "ENG", "0", "BOH"),
	LocationSpec("ENG-ELEC", "Service Area", "غرفة الكهرباء الرئيسية", "ENG", "0", "BOH"),
	LocationSpec("SPA-01", "Service Area", "السبا — منطقة العلاج", "SPA", "0", "Leisure"),
	LocationSpec("POOL-01", "Service Area", "المسبح — منطقة الضيوف", "POOL", "0", "Leisure"),
	LocationSpec("PARK-B1", "Service Area", "مواقف الطابق B1", "PARK", "B1", "Parking"),
	LocationSpec("PARK-B2", "Service Area", "مواقف الطابق B2", "PARK", "B2", "Parking"),
	LocationSpec("ADM-FIN", "Service Area", "الإدارة — المالية", "ADMIN", "0", "Admin"),
	LocationSpec("ADM-HR", "Service Area", "الإدارة — الموارد البشرية", "ADMIN", "0", "Admin"),
	LocationSpec("ADM-IT", "Service Area", "الإدارة — تقنية المعلومات", "ADMIN", "0", "Admin"),
	LocationSpec("ADM-SEC", "Service Area", "الإدارة — الأمن", "ADMIN", "0", "Admin"),
	LocationSpec("ADM-PUR", "Service Area", "الإدارة — المشتريات", "ADMIN", "0", "Admin"),
)


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


def _ensure_hotel_property(
	company: str,
	branch: str,
	property_name: str,
	number_of_floors: int,
	total_rooms: int,
) -> str:
	if frappe.db.exists("Hotel Property", property_name):
		frappe.db.set_value(
			"Hotel Property",
			property_name,
			{
				"number_of_floors": number_of_floors,
				"total_rooms": total_rooms,
				"property_type": "Hotel",
				"star_rating": "5 Star",
				"operational_status": "Operational",
				"is_active": 1,
			},
			update_modified=False,
		)
		return property_name

	doc = frappe.get_doc(
		{
			"doctype": "Hotel Property",
			"company": company,
			"branch": branch,
			"property_name": property_name,
			"property_type": "Hotel",
			"star_rating": "5 Star",
			"number_of_floors": number_of_floors,
			"total_rooms": total_rooms,
			"operational_status": "Operational",
			"is_active": 1,
		}
	)
	doc.insert(ignore_permissions=True)
	return doc.name


def _ensure_functional_area(
	company: str,
	branch: str,
	hotel_property: str,
	spec: FunctionalAreaSpec,
) -> str:
	name_guess = f"{hotel_property}-{spec.code}"
	if frappe.db.exists("Hotel Functional Area", name_guess):
		frappe.db.set_value(
			"Hotel Functional Area",
			name_guess,
			{
				"area_name": spec.name_ar,
				"area_type": spec.area_type,
				"is_active": 1,
			},
			update_modified=False,
		)
		return name_guess

	doc = frappe.get_doc(
		{
			"doctype": "Hotel Functional Area",
			"company": company,
			"branch": branch,
			"hotel_property": hotel_property,
			"area_code": spec.code,
			"area_name": spec.name_ar,
			"area_type": spec.area_type,
			"is_active": 1,
		}
	)
	doc.insert(ignore_permissions=True)
	return doc.name


def _ensure_room(
	company: str,
	branch: str,
	hotel_property: str,
	spec: LocationSpec,
	functional_area_map: dict[str, str],
) -> str:
	name_guess = f"{hotel_property}-{spec.room_number}"
	fa_link = functional_area_map.get(spec.functional_area_code)
	values = {
		"room_type": spec.room_type,
		"floor": spec.floor or "",
		"wing": spec.wing or "",
		"hotel_functional_area": fa_link,
		"status": "Available",
	}
	if frappe.db.exists("Hotel Room", name_guess):
		frappe.db.set_value("Hotel Room", name_guess, values, update_modified=False)
		return name_guess

	doc = frappe.get_doc(
		{
			"doctype": "Hotel Room",
			"company": company,
			"branch": branch,
			"hotel_property": hotel_property,
			"hotel_functional_area": fa_link,
			"room_number": spec.room_number,
			"room_type": spec.room_type,
			"floor": spec.floor or "",
			"wing": spec.wing or "",
			"status": "Available",
		}
	)
	doc.insert(ignore_permissions=True)
	return doc.name


def _guest_room_type(floor: int, room_index: int) -> str:
	if floor >= 5:
		return "Suite"
	if floor >= 3:
		return "Deluxe"
	return "Standard"


def _build_guest_room_specs(guest_floors: int, guest_rooms_per_floor: int) -> list[LocationSpec]:
	specs: list[LocationSpec] = []
	for floor in range(1, guest_floors + 1):
		for idx in range(1, guest_rooms_per_floor + 1):
			room_number = f"{floor}{idx:02d}"
			specs.append(
				LocationSpec(
					room_number=room_number,
					room_type=_guest_room_type(floor, idx),
					zone_label=f"غرفة ضيوف — طابق {floor}",
					functional_area_code="GUEST",
					floor=str(floor),
					wing="East" if idx <= guest_rooms_per_floor // 2 else "West",
				)
			)
	return specs


def _ensure_hotel_layout(
	company: str,
	branch: str,
	hotel_property: str,
	guest_floors: int,
	guest_rooms_per_floor: int,
) -> dict:
	functional_area_map: dict[str, str] = {}
	for fa_spec in FUNCTIONAL_AREA_SPECS:
		functional_area_map[fa_spec.code] = _ensure_functional_area(
			company, branch, hotel_property, fa_spec
		)

	location_specs: list[LocationSpec] = list(SERVICE_LOCATION_SPECS)
	location_specs.extend(_build_guest_room_specs(guest_floors, guest_rooms_per_floor))

	locations: list[dict] = []
	for spec in location_specs:
		room_name = _ensure_room(company, branch, hotel_property, spec, functional_area_map)
		locations.append(
			{
				"name": room_name,
				"room_number": spec.room_number,
				"zone_label": spec.zone_label,
				"functional_area": functional_area_map.get(spec.functional_area_code),
				"functional_area_code": spec.functional_area_code,
				"floor": spec.floor,
			}
		)

	return {
		"functional_areas": functional_area_map,
		"locations": locations,
		"guest_rooms": guest_floors * guest_rooms_per_floor,
		"service_locations": len(SERVICE_LOCATION_SPECS),
	}


def run(
	company: str | None = None,
	branch: str | None = None,
	count: int = 50,
	property_name: str = "فندق تجريبي — أصول",
	guest_floors: int = 6,
	guest_rooms_per_floor: int = 20,
	with_transfer: bool = True,
	with_rfid: bool = True,
	commit: bool = True,
):
	"""Create demo hotel layout and ``count`` assets distributed across all locations."""
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

	guest_floors = max(1, min(int(guest_floors), 20))
	guest_rooms_per_floor = max(1, min(int(guest_rooms_per_floor), 50))

	frappe.flags.omnexa_hotel_guard_company = company
	user = frappe.session.user
	prev_view_all = frappe.defaults.get_user_default("omnexa_view_all_branches", user)
	prev_view_branch = frappe.defaults.get_user_default("omnexa_view_branch", user)
	frappe.defaults.set_user_default("omnexa_view_all_branches", 1, user)
	frappe.defaults.set_user_default("omnexa_view_branch", "", user)
	try:
		return _run_seed_body(
			company=company,
			branch=branch,
			count=count,
			property_name=property_name,
			guest_floors=guest_floors,
			guest_rooms_per_floor=guest_rooms_per_floor,
			with_transfer=with_transfer,
			with_rfid=with_rfid,
			commit=commit,
		)
	finally:
		frappe.flags.omnexa_hotel_guard_company = None
		frappe.defaults.set_user_default("omnexa_view_all_branches", prev_view_all or 0, user)
		frappe.defaults.set_user_default("omnexa_view_branch", prev_view_branch or "", user)


def _run_seed_body(
	company: str,
	count: int,
	property_name: str,
	guest_floors: int,
	guest_rooms_per_floor: int,
	with_transfer: bool,
	with_rfid: bool,
	commit: bool,
	branch: str | None = None,
):
	count = max(1, min(int(count), 500))
	if not branch:
		branch = _branch_for_company(company)

	total_guest_rooms = guest_floors * guest_rooms_per_floor
	category = _leaf_category(company)
	cat_gl = frappe.db.get_value(
		"Fixed Asset Category",
		category,
		["asset_gl_account", "accumulated_depreciation_gl_account", "depreciation_expense_gl_account"],
		as_dict=True,
	)
	forbid_gl = {v for v in (cat_gl or {}).values() if v}
	credit_gl = _credit_account(company, *forbid_gl)

	hp = _ensure_hotel_property(
		company,
		branch,
		property_name,
		number_of_floors=guest_floors,
		total_rooms=total_guest_rooms,
	)
	layout = _ensure_hotel_layout(
		company,
		branch,
		hp,
		guest_floors=guest_floors,
		guest_rooms_per_floor=guest_rooms_per_floor,
	)
	locations = layout["locations"]
	n_locs = len(locations)

	results = {
		"company": company,
		"branch": branch,
		"hotel_property": hp,
		"functional_areas_created": len(layout["functional_areas"]),
		"guest_rooms_created": layout["guest_rooms"],
		"service_locations_created": layout["service_locations"],
		"total_locations": n_locs,
		"assets": [],
		"errors": [],
	}

	for i in range(count):
		loc = locations[i % n_locs]
		initial_room = loc["name"]
		transfer_loc = locations[(i + 17) % n_locs]
		transfer_target = transfer_loc["name"]

		try:
			fa = frappe.get_doc(
				{
					"doctype": "Fixed Asset",
					"company": company,
					"branch": branch,
					"asset_name": f"أصل فندقي — {loc['room_number']} — {i + 1}",
					"category": category,
					"status": "draft",
					"measurement_model": "Cost Model",
					"hotel_property": hp,
					"hotel_room": initial_room,
					"hotel_functional_area": loc["functional_area"],
					"hotel_zone": loc["zone_label"],
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
						"location_text": loc["room_number"],
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
						"notes": f"Demo seed — transfer to {transfer_loc['room_number']}",
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
