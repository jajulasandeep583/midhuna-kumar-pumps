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
from kumar_service.utils import EXPIRING_SOON_DAYS
from frappe.utils import add_days, cint, flt, getdate, now_datetime, nowdate

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
		"expiring_soon_days": EXPIRING_SOON_DAYS,
		"request_types": options("Service Request", "custom_request_type")
			or ["Complaint", "Installation", "Paid Service", "Spare Part", "Enquiry"],
	}


@frappe.whitelist()
def my_summary():
	"""The counts the dealer's sidebar and home screen read.

	One call, because the rail needs three numbers and a name and firing four
	requests to paint a sidebar is how a page ends up feeling slow on a phone
	on a village connection.
	"""
	me = _me()
	scope = _my_scope()
	today = getdate(nowdate())
	soon = add_days(today, EXPIRING_SOON_DAYS)

	pumps = frappe.get_all(
		"Pump Registration",
		filters={"dealer": ["in", scope], "docstatus": 1},
		fields=["warranty_expiry_date"],
		limit_page_length=0,
	)
	in_warranty = expiring = expired = 0
	for r in pumps:
		expiry = getdate(r.warranty_expiry_date) if r.warranty_expiry_date else None
		if not expiry:
			continue
		if expiry < today:
			expired += 1
		elif expiry <= soon:
			expiring += 1
		else:
			in_warranty += 1

	open_requests = frappe.db.count(
		"Service Request",
		{"dealer": ["in", scope], "status": ["not in", ("Resolved", "Closed", "Cancelled")],
		 "docstatus": ["<", 2]},
	)
	open_claims = frappe.db.count(
		"Kumar Warranty Claim",
		{"dealer": ["in", scope], "workflow_state": ["not in", ("Settled", "Rejected")],
		 "docstatus": ["<", 2]},
	)

	return {
		"dealer": me.name,
		"dealer_name": frappe.db.get_value("Dealer", me.name, "dealer_name") or me.name,
		"pumps": len(pumps),
		"in_warranty": in_warranty,
		"expiring": expiring,
		"expired": expired,
		"open_tickets": open_requests + open_claims,
		"open_requests": open_requests,
		"open_claims": open_claims,
		"expiring_soon_days": EXPIRING_SOON_DAYS,
	}


