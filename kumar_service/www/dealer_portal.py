"""Mobile-first dealer portal: register a pump, see my registrations and claims."""

import frappe
from frappe import _
from frappe.utils import add_days, cint, nowdate

no_cache = 1


def get_context(context):
	if frappe.session.user == "Guest":
		frappe.throw(_("Please log in to use the dealer portal"), frappe.PermissionError)

	from kumar_service.i18n import apply_language

	context.no_cache = 1
	apply_language(context)
	context.title = _("KUMAR Dealer Portal")

	# define everything the template reads up front - a staff login that is not
	# linked to a dealer must still get a page, not a 500
	context.not_a_dealer = False
	context.is_own_outlet = 0
	context.registrations = []
	context.open_requests = []
	context.claims = []
	context.expiring = []
	context.counts = {"registrations": 0, "open": 0, "claims": 0, "expiring": 0}

	from kumar_service.utils import dealer_and_descendants, user_dealer

	own = user_dealer()
	context.dealer = own.name if own else None

	if not context.dealer:
		context.not_a_dealer = True
		return context

	# a KUMAR branch and an independent dealer sell the same pump on completely
	# different paperwork, so the register form asks them different questions
	context.is_own_outlet = cint(frappe.db.get_value("Dealer", context.dealer, "is_own_outlet"))

	scope = dealer_and_descendants(context.dealer)

	from kumar_service.api import certificate_url

	context.registrations = frappe.get_all(
		"Pump Registration",
		filters={"dealer": ["in", scope], "docstatus": 1},
		fields=["name", "serial_no", "pump_model", "end_customer_name", "end_customer_mobile",
			"sale_date", "warranty_expiry_date"],
		order_by="sale_date desc",
		limit=25,
	)
	# the certificate is what the dealer actually owes the customer, so it
	# belongs on the row rather than three clicks into the desk
	for r in context.registrations:
		r["certificate_url"] = certificate_url(r["name"])

	context.open_requests = frappe.get_all(
		"Service Request",
		filters={
			"dealer": ["in", scope],
			"docstatus": ["<", 2],
			"status": ["in", ["Open", "Assigned", "In Progress", "Awaiting Parts"]],
		},
		fields=["name", "serial_no", "complaint_category", "status", "reported_on"],
		order_by="reported_on desc",
		limit=25,
	)

	context.claims = frappe.get_all(
		"Kumar Warranty Claim",
		filters={"dealer": ["in", scope], "docstatus": ["<", 2]},
		fields=["name", "serial_no", "claim_type", "claim_amount", "workflow_state", "claim_date"],
		order_by="claim_date desc",
		limit=25,
	)

	context.expiring = frappe.get_all(
		"Serial No",
		filters={
			"custom_dealer": ["in", scope],
			"custom_warranty_expiry_date": ["between", [nowdate(), add_days(nowdate(), 30)]],
		},
		fields=["name", "custom_end_customer_name", "custom_end_customer_mobile",
			"custom_warranty_expiry_date"],
		limit=25,
	)

	context.counts = {
		"registrations": frappe.db.count("Pump Registration", {"dealer": ["in", scope], "docstatus": 1}),
		"open": len(context.open_requests),
		"claims": len(context.claims),
		"expiring": len(context.expiring),
	}

	context.performance = _performance(scope, context.dealer)

	# --- everything the dealer can DO from here, so nobody needs the desk ------
	from kumar_service import portal_api

	context.options = portal_api.portal_options()
	context.tickets = portal_api.my_tickets(limit=40)
	context.contacts = portal_api.my_contacts()
	context.outlet = context.contacts["outlet"]

	# Serials this dealer sold, for the complaint and claim pickers. A dealer
	# should never have to remember a serial number to raise a complaint.
	context.my_serials = frappe.get_all(
		"Pump Registration",
		filters={"dealer": ["in", scope], "docstatus": 1},
		fields=["serial_no", "pump_model", "end_customer_name", "end_customer_mobile",
		        "warranty_expiry_date"],
		order_by="sale_date desc",
		limit=300,
	)

	# Spare parts a claim can be raised against, priced from the item master.
	from kumar_service.setup.masters import ITEM_GROUP_COMPONENTS

	context.claim_items = frappe.get_all(
		"Item",
		filters={"item_group": ITEM_GROUP_COMPONENTS, "disabled": 0},
		fields=["name", "item_name", "valuation_rate"],
		order_by="item_name",
		limit=60,
	)

	# Which pumps of theirs KUMAR has flagged as coming off warranty - the
	# dealer's best reason to ring a customer.
	context.product_families = frappe.db.sql(
		"""
		select   c.name as category, count(*) as sold
		from     `tabPump Registration` r
		join     `tabPump Model` m on m.name = r.pump_model
		join     `tabPump Category` c on c.name = m.pump_category
		where    r.docstatus = 1 and r.dealer in %(scope)s
		group by c.name
		order by count(*) desc
		limit 6
		""",
		{"scope": scope},
		as_dict=True,
	)
	return context


