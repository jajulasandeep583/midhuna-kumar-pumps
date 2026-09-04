"""The bridge between a Service Request and its HD Ticket in KUMAR Pumps Desk.

Service Request stays the source of truth. It knows the serial number, the pump
model, the warranty position, the heat and winding batches, the SLA clocks and
the dealer tree that decides who may see it - none of which HD Ticket has any
concept of, and all of which the portal, the reports and the warranty engine
already read.

So the desk gets a mirror, not custody. Every request raises an HD Ticket that
carries the pump facts and a link home, agents work the queue in the desk UI
they asked for, and the answer to "what is true about this pump" still has one
place to live. Nothing here writes back into a Service Request except status,
and that only through set_status below.

Two rules this module must never break:

  1. It must never stop a Service Request being saved. A dealer raising a
     complaint at eight in the evening does not care that the desk is having a
     bad day, and a mirror that can veto the thing it mirrors is worse than no
     mirror. Every entry point is wrapped and logs rather than raises.

  2. It must do nothing at all when helpdesk is not installed. This app has to
     keep working on a site that never wanted a desk.
"""

import frappe
from frappe.utils import cint, flt

# Service Request has seven states and the desk has four. Anything a dealer is
# still waiting on is Open to an agent - "Awaiting Parts" is a detail of how
# KUMAR is working it, not a reason for it to leave the queue.
STATUS_TO_DESK = {
	"Open": "Open",
	"Assigned": "Open",
	"In Progress": "Open",
	"Awaiting Parts": "Open",
	"Resolved": "Resolved",
	"Closed": "Closed",
	"Cancelled": "Closed",
}

# Coming back the other way we can only be coarse, because the desk cannot know
# whether a request is Assigned or Awaiting Parts. So a desk status only ever
# moves a request between the three states the desk actually models, and never
# overwrites a more specific one with a vaguer one - see set_status.
STATUS_FROM_DESK = {
	"Open": "Open",
	"Replied": "In Progress",
	"Resolved": "Resolved",
	"Closed": "Closed",
}

_SPECIFIC_OPEN = ("Assigned", "In Progress", "Awaiting Parts")


def desk_installed():
	return bool(frappe.db.exists("DocType", "HD Ticket"))


def _quietly(fn, *args, **kwargs):
	"""Run a bridge step; log and swallow anything it throws. See rule 1."""
	try:
		return fn(*args, **kwargs)
	except Exception:
		frappe.log_error(
			title="KUMAR Pumps Desk bridge",
			message=frappe.get_traceback(with_context=True),
		)
		return None


# ------------------------------------------------------------------ customer

def contact_for(dealer):
	"""The Contact of the dealer's portal login, walking up to a parent if needed.

	This is what makes a mirrored ticket visible to the dealer at all. Helpdesk
	shows a non-agent the tickets they own, are the contact on, or raised - and
	a ticket inserted by the bridge is owned by whoever triggered it, usually
	Administrator. Setting the contact is what puts it in the dealer's list.

	A sub-dealer with no login of its own is handled by its parent, the same way
	the conversation notifications already are.
	"""
	hops = 0
	while dealer and hops < 8:
		user = frappe.db.get_value("Dealer", dealer, "portal_user")
		if user:
			contact = frappe.db.get_value("Contact", {"user": user})
			if contact:
				return contact, user
		dealer = frappe.db.get_value("Dealer", dealer, "parent_dealer")
		hops += 1
	return None, None


def customer_for(dealer):
	"""One HD Customer per Dealer, so an agent can filter the queue by outlet."""
	if not dealer or not frappe.db.exists("DocType", "HD Customer"):
		return None
	if frappe.db.exists("HD Customer", dealer):
		return dealer
	doc = frappe.get_doc({"doctype": "HD Customer", "name": dealer, "customer_name": dealer})
	doc.flags.ignore_permissions = True
	doc.insert(ignore_permissions=True)
	return doc.name