@frappe.whitelist()
def my_pumps(limit=600):
	"""The dealer's own pumps, slim enough to search in the browser.

	The same rows the portal renders into its picker, exposed as an endpoint so
	the desk can offer the same "type a serial, model or customer" search
	without a round trip per keystroke. Scoped by _my_scope, so it can only ever
	return pumps this dealer's tree sold.
	"""
	scope = _my_scope()
	rows = frappe.get_all(
		"Pump Registration",
		filters={"dealer": ["in", scope], "docstatus": 1},
		fields=["name", "serial_no", "pump_model", "end_customer_name",
			"end_customer_mobile", "installation_address", "district",
			"warranty_expiry_date", "sale_date"],
		order_by="sale_date desc, creation desc",
		limit=cint(limit) or 600,
	)

	from kumar_service.api import certificate_url

	# model -> family, so "What I Sold" can filter by product family the way the
	# portal does. One query for the whole catalogue rather than one per row.
	categories = dict(
		frappe.get_all("Pump Model", fields=["name", "pump_category"], as_list=True,
			limit_page_length=0)
	)

	from frappe.utils import getdate

	today = getdate(nowdate())
	soon = add_days(today, EXPIRING_SOON_DAYS)
	out = []
	for r in rows:
		if not r.serial_no:
			continue
		expiry = getdate(r.warranty_expiry_date) if r.warranty_expiry_date else None
		if not expiry:
			state = "Not Registered"
		elif expiry < today:
			state = "Expired"
		elif expiry <= soon:
			state = "Expiring Soon"
		else:
			state = "In Warranty"
		out.append(
			{
				"registration": r.name,
				# the sheet the dealer actually owes the customer - without it
				# they are back in the old portal to print a certificate
				"certificate_url": certificate_url(r.name),
				"serial_no": r.serial_no,
				"model": r.pump_model or "",
				"category": categories.get(r.pump_model) or "",
				"customer": r.end_customer_name or "",
				"mobile": r.end_customer_mobile or "",
				"where": r.installation_address or "",
				"district": r.district or "",
				"sale_date": r.sale_date,
				"warranty_expiry_date": r.warranty_expiry_date,
				"days_left": (getdate(r.warranty_expiry_date) - today).days
					if r.warranty_expiry_date else None,
				"state": state,
			}
		)
	return out


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
def raise_complaint(serial_no, complaint_category, complaint_description, priority="Medium",
		attachments=None, request_type="Complaint"):
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
			"custom_request_type": request_type or "Complaint",
			"custom_channel": "Dealer Portal",
			"priority": priority or "Medium",
			"reported_on": now_datetime(),
		}
	)
	# The controller pulls model, warranty and dealer off the serial itself, so
	# nothing here needs to be trusted from the client.
	doc.insert(ignore_permissions=True)
	doc.submit()

	# Photographs and a short video are most of what a dealer has to offer: a
	# picture of a burnt winding or a video of a pump that will not prime says
	# more than a paragraph, and it is what decides whether a technician is sent.
	# They ride on the ticket's own thread through the same path a reply takes,
	# so the desk and the portal both show them with no special case.
	attached = 0
	if attachments:
		# add_reply takes the raw [{filename, content}] list and does the
		# decoding, size check and File row itself - the same path a reply with
		# photos already takes, so there is one place where this can go wrong.
		if isinstance(attachments, str):
			attachments = frappe.parse_json(attachments)
		attachments = [a for a in (attachments or []) if a]
		if attachments:
			add_reply(
				"Service Request",
				doc.name,
				_("Photos from the dealer"),
				notify_users=_staff_to_notify("Service Request", doc.name),
				attachments=attachments,
			)
			attached = len(attachments)

	return {
		"name": doc.name,
		"attached": attached,
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
	attachments=None,
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
	doc.flags.channel = "Dealer Portal"

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

	# A claim is money, and a claim with evidence is settled faster than one
	# without - a photograph of the failed part is the whole argument. Same path
	# a complaint's photos take, so there is one place this can go wrong.
	attached = 0
	if attachments:
		if isinstance(attachments, str):
			attachments = frappe.parse_json(attachments)
		attachments = [a for a in (attachments or []) if a]
		if attachments:
			add_reply(
				"Kumar Warranty Claim",
				doc.name,
				_("Photos from the dealer"),
				notify_users=_staff_to_notify("Kumar Warranty Claim", doc.name),
				attachments=attachments,
			)
			attached = len(attachments)

	return {
		"name": doc.name,
		"attached": attached,
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

	# Whether KUMAR has come back on each ticket. One grouped query rather than a
	# thread read per card, because a dealer with sixty tickets should not cost
	# sixty round trips.
	portal_users = _portal_users()
	refs = [(TICKET_DOCTYPES[t["kind"]], t["name"]) for t in tickets]
	replies = {}
	if refs:
		for row in frappe.get_all(
			"Comment",
			filters={
				"comment_type": "Comment",
				"reference_doctype": ["in", list({r[0] for r in refs})],
				"reference_name": ["in", list({r[1] for r in refs})],
			},
			fields=["reference_doctype", "reference_name", "owner", "creation"],
			order_by="creation asc",
		):
			replies.setdefault((row.reference_doctype, row.reference_name), []).append(row)

	for t in tickets:
		msgs = replies.get((TICKET_DOCTYPES[t["kind"]], t["name"]), [])
		t["replies"] = len(msgs)
		last = msgs[-1] if msgs else None
		t["last_reply_on"] = last.creation if last else None
		# "KUMAR replied" only when the LAST word was theirs - otherwise the
		# dealer is the one who is waiting on nobody.
		t["kumar_replied"] = 1 if last and last.owner not in portal_users else 0

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
			"thread": thread_for("Service Request", name),
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
			"thread": thread_for("Kumar Warranty Claim", name),
		}

	frappe.throw(_("Unknown ticket type"))


# ---------------------------------------------------------------------------
# The conversation
#
# A portal that only takes messages in is half a system: the dealer needs to see
# KUMAR come back to them. Built on frappe's own `Comment` timeline rather than a
# bespoke DocType, for one decisive reason - KUMAR staff can then reply from the
# Service Request form they already work in, using the comment box that is
# already there, and it shows up in the dealer's portal. No new screen for staff
# to learn, and nothing to keep in sync.
#
# Who said it is derived from the comment's owner against the Dealer.portal_user
# list, the same way the Dealer Requests report tells Portal from Desk.
# ---------------------------------------------------------------------------

TICKET_DOCTYPES = {"complaint": "Service Request", "claim": "Kumar Warranty Claim"}


def _ticket_doctype(kind):
	doctype = TICKET_DOCTYPES.get(kind)
	if not doctype:
		frappe.throw(_("Unknown ticket type"))
	return doctype


def _my_ticket(kind, name):
	"""Assert this ticket belongs to the calling dealer's network."""
	doctype = _ticket_doctype(kind)
	dealer = frappe.db.get_value(doctype, name, "dealer")
	if not dealer:
		frappe.throw(_("{0} does not exist").format(name), frappe.DoesNotExistError)
	if dealer not in _my_scope():
		frappe.throw(_("Not permitted"), frappe.PermissionError)
	return doctype, dealer


def _portal_users():
	return set(
		frappe.get_all("Dealer", filters={"portal_user": ["!=", ""]}, pluck="portal_user")
	)


#: What may be attached to a message. A dealer photographs a burnt winding on a
#: phone and KUMAR sends back a credit note, so images and PDFs cover it; nothing
#: executable is accepted, and the cap keeps a phone photo from timing out on a
#: village connection.
ALLOWED_ATTACHMENTS = {
	".jpg", ".jpeg", ".png", ".webp", ".heic", ".gif", ".pdf",
}
MAX_ATTACHMENT_MB = 8
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".gif"}


