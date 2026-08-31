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
def reply_to_dealer(kind, name, message, mark_responded=1, attachments=None, attach_urls=None):
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

	# Two attachment routes because the two callers differ: the Conversations page
	# reads files in the browser and posts base64 (`attachments`); the form's
	# Attach field uploads through frappe first and hands back a URL
	# (`attach_urls`). Either is how a credit note reaches the dealer.
	add_reply(
		doctype, name, message,
		notify_users=notify, attachments=attachments, attach_urls=attach_urls,
	)

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


# ===================================================================== visits
#
# KUMAR's team schedules the visit, and does it on behalf of whoever the pump
# belongs to - a dealer who raised the request, or a customer who bought direct
# and has no login of their own. Either way the desk is where the work is
# arranged, so scheduling lives here rather than on the dealer's side.


@frappe.whitelist()
def visit_board(limit=100):
	"""What needs a visit, what is already booked, and who can go.

	One call for the whole screen. A service manager deciding who goes where
	tomorrow is holding three lists in their head at once, and three round trips
	to paint them is three chances to see a stale one.
	"""
	_require_staff()
	limit = cint(limit) or 100
	today = nowdate()

	open_requests = frappe.get_all(
		"Service Request",
		filters={
			"status": ["not in", ("Resolved", "Closed", "Cancelled")],
			"docstatus": ["<", 2],
		},
		fields=["name", "serial_no", "pump_model", "dealer", "end_customer_name",
			"end_customer_mobile", "status", "priority", "complaint_category",
			"custom_request_type", "is_under_warranty", "reported_on",
			"resolution_due_on"],
		order_by="reported_on asc",
		limit=limit,
	)

	# a request that already has a visit booked is not waiting on one
	booked = set(
		frappe.get_all(
			"Service Visit",
			filters={"docstatus": ["<", 2], "visit_date": [">=", today]},
			pluck="service_request",
		)
	)
	# where to go is on the registration, not the request - and a technician
	# cannot be sent anywhere without it
	sites = {}
	serials = [r["serial_no"] for r in open_requests if r["serial_no"]]
	if serials:
		for reg in frappe.get_all(
			"Pump Registration",
			filters={"serial_no": ["in", serials], "docstatus": 1},
			fields=["serial_no", "installation_address", "district", "state"],
			limit_page_length=0,
		):
			sites.setdefault(reg.serial_no, reg)

	for r in open_requests:
		site = sites.get(r["serial_no"]) or {}
		r["where"] = site.get("installation_address") or ""
		r["district"] = site.get("district") or ""
		r["has_visit"] = r["name"] in booked
		r["overdue"] = bool(
			r["resolution_due_on"] and str(r["resolution_due_on"]) < str(now_datetime())
		)

	visits = frappe.get_all(
		"Service Visit",
		filters={"docstatus": ["<", 2], "visit_date": [">=", today]},
		fields=["name", "service_request", "serial_no", "technician", "visit_date",
			"visit_type", "is_chargeable", "docstatus"],
		order_by="visit_date asc",
		limit=limit,
	)
	for v in visits:
		v["customer"] = frappe.db.get_value(
			"Service Request", v.service_request, "end_customer_name"
		)
		v["dealer"] = frappe.db.get_value("Service Request", v.service_request, "dealer")

	technicians = frappe.get_all(
		"Service Technician",
		filters={"status": "Active"} if frappe.get_meta("Service Technician").get_field("status")
			else {},
		fields=["name", "technician_name", "dealer", "mobile_no"],
		order_by="technician_name",
		limit_page_length=0,
	)

	return {
		"needs_visit": [r for r in open_requests if not r["has_visit"]],
		"scheduled": visits,
		"technicians": technicians,
		"visit_types": ["On-Site", "Workshop", "Telephonic"],
	}


