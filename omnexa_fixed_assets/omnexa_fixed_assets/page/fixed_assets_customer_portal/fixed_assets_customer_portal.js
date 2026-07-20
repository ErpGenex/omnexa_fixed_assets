frappe.pages["fixed-assets-customer-portal"].on_page_load = function (wrapper) {
	if (window.omnexa_core && omnexa_core.vertical_portal && omnexa_core.vertical_portal.mountRoleDesk) {
		omnexa_core.vertical_portal.mountRoleDesk(wrapper, "omnexa_fixed_assets", "customer-portal");
		return;
	}
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("fixed-assets-customer-portal"),
		single_column: true,
	});
	$(page.body).html("<p class=\"text-muted\">" + __("Load omnexa_core vertical portal desk") + "</p>");
};
