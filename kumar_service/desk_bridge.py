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
from frappe.utils import cint

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
	return f"<p>{body}</p><table>{lines}</table>"


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
	existing = frappe.db.get_value("HD Ticket", {"custom_service_request": sr.name}, "name")
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
		if frappe.db.exists("HD Ticket", {"custom_service_request": name}):
			continue
		if _quietly(_mirror, frappe.get_doc("Service Request", name)):
			made += 1
	frappe.db.commit()
	return {"seen": len(names), "mirrored": made}
