frappe.ui.form.on("Pump Registration", {
	refresh(frm) {
		kumar.scan_serial(frm);

		if (frm.doc.docstatus === 1) {
			frm.add_custom_button(__("Print Warranty Certificate"), () => {
				window.open(
					`/printview?doctype=Pump%20Registration&name=${encodeURIComponent(
						frm.doc.name
					)}&format=KUMAR%20Warranty%20Certificate&no_letterhead=1`
				);
			}).addClass("btn-primary");

			frm.add_custom_button(__("Raise Complaint"), () => {
				frappe.new_doc("Service Request", { serial_no: frm.doc.serial_no });
			});
		}

		if (frm.doc.serial_no) show_banner(frm);
	},

	serial_no(frm) {
		if (!frm.doc.serial_no) return;
		kumar.fetch_snapshot(frm, frm.doc.serial_no).then((snap) => {
			if (!snap) return;
			if (snap.is_registered && frm.is_new()) {
				frappe.msgprint({
					title: __("Already Registered"),
					indicator: "red",
					message: __("Serial {0} is already registered ({1}).", [
						snap.serial_no,
						snap.registration,
					]),
				});
			}
			if (snap.qc_status && snap.qc_status !== "Passed") {
				frappe.msgprint({
					title: __("QC Not Passed"),
					indicator: "orange",
					message: __("This unit's QC status is {0}. Check with the plant before selling it.", [
						snap.qc_status,
					]),
				});
			}
			show_banner(frm);
		});
	},
});

function show_banner(frm) {
	if (!frm.doc.warranty_expiry_date) return;
	frm.dashboard.clear_headline();
	frm.dashboard.set_headline(
		`<span class="indicator-pill blue" style="font-size:13px">${__(
			"Warranty {0} months - valid upto {1}",
			[frm.doc.warranty_months, frappe.datetime.str_to_user(frm.doc.warranty_expiry_date)]
		)}</span>`
	);
}