def link_contact_to_customer(customer, contact):
	"""Make the contact a member of this customer, if it is not already.

	HD Ticket refuses a customer that is not among the contact's own customers.
	That rule is right for a helpdesk where one contact belongs to one company,
	and wrong for a dealer tree: a sub-dealer with no login of its own is handled
	by its parent, so the ticket carries the sub-dealer as the customer - which
	is true, they sold the pump - and the parent's login as the contact.

	The membership is the honest fix rather than lying about either field: a
	parent dealer really does cover its sub-dealers, so its contact really is a
	member of that outlet.
	"""
	if not (customer and contact):
		return
	cust = frappe.get_doc("HD Customer", customer)
	if any(m.contact_name == contact for m in (cust.get("contacts") or [])):
		return
	cust.append("contacts", {"contact_name": contact, "is_manager": 1})
	cust.flags.ignore_permissions = True
	cust.save(ignore_permissions=True)


# -------------------------------------------------------------------- mirror

def _subject(sr):
	kind = sr.get("custom_request_type") or "Complaint"
	# "Installation - KP-..." reads better in a queue than the category alone
	bits = [kind if kind != "Complaint" else (sr.get("complaint_category") or "Complaint")]
	if sr.get("serial_no"):
		bits.append(sr.serial_no)
	return " - ".join(bits)


def _channel(doc):
	"""How it reached KUMAR. Set on the document by whoever raised it; else
	inferred: a portal user's document came through the portal, anyone else's
	was a call taken by staff."""
	if doc.get("custom_channel"):
		return doc.get("custom_channel")
	if doc.flags.get("channel"):
		return doc.flags.get("channel")
	from kumar_service.portal_api import _portal_users
	return "Dealer Portal" if (doc.get("owner") or frappe.session.user) in _portal_users() else "Phone"


def _raised_for_line(doc, dealer):
	"""'Raised by KUMAR (Ravi) for Deccan Pumps, by phone.' - or nothing when the
	dealer raised it themselves, because then the sender line already says so."""
	channel = _channel(doc)
	if channel == "Dealer Portal":
		return ""
	who = doc.get("owner") or frappe.session.user
	name = frappe.db.get_value("User", who, "full_name") or who
	for_whom = f" for {frappe.utils.escape_html(dealer)}" if dealer else ""
	return (
		f"<p><em>Raised by KUMAR ({frappe.utils.escape_html(name)}){for_whom}, "
		f"via {frappe.utils.escape_html(channel)}.</em></p>"
	)


def _description(sr):
	rows = [
		("Serial No", sr.get("serial_no")),
		("Pump Model", sr.get("pump_model")),
		("Dealer", sr.get("dealer")),
		("Customer", sr.get("end_customer_name")),
		("Mobile", sr.get("end_customer_mobile")),
		("Warranty", "In warranty - not chargeable" if cint(sr.get("is_under_warranty"))
			else "Out of warranty - chargeable"),
	]
	lines = "".join(
		f"<tr><td><b>{frappe.utils.escape_html(str(k))}</b></td>"
		f"<td>{frappe.utils.escape_html(str(v))}</td></tr>"
		for k, v in rows if v
	)
	body = frappe.utils.escape_html(sr.get("complaint_description") or "")
	return f"{_raised_for_line(sr, sr.get('dealer'))}<p>{body}</p><table>{lines}</table>"


def _ticket_type(sr):
	"""The desk's ticket type, from what the dealer said they wanted."""
	wanted = sr.get("custom_request_type") or "Complaint"
	if frappe.db.exists("HD Ticket Type", wanted):
		return wanted
	return "Complaint" if frappe.db.exists("HD Ticket Type", "Complaint") else None


def mirror(doc, method=None):
	"""Raise or refresh the HD Ticket that shadows this Service Request."""
	if not desk_installed():
		return
	_quietly(_mirror, doc)