def _is_image(name_or_url):
	value = (name_or_url or "").split("?")[0]
	ext = ("." + value.rsplit(".", 1)[-1]).lower() if "." in value else ""
	return ext in IMAGE_EXTENSIONS


def _parse_attachments(content):
	"""Read a message's attachments back out of its own rendered block.

	The File row lives on the TICKET, not on the Comment, and this is why:
	frappe's File controller RENAMES a second row that points at an existing
	file (`photo.jpeg` becomes `photoe9f33e.jpeg`), so keeping one row per
	message and another per ticket silently produced two different URLs - the
	timeline showed one file and the Attachments sidebar another. One row, on the
	ticket, gets the sidebar and the private-file permission right; the message
	link is carried by the block we rendered into the comment, which is the
	source of truth for "which message did this come with".
	"""
	import html
	import re

	block = re.search(
		rf'<div class="{ATTACH_MARKER}">(.*?)</div>', content or "", flags=re.S
	)
	if not block:
		return []
	out = []
	for href, data_name in re.findall(
		r'<a[^>]+href="([^"]+)"[^>]*data-name="([^"]*)"', block.group(1)
	):
		# stdlib: frappe.utils has escape_html but no unescape_html
		url = html.unescape(href)
		name = html.unescape(data_name) or url.rsplit("/", 1)[-1]
		out.append({"file_url": url, "file_name": name, "is_image": _is_image(name)})
	return out


#: Attachments are rendered into the Comment's own HTML inside this marker, so
#: frappe's native desk timeline shows them without knowing anything about us.
#: `thread_for` strips the block back out before handing the plain message to our
#: own screens, or the portal would print the markup twice.
ATTACH_MARKER = "kumar-attachments"


