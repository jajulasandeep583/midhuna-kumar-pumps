"""Everything a dealer can do, without ever opening the desk.

The desk is for KUMAR staff. A dealer in a village works from `/dealer-portal`
on a phone, so registering a sale, raising a complaint, claiming warranty and
chasing a ticket all have to be reachable from there.

Security rule for this whole module, and it is the important one: **the dealer is
never taken from the request**. It is derived from the session user via
`user_dealer()`, and every serial number, ticket and claim is checked against
that dealer's own nested-set subtree before anything is read or written. A dealer
posting somebody else's serial number gets a permission error, not their data.
"""

import frappe
from frappe import _
from frappe.utils import cint, flt, now_datetime, nowdate

from kumar_service.utils import dealer_and_descendants, user_dealer

# Statuses a dealer should read as "still with KUMAR" vs "finished".
OPEN_REQUEST_STATES = ("Open", "Assigned", "In Progress", "Awaiting Parts")
CLOSED_REQUEST_STATES = ("Resolved", "Closed", "Cancelled")

# Colour keys, resolved to CSS classes in the template. Kept server-side so the
# portal and any future screen agree on what "late" looks like.
STATUS_TONE = {
	"Open": "warn",
	"Assigned": "info",
	"In Progress": "info",
	"Awaiting Parts": "warn",
	"Resolved": "ok",
	"Closed": "mute",
	"Cancelled": "mute",
	"Draft": "mute",
	"Submitted": "info",
	"Under Investigation": "info",
	"Approved": "ok",
	"Rejected": "bad",
	"Settled": "ok",
}


def _me():
	"""The calling dealer, or a hard stop."""
	own = user_dealer()
	if not own:
		frappe.throw(
			_("Your login is not linked to a dealer record. Ask the branch office to set Portal User on your Dealer."),
			frappe.PermissionError,
		)
	return own


def _my_scope():
	return dealer_and_descendants(_me().name)


def _my_serial(serial_no):
	"""Assert this serial was sold by this dealer's network, and return its registration.

	Without this check a dealer could raise a complaint - or worse, a warranty
	claim - against a pump belonging to a different dealer entirely.
	"""
	serial_no = (serial_no or "").strip()
	if not serial_no:
		frappe.throw(_("Serial number is required"))

	reg = frappe.db.get_value(
		"Pump Registration",
		{"serial_no": serial_no, "docstatus": 1},
		["name", "dealer", "pump_model", "end_customer_name", "end_customer_mobile",
		 "sale_date", "warranty_expiry_date", "installation_address", "district"],
		as_dict=True,
	)
	if not reg:
		frappe.throw(
			_("{0} is not registered yet. Register the sale first, then a complaint can be raised against it.").format(serial_no)
		)
	if reg.dealer not in _my_scope():
		frappe.throw(
			_("{0} was not sold by your outlet, so you cannot raise a request against it.").format(serial_no),
			frappe.PermissionError,
		)
	return reg


@frappe.whitelist()
def portal_options():
	"""Select options for the portal's own forms.

	Read from the DocType meta rather than duplicated here, so a new complaint
	category added in the desk appears in the dealer's dropdown with no code
	change.
	"""

	def options(doctype, fieldname):
		field = frappe.get_meta(doctype).get_field(fieldname)
		return [o for o in (field.options or "").split("\n") if o]

	return {
		"complaint_categories": options("Service Request", "complaint_category"),
		"priorities": options("Service Request", "priority"),
		"claim_types": options("Kumar Warranty Claim", "claim_type"),
		"root_causes": options("Kumar Warranty Claim", "root_cause"),
		"applications": options("Pump Registration", "application_type"),
	}


