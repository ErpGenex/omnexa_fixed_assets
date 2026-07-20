frappe.ui.form.on("Asset Work Order", {
	refresh(frm) {
		if (frm.is_new()) return;
		if (!frappe.boot?.versions?.["erpgenex_maintenance_core"]) return;

		frm.add_custom_button(
			__("Core Work Order"),
			() => {
				frappe.route_options = {
					company: frm.doc.company,
					branch: frm.doc.branch,
					subject_doctype: "Fixed Asset",
					subject_name: frm.doc.asset,
					work_order_type: map_legacy_wo_type(frm.doc.work_order_type),
					priority: frm.doc.priority || "Medium",
					description: (frm.doc.description || "").slice(0, 280),
					service_request: "",
				};
				frappe.new_doc("Core Work Order");
			},
			__("Maintenance Core")
		);
	},
});

function map_legacy_wo_type(t) {
	const m = {
		Corrective: "Corrective",
		Preventive: "Preventive",
		Predictive: "Predictive",
		"Inspection-Triggered": "Inspection",
		Emergency: "Emergency",
	};
	return m[t] || "Corrective";
}