def _attachment_block(files):
	"""The HTML frappe's timeline renders under a comment."""
	if not files:
		return ""
	parts = []
	for f in files:
		url = frappe.utils.escape_html(f.get("file_url") or "")
		label = frappe.utils.escape_html(f.get("file_name") or "attachment")
		# data-name is what `_parse_attachments` reads back, so it is not
		# decoration - drop it and the chat panels lose their file names
		common = f'href="{url}" data-name="{label}" target="_blank" rel="noopener"'
		if f.get("is_image"):
			parts.append(
				f'<a {common} title="{label}">'
				f'<img src="{url}" alt="{label}" '
				f'style="max-width:200px;max-height:200px;border-radius:8px;'
				f'margin:6px 6px 0 0;vertical-align:top"></a>'
			)
		else:
			parts.append(
				f'<a {common} '
				f'style="display:inline-block;margin:6px 8px 0 0;font-weight:600">'
				f"&#128206; {label}</a>"
			)
	# one flat div, no nesting: `_strip_attachment_block` matches to the first
	# closing tag and nesting would break that
	return f'<div class="{ATTACH_MARKER}">' + "".join(parts) + "</div>"


def _strip_attachment_block(content):
	"""Remove the rendered block so the plain message can be read back out."""
	import re

	return re.sub(
		rf'<div class="{ATTACH_MARKER}">.*?</div>', "", content or "", flags=re.S
	)


def _write_attachment_block(comment_name, files):
	"""Render a message's files into its own HTML.

	This is what makes them visible in the DESK: frappe's timeline renders the
	comment's content, so an `<img>` in there is the whole fix. It is also where
	our own chat panels read the message's attachments back from.
	"""
	content = frappe.db.get_value("Comment", comment_name, "content") or ""
	fresh = _strip_attachment_block(content).rstrip() + _attachment_block(files)
	frappe.db.set_value("Comment", comment_name, "content", fresh, update_modified=False)


def repair_message_attachments():
	"""Backfill anything attached to a message before it was visible in the desk.

	The first cut of message attachments hung the File on the Comment only, so a
	dealer's photograph existed but the Service Request's Attachments sidebar was
	empty and frappe's timeline showed nothing - the file was effectively lost to
	anyone working in the desk. Idempotent, and called from `run_data_setup`, so an
	existing site is repaired on migrate rather than by hand.
	"""
	fixed = 0
	for row in frappe.db.sql(
		"""select f.name, f.file_url, f.file_name, f.attached_to_name as comment,
		          c.reference_doctype, c.reference_name
		   from   `tabFile` f
		   join   `tabComment` c on c.name = f.attached_to_name
		   where  f.attached_to_doctype = 'Comment'
		     and  ifnull(c.reference_doctype,'') != ''""",
		as_dict=True,
	):
		# Re-point the single File row at the ticket instead of creating a second
		# one. Written with db.set_value on purpose: File.validate() renames a row
		# whose file already exists on disk, which is exactly the bug that made
		# the desk and the timeline disagree about the URL.
		frappe.db.set_value(
			"File",
			row.name,
			{
				"attached_to_doctype": row.reference_doctype,
				"attached_to_name": row.reference_name,
			},
			update_modified=False,
		)
		_write_attachment_block(
			row.comment,
			[
				{
					"file_url": row.file_url,
					"file_name": row.file_name,
					"is_image": _is_image(row.file_name),
				}
			],
		)
		fixed += 1

	if fixed:
		frappe.db.commit()
		print(f"  repaired {fixed} message attachment(s) so the desk can see them")
	return fixed


