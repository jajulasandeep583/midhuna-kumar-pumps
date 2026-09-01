"""Whitelisted API.

Every entry point checks permissions explicitly, and any `dealer` value is
re-derived from the session user rather than trusted from the client.
"""

from urllib.parse import quote

import frappe
from frappe import _
from frappe.utils import add_days, cint, flt, getdate, now_datetime, nowdate

from kumar_service.permissions import has_full_access
from kumar_service.traceability import trace_backward, trace_forward  # noqa: F401 (re-exported)
from kumar_service.utils import (
	CH_DIRECT,
	dealer_and_descendants,
	qr_base64,
	qr_url_for,
	sale_channel_for,
	setting,
	user_dealer,
	validate_mobile,
	warranty_months_for,
	warranty_status_for,
)


@frappe.whitelist()
def get_pump_snapshot(serial_no):
	"""Everything the desk needs about one physical pump, in one round trip."""
	frappe.has_permission("Serial No", "read", throw=True)

	sn = frappe.db.get_value("Serial No", serial_no, "*", as_dict=True)
	if not sn:
		frappe.throw(_("Serial number {0} not found").format(serial_no), frappe.DoesNotExistError)

	# The doctype check above says "may this user read serials at all"; it does
	# NOT say "may they read THIS one". Everything below is fetched with
	# frappe.db, which applies no row scoping whatever - so a dealer granted the
	# doctype could otherwise read any pump in the network through this endpoint.
	# The document check is what confines them to their own tree; staff roles
	# have full access and pass it unchanged.
	if not frappe.has_permission("Serial No", doc=serial_no, ptype="read"):
		frappe.throw(
			_("{0} was not sold by your outlet.").format(serial_no), frappe.PermissionError
		)

	model = {}
	if sn.get("custom_pump_model"):
		model = frappe.db.get_value(
			"Pump Model",
			sn.custom_pump_model,
			["model_code", "pump_category", "hp", "kw", "phase", "rpm", "delivery_size_inch",
			 "bis_standard", "warranty_months", "impeller_material"],
			as_dict=True,
		) or {}

	expiry = sn.get("custom_warranty_expiry_date")
	registered = bool(sn.get("custom_registration"))
	status = warranty_status_for(expiry, registered)
	days_left = (getdate(expiry) - getdate(nowdate())).days if expiry else None

	history = frappe.get_all(
		"Service Request",
		filters={"serial_no": serial_no, "docstatus": ["<", 2]},
		fields=["name", "reported_on", "complaint_category", "status", "root_cause",
			"is_under_warranty", "sla_status"],
		order_by="reported_on desc",
		limit=5,
	)

	window = cint(setting("repeat_failure_window_days", 90))
	repeat = frappe.db.count(
		"Service Request",
		{
			"serial_no": serial_no,
			"docstatus": ["<", 2],
			"reported_on": [">=", add_days(nowdate(), -window)],
		},
	)

	return {
		"serial_no": sn.name,
		"item_code": sn.item_code,
		"item_name": frappe.db.get_value("Item", sn.item_code, "item_name"),
		"pump_model": sn.get("custom_pump_model"),
		"model_code": model.get("model_code"),
		"category": model.get("pump_category"),
		"hp": model.get("hp"),
		"kw": model.get("kw"),
		"phase": model.get("phase"),
		"rpm": model.get("rpm"),
		"impeller_material": model.get("impeller_material"),
		"bis_standard": model.get("bis_standard"),
		"manufacturing_date": sn.get("custom_manufacturing_date"),
		"qc_status": sn.get("custom_qc_status"),
		"test_certificate": sn.get("custom_test_certificate"),
		"heat_no": sn.get("custom_heat_no"),
		"winding_batch": sn.get("custom_winding_batch"),
		"rotor_batch": sn.get("custom_rotor_batch"),
		"work_order": sn.get("custom_work_order"),
		"dealer": sn.get("custom_dealer"),
		"registration": sn.get("custom_registration"),
		"sale_date": sn.get("custom_sale_date"),
		"end_customer_name": sn.get("custom_end_customer_name"),
		"end_customer_mobile": sn.get("custom_end_customer_mobile"),
		"installation_pincode": sn.get("custom_installation_pincode"),
		"warranty_expiry_date": expiry,
		"warranty_status": status,
		"is_under_warranty": status in ("In Warranty", "Expiring Soon"),
		"is_registered": registered,
		"days_remaining": days_left,
		"service_history": history,
		"open_complaints": sum(
			1 for h in history if h.status in ("Open", "Assigned", "In Progress", "Awaiting Parts")
		),
		"is_repeat_failure": repeat > 1,
		"qr_url": qr_url_for(serial_no),
	}


