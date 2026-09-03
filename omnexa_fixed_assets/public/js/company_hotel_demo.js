// i18n:managed-catalog — bilingual/regional catalog; UI via ar.csv
// Copyright (c) 2026, Omnexa and contributors
// License: MIT. See license.txt

function setup_company_hotel_demo_buttons(frm) {
	const grp = __("أصول الفنادق — تجريبي");
	const demo_btn = (label, fn) => erpgenex.company_demo.demo_btn(frm, label, fn, grp);

	demo_btn(
		__("إنشاء 50 أصلًا (غرف + مناطق إدارية + حركات)"),
		() => {
			frappe.confirm(
				__(
					"سيتم إنشاء فندقًا تجريبيًا وغرفًا وعدد 50 أصلًا مع رسملة، وتحويلات فندقية، وسجلات RFID. قد يستغرق ذلك أكثر من دقيقة. المتابعة؟",
				),
				() => {
					frappe.call({
						method: "omnexa_fixed_assets.api.seed_hotel_demo_assets_from_company",
						args: {
							company: frm.doc.name,
							count: 50,
							with_transfer: 1,
							with_rfid: 1,
						},
						freeze: true,
						freeze_message: __("جاري إنشاء البيانات التجريبية..."),
						callback(r) {
							const m = r.message || {};
							const n = m.created_count ?? 0;
							const hp = m.hotel_property || "—";
							frappe.msgprint({
								title: __("تم"),
								indicator: "green",
								message: `تم إنشاء ${n} أصلًا تجريبيًا. الفندق: ${hp}`,
							});
						},
					});
				},
			);
		},
	);
}

frappe.ui.form.on("Company", {
	refresh(frm) {
		if (window.erpgenex?.company_demo?.register) {
			erpgenex.company_demo.register(setup_company_hotel_demo_buttons);
			erpgenex.company_demo.refresh_panel(frm);
		}
	},
});
