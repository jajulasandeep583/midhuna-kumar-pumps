"""The KUMAR side of the dealer conversation.

The portal takes complaints and claims in; this is how the company answers. Staff
can already reply from the comment box on the Service Request form - that is
deliberate, and this module does not replace it. What it adds is the view a
service manager actually wants: every dealer's open tickets on one screen, with
the last thing each side said, so they can work down the list and answer without
opening sixty documents.

Permission model is the mirror image of `portal_api`: that module narrows
everything to one dealer's subtree, this one requires a KUMAR staff role and then
deliberately spans the whole network.
"""

import frappe
from frappe import _
from frappe.utils import add_days, cint, flt, now_datetime, nowdate

from kumar_service.portal_api import TICKET_DOCTYPES, add_reply, thread_for

#: Who may answer a dealer. A Dealer role must never reach these - a dealer
#: replying to another dealer's ticket would be a data leak dressed as a feature.
STAFF_ROLES = (
	"System Manager",
	"Service Manager",
	"Warranty Approver",
	"Dealer Manager",
	"Quality Engineer",
)


def _require_staff():
	roles = set(frappe.get_roles())
	if not roles.intersection(STAFF_ROLES):
		frappe.throw(_("Not permitted"), frappe.PermissionError)


@frappe.whitelist()
def dealer_conversations(dealer=None, state="open", search=None, limit=200):
	"""Every dealer ticket, with the state of the conversation on each.

	`state`:
	  open      - not yet resolved or settled (the working list)
	  waiting   - the dealer spoke last, so KUMAR owes them a reply
	  answered  - KUMAR spoke last
	  silent    - nobody has said anything yet
	  all
	"""
	_require_staff()
	limit = cint(limit) or 200

	scope = None
	if dealer:
		bounds = frappe.db.get_value("Dealer", dealer, ["lft", "rgt"], as_dict=True)
		if bounds:
			scope = frappe.get_all(
				"Dealer",
				filters={"lft": [">=", bounds.lft], "rgt": ["<=", bounds.rgt]},
				pluck="name",
			)

	portal_users = set(
		frappe.get_all("Dealer", filters={"portal_user": ["!=", ""]}, pluck="portal_user")
	)

	rows = []
	for r in frappe.get_all(
		"Service Request",
		filters={"docstatus": ["<", 2]},
		fields=["name", "dealer", "serial_no", "pump_model", "complaint_category", "status",
		        "priority", "reported_on", "end_customer_name", "end_customer_mobile",
		        "is_under_warranty", "sla_status", "resolution_due_on", "resolved_on",
		        "assigned_technician", "complaint_description"],
		order_by="reported_on desc",
		limit=limit,
	):
		rows.append(
			{
				"kind": "complaint",
				"doctype": "Service Request",
				"name": r.name,
				"dealer": r.dealer,
				"serial_no": r.serial_no,
				"pump_model": r.pump_model,
				"headline": r.complaint_category,
				"detail": r.complaint_description,
				"status": r.status,
				"priority": r.priority,
				"on": r.reported_on,
				"customer": r.end_customer_name,
				"mobile": r.end_customer_mobile,
				"free": cint(r.is_under_warranty),
				"sla_status": r.sla_status,
				"due_on": r.resolution_due_on,
				"closed": bool(r.resolved_on),
				"technician": r.assigned_technician,
				"amount": 0,
			}
		)

	for r in frappe.get_all(
		"Kumar Warranty Claim",
		filters={"docstatus": ["<", 2]},
		fields=["name", "dealer", "serial_no", "pump_model", "claim_type", "workflow_state",
		        "claim_date", "claim_amount", "approved_amount", "settled_on", "root_cause",
		        "technician_report"],
		order_by="claim_date desc",
		limit=limit,
	):
		rows.append(
			{
				"kind": "claim",
				"doctype": "Kumar Warranty Claim",
				"name": r.name,
				"dealer": r.dealer,
				"serial_no": r.serial_no,
				"pump_model": r.pump_model,
				"headline": r.claim_type,
				"detail": r.technician_report,
				"status": r.workflow_state or "Draft",
				"priority": "",
				"on": r.claim_date,
				"customer": "",
				"mobile": "",
				"free": 0,
				"sla_status": r.root_cause,
				"due_on": None,
				"closed": bool(r.settled_on),
				"technician": "",
				"amount": flt(r.claim_amount),
			}
		)

	# One grouped read of the whole conversation set, not one per ticket.
	names = {r["name"] for r in rows}
	msgs = {}
	if names:
		for c in frappe.get_all(
			"Comment",
			filters={
				"comment_type": "Comment",
				"reference_doctype": ["in", list(TICKET_DOCTYPES.values())],
				"reference_name": ["in", list(names)],
			},
			fields=["reference_doctype", "reference_name", "content", "owner", "creation"],
			order_by="creation asc",
		):
			msgs.setdefault((c.reference_doctype, c.reference_name), []).append(c)

	out = []
	needle = (search or "").strip().lower()
	for r in rows:
		if scope is not None and r["dealer"] not in scope:
			continue

		conversation = msgs.get((r["doctype"], r["name"]), [])
		last = conversation[-1] if conversation else None
		r["replies"] = len(conversation)
		r["last_message"] = (
			frappe.utils.strip_html(last.content or "").strip()[:220] if last else ""
		)
		r["last_by"] = last.owner if last else None
		r["last_on"] = last.creation if last else None
		if not last:
			r["conversation"] = "silent"
		elif last.owner in portal_users:
			r["conversation"] = "waiting"
		else:
			r["conversation"] = "answered"

		if r["due_on"] and not r["closed"]:
			r["late"] = 1 if str(r["due_on"]) < str(now_datetime()) else 0
		else:
			r["late"] = 0

		if state == "open" and r["closed"]:
			continue
		if state in ("waiting", "answered", "silent") and r["conversation"] != state:
			continue

		if needle:
			blob = " ".join(
				str(r.get(k) or "")
				for k in ("name", "dealer", "serial_no", "pump_model", "customer", "mobile",
				          "headline", "last_message")
			).lower()
			if needle not in blob:
				continue

		out.append(r)

	# Whoever KUMAR owes a reply to, first; then the late ones; then newest.
	order = {"waiting": 0, "silent": 1, "answered": 2}
	out.sort(key=lambda r: (order.get(r["conversation"], 3), -r["late"], str(r["on"] or "")))

	summary = {
		"total": len(out),
		"waiting": sum(1 for r in out if r["conversation"] == "waiting"),
		"answered": sum(1 for r in out if r["conversation"] == "answered"),
		"silent": sum(1 for r in out if r["conversation"] == "silent"),
		"late": sum(1 for r in out if r["late"]),
	}

	# Per dealer, so a manager can see which outlet is being left waiting.
	by_dealer = {}
	for r in out:
		row = by_dealer.setdefault(
			r["dealer"], {"dealer": r["dealer"], "total": 0, "waiting": 0, "late": 0}
		)
		row["total"] += 1
		if r["conversation"] == "waiting":
			row["waiting"] += 1
		if r["late"]:
			row["late"] += 1
	dealers = sorted(by_dealer.values(), key=lambda d: (-d["waiting"], -d["total"]))

	return {"tickets": out, "summary": summary, "dealers": dealers}


