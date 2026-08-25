frappe.ui.form.on("Asset Work Order", {
	refresh(frm) {
		if (frm.is_new()) return;
		if (!frappe.boot?.versions?.["erpgenex_maintenance_core"]) return;

		const open_core = (name) => frappe.set_route("Form", "Core Work Order", name);

		if (frm.doc.core_work_order) {
			frm.add_custom_button(
				__("Open Core Work Order"),
				() => open_core(frm.doc.core_work_order),
				__("Maintenance Core")
			);
			return;
		}

		frm.add_custom_button(
			__("Create / Link Core Work Order"),
			() => {
				frappe.call({
					method: "erpgenex_maintenance_core.utils.work_management.ensure_core_work_order_for_asset_wo_api",
					args: { asset_work_order: frm.doc.name },
					freeze: true,
					callback(r) {
						if (r.message?.ok && r.message.core_work_order) {
							frappe.show_alert({
								message: r.message.created
									? __("Core Work Order created")
									: __("Linked to existing Core Work Order"),
								indicator: "green",
							});
							frm.reload_doc();
							open_core(r.message.core_work_order);
						}
					},
				});
			},
			__("Maintenance Core")
		);
	},
});