def attach_to_message(comment_name, filename, content_base64, ticket_doctype=None,
		ticket_name=None):
	"""Save one file for a message.

	The File row is attached to the TICKET, not to the Comment - see
	`_parse_attachments` for why. `comment_name` is still taken so the caller
	cannot forget to render the block that links file to message.
	"""
	import base64
	import os

	filename = os.path.basename(filename or "").strip() or "attachment"
	ext = os.path.splitext(filename)[1].lower()
	if ext not in ALLOWED_ATTACHMENTS:
		frappe.throw(
			_("{0} cannot be attached. Send a photo or a PDF.").format(filename or ext)
		)

	try:
		content = base64.b64decode(content_base64 or "", validate=True)
	except Exception:  # noqa: BLE001
		frappe.throw(_("That file could not be read. Try again."))

	if not content:
		frappe.throw(_("That file is empty."))
	if len(content) > MAX_ATTACHMENT_MB * 1024 * 1024:
		frappe.throw(
			_("{0} is too large. The limit is {1} MB.").format(filename, MAX_ATTACHMENT_MB)
		)

	doc = frappe.get_doc(
		{
			"doctype": "File",
			"file_name": filename,
			# on the ticket, so it shows in the desk's Attachments sidebar and a
			# private file's permission resolves through a document staff can read
			"attached_to_doctype": ticket_doctype,
			"attached_to_name": ticket_name,
			"content": content,
			"decode": False,
			# a message on a dealer's ticket is not public
			"is_private": 1,
		}
	)
	doc.flags.ignore_permissions = True
	doc.insert(ignore_permissions=True)
	return {
		"file_url": doc.file_url,
		"file_name": doc.file_name,
		"is_image": _is_image(doc.file_name),
	}


def link_file_to_message(comment_name, file_url, ticket_doctype=None, ticket_name=None):
	"""Hang an ALREADY-uploaded file on a message.

	The desk's Attach field uploads through frappe and hands back a URL, so there
	is no base64 to decode - only a second File row to create pointing at the same
	stored file. Frappe keys content by hash, so this costs a row, not a copy.
	"""
	file_url = (file_url or "").strip()
	if not file_url:
		return None

	source = frappe.db.get_value(
		"File", {"file_url": file_url}, ["file_name", "is_private"], as_dict=True
	)
	doc = frappe.get_doc(
		{
			"doctype": "File",
			"file_url": file_url,
			"file_name": (source or {}).get("file_name") or file_url.rsplit("/", 1)[-1],
			"attached_to_doctype": ticket_doctype,
			"attached_to_name": ticket_name,
			"is_private": (source or {}).get("is_private", 1),
		}
	)
	doc.flags.ignore_permissions = True
	doc.insert(ignore_permissions=True)
	return {
		"file_url": doc.file_url,
		"file_name": doc.file_name,
		"is_image": _is_image(doc.file_name),
	}


def thread_for(doctype, name, portal_users=None):
	"""The conversation on one ticket, oldest first.

	Shared by the portal and the management screen so both sides read exactly the
	same thread - if they could diverge, one of them would be lying.
	"""
	portal_users = portal_users if portal_users is not None else _portal_users()
	rows = frappe.get_all(
		"Comment",
		filters={
			"reference_doctype": doctype,
			"reference_name": name,
			# only real replies: frappe also files Info/Workflow/Edit comments
			# against the same document and they are audit noise, not conversation
			"comment_type": "Comment",
		},
		fields=["name", "content", "owner", "creation", "comment_by"],
		order_by="creation asc",
	)
	thread = []
	for r in rows:
		from_dealer = r.owner in portal_users
		thread.append(
			{
				"name": r.name,
				# the rendered attachment block is stripped first, or the portal
				# would print the file names again under the bubble
				"message": frappe.utils.strip_html(
					_strip_attachment_block(r.content or "")
				).strip(),
				"html": r.content,
				"by": r.comment_by or r.owner,
				"from_dealer": 1 if from_dealer else 0,
				"side": "dealer" if from_dealer else "kumar",
				"who": _("Dealer") if from_dealer else "KUMAR",
				"on": r.creation,
				"attachments": _parse_attachments(r.content),
			}
		)
	return thread