def _performance(scope, dealer):
	"""How this shop is doing, and how it sits against the rest of the network.

	A dealer does not want the head-office ranking table; they want to know
	whether this month beat last month and whether anything of theirs is about
	to fall out of warranty. Rank is included because it is the one comparative
	fact that changes behaviour.
	"""
	from frappe.utils import add_months, date_diff, flt, getdate

	today = getdate(nowdate())
	month_start = today.replace(day=1)

	def sold(start, end):
		return frappe.db.count(
			"Pump Registration",
			{"dealer": ["in", scope], "docstatus": 1, "sale_date": ["between", [start, end]]},
		)

	# A rolling thirty days, not the calendar month.
	#
	# On the 8th the month holds eight days of trade, so a headline built on it
	# reads as a collapse and a comparison against all of last month makes it
	# worse. Thirty days always covers the same amount of business whenever the
	# shop happens to open the page.
	window_start = add_days(today, -29)
	prev_end = add_days(window_start, -1)
	prev_start = add_days(prev_end, -29)

	last_30 = sold(window_start, today)
	prev_30 = sold(prev_start, prev_end)
	this_month = sold(month_start, today)

	revenue = flt(
		frappe.db.sql(
			"""select ifnull(sum(base_grand_total), 0) from `tabSales Invoice`
			   where custom_dealer in %(scope)s and docstatus = 1 and is_return = 0
			     and posting_date between %(f)s and %(t)s""",
			{"scope": scope, "f": window_start, "t": today},
		)[0][0]
	)
	in_warranty = frappe.db.count(
		"Serial No",
		{"custom_dealer": ["in", scope], "custom_warranty_expiry_date": [">=", today]},
	)
	outstanding = flt(
		frappe.db.sql(
			"""select ifnull(sum(outstanding_amount), 0) from `tabSales Invoice`
			   where custom_dealer in %(scope)s and docstatus = 1 and is_return = 0""",
			{"scope": scope},
		)[0][0]
	)

	# Rank this month, counting each outlet's whole subtree.
	#
	# Ranking raw `dealer` values would leave every distributor unranked: a
	# group never appears on a registration itself, its sub-dealers do. So sum
	# each outlet over its own nested-set range and rank those, which puts a
	# distributor and a single shop on the same footing.
	sold_by = dict(
		frappe.db.sql(
			"""select r.dealer, count(*) from `tabPump Registration` r
			   where r.docstatus = 1 and r.sale_date between %(f)s and %(t)s
			   group by r.dealer""",
			{"f": window_start, "t": today},
		)
	)
	outlets = frappe.get_all(
		"Dealer", filters={"status": "Active"}, fields=["name", "lft", "rgt", "parent_dealer"]
	)
	# the root of the tree is the company itself, not an outlet competing with
	# its own members
	totals = [
		(o.name, sum(u for n, u in sold_by.items()
			for d2 in [next((x for x in outlets if x.name == n), None)]
			if d2 and o.lft <= d2.lft and d2.rgt <= o.rgt))
		for o in outlets
		if o.parent_dealer
	]
	totals = sorted([t for t in totals if t[1]], key=lambda t: -t[1])
	rank = next((i + 1 for i, (n, _u) in enumerate(totals) if n == dealer), None)
	ranking = totals

	# A percentage off a handful of pumps is noise dressed as insight: one sale
	# last month against forty this month is "+3900%", which reads as a bug.
	# Below the floor, show the two counts and let the reader do the comparing.
	MEANINGFUL_BASE = 5
	change = (
		round((last_30 - prev_30) * 100.0 / prev_30, 1)
		if prev_30 >= MEANINGFUL_BASE
		else None
	)

	return {
		"last_30": last_30,
		"prev_30": prev_30,
		"change_pct": change,
		"this_month": this_month,
		"month_label": today.strftime("%B"),
		"revenue": revenue,
		"outstanding": outstanding,
		"in_warranty": in_warranty,
		"rank": rank,
		"of": len(ranking),
	}