@frappe.whitelist()
def get_qr_image(serial_no):
	frappe.has_permission("Serial No", "read", throw=True)
	return {"serial_no": serial_no, "url": qr_url_for(serial_no), "image": qr_base64(qr_url_for(serial_no))}


@frappe.whitelist()
def register_pump(**kwargs):
	"""Create and submit a Pump Registration. Dealer comes from the session."""
	frappe.has_permission("Pump Registration", "create", throw=True)

	data = frappe._dict(kwargs)
	if not data.serial_no:
		frappe.throw(_("Serial number is required"))

	dealer = data.dealer
	own = user_dealer()
	if own:
		dealer = own.name  # never trust a posted dealer for a dealer login
	if not dealer:
		frappe.throw(_("No dealer could be determined for your login"))

	validate_mobile(data.end_customer_mobile, _("Customer Mobile"))

	channel = sale_channel_for(dealer)
	sales_invoice = data.sales_invoice
	if channel == CH_DIRECT and not sales_invoice:
		# our own branch sold it, so the customer's invoice is one of ours -
		# find it rather than asking a counter clerk to type an invoice number
		sales_invoice = kumar_invoice_for(data.serial_no)
		if not sales_invoice:
			frappe.throw(
				_("{0} is a KUMAR outlet, so this sale needs the KUMAR invoice behind it, "
					"and none was found for serial {1}. Raise the invoice first.").format(
					dealer, data.serial_no
				)
			)

	reg = frappe.new_doc("Pump Registration")
	reg.update(
		{
			"serial_no": data.serial_no,
			"dealer": dealer,
			# derived from who owns the outlet, never from the form - a dealer
			# must not be able to claim their sale was on a KUMAR invoice
			"sale_channel": channel,
			"sale_date": data.sale_date or nowdate(),
			"invoice_no": data.invoice_no,
			"dealer_invoice_date": data.dealer_invoice_date or data.sale_date or nowdate(),
			"sales_invoice": sales_invoice,
			"end_customer_name": data.end_customer_name,
			"end_customer_mobile": data.end_customer_mobile,
			"end_customer_email": data.end_customer_email,
			"installation_address": data.installation_address,
			"state": data.state,
			"district": data.district,
			"pincode": data.pincode,
			"application_type": data.application_type or "Agriculture",
			"borewell_depth_ft": flt(data.borewell_depth_ft),
			"static_water_level_ft": flt(data.static_water_level_ft),
			"registration_source": data.registration_source or "Dealer Portal",
		}
	)
	reg.insert()
	reg.submit()
	return {
		"name": reg.name,
		"warranty_expiry_date": reg.warranty_expiry_date,
		"warranty_card_no": reg.warranty_card_no,
		"warranty_months": reg.warranty_months,
		"pump_model": reg.pump_model,
		"certificate_url": certificate_url(reg.name),
	}