def add_reply(doctype, name, message, notify_users=None, attachments=None, attach_urls=None):
	"""Append to a ticket's conversation and tell the other side.

	`notify_users` is who to alert. Without the notification this is a noticeboard
	nobody reads - the whole point is that neither side has to keep checking.

	`attachments` is a list of `{filename, content}` where content is base64. A
	message may be attachment-only: a photograph of a burnt winding says more than
	a paragraph, and refusing it because the text box was empty would be silly.
	"""
	message = (message or "").strip()
	if isinstance(attachments, str):
		attachments = frappe.parse_json(attachments)
	attachments = attachments or []
	if isinstance(attach_urls, str):
		attach_urls = frappe.parse_json(attach_urls) if attach_urls.startswith("[") else [attach_urls]
	attach_urls = [u for u in (attach_urls or []) if u]

	if not message and not attachments and not attach_urls:
		frappe.throw(_("Write a message before sending"))
	if not message:
		message = _("(photo attached)")

	comment = frappe.get_doc(
		{
			"doctype": "Comment",
			"comment_type": "Comment",
			"reference_doctype": doctype,
			"reference_name": name,
			"content": frappe.utils.escape_html(message),
			"comment_by": frappe.session.user,
		}
	)
	comment.flags.ignore_permissions = True
	comment.insert(ignore_permissions=True)

	saved = []
	for row in attachments:
		saved.append(
			attach_to_message(
				comment.name,
				(row or {}).get("filename"),
				(row or {}).get("content"),
				ticket_doctype=doctype,
				ticket_name=name,
			)
		)
	for url in attach_urls:
		saved.append(
			link_file_to_message(comment.name, url, ticket_doctype=doctype, ticket_name=name)
		)

	# Render the files into the comment itself. This is what makes them visible in
	# the desk - frappe's timeline renders comment HTML - and it is also how the
	# message keeps its link to the files now that the File rows sit on the ticket.
	if saved:
		_write_attachment_block(comment.name, saved)

	# A Notification Log is both the in-app alert and, where the recipient has
	# email notifications on AND an outgoing Email Account is configured, the
	# email frappe sends from it. Complaints and warranty claims go through this
	# same path, so they behave identically - which is the point: a dealer should
	# not have to learn that one kind of message reaches them and another does not.
	subject = _("KUMAR replied on {0}").format(name)
	if doctype == "Kumar Warranty Claim":
		subject = _("Warranty claim {0} - an update from KUMAR").format(name)
	elif doctype == "Service Request":
		what = frappe.db.get_value(doctype, name, "serial_no")
		subject = _("Service request {0}{1} - an update from KUMAR").format(
			name, f" ({what})" if what else ""
		)

	for user in {u for u in (notify_users or []) if u and u != frappe.session.user}:
		try:
			frappe.get_doc(
				{
					"doctype": "Notification Log",
					# the subject is what lands in an inbox, so it says which pump
					# and which kind of thing rather than only a document id
					"subject": subject,
					"email_content": message[:500],
					"for_user": user,
					"type": "Alert",
					"document_type": doctype,
					"document_name": name,
					"from_user": frappe.session.user,
				}
			).insert(ignore_permissions=True)
		except Exception:  # noqa: BLE001 - a failed alert must not lose the reply
			frappe.clear_last_message()


	# the same message onto the desk ticket, so the agent's ticket page and the
	# dealer's My Tickets both carry it - see desk_bridge.mirror_message
	try:
		from kumar_service.desk_bridge import mirror_message

		mirror_message(
			doctype, name, comment.name, message,
			from_dealer=frappe.session.user in _portal_users(),
			file_urls=[u for u in (attach_urls or [])]
			+ [f.get("file_url") for f in (_parse_attachments(comment.content or "") or [])],
		)
	except Exception:  # noqa: BLE001 - the mirror must never lose the reply
		frappe.log_error(title="KUMAR Pumps Desk bridge", message=frappe.get_traceback())

	return comment.name


