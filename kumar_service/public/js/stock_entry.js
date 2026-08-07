frappe.ui.form.on("Stock Entry", {
	refresh(frm) {
		if (frm.doc.docstatus === 1 && frm.doc.purpose === "Manufacture") {
			frm.add_custom_button(__("Genealogy of Produced Units"), () => {
				const serials = [];
				(frm.doc.items || []).forEach((row) => {
					if (row.t_warehouse && !row.s_warehouse && row.serial_no) {
						serials.push(...row.serial_no.split("\n").filter(Boolean));
					}
				});
				if (!serials.length) {
					frappe.msgprint(__("No serialised units on this entry."));
					return;
				}
				frappe.call({
					method: "kumar_service.traceability.trace_backward",
					args: { serial_no: serials[0] },
					callback: (r) => kumar.show_genealogy(r.message),
				});
			});
		}

		if (frm.doc.docstatus === 0) {
			frm.add_custom_button(__("Scan Serial / Batch"), () => {
				new frappe.ui.Scanner({
					dialog: true,
					multiple: true,
					on_scan(data) {
						const value = (data && (data.decodedText || data.result)) || "";
						frappe.show_alert({ message: __("Scanned {0}", [value]), indicator: "green" });
					},
				});
			});
		}
	},
});