def certificate_url(registration, lang=None):
	"""The printable warranty certificate for a registration.

	`format=` picks our A5 card rather than the standard form, and `no_letterhead=0`
	keeps the KUMAR header on it - this is the sheet the customer keeps.

	`lang` carries the reader's language into the print view, so a dealer working
	in Telugu hands over a Telugu certificate rather than an English one.
	"""
	url = (
		"/printview?doctype=Pump%20Registration"
		f"&name={quote(registration)}"
		"&format=KUMAR%20Warranty%20Certificate"
		"&no_letterhead=0&trigger_print=1"
	)
	lang = lang or getattr(frappe.local, "lang", None)
	if lang and lang != "en":
		url += f"&_lang={quote(lang)}"
	return url


@frappe.whitelist()
def portal_serial_lookup(serial_no):
	"""What the dealer portal needs to know before it will take a registration.

	The dealer types a serial and nothing else. Everything that follows - the
	model, and above all the warranty WE will honour - is ours to state, so it
	is read here rather than posted from the browser.
	"""
	serial_no = (serial_no or "").strip()
	if not serial_no:
		frappe.throw(_("Enter a serial number"))

	sn = frappe.db.get_value(
		"Serial No",
		serial_no,
		["name", "item_code", "custom_pump_model", "custom_manufacturing_date",
			"custom_qc_status", "custom_dealer"],
		as_dict=True,
	)
	if not sn:
		frappe.throw(_("Serial {0} is not a KUMAR pump we have any record of.").format(serial_no))

	existing = frappe.db.get_value(
		"Pump Registration",
		{"serial_no": serial_no, "docstatus": 1},
		["name", "end_customer_name", "sale_date", "warranty_expiry_date"],
		as_dict=True,
	)

	months = warranty_months_for(sn.custom_pump_model, sn.item_code)
	model = (
		frappe.db.get_value("Pump Model", sn.custom_pump_model, ["hp", "phase"], as_dict=True)
		if sn.custom_pump_model
		else None
	)

	own = user_dealer()
	return {
		"serial_no": sn.name,
		"pump_model": sn.custom_pump_model,
		"hp": model.hp if model else None,
		"phase": model.phase if model else None,
		"manufacturing_date": sn.custom_manufacturing_date,
		"qc_status": sn.custom_qc_status,
		# stated by us, not negotiable, and shown to the dealer before they commit
		"warranty_months": months,
		"already_registered": bool(existing),
		"existing": existing,
		# the invoice this pump left our factory on. For one of our own branches
		# that IS the customer's invoice; for a dealer it is the one that sold
		# the pump to them, and their own invoice is still to come.
		"kumar_invoice": kumar_invoice_for(serial_no),
		"sale_channel": sale_channel_for(own.name if own else None),
	}


def kumar_invoice_for(serial_no):
	"""The submitted Sales Invoice that dispatched this serial, if there is one.

	Two ways a serial reaches an invoice line, so look for both: the v15+
	bundle, and the plain text field left behind by `use_serial_batch_fields`.
	"""
	row = frappe.db.sql(
		"""
		select sbb.voucher_no
		from `tabSerial and Batch Entry` sbe
		join `tabSerial and Batch Bundle` sbb on sbb.name = sbe.parent
		join `tabSales Invoice` si on si.name = sbb.voucher_no
		where sbe.serial_no = %s and sbb.voucher_type = 'Sales Invoice' and si.docstatus = 1
		limit 1
		""",
		(serial_no,),
	)
	if row:
		return row[0][0]

	row = frappe.db.sql(
		"""
		select sii.parent
		from `tabSales Invoice Item` sii
		join `tabSales Invoice` si on si.name = sii.parent
		where si.docstatus = 1
		  and concat('\n', sii.serial_no, '\n') like %s
		limit 1
		""",
		(f"%\n{serial_no}\n%",),
	)
	return row[0][0] if row else None


@frappe.whitelist()
def my_registrations(limit=50):
	"""This dealer's registrations, each with the certificate to hand over."""
	own = user_dealer()
	if not own:
		return []

	rows = frappe.get_all(
		"Pump Registration",
		filters={"dealer": ["in", dealer_and_descendants(own.name)], "docstatus": 1},
		fields=["name", "serial_no", "pump_model", "end_customer_name", "end_customer_mobile",
			"sale_date", "warranty_expiry_date", "invoice_no"],
		order_by="sale_date desc, creation desc",
		limit=cint(limit),
	)
	for r in rows:
		r["certificate_url"] = certificate_url(r["name"])
	return rows