@frappe.whitelist()
def ticket_thread(kind, name):
	"""The dealer reading the conversation on their own ticket."""
	doctype, _dealer = _my_ticket(kind, name)
	return {"kind": kind, "name": name, "thread": thread_for(doctype, name)}


def _staff_to_notify(doctype, name):
	"""Who at KUMAR should hear about this ticket.

	Whoever it is assigned to, the technician on it, and the Service Managers.
	Shared by a dealer's reply and by a complaint that arrives with photos.
	"""
	notify = set()
	if doctype == "Service Request":
		tech_user = frappe.db.get_value(
			"Service Technician",
			frappe.db.get_value(doctype, name, "assigned_technician"),
			"user",
		)
		if tech_user:
			notify.add(tech_user)
	notify.update(
		frappe.get_all(
			"Has Role",
			filters={"role": "Service Manager", "parenttype": "User"},
			pluck="parent",
		)
	)
	owner = frappe.db.get_value(doctype, name, "owner")
	if owner:
		notify.add(owner)
	return notify


@frappe.whitelist()
def post_reply(kind, name, message, attachments=None):
	"""The dealer writing back to KUMAR, with photos if they have them."""
	doctype, dealer = _my_ticket(kind, name)
	notify = _staff_to_notify(doctype, name)

	before = frappe.db.get_value(doctype, name, "status")
	add_reply(doctype, name, message, notify_users=notify, attachments=attachments)
	reopened = _reopen_if_settled(doctype, name, previous=before)
	return {
		"thread": thread_for(doctype, name),
		"reopened": reopened,
		"status": frappe.db.get_value(doctype, name, "status"),
		"message": _("Reopened, and sent to KUMAR.") if reopened else _("Sent to KUMAR."),
	}


# Who KUMAR still owes an answer to is derived from who wrote last, so a ticket
# that is still open needs no status change when the dealer writes - it simply
# moves to the top of the "waiting on KUMAR" queue.
#
# A ticket that was already resolved or closed is the problem. The staff queue
# only lists open ones, so a dealer replying "it has failed again" to a closed
# ticket was writing into a thread nobody was going to read. Their reply reopens
# it, which is what a helpdesk does and what the dealer plainly expects.
# Only the Service Request. A Kumar Warranty Claim is driven by a Workflow whose
# Settled and Rejected states have no outgoing transition - they are terminal by
# design, and an approver decided to end it there. Writing workflow_state back by
# hand would walk around the workflow rather than through it, so a dealer replying
# to a settled claim notifies the desk (which it already did) and leaves the state
# alone. If the business does want claims reopened, that is a Workflow Transition
# somebody has to add deliberately, not something this function should invent.
_SETTLED = {"Service Request": ("Resolved", "Closed")}


def _reopen_if_settled(doctype, name, previous=None):
	"""Reopen a settled request because the dealer wrote on it.

	`previous` is the status as it was before the reply landed. It matters
	because the reply is mirrored onto the desk ticket first, the desk marks
	the ticket Open on a customer message, and the status sync carries that
	back - so by the time this runs the request may already read Open. That
	is the right outcome, but the dealer still deserves the trail note, and
	the caller still deserves to be told it happened.
	"""
	settled = _SETTLED.get(doctype) or ()
	if not settled:
		return False
	status = previous if previous is not None else frappe.db.get_value(doctype, name, "status")
	if status not in settled:
		return False

	reopen_to = "Open"
	field = frappe.get_meta(doctype).get_field("status")
	allowed = (field.options or "").split("\n") if field else []
	if reopen_to not in allowed:
		# never invent a status the doctype does not define
		return False

	# update_modified so it surfaces at the top of a queue sorted by recency
	frappe.db.set_value(doctype, name, "status", reopen_to)
	frappe.get_doc(
		{
			"doctype": "Comment",
			"comment_type": "Info",
			"reference_doctype": doctype,
			"reference_name": name,
			"content": _("Reopened by the dealer, who replied after it was marked {0}.").format(
				_(status)
			),
		}
	).insert(ignore_permissions=True)
	return True


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
