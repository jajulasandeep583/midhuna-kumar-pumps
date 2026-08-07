frappe.ui.form.on("Sales Invoice", {
	refresh(frm) {
		if (frm.doc.docstatus === 1 && frm.doc.custom_warranty_note) {
			frm.dashboard.clear_headline();
			frm.dashboard.set_headline(
				`<span class="indicator-pill green">${frappe.utils.escape_html(
					frm.doc.custom_warranty_note
				)}</span>`
			);
		}
	},

	custom_auto_register_pumps(frm) {
		if (frm.doc.custom_auto_register_pumps && !frm.doc.custom_dealer) {
			frappe.msgprint(
				__("Set the Dealer as well, otherwise there is nobody to register the pumps against.")
			);
		}
	},
});
