"""Make the demo data tell the story of a working service operation.

This is for the pitch. KUMAR will judge the product by what the Command Centre
shows in the first ten seconds, and what it showed was forty-six requests of
which none had ever been resolved and forty-three had blown their SLA - the
data of a company whose service desk does not work, wearing the product that is
supposed to fix that.

So this reshapes what the seed left behind into what a healthy month looks like,
relative to TODAY, so it stays convincing whenever the demo is given:

  * most requests resolved, inside their SLA
  * a handful open and being worked, answered on time
  * one or two genuinely late - realism, and it proves the alerting works
  * visits booked for the coming week, not only in the past
  * some warranties about to lapse, because "a customer worth ringing" is the
    dealer's best reason to open the app every morning
  * claims at every stage, so the claims desk has something to decide

It is seeded, so the same picture comes back every run, and idempotent - run it
twice and nothing doubles. It only ever touches documents the demo seed created;
a real site would run it against nothing.

    bench --site kumarpumps.localhost execute kumar_service.setup.demo_story.build_all
"""

import random

import frappe
from frappe.utils import add_days, add_to_date, cint, get_datetime, getdate, now_datetime, nowdate

from kumar_service.utils import EXPIRING_SOON_DAYS, setting

SEED = 2026

# stamped on anything this script creates, so a later run can find it again
DEMO_TAG = "[demo: booked by demo_story]"

# Statuses a request can be left in, and roughly how many of each a healthy
# month has. The counts scale to however many requests exist.
SHAPE = [
	# (status,        share, days_ago_range, first_response_on, resolved)
	("Resolved", 0.52, (8, 60), True, True),
	("Closed", 0.14, (20, 75), True, True),
	# open work is recent: with a 72-hour resolution window, anything older
	# than three days is past due, and a desk where half the open work is
	# late is not the desk being pitched
	("In Progress", 0.14, (0, 2), True, False),
	("Assigned", 0.06, (0, 1), True, False),
	("Awaiting Parts", 0.06, (2, 4), True, False),
	("Open", 0.04, (0, 1), False, False),
	# these two are the point: a real desk is late sometimes, and the manager
	# should see it in red rather than the demo pretending otherwise
	("In Progress", 0.04, (9, 14), False, False),
]


def _rng():
	return random.Random(SEED)


def _at(days_ago, hour, minute=0):
	"""A datetime `days_ago` before now, at a plausible working hour."""
	base = get_datetime(add_days(nowdate(), -days_ago))
	return add_to_date(base, hours=hour, minutes=minute)


# ------------------------------------------------------------------- requests

def requests():
	"""Re-date and re-status every Service Request into the SHAPE above."""
	rows = frappe.get_all(
		"Service Request",
		filters={"docstatus": ["<", 2]},
		fields=["name", "assigned_technician"],
		order_by="name asc",
	)
	if not rows:
		return {"requests": 0}

	rng = _rng()
	response_h = cint(setting("sla_response_hours", 24))
	resolution_h = cint(setting("sla_resolution_hours", 72))

	# deal each request a status by share, deterministically
	deck = []
	for status, share, span, responded, resolved in SHAPE:
		deck += [(status, span, responded, resolved)] * max(1, round(share * len(rows)))
	rng.shuffle(deck)

	counts = {}
	for i, r in enumerate(rows):
		status, (lo, hi), responded, resolved = deck[i % len(deck)]
		days_ago = rng.randint(lo, hi)
		reported = _at(days_ago, rng.randint(8, 17), rng.choice((0, 15, 30, 45)))
		response_due = add_to_date(reported, hours=response_h)
		resolution_due = add_to_date(reported, hours=resolution_h)

		values = {
			"status": status,
			"reported_on": reported,
			"response_due_on": response_due,
			"resolution_due_on": resolution_due,
			"first_response_on": None,
			"resolved_on": None,
		}

		if responded:
			# answered inside the response window, usually well inside it
			values["first_response_on"] = add_to_date(
				reported, hours=rng.choice((1, 2, 3, 5, 8, 20))
			)

		if resolved:
			# resolved inside the resolution window most of the time; a few run
			# right up to it, which is what a real month looks like
			hours = rng.choice((10, 18, 26, 40, 55, 68, 70))
			values["resolved_on"] = add_to_date(reported, hours=hours)
			values["sla_status"] = (
				"Fulfilled" if values["resolved_on"] <= resolution_due else "Failed"
			)
			if not values.get("resolution_summary"):
				values["resolution_summary"] = rng.choice(
					(
						"Foot valve replaced and primed; running normally.",
						"Capacitor replaced at site. Customer shown the starting procedure.",
						"Bearing replaced under warranty; test run for 30 minutes.",
						"Air lock cleared; no fault with the pump.",
						"Impeller replaced; abrasion from sandy water noted to the customer.",
						"Cable joint below water re-made and sealed.",
					)
				)
		elif values["first_response_on"]:
			values["sla_status"] = "Responded"
		elif resolution_due < now_datetime():
			values["sla_status"] = "Failed"
		else:
			values["sla_status"] = "Ongoing"

		# a request that is being worked has somebody working it
		if status in ("In Progress", "Awaiting Parts", "Resolved", "Closed") and not r.assigned_technician:
			techs = frappe.get_all("Service Technician", pluck="name", limit_page_length=0)
			if techs:
				values["assigned_technician"] = rng.choice(techs)

		frappe.db.set_value("Service Request", r.name, values, update_modified=False)
		counts[status] = counts.get(status, 0) + 1

	return {"requests": len(rows), "by_status": counts}


