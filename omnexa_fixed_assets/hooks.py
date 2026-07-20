app_name = "omnexa_fixed_assets"
app_title = "ErpGenEx — Fixed Assets"
app_publisher = "ErpGenEx"
app_description = "Fixed assets (IAS 16 / IFRS cost model: capitalization, depreciation, derecognition)"
app_email = "dev@erpgenex.com"
app_license = "mit"

# Apps
# ------------------

required_apps = ["omnexa_core", "omnexa_accounting", "erpgenex_maintenance_core"]

# Each item in the list will be shown as an app in the apps page
add_to_apps_screen = [
	{
		"name": "omnexa_fixed_assets",
		"logo": "/assets/omnexa_fixed_assets/logo.png",
		"title": "Fixed Assets",
		"route": "/app/fixed-assets",
	}
]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/omnexa_fixed_assets/css/omnexa_fixed_assets.css"
app_include_js = "/assets/omnexa_fixed_assets/js/fixed_assets_desk_sidebar.js"

# include js, css files in header of web template
# web_include_css = "/assets/omnexa_fixed_assets/css/omnexa_fixed_assets.css"
# web_include_js = "/assets/omnexa_fixed_assets/js/omnexa_fixed_assets.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "omnexa_fixed_assets/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
doctype_js = {
	"Fixed Asset Auto Depreciation Policy": "public/js/fixed_asset_auto_depreciation_policy.js",
	"Fixed Asset": "public/js/fixed_asset.js",
	"Asset Work Order": "public/js/asset_work_order_maintenance_core.js",
}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "omnexa_fixed_assets/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "omnexa_fixed_assets.utils.jinja_methods",
# 	"filters": "omnexa_fixed_assets.utils.jinja_filters"
# }

# Installation
# ------------

before_install = "omnexa_fixed_assets.install.enforce_supported_frappe_version"
before_migrate = "omnexa_fixed_assets.install.enforce_supported_frappe_version"
after_migrate = [
	"omnexa_fixed_assets.install.after_migrate",
	"omnexa_fixed_assets.workspace_enhancer.after_migrate",
]

# Uninstallation
# ------------

# before_uninstall = "omnexa_fixed_assets.uninstall.before_uninstall"
# after_uninstall = "omnexa_fixed_assets.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "omnexa_fixed_assets.utils.before_app_install"
# after_app_install = "omnexa_fixed_assets.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "omnexa_fixed_assets.utils.before_app_uninstall"
# after_app_uninstall = "omnexa_fixed_assets.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "omnexa_fixed_assets.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

