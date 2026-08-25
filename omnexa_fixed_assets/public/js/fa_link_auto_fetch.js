/* global frappe */
// Omnexa Fixed Assets — auto-fetch from Link/dropdown fields across module forms.

(function () {
	"use strict";

	const ASSET_LINK_DOCTYPES = [
		"Fixed Asset Acquisition",
		"Fixed Asset Depreciation Entry",
		"Fixed Asset Disposal",
		"Fixed Asset Transfer",
		"Fixed Asset Write-Off",
		"Fixed Asset Revaluation",
		"Fixed Asset Maintenance",
		"Fixed Asset Inspection",
		"Fixed Asset Movement Log",
		"Hotel Asset Transfer",
		"Hotel Asset Inspection",
		"Asset Work Order",
		"Asset Alert",
		"Asset Meter Reading",
		"Asset Failure Event",
		"Asset Inspection",
		"Asset Condition Snapshot",
		"Asset Reliability Trend",
		"Asset Recommendation",
		"Asset Risk Matrix",
		"Asset Relationship",
		"RFID Scan Log",
		"Insurance Policy",
		"Asset Lifecycle Wizard Session",
	];

	const ASSET_FIELD_MAP = {
		company: "company",
		branch: "branch",
		asset_owner: "asset_owner",
		category: "category",
		hotel_property: "hotel_property",
		hotel_room: "hotel_room",
		hotel_zone: "hotel_zone",
		from_hotel_property: "hotel_property",
		from_hotel_room: "hotel_room",
		functional_location: "functional_location",
		asset_display: "asset_name",
	};

	const CATEGORY_FIELD_MAP = {
		depreciation_method: "default_depreciation_method",
		useful_life_months: "default_useful_life_months",
		asset_gl_account: "asset_gl_account",
		accumulated_depreciation_gl_account: "accumulated_depreciation_gl_account",
		depreciation_expense_gl_account: "depreciation_expense_gl_account",
	};

	function scope_filters(frm) {
		const scope = frappe.omnexa_core?.view_scope?.get?.() || {};
		const filters = {};
		const company = scope.company || frm.doc.company;
		const branch = scope.view_all_branches ? null : scope.branch || frm.doc.branch;
		if (company) filters.company = company;
		if (branch) filters.branch = branch;
		return filters;
	}

	function setup_link_queries(frm) {
		const filters = scope_filters(frm);
		["fixed_asset", "asset"].forEach((field) => {
			if (frm.fields_dict[field]) {
				frm.set_query(field, () => ({ filters }));
			}
		});
		if (frm.fields_dict.category) {
			frm.set_query("category", () => ({ filters: scope_filters(frm) }));
		}
		if (frm.fields_dict.hotel_property) {
			frm.set_query("hotel_property", () => ({ filters: scope_filters(frm) }));
		}
		if (frm.fields_dict.hotel_room) {
			frm.set_query("hotel_room", () => {
				const f = { ...scope_filters(frm) };
				if (frm.doc.hotel_property) f.hotel_property = frm.doc.hotel_property;
				return { filters: f };
			});
		}
		if (frm.fields_dict.from_hotel_property) {
			frm.set_query("from_hotel_property", () => ({ filters: scope_filters(frm) }));
		}
		if (frm.fields_dict.to_hotel_property) {
			frm.set_query("to_hotel_property", () => ({ filters: scope_filters(frm) }));
		}
		if (frm.fields_dict.from_hotel_room) {
			frm.set_query("from_hotel_room", () => {
				const f = { ...scope_filters(frm) };
				if (frm.doc.from_hotel_property) f.hotel_property = frm.doc.from_hotel_property;
				return { filters: f };
			});
		}
		if (frm.fields_dict.to_hotel_room) {
			frm.set_query("to_hotel_room", () => {
				const f = { ...scope_filters(frm) };
				if (frm.doc.to_hotel_property) f.hotel_property = frm.doc.to_hotel_property;
				return { filters: f };
			});
		}
	}

	function apply_mapping(frm, source, mapping) {
		if (!source) return;
		Object.entries(mapping).forEach(([target, sourceKey]) => {
			if (!frm.fields_dict[target]) return;
			const value = source[sourceKey];
			if (value != null && value !== "" && frm.doc[target] !== value) {
				frm.set_value(target, value);
			}
		});
	}

	function sync_from_fixed_asset(frm, assetField) {
		const asset = frm.doc[assetField];
		if (!asset) return;
		frappe.call({
			method: "omnexa_fixed_assets.utils.fa_doc_autofill.get_fixed_asset_autofill",
			args: { asset },
			callback(r) {
				if (!r.message?.ok) return;
				apply_mapping(frm, r.message.asset, ASSET_FIELD_MAP);
			},
		});
	}

	function sync_from_category(frm) {
		if (!frm.doc.category) return;
		frappe.call({
			method: "omnexa_fixed_assets.utils.fa_doc_autofill.get_category_autofill",
			args: { category: frm.doc.category },
			callback(r) {
				if (!r.message?.ok) return;
				apply_mapping(frm, r.message.category, CATEGORY_FIELD_MAP);
			},
		});
	}

	function sync_hotel_property_brand(frm) {
		if (!frm.doc.hotel_property) return;
		frappe.db.get_value("Hotel Property", frm.doc.hotel_property, ["brand", "location", "company", "branch"], (r) => {
			const row = r?.message;
			if (!row) return;
			if (frm.fields_dict.brand && row.brand) frm.set_value("brand", row.brand);
			if (frm.fields_dict.location && row.location) frm.set_value("location", row.location);
			if (frm.fields_dict.company && row.company) frm.set_value("company", row.company);
			if (frm.fields_dict.branch && row.branch) frm.set_value("branch", row.branch);
		});
	}

	function register_standard_fetches(frm) {
		if (frm.fields_dict.fixed_asset && frm.fields_dict.asset_display) {
			frm.add_fetch("fixed_asset", "asset_name", "asset_display");
		}
		if (frm.fields_dict.fixed_asset && frm.fields_dict.company) {
			frm.add_fetch("fixed_asset", "company", "company");
		}
		if (frm.fields_dict.fixed_asset && frm.fields_dict.branch) {
			frm.add_fetch("fixed_asset", "branch", "branch");
		}
		if (frm.fields_dict.fixed_asset && frm.fields_dict.asset_owner) {
			frm.add_fetch("fixed_asset", "asset_owner", "asset_owner");
		}
		if (frm.fields_dict.asset && frm.fields_dict.company) {
			frm.add_fetch("asset", "company", "company");
		}
		if (frm.fields_dict.asset && frm.fields_dict.branch) {
			frm.add_fetch("asset", "branch", "branch");
		}
		if (frm.fields_dict.asset && frm.fields_dict.asset_owner) {
			frm.add_fetch("asset", "asset_owner", "asset_owner");
		}
	}

	function setup_form(frm) {
		setup_link_queries(frm);
		register_standard_fetches(frm);
	}

	function bind_doctype(doctype) {
		const handlers = {
			onload(frm) {
				setup_form(frm);
			},
			refresh(frm) {
				setup_form(frm);
			},
			fixed_asset(frm) {
				sync_from_fixed_asset(frm, "fixed_asset");
			},
			asset(frm) {
				sync_from_fixed_asset(frm, "asset");
			},
			category(frm) {
				sync_from_category(frm);
			},
			hotel_property(frm) {
				sync_hotel_property_brand(frm);
				setup_link_queries(frm);
			},
			from_hotel_property(frm) {
				setup_link_queries(frm);
			},
			to_hotel_property(frm) {
				setup_link_queries(frm);
			},
			hotel_room(frm) {
				setup_link_queries(frm);
			},
		};
		frappe.ui.form.on(doctype, handlers);
	}

	ASSET_LINK_DOCTYPES.forEach(bind_doctype);

	frappe.ui.form.on("Fixed Asset", {
		onload(frm) {
			setup_form(frm);
		},
		refresh(frm) {
			setup_form(frm);
		},
		category(frm) {
			sync_from_category(frm);
		},
		hotel_property(frm) {
			sync_hotel_property_brand(frm);
			setup_link_queries(frm);
		},
		hotel_room(frm) {
			setup_link_queries(frm);
		},
	});
})();