def _mirror(sr):
	existing = frappe.db.get_value("HD Ticket", {"custom_service_request": sr.name, "custom_warranty_claim": ["is", "not set"]}, "name")
	desk_status = STATUS_TO_DESK.get(sr.get("status"), "Open")

	contact, portal_user = contact_for(sr.get("dealer"))
	customer = customer_for(sr.get("dealer"))
	# the contact answering for this outlet has to be a member of it, or
	# HD Ticket rejects the pair - see link_contact_to_customer
	link_contact_to_customer(customer, contact)
	values = {
		"subject": _subject(sr),
		"status": desk_status,
		# without these the dealer who raised it cannot see their own ticket
		"contact": contact,
		"raised_by": portal_user,
		"custom_service_request": sr.name,
		"custom_serial_no": sr.get("serial_no"),
		"custom_dealer": sr.get("dealer"),
		"custom_pump_model": sr.get("pump_model"),
		"custom_warranty": "In Warranty" if cint(sr.get("is_under_warranty")) else "Out of Warranty",
		"custom_channel": _channel(sr),
	}

	if existing:
		# only touch what can drift; never rewrite the agent's own triage
		for field, value in values.items():
			if frappe.db.get_value("HD Ticket", existing, field) != value:
				frappe.db.set_value("HD Ticket", existing, field, value)
		return existing

	ticket = frappe.get_doc(
		dict(
			doctype="HD Ticket",
			description=_description(sr),
			customer=customer,
			ticket_type=_ticket_type(sr),
			**values,
		)
	)
	ticket.flags.ignore_permissions = True
	ticket.insert(ignore_permissions=True)
	return ticket.name


# ------------------------------------------------------------- status upward

def set_status(doc, method=None):
	"""An agent moved the ticket in the desk; carry it back to the request.

	Deliberately conservative. The desk has no way to express "Awaiting Parts",
	so a desk ticket sitting at Open must not flatten a request that somebody
	has already triaged into a more specific open state - that would erase real
	information every time an agent so much as looked at it.
	"""
	if not desk_installed():
		return
	_quietly(_set_status, doc)


def _set_status(ticket):
	sr = ticket.get("custom_service_request")
	if not sr or not frappe.db.exists("Service Request", sr):
		return
	want = STATUS_FROM_DESK.get(ticket.get("status"))
	if not want:
		return
	current = frappe.db.get_value("Service Request", sr, "status")
	if current == want:
		return
	# Open from the desk must not undo Assigned / In Progress / Awaiting Parts
	if want == "Open" and current in _SPECIFIC_OPEN:
		return
	if current in ("Cancelled",):
		return
	frappe.db.set_value("Service Request", sr, "status", want)


# ------------------------------------------------------------- claims
#
# A warranty claim gets a ticket of its own, for the same reason a request does:
# the desk's ticket page is the one conversation screen everybody uses, and a
# claim decided in a side panel with its own little chat box was a claim
# nobody could find the thread on afterwards.

CLAIM_STATE_TO_DESK = {
	"Draft": "Open",
	"Pending Review": "Open",
	"Under Investigation": "Open",
	"Approved": "Open",       # still needs settling; it has not left the queue
	"Settled": "Resolved",
	"Rejected": "Closed",
}


def mirror_claim(doc, method=None):
	if not desk_installed():
		return
	_quietly(_mirror_claim, doc)


def _warranty_label(serial):
	"""'In Warranty' / 'Out of Warranty' for the ticket column, or '' if unknown."""
	if not serial:
		return ""
	# warranty_status_for wants the expiry date, which lives on the registration
	expiry = frappe.db.get_value(
		"Pump Registration", {"serial_no": serial, "docstatus": 1}, "warranty_expiry_date"
	)
	if not expiry:
		return ""
	from kumar_service.utils import warranty_status_for
	st = warranty_status_for(expiry)
	# the column is the same two words every request ticket uses
	return "Out of Warranty" if st == "Expired" else "In Warranty"


