/* global frappe */
// Hotel fixed-assets: auto-fill brand/location and cascade link fields from parent records.

(function () {
	"use strict";

	const HOTEL_DOCTYPES = new Set([
		"Hotel Property",
		"Hotel Room",
		"Hotel Functional Area",
		"Hotel Asset Transfer",
		"Hotel Asset Inspection",
		"Fixed Asset",
	]);

	const EMPTY_QUERY = { filters: { name: ["in", []] } };

	function scope_filters(frm) {
		const scope = frappe.omnexa_core?.view_scope?.get?.() || {};
		const filters = {};
		const company = scope.company || frm.doc.company;
		const branch = scope.view_all_branches ? null : scope.branch || frm.doc.branch;
		if (company) filters.company = company;
		if (branch) filters.branch = branch;
		return filters;
	}

	function property_filters(frm, property_field) {
		const property = frm.doc[property_field];
		if (!property) return scope_filters(frm);
		return { ...scope_filters(frm), hotel_property: property };
	}

	function apply_branch_brand_location(frm) {
		if (!frm.doc.branch) return;
		frappe.call({
			method: "omnexa_fixed_assets.utils.hotel_field_defaults.get_branch_hotel_defaults",
			args: { branch: frm.doc.branch },
			callback(r) {
				const defaults = (r && r.message) || {};
				if (defaults.brand && !(frm.doc.brand || "").trim()) {
					frm.set_value("brand", defaults.brand);
				}
				if (defaults.location && !(frm.doc.location || "").trim()) {
					frm.set_value("location", defaults.location);
				}
			},
		});
	}

	function sync_from_hotel_property(frm) {
		if (!frm.doc.hotel_property) return;
		frappe.db.get_value(
			"Hotel Property",
			frm.doc.hotel_property,
			["brand", "location"],
			(r) => {
				const row = r && r.message;
				if (!row) return;
				if (frm.fields_dict.brand && !(frm.doc.brand || "").trim() && row.brand) {
					frm.set_value("brand", row.brand);
				}
				if (frm.fields_dict.location && !(frm.doc.location || "").trim() && row.location) {
					frm.set_value("location", row.location);
				}
			}
		);
	}

	function sync_from_fixed_asset(frm, mapping) {
		if (!frm.doc.fixed_asset) return;
		frappe.db.get_value(
			"Fixed Asset",
			frm.doc.fixed_asset,
			["hotel_property", "hotel_room", "company", "branch"],
			(r) => {
				const asset = r && r.message;
				if (!asset) return;
				Object.entries(mapping).forEach(([target, source]) => {
					if (!frm.fields_dict[target]) return;
					const value = asset[source];
					if (value && frm.doc[target] !== value) {
						frm.set_value(target, value);
					}
				});
			}
		);
	}

	function sync_fixed_asset_from_room(frm) {
		if (!frm.doc.hotel_room) return;
		frappe.db.get_value(
			"Hotel Room",
			frm.doc.hotel_room,
			["hotel_property", "hotel_functional_area", "wing", "company", "branch"],
			(r) => {
				const room = r && r.message;
				if (!room) return;
				if (room.hotel_property && frm.fields_dict.hotel_property) {
					frm.set_value("hotel_property", room.hotel_property);
				}
				if (room.hotel_functional_area && frm.fields_dict.hotel_functional_area) {
					frm.set_value("hotel_functional_area", room.hotel_functional_area);
				}
				if (room.wing && frm.fields_dict.hotel_zone && !(frm.doc.hotel_zone || "").trim()) {
					frm.set_value("hotel_zone", room.wing);
				}
			}
		);
	}

	function setup_hotel_link_queries(frm) {
		if (frm.fields_dict.hotel_property) {
			frm.set_query("hotel_property", () => ({ filters: scope_filters(frm) }));
		}
		if (frm.fields_dict.from_hotel_property) {
			frm.set_query("from_hotel_property", () => ({ filters: scope_filters(frm) }));
		}
		if (frm.fields_dict.to_hotel_property) {
			frm.set_query("to_hotel_property", () => ({ filters: scope_filters(frm) }));
		}
		if (frm.fields_dict.hotel_room) {
			frm.set_query("hotel_room", () => {
				const filters = property_filters(frm, "hotel_property");
				return Object.keys(filters).length ? { filters } : EMPTY_QUERY;
			});
		}
		if (frm.fields_dict.from_hotel_room) {
			frm.set_query("from_hotel_room", () => {
				const filters = property_filters(frm, "from_hotel_property");
				return Object.keys(filters).length ? { filters } : EMPTY_QUERY;
			});
		}
		if (frm.fields_dict.to_hotel_room) {
			frm.set_query("to_hotel_room", () => {
				const filters = property_filters(frm, "to_hotel_property");
				return Object.keys(filters).length ? { filters } : EMPTY_QUERY;
			});
		}
		if (frm.fields_dict.hotel_functional_area) {
			frm.set_query("hotel_functional_area", () => {
				const filters = property_filters(frm, "hotel_property");
				return Object.keys(filters).length ? { filters } : EMPTY_QUERY;
			});
		}
		if (frm.fields_dict.fixed_asset) {
			frm.set_query("fixed_asset", () => ({ filters: scope_filters(frm) }));
		}
	}

	function setup_form(frm) {
		if (!HOTEL_DOCTYPES.has(frm.doctype)) return;
		setup_hotel_link_queries(frm);

		if (frm.doctype === "Hotel Property") {
			apply_branch_brand_location(frm);
		}
		if (["Hotel Room", "Hotel Functional Area"].includes(frm.doctype)) {
			sync_from_hotel_property(frm);
		}
		if (frm.doctype === "Hotel Asset Transfer") {
			sync_from_fixed_asset(frm, {
				from_hotel_property: "hotel_property",
				from_hotel_room: "hotel_room",
			});
		}
		if (frm.doctype === "Hotel Asset Inspection") {
			sync_from_fixed_asset(frm, {
				hotel_property: "hotel_property",
				hotel_room: "hotel_room",
			});
		}
		if (frm.doctype === "Fixed Asset") {
			sync_fixed_asset_from_room(frm);
		}
	}

	frappe.ui.form.on("Hotel Property", {
		onload: setup_form,
		refresh: setup_form,
		branch() {
			apply_branch_brand_location(cur_frm);
		},
	});

	frappe.ui.form.on("Hotel Room", {
		onload: setup_form,
		refresh: setup_form,
		hotel_property() {
			sync_from_hotel_property(cur_frm);
			setup_hotel_link_queries(cur_frm);
		},
	});

	frappe.ui.form.on("Hotel Functional Area", {
		onload: setup_form,
		refresh: setup_form,
		hotel_property() {
			sync_from_hotel_property(cur_frm);
		},
	});

	frappe.ui.form.on("Hotel Asset Transfer", {
		onload: setup_form,
		refresh: setup_form,
		fixed_asset() {
			sync_from_fixed_asset(cur_frm, {
				from_hotel_property: "hotel_property",
				from_hotel_room: "hotel_room",
			});
		},
		from_hotel_property() {
			setup_hotel_link_queries(cur_frm);
		},
		to_hotel_property() {
			setup_hotel_link_queries(cur_frm);
		},
	});

	frappe.ui.form.on("Hotel Asset Inspection", {
		onload: setup_form,
		refresh: setup_form,
		fixed_asset() {
			sync_from_fixed_asset(cur_frm, {
				hotel_property: "hotel_property",
				hotel_room: "hotel_room",
			});
		},
		hotel_property() {
			setup_hotel_link_queries(cur_frm);
		},
	});

	frappe.ui.form.on("Fixed Asset", {
		onload: setup_form,
		refresh: setup_form,
		hotel_property() {
			setup_hotel_link_queries(cur_frm);
			if (cur_frm.doc.hotel_property && cur_frm.doc.hotel_room) {
				frappe.db.get_value("Hotel Room", cur_frm.doc.hotel_room, "hotel_property", (r) => {
					if (r?.message && r.message !== cur_frm.doc.hotel_property) {
						cur_frm.set_value("hotel_room", "");
					}
				});
			}
		},
		hotel_room() {
			sync_fixed_asset_from_room(cur_frm);
		},
	});
})();