@frappe.whitelist()
def create_service_request(serial_no, complaint_category, complaint_description, priority="Medium"):
	frappe.has_permission("Service Request", "create", throw=True)

	sr = frappe.new_doc("Service Request")
	sr.update(
		{
			"serial_no": serial_no,
			"complaint_category": complaint_category,
			"complaint_description": complaint_description,
			"priority": priority,
			"reported_on": now_datetime(),
		}
	)
	sr.insert()
	sr.submit()
	return {
		"name": sr.name,
		"response_due_on": sr.response_due_on,
		"resolution_due_on": sr.resolution_due_on,
		"is_under_warranty": sr.is_under_warranty,
	}


@frappe.whitelist()
def get_dealer_dashboard_data(dealer=None):
	"""Counts for the dealer's number cards, scoped to their own tree."""
	own = user_dealer()
	if own:
		dealer = own.name
	elif not has_full_access():
		frappe.throw(_("Not permitted"), frappe.PermissionError)

	from kumar_service.utils import dealer_and_descendants

	scope = dealer_and_descendants(dealer) if dealer else None
	reg_filter = {"docstatus": 1}
	sr_filter = {"docstatus": ["<", 2]}
	claim_filter = {"docstatus": ["<", 2]}
	if scope:
		reg_filter["dealer"] = ["in", scope]
		sr_filter["dealer"] = ["in", scope]
		claim_filter["dealer"] = ["in", scope]

	month_start = getdate(nowdate()).replace(day=1)
	regs_mtd = dict(reg_filter, sale_date=[">=", month_start])

	open_sr = dict(sr_filter, status=["in", ["Open", "Assigned", "In Progress", "Awaiting Parts"]])

	expiring = {
		"custom_warranty_expiry_date": ["between", [nowdate(), add_days(nowdate(), 30)]],
	}
	if scope:
		expiring["custom_dealer"] = ["in", scope]

	return {
		"dealer": dealer,
		"registrations_mtd": frappe.db.count("Pump Registration", regs_mtd),
		"registrations_total": frappe.db.count("Pump Registration", reg_filter),
		"open_complaints": frappe.db.count("Service Request", open_sr),
		"claims_pending": frappe.db.count(
			"Kumar Warranty Claim",
			dict(claim_filter, workflow_state=["in", ["Pending Review", "Under Investigation"]]),
		),
		"warranty_expiring_30d": frappe.db.count("Serial No", expiring),
	}


@frappe.whitelist()
def bulk_generate_serials(item_code, qty, work_order=None, pump_model=None):
	"""Pre-generate serials for a production run. Large runs go to the queue."""
	frappe.has_permission("Serial No", "create", throw=True)
	qty = cint(qty)
	if qty < 1:
		frappe.throw(_("Quantity must be at least 1"))

	if qty > 200:
		frappe.enqueue(
			"kumar_service.api._generate_serials",
			queue="long",
			item_code=item_code,
			qty=qty,
			work_order=work_order,
			pump_model=pump_model,
		)
		return {"queued": True, "qty": qty}

	return {"queued": False, "serials": _generate_serials(item_code, qty, work_order, pump_model)}


def _generate_serials(item_code, qty, work_order=None, pump_model=None):
	from kumar_service.setup.demo import make_serial  # shared generator

	made = []
	for _i in range(cint(qty)):
		made.append(make_serial(item_code, work_order=work_order, pump_model=pump_model))
	frappe.db.commit()
	return made


@frappe.whitelist()
def validate_serial_format(serial_no):
	from kumar_service.utils import validate_serial_format as _check

	return {"serial_no": serial_no, "valid": _check(serial_no)}
