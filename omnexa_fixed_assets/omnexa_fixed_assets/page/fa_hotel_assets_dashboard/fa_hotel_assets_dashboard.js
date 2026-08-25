frappe.pages["fa-hotel-assets-dashboard"].on_page_load = function (wrapper) {
	const assets = [
		"/assets/omnexa_core/css/portal_theme.css",
		"/assets/omnexa_core/css/omnexa_core.css",
		"/assets/omnexa_fixed_assets/js/hotel_assets_portal_desk.js",
	];

	frappe.require(assets, () => {
		if (window.omnexa_fixed_assets && omnexa_fixed_assets.hotel_portal && omnexa_fixed_assets.hotel_portal.mount) {
			omnexa_fixed_assets.hotel_portal.mount(wrapper);
			return;
		}
		frappe.msgprint(__("Hotel portal desk failed to load."));
	});
};