@frappe.whitelist()
def pump_snapshot(serial_no):
	"""What the dealer needs to see before raising a complaint or a claim.

	Deliberately NOT `api.get_pump_snapshot`. That one is for the desk, and it
	reads the Serial No with `frappe.db.get_value`, which ignores permissions -
	so a dealer could type any serial at all and read another dealer's customer
	name and mobile number. This goes through `_my_serial()`, which refuses a
	pump the dealer did not sell, and returns only the fields the portal shows.
	"""
	reg = _my_serial(serial_no)

	from kumar_service.utils import warranty_status_for

	expiry = reg.warranty_expiry_date
	status = warranty_status_for(expiry, True)
	model = (
		frappe.db.get_value(
			"Pump Model", reg.pump_model, ["hp", "phase", "pump_category"], as_dict=True
		)
		or {}
	)
	return {
		"serial_no": serial_no,
		"pump_model": reg.pump_model,
		"hp": model.get("hp"),
		"phase": model.get("phase"),
		"category": model.get("pump_category"),
		"end_customer_name": reg.end_customer_name,
		"end_customer_mobile": reg.end_customer_mobile,
		"sale_date": reg.sale_date,
		"warranty_expiry_date": expiry,
		"warranty_status": status,
		"in_warranty": status in ("In Warranty", "Expiring Soon"),
		"district": reg.district,
	}


@frappe.whitelist()
def raise_complaint(serial_no, complaint_category, complaint_description, priority="Medium"):
	"""A dealer logging a customer's complaint. Submits, so the SLA clock starts."""
	reg = _my_serial(serial_no)

	if not (complaint_description or "").strip():
		frappe.throw(_("Describe what the customer is reporting"))
	if not complaint_category:
		frappe.throw(_("Choose what is wrong with the pump"))

	doc = frappe.new_doc("Service Request")
	doc.update(
		{
			"serial_no": serial_no,
			"complaint_category": complaint_category,
			"complaint_description": complaint_description,
			"priority": priority or "Medium",
			"reported_on": now_datetime(),
		}
	)
	# The controller pulls model, warranty and dealer off the serial itself, so
	# nothing here needs to be trusted from the client.
	doc.insert(ignore_permissions=True)
	doc.submit()

	return {
		"name": doc.name,
		"status": doc.status,
		"is_under_warranty": cint(doc.is_under_warranty),
		"response_due_on": doc.response_due_on,
		"resolution_due_on": doc.resolution_due_on,
		"customer": reg.end_customer_name,
		"message": (
			_("Complaint {0} is with KUMAR. A free visit is due - this pump is in warranty.").format(doc.name)
			if cint(doc.is_under_warranty)
			else _("Complaint {0} is with KUMAR. This pump is out of warranty, so the visit is chargeable.").format(doc.name)
		),
	}


@frappe.whitelist()
def raise_claim(
	serial_no,
	claim_type="Part Replacement",
	root_cause=None,
	technician_report=None,
	service_request=None,
	parts=None,
):
	"""A dealer asking KUMAR to settle a warranty claim.

	Left in Draft on purpose. A claim is money, and the workflow (Draft ->
	Submitted -> Under Investigation -> Approved/Rejected -> Settled) is what
	KUMAR's own staff drive - the dealer's job ends at lodging it with evidence.
	"""
	reg = _my_serial(serial_no)

	if service_request:
		owner_dealer = frappe.db.get_value("Service Request", service_request, "dealer")
		if owner_dealer not in _my_scope():
			frappe.throw(_("Not permitted"), frappe.PermissionError)

	doc = frappe.new_doc("Kumar Warranty Claim")
	doc.update(
		{
			"serial_no": serial_no,
			# derived, never taken from the client
			"dealer": reg.dealer,
			"claim_date": nowdate(),
			"claim_type": claim_type or "Part Replacement",
			"root_cause": root_cause or None,
			"technician_report": technician_report or None,
			"service_request": service_request or None,
		}
	)

	if parts:
		if isinstance(parts, str):
			parts = frappe.parse_json(parts)
		for row in parts or []:
			item = (row.get("item_code") or "").strip()
			if not item:
				continue
			doc.append(
				"defective_parts",
				{
					"item_code": item,
					"qty": flt(row.get("qty")) or 1,
					"defect_observed": row.get("defect_observed"),
				},
			)

	doc.insert(ignore_permissions=True)
	return {
		"name": doc.name,
		"state": doc.get("workflow_state") or "Draft",
		"claim_amount": flt(doc.claim_amount),
		"message": _("Claim {0} has been lodged. KUMAR will review it and you can follow it under My Tickets.").format(doc.name),
	}