permission_query_conditions = {
	"Fixed Asset Category": "omnexa_fixed_assets.permissions.fixed_asset_category_query_conditions",
	"Fixed Asset": "omnexa_fixed_assets.permissions.fixed_asset_query_conditions",
	"Fixed Asset Acquisition": "omnexa_fixed_assets.permissions.fixed_asset_acquisition_query_conditions",
	"Fixed Asset Depreciation Entry": "omnexa_fixed_assets.permissions.fixed_asset_depreciation_entry_query_conditions",
	"Fixed Asset Disposal": "omnexa_fixed_assets.permissions.fixed_asset_disposal_query_conditions",
	"Fixed Asset Auto Depreciation Policy": "omnexa_fixed_assets.permissions.fixed_asset_auto_depreciation_policy_query_conditions",
	"Fixed Asset Transfer": "omnexa_fixed_assets.permissions.fixed_asset_transfer_query_conditions",
	"Fixed Asset Write-Off": "omnexa_fixed_assets.permissions.fixed_asset_write_off_query_conditions",
	"Fixed Asset Revaluation": "omnexa_fixed_assets.permissions.fixed_asset_revaluation_query_conditions",
	"Fixed Asset Maintenance": "omnexa_fixed_assets.permissions.fixed_asset_maintenance_query_conditions",
	"Fixed Asset Inspection": "omnexa_fixed_assets.permissions.fixed_asset_inspection_query_conditions",
	"Fixed Asset Movement Log": "omnexa_fixed_assets.permissions.fixed_asset_movement_log_query_conditions",
	"Fixed Asset Location": "omnexa_fixed_assets.permissions.fixed_asset_location_query_conditions",
	"Asset Meter Reading": "omnexa_fixed_assets.permissions.asset_meter_reading_query_conditions",
	"Asset Failure Event": "omnexa_fixed_assets.permissions.asset_failure_event_query_conditions",
	"Asset Condition Snapshot": "omnexa_fixed_assets.permissions.asset_condition_snapshot_query_conditions",
	"Asset Reliability Trend": "omnexa_fixed_assets.permissions.asset_reliability_trend_query_conditions",
	"Asset Alert": "omnexa_fixed_assets.permissions.asset_alert_query_conditions",
	"Asset Recommendation": "omnexa_fixed_assets.permissions.asset_recommendation_query_conditions",
	"Asset Relationship": "omnexa_fixed_assets.permissions.asset_relationship_query_conditions",
	"Asset Inspection": "omnexa_fixed_assets.permissions.asset_inspection_query_conditions",
	"Asset Risk Matrix": "omnexa_fixed_assets.permissions.asset_risk_matrix_query_conditions",
	"Asset Threshold Profile": "omnexa_fixed_assets.permissions.asset_threshold_profile_query_conditions",
	"Asset Health Rule": "omnexa_fixed_assets.permissions.asset_health_rule_query_conditions",
	"Functional Location": "omnexa_fixed_assets.permissions.functional_location_query_conditions",
	"Maintenance Strategy": "omnexa_fixed_assets.permissions.maintenance_strategy_query_conditions",
	"Asset Work Order": "omnexa_fixed_assets.permissions.asset_work_order_query_conditions",
	"Asset Inspection Template": "omnexa_fixed_assets.permissions.asset_inspection_template_query_conditions",
	"Hotel Property": "omnexa_fixed_assets.permissions.hotel_property_query_conditions",
	"Hotel Room": "omnexa_fixed_assets.permissions.hotel_room_query_conditions",
	"Hotel Functional Area": "omnexa_fixed_assets.permissions.hotel_functional_area_query_conditions",
	"RFID Scan Log": "omnexa_fixed_assets.permissions.rfid_scan_log_query_conditions",
	"Hotel Asset Inspection": "omnexa_fixed_assets.permissions.hotel_asset_inspection_query_conditions",
	"Hotel Asset Transfer": "omnexa_fixed_assets.permissions.hotel_asset_transfer_query_conditions",
}

# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
	"Fixed Asset Category": {
		"before_validate": "omnexa_fixed_assets.permissions.populate_company_branch_from_user_context",
	},
	"Fixed Asset": {
		"before_validate": "omnexa_fixed_assets.permissions.populate_company_branch_from_user_context",
		"validate": "omnexa_fixed_assets.permissions.enforce_branch_access_for_doc",
	},
	"Fixed Asset Acquisition": {
		"before_validate": "omnexa_fixed_assets.permissions.populate_company_branch_from_user_context",
		"validate": "omnexa_fixed_assets.permissions.enforce_branch_access_for_doc",
	},
	"Fixed Asset Depreciation Entry": {
		"before_validate": "omnexa_fixed_assets.permissions.populate_company_branch_from_user_context",
		"validate": "omnexa_fixed_assets.permissions.enforce_branch_access_for_doc",
	},
	"Fixed Asset Disposal": {
		"before_validate": "omnexa_fixed_assets.permissions.populate_company_branch_from_user_context",
		"validate": "omnexa_fixed_assets.permissions.enforce_branch_access_for_doc",
	},
	"Fixed Asset Auto Depreciation Policy": {
		"before_validate": "omnexa_fixed_assets.permissions.populate_company_branch_from_user_context",
	},
	"Fixed Asset Transfer": {
		"before_validate": "omnexa_fixed_assets.permissions.populate_company_branch_from_user_context",
		"validate": "omnexa_fixed_assets.permissions.enforce_branch_access_for_doc",
	},
	"Fixed Asset Write-Off": {
		"before_validate": "omnexa_fixed_assets.permissions.populate_company_branch_from_user_context",
		"validate": "omnexa_fixed_assets.permissions.enforce_branch_access_for_doc",
	},
	"Fixed Asset Revaluation": {
		"before_validate": "omnexa_fixed_assets.permissions.populate_company_branch_from_user_context",
		"validate": "omnexa_fixed_assets.permissions.enforce_branch_access_for_doc",
	},
	"Fixed Asset Maintenance": {
		"before_validate": "omnexa_fixed_assets.permissions.populate_company_branch_from_user_context",
		"validate": "omnexa_fixed_assets.permissions.enforce_branch_access_for_doc",
	},
	"Fixed Asset Inspection": {
		"before_validate": "omnexa_fixed_assets.permissions.populate_company_branch_from_user_context",
		"validate": "omnexa_fixed_assets.permissions.enforce_branch_access_for_doc",
	},
	"Fixed Asset Movement Log": {
		"before_validate": "omnexa_fixed_assets.permissions.populate_company_branch_from_user_context",
		"validate": "omnexa_fixed_assets.permissions.enforce_branch_access_for_doc",
	},
	"Fixed Asset Location": {
		"before_validate": "omnexa_fixed_assets.permissions.populate_company_branch_from_user_context",
		"validate": "omnexa_fixed_assets.permissions.enforce_branch_access_for_doc",
	},
	"Asset Meter Reading": {
		"before_validate": "omnexa_fixed_assets.permissions.populate_company_branch_from_user_context",
		"validate": "omnexa_fixed_assets.permissions.enforce_branch_access_for_doc",
	},
	"Asset Failure Event": {
		"before_validate": "omnexa_fixed_assets.permissions.populate_company_branch_from_user_context",
		"validate": "omnexa_fixed_assets.permissions.enforce_branch_access_for_doc",
	},
	"Asset Condition Snapshot": {
		"before_validate": "omnexa_fixed_assets.permissions.populate_company_branch_from_user_context",
		"validate": "omnexa_fixed_assets.permissions.enforce_branch_access_for_doc",
	},
	"Asset Reliability Trend": {
		"before_validate": "omnexa_fixed_assets.permissions.populate_company_branch_from_user_context",
		"validate": "omnexa_fixed_assets.permissions.enforce_branch_access_for_doc",
	},
	"Asset Alert": {
		"before_validate": "omnexa_fixed_assets.permissions.populate_company_branch_from_user_context",
		"validate": "omnexa_fixed_assets.permissions.enforce_branch_access_for_doc",
	},
	"Asset Recommendation": {
		"before_validate": "omnexa_fixed_assets.permissions.populate_company_branch_from_user_context",
		"validate": "omnexa_fixed_assets.permissions.enforce_branch_access_for_doc",
	},
	"Asset Relationship": {
		"before_validate": "omnexa_fixed_assets.permissions.populate_company_branch_from_user_context",
		"validate": "omnexa_fixed_assets.permissions.enforce_branch_access_for_doc",
	},
	"Asset Inspection": {
		"before_validate": "omnexa_fixed_assets.permissions.populate_company_branch_from_user_context",
		"validate": "omnexa_fixed_assets.permissions.enforce_branch_access_for_doc",
	},
	"Asset Risk Matrix": {
		"before_validate": "omnexa_fixed_assets.permissions.populate_company_branch_from_user_context",
		"validate": "omnexa_fixed_assets.permissions.enforce_branch_access_for_doc",
	},
	"Asset Threshold Profile": {
		"before_validate": "omnexa_fixed_assets.permissions.populate_company_branch_from_user_context",
		"validate": "omnexa_fixed_assets.permissions.enforce_branch_access_for_doc",
	},
	"Asset Health Rule": {
		"before_validate": "omnexa_fixed_assets.permissions.populate_company_branch_from_user_context",
		"validate": "omnexa_fixed_assets.permissions.enforce_branch_access_for_doc",
	},
	"Functional Location": {
		"before_validate": "omnexa_fixed_assets.permissions.populate_company_branch_from_user_context",
		"validate": "omnexa_fixed_assets.permissions.enforce_branch_access_for_doc",
	},
	"Maintenance Strategy": {
		"before_validate": "omnexa_fixed_assets.permissions.populate_company_branch_from_user_context",
		"validate": "omnexa_fixed_assets.permissions.enforce_branch_access_for_doc",
	},
	"Asset Work Order": {
		"before_validate": "omnexa_fixed_assets.permissions.populate_company_branch_from_user_context",
		"validate": "omnexa_fixed_assets.permissions.enforce_branch_access_for_doc",
	},
	"Asset Inspection Template": {
		"before_validate": "omnexa_fixed_assets.permissions.populate_company_branch_from_user_context",
		"validate": "omnexa_fixed_assets.permissions.enforce_branch_access_for_doc",
	},
	"Hotel Property": {
		"before_validate": "omnexa_fixed_assets.permissions.populate_company_branch_from_user_context",
		"validate": "omnexa_fixed_assets.permissions.enforce_branch_access_for_doc",
	},
	"Hotel Room": {
		"before_validate": "omnexa_fixed_assets.permissions.populate_company_branch_from_user_context",
		"validate": "omnexa_fixed_assets.permissions.enforce_branch_access_for_doc",
	},
	"Hotel Functional Area": {
		"before_validate": "omnexa_fixed_assets.permissions.populate_company_branch_from_user_context",
		"validate": "omnexa_fixed_assets.permissions.enforce_branch_access_for_doc",
	},
	"RFID Scan Log": {
		"before_validate": "omnexa_fixed_assets.permissions.populate_company_branch_from_user_context",
		"validate": "omnexa_fixed_assets.permissions.enforce_branch_access_for_doc",
	},
	"Hotel Asset Inspection": {
		"before_validate": "omnexa_fixed_assets.permissions.populate_company_branch_from_user_context",
		"validate": "omnexa_fixed_assets.permissions.enforce_branch_access_for_doc",
	},
	"Hotel Asset Transfer": {
		"before_validate": "omnexa_fixed_assets.permissions.populate_company_branch_from_user_context",
		"validate": "omnexa_fixed_assets.permissions.enforce_branch_access_for_doc",
	},
	"Company": {
		"after_insert": "omnexa_fixed_assets.install.company_on_save_sync_hotel_vertical",
		"on_update": "omnexa_fixed_assets.install.company_on_save_sync_hotel_vertical",
	},
}