@frappe.whitelist()
def schedule_visit(service_request, technician, visit_date, visit_type="On-Site",
		is_chargeable=None, note=None):
	"""Book a technician onto a request, and tell the dealer it is booked.

	The telling is the point. A visit scheduled in the desk and never mentioned
	is a visit the dealer cannot plan around and the customer is not home for -
	so this writes to the same thread the dealer already reads, through the same
	path every other reply takes.
	"""
	_require_staff()
	if not frappe.db.exists("Service Request", service_request):
		frappe.throw(_("{0} does not exist").format(service_request), frappe.DoesNotExistError)
	if not technician:
		frappe.throw(_("Choose a technician"))
	if not visit_date:
		frappe.throw(_("Choose a date for the visit"))
	if str(visit_date) < str(nowdate()):
		frappe.throw(_("A visit cannot be scheduled in the past"))

	sr = frappe.db.get_value(
		"Service Request", service_request,
		["serial_no", "dealer", "is_under_warranty", "end_customer_name"], as_dict=True,
	)

	# a pump in warranty is not chargeable unless somebody says otherwise
	chargeable = cint(is_chargeable) if is_chargeable is not None else (
		0 if cint(sr.is_under_warranty) else 1
	)

	visit = frappe.get_doc(
		{
			"doctype": "Service Visit",
			"service_request": service_request,
			"serial_no": sr.serial_no,
			"technician": technician,
			"visit_date": visit_date,
			"visit_type": visit_type or "On-Site",
			"is_chargeable": chargeable,
		}
	)
	visit.flags.ignore_permissions = True
	visit.insert(ignore_permissions=True)

	tech_name = frappe.db.get_value("Service Technician", technician, "technician_name") or technician
	when = frappe.utils.formatdate(visit_date, "dd-MM-yyyy")
	message = _("Visit scheduled for {0}. {1} will attend.").format(when, tech_name)
	if chargeable:
		message += " " + _("This visit is chargeable.")
	else:
		message += " " + _("Warranty job - nothing to pay.")
	if note:
		message += "\n\n" + str(note)

	# tell THIS dealer, walking up to a parent when a sub-dealer has no login of
	# its own - the same rule the conversation notifications already use
	from kumar_service.desk_bridge import contact_for

	_contact, portal_user = contact_for(sr.dealer)
	add_reply(
		"Service Request",
		service_request,
		message,
		notify_users={portal_user} if portal_user else None,
	)

	# the request is being worked now, not merely open
	if frappe.db.get_value("Service Request", service_request, "status") in ("Open", "Assigned"):
		frappe.db.set_value("Service Request", service_request, "status", "In Progress")

	frappe.db.commit()
	return {"name": visit.name, "message": message, "chargeable": bool(chargeable)}


# ================================================================== manager
#
# What a manager asks is not what an agent asks. An agent asks "what is my next
# ticket"; a manager asks "what is going wrong, who is it going wrong for, and
# what is it costing me". This is one call because that question is one glance -
# a manager who has to click four times to assemble the picture stops looking.


