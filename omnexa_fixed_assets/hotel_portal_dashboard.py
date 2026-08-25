# Copyright (c) 2026, Omnexa and contributors
# License: MIT

"""Hotel Asset Management director portal — same payload shape as pharma role desks."""

from __future__ import annotations

import frappe
from frappe.utils import fmt_money, flt


def _t(en: str, ar: str) -> dict:
	return {"label_en": en, "label_ar": ar}


def _menu_item(en: str, ar: str, route: str, icon: str = "📄") -> dict:
	return {"label_en": en, "label_ar": ar, "route": route, "icon": icon}


def _section(en: str, ar: str, items: list[dict]) -> dict:
	return {"title_en": en, "title_ar": ar, "items": items}


def _kpi(en: str, ar: str, value, icon: str = "📊") -> dict:
	return {"title_en": en, "title_ar": ar, "title": en, "value": value, "icon": icon}


def _action(en: str, ar: str, route: str, icon: str = "⚡") -> dict:
	return {"label_en": en, "label_ar": ar, "route": route, "icon": icon}


from urllib.parse import quote

from frappe.desk.utils import slug as desk_slug


def _report_route(name: str) -> str:
	return f"/app/query-report/{quote(name)}"


def _dt_route(doctype: str) -> str:
	return f"/app/{desk_slug(doctype)}"


def _list_route(doctype: str) -> str:
	return _dt_route(doctype)


def _new_route(doctype: str) -> str:
	return f"{_dt_route(doctype)}/new"


HOTEL_SIDEBAR = [
	{
		"label_en": "Hotel Assets Dashboard",
		"label_ar": "لوحة إدارة أصول الفنادق",
		"route": "/app/fa-hotel-assets-dashboard",
		"icon": "🏨",
	},
	{
		"label_en": "Executive Dashboard",
		"label_ar": "لوحة تنفيذية",
		"route": "/app/fa-executive-dashboard",
		"icon": "📊",
	},
	{
		"label_en": "Asset Scan PWA",
		"label_ar": "مسح الأصول",
		"route": "/app/fa-asset-scan-pwa",
		"icon": "📱",
	},
	{
		"label_en": "Fixed Assets Workspace",
		"label_ar": "مساحة الأصول الثابتة",
		"route": "/app/fixed-assets",
		"icon": "📁",
	},
]

HOTEL_MENU_SECTIONS = [
	_section(
		"Hotel Setup",
		"إعداد الفندق",
		[
			_menu_item("Hotel Property", "فندق / عقار", _dt_route("Hotel Property"), "🏨"),
			_menu_item("Functional Area", "منطقة وظيفية", _dt_route("Hotel Functional Area"), "🗺️"),
			_menu_item("Hotel Room", "غرفة / موقع", _dt_route("Hotel Room"), "🛏️"),
			_menu_item("Fixed Asset", "سجل الأصول", _dt_route("Fixed Asset"), "📦"),
		],
	),
	_section(
		"Hotel Operations",
		"عمليات الفندق",
		[
			_menu_item("RFID Scan Log", "سجل RFID", _dt_route("RFID Scan Log"), "📡"),
			_menu_item("Hotel Asset Transfer", "نقل أصل فندقي", _dt_route("Hotel Asset Transfer"), "🔄"),
			_menu_item("Hotel Asset Inspection", "فحص أصل فندقي", _dt_route("Hotel Asset Inspection"), "🔍"),
			_menu_item("Asset Work Order", "أمر عمل", _dt_route("Asset Work Order"), "🔧"),
		],
	),
	_section(
		"Maintenance & Quality",
		"الصيانة والجودة",
		[
			_menu_item("Fixed Asset Maintenance", "صيانة الأصول", _dt_route("Fixed Asset Maintenance"), "🛠️"),
			_menu_item("Asset Failure Event", "أعطال", _dt_route("Asset Failure Event"), "⚠️"),
			_menu_item("Asset Alert", "تنبيهات", _dt_route("Asset Alert"), "🔔"),
			_menu_item("Fixed Asset Inspection", "فحص الأصول", _dt_route("Fixed Asset Inspection"), "✅"),
		],
	),
	_section(
		"Finance & Valuation",
		"المالية والتقييم",
		[
			_menu_item("Acquisition", "رسملة", _new_route("Fixed Asset Acquisition"), "💰"),
			_menu_item("Depreciation Entry", "إهلاك", _list_route("Fixed Asset Depreciation Entry"), "📉"),
			_menu_item("Asset Valuation Report", "تقييم الأصول", _report_route("Asset Valuation Report"), "📊"),
			_menu_item("NBV by Category", "صافي القيمة", _report_route("Fixed Asset NBV by Category"), "📈"),
			_menu_item("Hotel NBV by Property", "صافي القيمة حسب العقار", _report_route("Hotel NBV by Property"), "🏨"),
			_menu_item("IAS 16 Disclosure", "IAS 16 — إفصاح", _report_route("IAS 16 Disclosure Schedule"), "📑"),
			_menu_item("Hotel IAS 16 Disclosure", "IAS 16 — الفندق", _report_route("Hotel IAS 16 Disclosure Schedule"), "📑"),
			_menu_item("Depreciation Schedule", "جدول الإهلاك", _report_route("Asset Depreciation Schedule"), "📉"),
		],
	),
	_section(
		"Hotel Reports",
		"تقارير الفندق",
		[
			_menu_item("Hotel Asset Register", "سجل أصول الفندق", _report_route("Hotel Asset Register"), "📋"),
			_menu_item("Assets by Room", "أصول حسب الغرفة", _report_route("Assets by Room"), "🛏️"),
			_menu_item("Assets by Floor", "أصول حسب الطابق", _report_route("Hotel Assets by Floor"), "🏢"),
			_menu_item("Operational Status", "الحالة التشغيلية", _report_route("Hotel Operational Asset Status"), "⚙️"),
			_menu_item("Inspection Summary", "ملخص الفحوصات", _report_route("Hotel Inspection Summary"), "📋"),
			_menu_item("Missing Assets", "أصول مفقودة", _report_route("Missing Assets"), "❓"),
			_menu_item("Unscanned Assets", "غير الممسوحة", _report_route("Unscanned Assets"), "📡"),
			_menu_item("Movement History", "سجل النقل", _report_route("Hotel Movement History"), "🔄"),
			_menu_item("Hotel Depreciation", "إهلاك الفندق", _report_route("Hotel Asset Depreciation"), "📉"),
		],
	),
]