def _mirror_claim(claim):
	if claim.get("docstatus") == 2:
		return None
	existing = frappe.db.get_value("HD Ticket", {"custom_warranty_claim": claim.name}, "name")
	contact, portal_user = contact_for(claim.get("dealer"))
	customer = customer_for(claim.get("dealer"))
	link_contact_to_customer(customer, contact)
	amount = flt(claim.get("approved_amount")) or flt(claim.get("claim_amount"))
	values = {
		"subject": f"Warranty claim {claim.name} - {claim.get('serial_no') or ''}".strip(" -"),
		"status": CLAIM_STATE_TO_DESK.get(claim.get("workflow_state"), "Open"),
		"contact": contact,
		"raised_by": portal_user,
		"custom_warranty_claim": claim.name,
		# NOT custom_service_request. A claim ticket is linked to its request
		# through the claim (ticket_context walks it); if it also carried the
		# request's field, the request would have two tickets and everything
		# that finds "the ticket for this request" could land on the wrong one.
		"custom_serial_no": claim.get("serial_no"),
		"custom_dealer": claim.get("dealer"),
		"custom_pump_model": claim.get("pump_model"),
		"custom_warranty": _warranty_label(claim.get("serial_no")),
		"custom_channel": _channel(claim),
	}
	if existing:
		for field, value in values.items():
			if frappe.db.get_value("HD Ticket", existing, field) != value:
				frappe.db.set_value("HD Ticket", existing, field, value)
		return existing

	rows = [
		("Claim type", claim.get("claim_type")),
		("Root cause", claim.get("root_cause")),
		("Amount claimed", frappe.utils.fmt_money(flt(claim.get("claim_amount")), currency="INR")),
		("Dealer", claim.get("dealer")),
		("Heat", claim.get("heat_no")),
		("Winding batch", claim.get("winding_batch")),
	]
	table = "".join(
		f"<tr><td><b>{frappe.utils.escape_html(str(k))}</b></td>"
		f"<td>{frappe.utils.escape_html(str(v))}</td></tr>" for k, v in rows if v
	)
	report = frappe.utils.escape_html(claim.get("technician_report") or "")
	ticket = frappe.get_doc(
		dict(
			doctype="HD Ticket",
			description=f"{_raised_for_line(claim, claim.get('dealer'))}<p>{report}</p><table>{table}</table>",
			customer=customer,
			ticket_type="Warranty Claim" if frappe.db.exists("HD Ticket Type", "Warranty Claim") else None,
			**values,
		)
	)
	ticket.flags.ignore_permissions = True
	ticket.insert(ignore_permissions=True)
	return ticket.name


# ------------------------------------------------------ one conversation
#
# The desk's ticket page renders Communication rows on the HD Ticket. The
# portal, the claim decisions, the visit notices and the photo uploads all
# write Comments on the Service Request or the claim through add_reply. Those
# were two threads: an agent opening a ticket saw none of the dealer's
# messages, a dealer in My Tickets saw none of KUMAR's, and "Visit scheduled"
# existed nowhere either of them looked.
#
# Now every message written through add_reply is ALSO a Communication on the
# mirrored ticket, and every Communication written on the ticket page flows
# back onto the request. Bridge-written rows carry communication_medium "Chat"
# and a message_id naming the Comment they came from - the first stops the
# reverse hook echoing them back, the second makes the backfill idempotent.

BRIDGE_MEDIUM = "Chat"


def ticket_for(doctype, name):
	field = {"Service Request": "custom_service_request",
		"Kumar Warranty Claim": "custom_warranty_claim"}.get(doctype)
	if not field:
		return None
	return frappe.db.get_value("HD Ticket", {field: name}, "name")


def mirror_message(doctype, name, comment_name, message, from_dealer, file_urls=None):
	"""A Comment on the request/claim -> a Communication on its ticket."""
	if not desk_installed():
		return None
	return _quietly(_mirror_message, doctype, name, comment_name, message, from_dealer,
		file_urls or [])