@frappe.whitelist()
def my_tickets(kind="all", limit=60):
	"""Complaints and warranty claims in one list, newest first.

	One list because a dealer does not think in DocTypes - they think "what have
	I got open with KUMAR".
	"""
	scope = _my_scope()
	limit = cint(limit) or 60
	tickets = []

	if kind in ("all", "complaint"):
		for r in frappe.get_all(
			"Service Request",
			filters={"dealer": ["in", scope], "docstatus": ["<", 2]},
			fields=["name", "serial_no", "pump_model", "complaint_category", "status", "priority",
			        "reported_on", "end_customer_name", "end_customer_mobile", "is_under_warranty",
			        "sla_status", "resolution_due_on", "resolved_on", "assigned_technician",
			        "linked_claim"],
			order_by="reported_on desc",
			limit=limit,
		):
			tickets.append(
				{
					"kind": "complaint",
					"kind_label": _("Complaint"),
					"name": r.name,
					"serial_no": r.serial_no,
					"pump_model": r.pump_model,
					"headline": r.complaint_category,
					"status": r.status,
					"tone": STATUS_TONE.get(r.status, "mute"),
					"on": r.reported_on,
					"customer": r.end_customer_name,
					"mobile": r.end_customer_mobile,
					"free": cint(r.is_under_warranty),
					"sla_status": r.sla_status,
					"due": r.resolution_due_on,
					"closed": bool(r.resolved_on),
					"technician": r.assigned_technician,
					"linked_claim": r.linked_claim,
					"can_claim": cint(r.is_under_warranty) and not r.linked_claim,
				}
			)

	if kind in ("all", "claim"):
		for r in frappe.get_all(
			"Kumar Warranty Claim",
			filters={"dealer": ["in", scope], "docstatus": ["<", 2]},
			fields=["name", "serial_no", "pump_model", "claim_type", "workflow_state", "claim_date",
			        "claim_amount", "approved_amount", "root_cause", "settled_on", "service_request"],
			order_by="claim_date desc, creation desc",
			limit=limit,
		):
			state = r.workflow_state or "Draft"
			tickets.append(
				{
					"kind": "claim",
					"kind_label": _("Warranty Claim"),
					"name": r.name,
					"serial_no": r.serial_no,
					"pump_model": r.pump_model,
					"headline": r.claim_type,
					"status": state,
					"tone": STATUS_TONE.get(state, "mute"),
					"on": r.claim_date,
					"amount": flt(r.claim_amount),
					"approved": flt(r.approved_amount),
					"root_cause": r.root_cause,
					"closed": bool(r.settled_on),
					"service_request": r.service_request,
				}
			)

	tickets.sort(key=lambda t: str(t.get("on") or ""), reverse=True)

	open_count = sum(
		1
		for t in tickets
		if not t["closed"] and t["status"] not in CLOSED_REQUEST_STATES + ("Settled", "Rejected")
	)
	shown = tickets[:limit]
	return {
		"tickets": shown,
		"open": open_count,
		"total": len(tickets),
		# only the statuses actually present, so the filter never offers an
		# option that would return nothing
		"statuses": sorted({t["status"] for t in shown if t.get("status")}),
	}


