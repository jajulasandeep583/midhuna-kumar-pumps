frappe.ui.form.on("Pump Test Certificate", {
	refresh(frm) {
		kumar.scan_serial(frm);

		if (frm.doc.docstatus === 1) {
			frm.add_custom_button(__("Print Certificate"), () => {
				window.open(
					`/printview?doctype=Pump%20Test%20Certificate&name=${encodeURIComponent(
						frm.doc.name
					)}&format=KUMAR%20Pump%20Test%20Certificate&no_letterhead=1`
				);
			}).addClass("btn-primary");

			frm.dashboard.clear_headline();
			const pass = frm.doc.overall_result === "Pass";
			frm.dashboard.set_headline(
				`<span class="indicator-pill ${pass ? "green" : "red"}">${__(
					"QC {0} - serial marked {1}",
					[frm.doc.overall_result, pass ? "Passed" : frm.doc.overall_result]
				)}</span>`
			);
		}

		if (frm.is_new() && !(frm.doc.duty_points || []).length) {
			frm.add_custom_button(__("Add Standard Duty Points"), () => {
				[6, 12, 20].forEach((head) => {
					const row = frm.add_child("duty_points");
					row.head_m = head;
					row.is_duty_point = head === 12 ? 1 : 0;
				});
				frm.refresh_field("duty_points");
			});
		}
	},
});