@frappe.whitelist()
def manager_dashboard(days=30):
	_require_staff()
	days = cint(days) or 30
	since = add_days(nowdate(), -days)
	today = nowdate()
	now = now_datetime()

	OPEN = ("Resolved", "Closed", "Cancelled")

	# ---------------------------------------------------------------- work
	open_requests = frappe.get_all(
		"Service Request",
		filters={"status": ["not in", OPEN], "docstatus": ["<", 2]},
		fields=["name", "dealer", "serial_no", "pump_model", "status", "priority",
			"complaint_category", "custom_request_type", "is_under_warranty",
			"reported_on", "response_due_on", "first_response_on", "resolution_due_on",
			"end_customer_name"],
		limit_page_length=0,
	)
	breached, unanswered = [], []
	for r in open_requests:
		r["overdue"] = bool(r["resolution_due_on"] and str(r["resolution_due_on"]) < str(now))
		r["no_reply"] = not r["first_response_on"] and bool(
			r["response_due_on"] and str(r["response_due_on"]) < str(now)
		)
		if r["overdue"]:
			breached.append(r)
		if r["no_reply"]:
			unanswered.append(r)

	# ---------------------------------------------------------- money owed
	claims = frappe.get_all(
		"Kumar Warranty Claim",
		filters={"docstatus": ["<", 2]},
		fields=["name", "dealer", "serial_no", "claim_type", "claim_amount",
			"approved_amount", "workflow_state", "creation"],
		limit_page_length=0,
	)
	pending = [c for c in claims if c.workflow_state in ("Pending Review", "Under Investigation")]
	approved = [c for c in claims if c.workflow_state == "Approved"]
	settled = [c for c in claims if c.workflow_state == "Settled"
		and str(c.creation)[:10] >= since]

	# ------------------------------------------------------------- warranty
	regs = frappe.get_all(
		"Pump Registration",
		filters={"docstatus": 1},
		fields=["dealer", "warranty_expiry_date"],
		limit_page_length=0,
	)
	soon = add_days(today, 45)
	in_warranty = expiring = expired = 0
	for r in regs:
		e = r.warranty_expiry_date
		if not e:
			continue
		if str(e) < today:
			expired += 1
		elif str(e) <= soon:
			expiring += 1
		else:
			in_warranty += 1

	# --------------------------------------------------------------- visits
	visits = frappe.get_all(
		"Service Visit",
		filters={"docstatus": ["<", 2], "visit_date": [">=", today]},
		fields=["name", "visit_date", "technician", "serial_no", "is_chargeable"],
		order_by="visit_date asc",
		limit_page_length=0,
	)

	# ---------------------------------------------------- the dealer network
	#
	# One row per outlet: what they sell, what they are complaining about, and
	# what they are claiming. A dealer with many pumps and no requests is not
	# necessarily healthy - they may simply not be using the portal - so silence
	# is shown rather than hidden.
	dealers = {}
	for d in frappe.get_all(
		"Dealer", fields=["name", "dealer_name", "city", "state", "is_own_outlet"],
		limit_page_length=0
	):
		dealers[d.name] = {
			"dealer": d.name, "label": d.dealer_name or d.name,
			"city": d.city, "state": d.state, "own": cint(d.is_own_outlet),
			"pumps": 0, "open": 0, "breached": 0, "claims": 0, "claim_value": 0.0,
		}
	for r in regs:
		if r.dealer in dealers:
			dealers[r.dealer]["pumps"] += 1
	for r in open_requests:
		row = dealers.get(r["dealer"])
		if row:
			row["open"] += 1
			if r["overdue"]:
				row["breached"] += 1
	for c in claims:
		row = dealers.get(c.dealer)
		if row and c.workflow_state not in ("Rejected",):
			row["claims"] += 1
			row["claim_value"] += flt(c.approved_amount) or flt(c.claim_amount)

	network = sorted(
		[d for d in dealers.values() if d["pumps"] or d["open"] or d["claims"]],
		key=lambda d: (-d["breached"], -d["open"], -d["pumps"]),
	)

	# ------------------------------------------------- what keeps breaking
	by_category = {}
	for r in frappe.get_all(
		"Service Request",
		filters={"reported_on": [">=", since], "docstatus": ["<", 2]},
		fields=["complaint_category", "custom_request_type"],
		limit_page_length=0,
	):
		key = r.complaint_category or r.custom_request_type or "Other"
		by_category[key] = by_category.get(key, 0) + 1
	top_faults = sorted(
		[{"label": k, "count": v} for k, v in by_category.items()],
		key=lambda x: -x["count"],
	)[:6]

	def slim(rows, n=8):
		return [
			{
				"name": r["name"], "dealer": r["dealer"], "serial_no": r["serial_no"],
				"what": r["custom_request_type"] or r["complaint_category"],
				"customer": r["end_customer_name"], "status": r["status"],
				"reported_on": r["reported_on"],
				"warranty": bool(cint(r["is_under_warranty"])),
			}
			for r in sorted(rows, key=lambda x: str(x["reported_on"]))[:n]
		]

	return {
		"window_days": days,
		"work": {
			"open": len(open_requests),
			"breached": len(breached),
			"unanswered": len(unanswered),
			"visits_booked": len(visits),
			"visits_today": len([v for v in visits if str(v.visit_date) == today]),
		},
		"money": {
			"pending_count": len(pending),
			"pending_value": sum(flt(c.claim_amount) for c in pending),
			"approved_count": len(approved),
			"approved_value": sum(flt(c.approved_amount) or flt(c.claim_amount) for c in approved),
			"settled_count": len(settled),
			"settled_value": sum(flt(c.approved_amount) or flt(c.claim_amount) for c in settled),
		},
		"warranty": {
			"in_warranty": in_warranty, "expiring": expiring, "expired": expired,
			"total": len(regs),
		},
		"needs_you": {
			"breached": slim(breached),
			"unanswered": slim(unanswered),
		},
		"visits": visits[:8],
		"network": network,
		"top_faults": top_faults,
	}


# =================================================================== claims
#
# A claim is money, and the decision on it is a manager's rather than an
# agent's. It moves through a real Workflow - Pending Review, Under
# Investigation, Approved, Settled - and this deliberately drives that workflow
# rather than writing workflow_state behind its back: the transitions carry role
# restrictions, and walking around them would let anyone settle anything.


CLAIM_OPEN = ("Pending Review", "Under Investigation", "Approved")