# --------------------------------------------------------------------- visits

def visits():
	"""Past visits sit with the requests they closed; a week of visits is booked."""
	rng = _rng()
	done = {"re_dated": 0, "booked": 0}

	# Every visit the seed created lands the day after its request was
	# reported - and never later than yesterday. A visit that already happened
	# is a past visit; letting one drift into the future made its request look
	# "already booked", so each run booked one fewer and the count never settled.
	yesterday = getdate(add_days(nowdate(), -1))
	for v in frappe.get_all(
		"Service Visit", filters={"docstatus": ["<", 2], "action_taken": ["!=", DEMO_TAG]},
		fields=["name", "service_request"], limit_page_length=0,
	):
		reported = frappe.db.get_value("Service Request", v.service_request, "reported_on")
		if reported:
			when = getdate(add_days(reported, rng.randint(1, 2)))
			frappe.db.set_value(
				"Service Visit", v.name, "visit_date", min(when, yesterday),
				update_modified=False,
			)
			done["re_dated"] += 1

	# Visits this script booked on a previous run are removed before booking
	# again. Without this every refresh added a week of visits on top of the
	# last week's, because re-dating had moved yesterday's "open" requests to
	# resolved while their booked visits stayed in the future.
	for v in frappe.get_all(
		"Service Visit", filters={"action_taken": DEMO_TAG, "docstatus": 0}, pluck="name"
	):
		frappe.delete_doc("Service Visit", v, force=True, ignore_permissions=True)
		done["unbooked"] = done.get("unbooked", 0) + 1

	# and the open ones that have nobody booked get a technician this week
	techs = frappe.get_all("Service Technician", pluck="name", limit_page_length=0)
	if not techs:
		return done
	booked = set(
		frappe.get_all(
			"Service Visit", filters={"docstatus": ["<", 2], "visit_date": [">=", nowdate()]},
			pluck="service_request",
		)
	)
	open_reqs = frappe.get_all(
		"Service Request",
		filters={"status": ["in", ("Assigned", "In Progress", "Awaiting Parts")],
			"docstatus": ["<", 2]},
		fields=["name", "serial_no", "is_under_warranty"],
		order_by="reported_on asc",
		limit_page_length=0,
	)
	for r in open_reqs[:7]:
		if r.name in booked:
			continue
		visit = frappe.get_doc(
			{
				"doctype": "Service Visit",
				"service_request": r.name,
				"serial_no": r.serial_no,
				"technician": rng.choice(techs),
				"visit_date": add_days(nowdate(), rng.randint(0, 6)),
				"visit_type": "On-Site",
				"is_chargeable": 0 if cint(r.is_under_warranty) else 1,
				# marks it as ours, so the next run can take it back
				"action_taken": DEMO_TAG,
			}
		)
		visit.flags.ignore_permissions = True
		visit.insert(ignore_permissions=True)
		done["booked"] += 1
	return done


# ------------------------------------------------------------------- warranty

