frappe.pages["fixed-assets-analytics-dashboard"].on_page_load = function (wrapper) {
	function mount() {
		if (window.omnexa_core && omnexa_core.vertical_portal && omnexa_core.vertical_portal.mountRoleDesk) {
			omnexa_core.vertical_portal.mountRoleDesk(wrapper, "omnexa_fixed_assets", "analytics-dashboard");
			return true;
		}
		return false;
	}
	if (mount()) return;
	frappe.require("/assets/omnexa_core/js/vertical-portal-desk.js", mount);
};