@frappe.whitelist()
def claims_board(state=None, dealer=None, limit=200):
	"""Every claim that still needs somebody, newest first."""
	_require_staff()
	filters = {"docstatus": ["<", 2]}
	if state:
		filters["workflow_state"] = state
	else:
		filters["workflow_state"] = ["in", CLAIM_OPEN]
	if dealer:
		filters["dealer"] = dealer

	rows = frappe.get_all(
		"Kumar Warranty Claim",
		filters=filters,
		fields=["name", "dealer", "serial_no", "pump_model", "claim_type", "root_cause",
			"claim_amount", "approved_amount", "workflow_state", "claim_date",
			"technician_report", "heat_no", "winding_batch", "service_request",
			"settled_on", "creation"],
		order_by="creation desc",
		limit=cint(limit) or 200,
	)

	# what this particular user may do to each one, so the UI offers only the
	# buttons that will actually work
	for r in rows:
		r["actions"] = _claim_actions(r["workflow_state"])
		r["customer"] = frappe.db.get_value(
			"Service Request", r["service_request"], "end_customer_name"
		) if r["service_request"] else None

	totals = {}
	for s in CLAIM_OPEN + ("Settled", "Rejected"):
		got = frappe.get_all(
			"Kumar Warranty Claim",
			filters={"workflow_state": s, "docstatus": ["<", 2]},
			fields=["claim_amount", "approved_amount"],
			limit_page_length=0,
		)
		totals[s] = {
			"count": len(got),
			"value": sum(flt(g.approved_amount) or flt(g.claim_amount) for g in got),
		}

	return {"claims": rows, "totals": totals, "states": list(CLAIM_OPEN)}


def _claim_actions(state):
	"""The transitions out of a state that this user's roles allow."""
	roles = set(frappe.get_roles())
	out = []
	for t in frappe.get_all(
		"Workflow Transition",
		filters={"parent": "Kumar Warranty Claim Approval", "state": state},
		fields=["action", "next_state", "allowed"],
	):
		if t.allowed in roles or "System Manager" in roles:
			out.append({"action": t.action, "next_state": t.next_state})
	return out


@frappe.whitelist()
def claim_action(name, action, approved_amount=None, remarks=None):
	"""Move a claim through its workflow, and tell the dealer what happened.

	The dealer is told because a claim decided in silence is a dealer ringing to
	ask - and on a rejection they are owed the reason, not just the outcome.
	"""
	_require_staff()
	if not frappe.db.exists("Kumar Warranty Claim", name):
		frappe.throw(_("{0} does not exist").format(name), frappe.DoesNotExistError)

	doc = frappe.get_doc("Kumar Warranty Claim", name)
	allowed = [a["action"] for a in _claim_actions(doc.workflow_state)]
	if action not in allowed:
		frappe.throw(
			_("You cannot {0} a claim that is {1}.").format(action, _(doc.workflow_state)),
			frappe.PermissionError,
		)

	# an approval that does not say how much is not an approval
	if action == "Approve":
		amount = flt(approved_amount) if approved_amount is not None else flt(doc.claim_amount)
		if amount <= 0:
			frappe.throw(_("Approve an amount greater than zero, or reject the claim."))
		if amount > flt(doc.claim_amount):
			frappe.throw(
				_("Approved amount cannot exceed the {0} claimed.").format(
					frappe.utils.fmt_money(doc.claim_amount, currency="INR")
				)
			)
		doc.approved_amount = amount
	if remarks:
		doc.remarks = (doc.remarks + "\n\n" if doc.remarks else "") + str(remarks)
	if action == "Settle" and doc.meta.get_field("settled_on") and not doc.settled_on:
		doc.settled_on = nowdate()
	doc.flags.ignore_permissions = True
	doc.save(ignore_permissions=True)

	from frappe.model.workflow import apply_workflow

	doc = apply_workflow(doc, action)

	# ------------------------------------------------------------- tell them
	money = frappe.utils.fmt_money(
		flt(doc.approved_amount) or flt(doc.claim_amount), currency="INR"
	)
	said = {
		"Review": _("Your claim {0} is being investigated."),
		"Approve": _("Your claim {0} is approved for {1}."),
		"Reject": _("Your claim {0} could not be accepted."),
		"Settle": _("Your claim {0} is settled. {1} has been passed for credit."),
	}.get(action, _("Your claim {0} has moved to {1}."))
	message = said.format(name, money if action in ("Approve", "Settle") else _(doc.workflow_state))
	if remarks:
		message += "\n\n" + str(remarks)

	from kumar_service.desk_bridge import contact_for

	_c, portal_user = contact_for(doc.dealer)
	add_reply(
		"Kumar Warranty Claim", name, message,
		notify_users={portal_user} if portal_user else None,
	)

	frappe.db.commit()
	return {
		"name": name,
		"state": doc.workflow_state,
		"approved_amount": flt(doc.approved_amount),
		"message": message,
	}