def warranties():
	"""Some cover about to lapse, some lapsed - the dealer's reason to ring.

	Chosen by a hash of the registration's name rather than a shuffle, so the
	same registrations are picked every run and the rest are put back to a
	healthy expiry. A shuffle looked deterministic and was not: each run picked
	the same slice positions off a list whose members had shifted, so the
	lapsed set grew by a few every time the demo was refreshed.
	"""
	import zlib

	regs = frappe.get_all(
		"Pump Registration", filters={"docstatus": 1},
		fields=["name", "serial_no", "warranty_months", "sale_date"],
		order_by="name asc", limit_page_length=0,
	)
	if not regs:
		return {"registrations": 0}

	def bucket(reg):
		# ~8% expiring soon, ~5% expired, everything else healthy
		h = zlib.crc32(reg.name.encode()) % 100
		if h < 8:
			return "expiring"
		if h < 13:
			return "expired"
		return "healthy"

	def redate(reg, expiry):
		months = cint(reg.warranty_months) or 12
		sale = add_days(expiry, -30 * months)
		frappe.db.set_value(
			"Pump Registration", reg.name,
			{"sale_date": sale, "warranty_start_date": sale, "warranty_expiry_date": expiry},
			update_modified=False,
		)
		# the registration is the record, but every screen reads the serial
		frappe.db.set_value(
			"Serial No", reg.serial_no,
			{"custom_sale_date": sale, "custom_warranty_expiry_date": expiry},
			update_modified=False,
		)

	counts = {"expiring": 0, "expired": 0, "healthy": 0}
	for reg in regs:
		b = bucket(reg)
		# a per-registration offset that is stable across runs
		off = zlib.crc32(reg.serial_no.encode())
		if b == "expiring":
			expiry = add_days(nowdate(), 3 + off % (EXPIRING_SOON_DAYS - 4))
		elif b == "expired":
			expiry = add_days(nowdate(), -(5 + off % 115))
		else:
			# sold in the last ten months, so most of the cover is still ahead
			months = cint(reg.warranty_months) or 12
			expiry = add_days(nowdate(), 30 * months - (off % 300))
		redate(reg, expiry)
		counts[b] += 1

	# let the app's own nightly job derive the statuses, so the demo shows
	# exactly what production would show
	from kumar_service.tasks import update_warranty_status

	update_warranty_status()
	return {"registrations": len(regs), **counts}


# --------------------------------------------------------------------- claims

def claims():
	"""Claims dated into the last two months, so the claims desk is current."""
	rng = _rng()
	rows = frappe.get_all(
		"Kumar Warranty Claim", filters={"docstatus": ["<", 2]},
		fields=["name", "workflow_state", "settled_on"], limit_page_length=0,
	)
	for c in rows:
		days = rng.randint(1, 12) if c.workflow_state in ("Pending Review", "Under Investigation") \
			else rng.randint(8, 60)
		values = {"claim_date": add_days(nowdate(), -days)}
		if c.workflow_state == "Settled":
			values["settled_on"] = add_days(nowdate(), -rng.randint(1, days))
		frappe.db.set_value("Kumar Warranty Claim", c.name, values, update_modified=False)
	return {"claims": len(rows)}


# --------------------------------------------------------------- desk mirror

def sync_desk():
	"""The HD Tickets follow the requests they mirror, since nothing above
	went through the document hooks."""
	if not frappe.db.exists("DocType", "HD Ticket"):
		return {"tickets": 0}
	from kumar_service.desk_bridge import STATUS_TO_DESK

	n = 0
	for t in frappe.get_all(
		"HD Ticket", filters={"custom_service_request": ["is", "set"]},
		fields=["name", "custom_service_request", "status"], limit_page_length=0,
	):
		sr = frappe.db.get_value(
			"Service Request", t.custom_service_request,
			["status", "reported_on", "resolved_on"], as_dict=True,
		)
		if not sr:
			continue
		want = STATUS_TO_DESK.get(sr.status, "Open")
		values = {"opening_date": getdate(sr.reported_on)} if sr.reported_on else {}
		if want != t.status:
			values["status"] = want
		if sr.resolved_on and frappe.get_meta("HD Ticket").has_field("resolution_date"):
			values["resolution_date"] = sr.resolved_on
		if values:
			frappe.db.set_value("HD Ticket", t.name, values, update_modified=False)
			n += 1
	return {"tickets": n}


def build_all():
	out = {
		"requests": requests(),
		"visits": visits(),
		"warranties": warranties(),
		"claims": claims(),
		"desk": sync_desk(),
	}
	frappe.db.commit()
	return out