@frappe.whitelist()
def ticket_detail(kind, name):
	"""One ticket, with whatever KUMAR has done about it so far."""
	scope = _my_scope()

	if kind == "complaint":
		doc = frappe.get_doc("Service Request", name)
		if doc.dealer not in scope:
			frappe.throw(_("Not permitted"), frappe.PermissionError)
		visits = frappe.get_all(
			"Service Visit",
			filters={"service_request": name, "docstatus": ["<", 2]},
			fields=["name", "visit_date", "visit_type", "technician", "findings", "action_taken",
			        "is_chargeable", "grand_total"],
			order_by="visit_date",
		)
		return {
			"kind": kind,
			"name": doc.name,
			"serial_no": doc.serial_no,
			"pump_model": doc.pump_model,
			"status": doc.status,
			"tone": STATUS_TONE.get(doc.status, "mute"),
			"category": doc.complaint_category,
			"description": doc.complaint_description,
			"priority": doc.priority,
			"reported_on": doc.reported_on,
			"response_due_on": doc.response_due_on,
			"first_response_on": doc.first_response_on,
			"resolution_due_on": doc.resolution_due_on,
			"resolved_on": doc.resolved_on,
			"sla_status": doc.sla_status,
			"resolution_summary": doc.resolution_summary,
			"root_cause": doc.root_cause,
			"technician": doc.assigned_technician,
			"service_centre": doc.service_centre,
			"free": cint(doc.is_under_warranty),
			"customer": doc.end_customer_name,
			"mobile": doc.end_customer_mobile,
			"visits": visits,
			"linked_claim": doc.linked_claim,
		}

	if kind == "claim":
		doc = frappe.get_doc("Kumar Warranty Claim", name)
		if doc.dealer not in scope:
			frappe.throw(_("Not permitted"), frappe.PermissionError)
		return {
			"kind": kind,
			"name": doc.name,
			"serial_no": doc.serial_no,
			"pump_model": doc.pump_model,
			"status": doc.get("workflow_state") or "Draft",
			"tone": STATUS_TONE.get(doc.get("workflow_state") or "Draft", "mute"),
			"claim_type": doc.claim_type,
			"claim_date": doc.claim_date,
			"claim_amount": flt(doc.claim_amount),
			"approved_amount": flt(doc.approved_amount),
			"root_cause": doc.root_cause,
			"technician_report": doc.technician_report,
			"remarks": doc.remarks,
			"settled_on": doc.settled_on,
			"heat_no": doc.heat_no,
			"winding_batch": doc.winding_batch,
			"service_request": doc.service_request,
			"parts": [
				{
					"item_code": p.item_code,
					"item_name": p.item_name,
					"qty": flt(p.qty),
					"rate": flt(p.rate),
					"amount": flt(p.amount),
					"defect_observed": p.defect_observed,
				}
				for p in doc.defective_parts
			],
		}

	frappe.throw(_("Unknown ticket type"))


@frappe.whitelist()
def my_contacts():
	"""Who at KUMAR this dealer should ring, and for what.

	Built from the dealer tree rather than a hardcoded list, so a dealer sees
	their OWN branch office - the one that actually handles them.
	"""
	# `user_dealer()` returns only name/lft/rgt - enough to scope a query, not
	# enough to describe an outlet - so read the record properly here.
	own = frappe.db.get_value(
		"Dealer",
		_me().name,
		["name", "dealer_name", "dealer_code", "parent_dealer", "city", "state", "gstin",
		 "is_own_outlet", "contact_person", "mobile_no"],
		as_dict=True,
	)
	contacts = []

	def add(role, dealer_name):
		if not dealer_name:
			return
		row = frappe.db.get_value(
			"Dealer",
			dealer_name,
			["dealer_name", "contact_person", "mobile_no", "landline", "email_id",
			 "address_line", "city", "state"],
			as_dict=True,
		)
		if row:
			row["role"] = role
			contacts.append(row)

	# The branch immediately above them, then the head of the tree.
	add(_("Your branch office"), own.parent_dealer)
	root = frappe.db.get_value("Dealer", {"parent_dealer": ["in", ["", None]]}, "name")
	if root and root != own.parent_dealer:
		add(_("Head office"), root)

	# Their nearest service centre, if the network has one flagged.
	centre = frappe.db.get_value(
		"Dealer", {"service_centre_flag": 1, "state": own.state, "status": "Active"}, "name"
	) or frappe.db.get_value("Dealer", {"service_centre_flag": 1, "status": "Active"}, "name")
	add(_("Service centre"), centre)

	return {
		"contacts": contacts,
		"outlet": {
			"name": own.name,
			"dealer_name": own.dealer_name,
			"code": own.dealer_code,
			"city": own.city,
			"state": own.state,
			"is_own_outlet": cint(own.is_own_outlet),
			"gstin": own.gstin,
		},
	}