def _mirror_message(doctype, name, comment_name, message, from_dealer, file_urls):
	ticket = ticket_for(doctype, name)
	if not ticket:
		return None
	message_id = f"kumar-comment:{comment_name}"
	if frappe.db.exists("Communication", {"message_id": message_id}):
		return None
	subject = frappe.db.get_value("HD Ticket", ticket, "subject") or name
	c = frappe.get_doc(
		{
			"doctype": "Communication",
			"communication_type": "Communication",
			"communication_medium": BRIDGE_MEDIUM,
			"sent_or_received": "Received" if from_dealer else "Sent",
			"email_status": "Open",
			"subject": f"Re: {subject}",
			"sender": frappe.session.user,
			"user": frappe.session.user,
			"content": frappe.utils.escape_html(message or "").replace("\n", "<br>"),
			"status": "Linked",
			"reference_doctype": "HD Ticket",
			"reference_name": ticket,
			"message_id": message_id,
		}
	)
	c.flags.ignore_permissions = True
	c.flags.ignore_mandatory = True
	c.insert(ignore_permissions=True)

	# the photographs travel too: a File row on the Communication is what the
	# ticket page shows as an attachment. Copied, not moved - the request keeps
	# its own copy for the certificate, the claim and the portal.
	for url in file_urls:
		if not url:
			continue
		src = frappe.db.get_value(
			"File", {"file_url": url}, ["file_name", "is_private", "file_size"], as_dict=True
		) or {}
		f = frappe.get_doc(
			{
				"doctype": "File",
				"file_url": url,
				"file_name": src.get("file_name") or url.rsplit("/", 1)[-1],
				"is_private": src.get("is_private", 1),
				"attached_to_doctype": "Communication",
				"attached_to_name": c.name,
			}
		)
		f.flags.ignore_permissions = True
		try:
			f.insert(ignore_permissions=True)
		except Exception:
			frappe.clear_last_message()
	return c.name


def on_communication(doc, method=None):
	"""A message written on the ticket page -> the request it mirrors.

	Sent (an agent) stamps the SLA first response. Received (a dealer) reopens
	a settled request, the same as a reply through the portal did.
	"""
	if doc.get("reference_doctype") != "HD Ticket":
		return
	if doc.get("communication_medium") == BRIDGE_MEDIUM:
		return   # we wrote it; do not echo it back
	_quietly(_on_communication, doc)


def _on_communication(comm):
	t = frappe.db.get_value(
		"HD Ticket", comm.reference_name,
		["custom_service_request", "custom_warranty_claim"], as_dict=True,
	)
	if not t:
		return
	doctype, name = (("Service Request", t.custom_service_request) if t.custom_service_request
		else ("Kumar Warranty Claim", t.custom_warranty_claim))
	if not name or not frappe.db.exists(doctype, name):
		return

	text = frappe.utils.strip_html(comm.get("content") or "").strip()
	if text:
		comment = frappe.get_doc(
			{
				"doctype": "Comment",
				"comment_type": "Comment",
				"reference_doctype": doctype,
				"reference_name": name,
				"content": frappe.utils.escape_html(text),
				"comment_by": comm.get("sender") or frappe.session.user,
				"comment_email": comm.get("sender") or frappe.session.user,
			}
		)
		comment.flags.ignore_permissions = True
		comment.insert(ignore_permissions=True)
		# the desk row is the original; mark it so a re-run never mirrors twice
		frappe.db.set_value("Communication", comm.name, "message_id",
			f"kumar-comment:{comment.name}", update_modified=False)

	if doctype != "Service Request":
		return
	if comm.get("sent_or_received") == "Sent":
		# The first response is the first response: a request that was settled
		# without one and then reopened still carries its old resolved_on, and
		# the agent's first word on it must count. Only an empty stamp is set,
		# so nothing ever moves an existing one.
		if not frappe.db.get_value("Service Request", name, "first_response_on"):
			frappe.db.set_value("Service Request", name, "first_response_on",
				frappe.utils.now_datetime(), update_modified=False)
	else:
		from kumar_service.portal_api import _reopen_if_settled
		_reopen_if_settled("Service Request", name)


# -------------------------------------------------------------- backfill

