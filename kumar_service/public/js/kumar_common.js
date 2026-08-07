// Shared helpers: the warranty banner and the serial scanner both get used on
// more than one form, so they live here.

window.kumar = window.kumar || {};

kumar.warranty_banner = function (frm, snap) {
	if (!snap) return;

	const d = snap.days_remaining;
	let colour = "gray";
	let text = __("NOT REGISTERED - ask the dealer to complete registration first");

	if (snap.is_registered && snap.warranty_expiry_date) {
		const expiry = frappe.datetime.str_to_user(snap.warranty_expiry_date);
		if (snap.warranty_status === "Expired") {
			colour = "red";
			text = __("WARRANTY EXPIRED on {0} - this service is chargeable", [expiry]);
		} else if (snap.warranty_status === "Expiring Soon") {
			colour = "orange";
			text = __("EXPIRING SOON - {0} days left (expires {1})", [d, expiry]);
		} else {
			colour = "green";
			text = __("IN WARRANTY - expires {0} ({1} days left)", [expiry, d]);
		}
	}

	frm.dashboard.clear_headline();
	frm.dashboard.set_headline(
		`<span class="indicator-pill ${colour}" style="font-size:13px">${text}</span>`
	);

	if (snap.is_repeat_failure) {
		frm.dashboard.add_comment(
			__("Repeat failure: this pump has been reported more than once recently."),
			"orange",
			true
		);
	}
};

kumar.history_html = function (snap) {
	const rows = snap.service_history || [];
	if (!rows.length) {
		return `<div class="text-muted">${__("No previous service requests for this pump.")}</div>`;
	}
	const body = rows
		.map(
			(r) => `<tr>
				<td><a href="/app/service-request/${r.name}">${r.name}</a></td>
				<td>${frappe.datetime.str_to_user(r.reported_on)}</td>
				<td>${frappe.utils.escape_html(r.complaint_category || "")}</td>
				<td>${frappe.utils.escape_html(r.root_cause || "-")}</td>
				<td>${frappe.utils.escape_html(r.status || "")}</td>
			</tr>`
		)
		.join("");
	return `<table class="table table-bordered table-sm">
		<thead><tr>
			<th>${__("Request")}</th><th>${__("Reported")}</th><th>${__("Complaint")}</th>
			<th>${__("Root Cause")}</th><th>${__("Status")}</th>
		</tr></thead><tbody>${body}</tbody></table>`;
};

kumar.scan_serial = function (frm, fieldname = "serial_no") {
	frm.add_custom_button(__("Scan Serial"), () => {
		new frappe.ui.Scanner({
			dialog: true,
			multiple: false,
			on_scan(data) {
				let value = (data && (data.decodedText || data.result)) || "";
				// the QR encodes a URL, so pull the serial back out of it
				const match = value.match(/[?&]sn=([^&]+)/);
				if (match) value = decodeURIComponent(match[1]);
				frm.set_value(fieldname, value);
			},
		});
	});
};

kumar.fetch_snapshot = function (frm, serial_no) {
	if (!serial_no) return Promise.resolve(null);
	return frappe
		.call({ method: "kumar_service.api.get_pump_snapshot", args: { serial_no } })
		.then((r) => r.message);
};
