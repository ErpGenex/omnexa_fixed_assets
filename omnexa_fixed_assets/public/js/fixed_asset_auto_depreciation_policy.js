frappe.ui.form.on("Fixed Asset Auto Depreciation Policy", {
	refresh(frm) {
		if (frm.is_new() || !frm.doc.enabled) {
			return;
		}
		frm.add_custom_button(__("Run Now"), () => {
			frappe.prompt(
				[
					{
						fieldname: "posting_date",
						fieldtype: "Date",
						label: __("Posting Date"),
						reqd: 1,
						default: frappe.datetime.nowdate(),
					},
				],
				(values) => {
					if (!values) return;
					frappe.call({
						method: "omnexa_fixed_assets.api.run_auto_depreciation_policy_now",
						args: {
							policy_name: frm.doc.name,
							posting_date: values.posting_date,
						},
						freeze: true,
						freeze_message: __("Running depreciation batch..."),
						callback(r) {
							if (r.exc) return;
							const res = r.message || {};
							frappe.msgprint(
								__(
									"Batch done for {0}: Created {1}, Submitted {2}, Skipped {3}.",
									[
										res.posting_date || values.posting_date,
										res.created_count || 0,
										res.submitted_count || 0,
										res.skipped_count || 0,
									]
								)
							);
							frm.reload_doc();
						},
					});
				},
				__("Run Monthly Depreciation"),
				__("Run")
			);
		});
	},
});
