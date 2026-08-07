// The Serial No form is the counter's lookup screen: identity, warranty, ancestry.

frappe.ui.form.on("Serial No", {
	refresh(frm) {
		if (frm.is_new()) return;

		kumar.fetch_snapshot(frm, frm.doc.name).then((snap) => {
			if (snap) kumar.warranty_banner(frm, snap);
		});

		frm.add_custom_button(__("Trace Genealogy"), () => {
			frappe.call({
				method: "kumar_service.traceability.trace_backward",
				args: { serial_no: frm.doc.name },
				callback: (r) => kumar.show_genealogy(r.message),
			});
		});

		if (frm.doc.custom_test_certificate) {
			frm.add_custom_button(__("Test Certificate"), () => {
				frappe.set_route("Form", "Pump Test Certificate", frm.doc.custom_test_certificate);
			});
		}

		frm.add_custom_button(__("Service History"), () => {
			frappe.set_route("List", "Service Request", { serial_no: frm.doc.name });
		});

		if (frm.doc.custom_registration) {
			frm.add_custom_button(__("Warranty Certificate"), () => {
				window.open(
					`/printview?doctype=Pump%20Registration&name=${encodeURIComponent(
						frm.doc.custom_registration
					)}&format=KUMAR%20Warranty%20Certificate&no_letterhead=1`
				);
			});
		} else {
			frm.add_custom_button(__("Register Sale"), () => {
				frappe.new_doc("Pump Registration", { serial_no: frm.doc.name });
			});
		}

		frm.add_custom_button(__("Show QR"), () => {
			frappe.call({
				method: "kumar_service.api.get_qr_image",
				args: { serial_no: frm.doc.name },
				callback: (r) => {
					const d = r.message || {};
					new frappe.ui.Dialog({
						title: __("QR for {0}", [frm.doc.name]),
						fields: [
							{
								fieldtype: "HTML",
								options: `<div style="text-align:center">
									${d.image ? `<img src="${d.image}" style="width:220px;height:220px">` : ""}
									<p style="margin-top:10px;font-size:12px;color:#666">${d.url || ""}</p>
									<p style="font-size:12px">${__("Print this on the nameplate. A phone camera opens the warranty page.")}</p>
								</div>`,
							},
						],
					}).show();
				},
			});
		});
	},
});