def relink(limit=None):
	"""Put the contact and raiser back on tickets mirrored before we set them.

	Separate from backfill because these tickets exist and are correct in every
	other respect - they were simply invisible to the dealer they belong to.
	"""
	if not desk_installed():
		return {"relinked": 0, "skipped": "helpdesk is not installed"}
	done = 0
	for t in frappe.get_all(
		"HD Ticket",
		filters={"custom_service_request": ["is", "set"]},
		fields=["name", "custom_dealer", "contact", "raised_by"],
		limit_page_length=cint(limit) or None,
	):
		if t.contact and t.raised_by:
			continue
		contact, user = contact_for(t.custom_dealer)
		if not contact:
			continue
		frappe.db.set_value("HD Ticket", t.name, {"contact": contact, "raised_by": user})
		done += 1
	frappe.db.commit()
	return {"relinked": done}


def backfill_claims(limit=None):
	"""Tickets for the claims that predate the mirror."""
	if not desk_installed():
		return {"mirrored": 0, "skipped": "helpdesk is not installed"}
	names = frappe.get_all(
		"Kumar Warranty Claim", filters={"docstatus": ["<", 2]}, pluck="name",
		order_by="creation asc", limit=cint(limit) or None,
	)
	made = 0
	for name in names:
		if frappe.db.exists("HD Ticket", {"custom_warranty_claim": name}):
			continue
		if _quietly(_mirror_claim, frappe.get_doc("Kumar Warranty Claim", name)):
			made += 1
	frappe.db.commit()
	return {"seen": len(names), "mirrored": made}


def backfill_thread(limit=None):
	"""Every message already on a request or claim, onto its ticket.

	Idempotent: a Communication names the Comment it mirrors in message_id, so
	one that is already there is skipped.
	"""
	if not desk_installed():
		return {"mirrored": 0, "skipped": "helpdesk is not installed"}
	from kumar_service.portal_api import _portal_users, _parse_attachments

	portal_users = _portal_users()
	made = skipped = 0
	for dt in ("Service Request", "Kumar Warranty Claim"):
		for c in frappe.get_all(
			"Comment",
			filters={"reference_doctype": dt, "comment_type": "Comment"},
			fields=["name", "reference_name", "content", "comment_email", "owner", "creation"],
			order_by="creation asc", limit_page_length=cint(limit) or 0,
		):
			tk = ticket_for(dt, c.reference_name)
			if not tk:
				continue
			# on THIS ticket: a marker left on a ticket that was since deleted (its
			# reference goes blank) must not stop the message reaching the new one
			if frappe.db.exists("Communication", {"reference_doctype": "HD Ticket", "reference_name": tk,
					"message_id": f"kumar-comment:{c.name}"}):
				skipped += 1
				continue
			who = c.comment_email or c.owner
			files = [a.get("file_url") for a in (_parse_attachments(c.content or "") or [])]
			text = frappe.utils.strip_html(c.content or "")
			frappe.set_user(who if frappe.db.exists("User", who) else "Administrator")
			try:
				comm = _mirror_message(dt, c.reference_name, c.name, text, who in portal_users, files)
			finally:
				frappe.set_user("Administrator")
			if comm:
				# keep the thread in its original order on the ticket page
				frappe.db.set_value("Communication", comm, "creation", c.creation, update_modified=False)
				frappe.db.set_value("Communication", comm, "communication_date", c.creation, update_modified=False)
				made += 1
	frappe.db.commit()
	return {"mirrored": made, "already": skipped}


def backfill(limit=None):
	"""Mirror the requests that already existed before the desk did."""
	if not desk_installed():
		return {"mirrored": 0, "skipped": "helpdesk is not installed"}
	names = frappe.get_all(
		"Service Request",
		filters={"docstatus": ["<", 2]},
		pluck="name",
		order_by="creation asc",
		limit=cint(limit) or None,
	)
	made = 0
	for name in names:
		if frappe.db.exists("HD Ticket", {"custom_service_request": name, "custom_warranty_claim": ["is", "not set"]}):
			continue
		if _quietly(_mirror, frappe.get_doc("Service Request", name)):
			made += 1
	frappe.db.commit()
	return {"seen": len(names), "mirrored": made}