@frappe.whitelist()
def conversation(kind, name):
	"""The full thread on one ticket, for the management screen."""
	_require_staff()
	doctype = TICKET_DOCTYPES.get(kind)
	if not doctype:
		frappe.throw(_("Unknown ticket type"))
	return {"kind": kind, "name": name, "thread": thread_for(doctype, name)}


@frappe.whitelist()
def reply_to_dealer(kind, name, message, mark_responded=1):
	"""KUMAR answering a dealer, and stopping the SLA response clock.

	`mark_responded` is why this exists rather than just a comment: the first real
	reply to a complaint IS the first response the SLA measures, and leaving that
	field to be filled in by hand later is how a service desk ends up reporting
	breaches it did not have.
	"""
	_require_staff()
	doctype = TICKET_DOCTYPES.get(kind)
	if not doctype:
		frappe.throw(_("Unknown ticket type"))
	if not frappe.db.exists(doctype, name):
		frappe.throw(_("{0} does not exist").format(name), frappe.DoesNotExistError)

	dealer = frappe.db.get_value(doctype, name, "dealer")
	notify = set()
	portal_user = frappe.db.get_value("Dealer", dealer, "portal_user")
	if portal_user:
		notify.add(portal_user)
	else:
		# A sub-dealer without its own login is handled through its parent.
		parent = frappe.db.get_value("Dealer", dealer, "parent_dealer")
		hops = 0
		while parent and hops < 8:
			candidate = frappe.db.get_value("Dealer", parent, "portal_user")
			if candidate:
				notify.add(candidate)
				break
			parent = frappe.db.get_value("Dealer", parent, "parent_dealer")
			hops += 1

	add_reply(doctype, name, message, notify_users=notify)

	responded = 0
	if cint(mark_responded) and doctype == "Service Request":
		row = frappe.db.get_value(
			"Service Request", name, ["first_response_on", "response_due_on", "resolved_on"],
			as_dict=True,
		)
		if row and not row.first_response_on:
			stamp = now_datetime()
			# Written with db.set_value on purpose: `first_response_on` has no
			# allow_on_submit, so the document API would refuse it on a submitted
			# request. That means validate() does not run either, so sla_status has
			# to be derived here with the SAME rule the controller uses - otherwise
			# the SLA report would keep calling this an unanswered breach.
			sla = None
			if not row.resolved_on and row.response_due_on:
				sla = "Responded" if stamp <= frappe.utils.get_datetime(row.response_due_on) else "Failed"
			frappe.db.set_value(
				"Service Request",
				name,
				{"first_response_on": stamp, **({"sla_status": sla} if sla else {})},
				update_modified=False,
			)
			responded = 1

	frappe.db.commit()
	return {
		"thread": thread_for(doctype, name),
		"first_response_recorded": responded,
		"notified": sorted(notify),
		"message": (
			_("Reply sent to {0}. First response recorded against the SLA.").format(dealer)
			if responded
			else _("Reply sent to {0}.").format(dealer)
		),
	}