# Scheduled Tasks
# ---------------

scheduler_events = {
	"hourly": ["omnexa_fixed_assets.tasks.run_hourly_condition_monitoring_jobs"],
	"daily": [
		"omnexa_fixed_assets.tasks.run_daily_reliability_jobs",
		"omnexa_fixed_assets.tasks.run_daily_hotel_asset_jobs",
	],
	"monthly": ["omnexa_fixed_assets.tasks.run_month_end_depreciation_jobs"],
}

# Testing
# -------

# before_tests = "omnexa_fixed_assets.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "omnexa_fixed_assets.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
override_doctype_dashboards = {
	"Hotel Property": ["omnexa_fixed_assets.dashboard.hotel_dashboards.extend_hotel_property_dashboard"],
	"Hotel Room": ["omnexa_fixed_assets.dashboard.hotel_dashboards.extend_hotel_room_dashboard"],
}

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["omnexa_fixed_assets.utils.before_request"]
# after_request = ["omnexa_fixed_assets.utils.after_request"]

# Job Events
# ----------
# before_job = ["omnexa_fixed_assets.utils.before_job"]
# after_job = ["omnexa_fixed_assets.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"omnexa_fixed_assets.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# Translation
# ------------
# List of apps whose translatable strings should be excluded from this app's translations.
# ignore_translatable_strings_from = []