def _money(company: str, amount) -> str:
	currency = frappe.get_cached_value("Company", company, "default_currency")
	if not currency:
		currency = frappe.defaults.get_global_default("currency") or "USD"
	return fmt_money(flt(amount), currency=currency)


def _branch_filter_sql(branch: str | None) -> tuple[str, dict]:
	if not branch:
		return "", {}
	return "AND fa.branch = %(branch)s", {"branch": branch}


def build_hotel_portal_context(company: str, branch: str | None = None) -> dict:
	"""Build director-style portal payload scoped to navbar company/branch."""
	extra, branch_params = _branch_filter_sql(branch)
	params = {"company": company, **branch_params}
	hotel_filter = f"fa.company = %(company)s AND IFNULL(fa.hotel_property, '') != '' {extra}"

	total_assets = frappe.db.sql(f"SELECT COUNT(*) FROM `tabFixed Asset` fa WHERE {hotel_filter}", params)[0][0]
	total_nbv = frappe.db.sql(
		f"SELECT IFNULL(SUM(fa.net_book_value), 0) FROM `tabFixed Asset` fa WHERE {hotel_filter}", params
	)[0][0]
	rfid_tagged = frappe.db.sql(
		f"SELECT COUNT(*) FROM `tabFixed Asset` fa WHERE {hotel_filter} AND IFNULL(fa.rfid_tag, '') != ''",
		params,
	)[0][0]

	prop_filters = {"company": company}
	if branch:
		prop_filters["branch"] = branch
	hotel_properties = frappe.db.count("Hotel Property", prop_filters)
	hotel_rooms = frappe.db.count("Hotel Room", {"company": company})
	functional_areas = frappe.db.count("Hotel Functional Area", {"company": company})
	open_inspections = frappe.db.count("Hotel Asset Inspection", {"company": company, "docstatus": 0})
	open_transfers = frappe.db.count("Hotel Asset Transfer", {"company": company, "docstatus": 0})
	missing_scans = max(0, int(total_assets) - int(rfid_tagged))

	work_queue = frappe.db.sql(
		f"""
		SELECT fa.name, fa.asset_name, fa.hotel_room, fa.status
		FROM `tabFixed Asset` fa
		WHERE {hotel_filter}
		ORDER BY fa.modified DESC
		LIMIT 8
		""",
		params,
		as_dict=True,
	)
	pending_inspections = frappe.get_all(
		"Hotel Asset Inspection",
		fields=["name", "hotel_property", "condition_status"],
		filters={"company": company, "docstatus": 0},
		limit=8,
		order_by="modified desc",
	)
	pending_transfers = frappe.get_all(
		"Hotel Asset Transfer",
		fields=["name", "fixed_asset", "to_hotel_room"],
		filters={"company": company, "docstatus": 0},
		limit=8,
		order_by="modified desc",
	)

	by_status = frappe.db.sql(
		f"""
		SELECT IFNULL(fa.status, '') AS status, COUNT(*) AS count
		FROM `tabFixed Asset` fa WHERE {hotel_filter}
		GROUP BY fa.status ORDER BY count DESC LIMIT 8
		""",
		params,
		as_dict=True,
	)
	by_property = frappe.db.sql(
		f"""
		SELECT fa.hotel_property, COUNT(*) AS count
		FROM `tabFixed Asset` fa WHERE {hotel_filter}
		GROUP BY fa.hotel_property ORDER BY count DESC LIMIT 8
		""",
		params,
		as_dict=True,
	)
	by_floor = frappe.db.sql(
		f"""
		SELECT IFNULL(hr.floor, '') AS floor, COUNT(*) AS count
		FROM `tabFixed Asset` fa
		LEFT JOIN `tabHotel Room` hr ON hr.name = fa.hotel_room
		WHERE {hotel_filter}
		GROUP BY hr.floor ORDER BY count DESC LIMIT 8
		""",
		params,
		as_dict=True,
	)
	by_area = frappe.db.sql(
		f"""
		SELECT IFNULL(fa.hotel_functional_area, '') AS functional_area, COUNT(*) AS count
		FROM `tabFixed Asset` fa WHERE {hotel_filter}
		GROUP BY fa.hotel_functional_area ORDER BY count DESC LIMIT 8
		""",
		params,
		as_dict=True,
	)

	return {
		"title_en": "Hotel Asset Management",
		"title_ar": "إدارة أصول الفنادق",
		"role_en": "Asset Director",
		"role_ar": "مدير أصول الفنادق",
		"workcenter_route": "/app/fixed-assets",
		"sidebar_portals": HOTEL_SIDEBAR,
		"menu_sections": HOTEL_MENU_SECTIONS,
		"dashboard": {
			"kpis": [
				_kpi("Total Hotel Assets", "إجمالي أصول الفندق", total_assets, "🏨"),
				_kpi("Total NBV", "إجمالي صافي القيمة", _money(company, total_nbv), "💰"),
				_kpi("Hotel Properties", "الفنادق / العقارات", hotel_properties, "🏢"),
				_kpi("Rooms & Locations", "الغرف والمواقع", hotel_rooms, "🛏️"),
				_kpi("Functional Areas", "المناطق الوظيفية", functional_areas, "🗺️"),
				_kpi("RFID Tagged", "مُعلَّمة RFID", rfid_tagged, "📡"),
				_kpi("Not Scanned", "غير ممسوحة", missing_scans, "⚠️"),
				_kpi("Open Inspections", "فحوصات مفتوحة", open_inspections, "🔍"),
			],
			"work_queue": [
				{"name": r.name, "description": f"{r.asset_name or r.name} · {r.hotel_room or '-'} · {r.status or ''}"}
				for r in work_queue
			],
			"pending_tasks": [
				{"name": r.name, "description": f"{r.name} · {r.hotel_property or ''} · {r.condition_status or ''}"}
				for r in pending_inspections
			],
			"approvals": [
				{"name": r.name, "description": f"{r.fixed_asset or ''} → {r.to_hotel_room or ''}"}
				for r in pending_transfers
			],
			"quick_actions": [
				_action("Hotel Property", "فندق / عقار", _new_route("Hotel Property"), "🏨"),
				_action("Hotel Room", "غرفة / موقع", _new_route("Hotel Room"), "🛏️"),
				_action("New Fixed Asset", "أصل جديد", _new_route("Fixed Asset"), "➕"),
				_action("RFID Scan", "مسح RFID", _new_route("RFID Scan Log"), "📡"),
				_action("Asset Transfer", "نقل أصل", _new_route("Hotel Asset Transfer"), "🔄"),
				_action("Inspection", "فحص", _new_route("Hotel Asset Inspection"), "🔍"),
				_action("Assets by Room", "أصول حسب الغرفة", _report_route("Assets by Room"), "📊"),
				_action("Scan PWA", "مسح ميداني", "/app/fa-asset-scan-pwa", "📱"),
			],
			"charts": [
				{"id": "by-status", "title_en": "Assets by Status", "title_ar": "الأصول حسب الحالة", "type": "bar"},
				{"id": "by-floor", "title_en": "Assets by Floor", "title_ar": "الأصول حسب الطابق", "type": "bar"},
				{"id": "nbv-trend", "title_en": "NBV Overview", "title_ar": "نظرة على صافي القيمة", "type": "line"},
			],
			"breakdowns": {
				"by_status": by_status,
				"by_property": by_property,
				"by_floor": by_floor,
				"by_functional_area": by_area,
			},
			"stats": {
				"open_transfers": open_transfers,
			},
		},
	}
