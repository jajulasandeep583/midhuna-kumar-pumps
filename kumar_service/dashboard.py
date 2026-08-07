"""Aggregates behind the management screens.

One call per screen. Each screen asks a different question of the same month,
so each endpoint returns the whole answer - tiles, series and table - in a
single round trip rather than making the browser stitch six calls together.

Rules that hold for every endpoint here:

* the date window is always explicit and always validated
* a dealer login is re-scoped to its own subtree server-side; the `dealer`
  argument from the client is never trusted
* only submitted documents count towards money, because a draft is not a sale
* nothing writes
"""

import frappe
from frappe import _
from frappe.utils import add_days, cint, date_diff, flt, get_first_day, getdate, nowdate

from kumar_service.permissions import has_full_access
from kumar_service.utils import dealer_and_descendants, user_dealer

MAX_WINDOW_DAYS = 400


# ------------------------------------------------------------------ shared


def _window(from_date=None, to_date=None):
	"""Resolve and sanity-check the reporting window. Defaults to this month."""
	to_date = getdate(to_date or nowdate())
	from_date = getdate(from_date or get_first_day(to_date))

	if from_date > to_date:
		from_date, to_date = to_date, from_date
	if (to_date - from_date).days > MAX_WINDOW_DAYS:
		frappe.throw(
			_("Date range is limited to {0} days").format(MAX_WINDOW_DAYS),
			title=_("Range too wide"),
		)
	return from_date, to_date


def _scope(dealer=None):
	"""The dealers this session may see. None means 'the whole company'.

	A dealer login is pinned to its own subtree whatever it asked for. A
	head-office login may narrow to one dealer, or see everything.
	"""
	own = user_dealer()
	if own:
		return dealer_and_descendants(own.name)
	if not has_full_access():
		frappe.throw(_("Not permitted"), frappe.PermissionError)
	if dealer:
		return dealer_and_descendants(dealer)
	return None


def _require(doctype):
	frappe.has_permission(doctype, "read", throw=True)


def _days(from_date, to_date):
	"""Every date in the window, so a chart has no holes on a quiet day."""
	out = []
	day = getdate(from_date)
	while day <= getdate(to_date):
		out.append(str(day))
		day = add_days(day, 1)
	return out


def _series(rows, from_date, to_date, key="day", value="total"):
	"""Turn sparse `[{day, total}]` rows into a dense day-by-day series."""
	found = {str(getdate(r[key])): flt(r[value]) for r in rows if r.get(key)}
	labels = _days(from_date, to_date)
	return {"labels": labels, "values": [found.get(d, 0) for d in labels]}


def _pct(part, whole):
	return flt(part * 100.0 / whole, 1) if whole else 0.0


# A percentage needs something to be a percentage OF. One pump last period
# against forty this period is "+3900%", which reads as a broken screen rather
# than a good month. Below this, report no figure and let the counts speak.
MEANINGFUL_BASE = 5


def _growth(now, before, base=MEANINGFUL_BASE):
	"""Percent change against the previous period, or None if there isn't a
	previous period worth dividing by.

	Nothing to divide by is not the same as no growth, and it is not "+100%"
	either - that reads as a real doubling. A dealer with no meaningful prior
	period is simply new, and the screen should say so rather than invent a
	number.
	"""
	before = flt(before)
	if before < base:
		return None
	return flt((flt(now) - before) * 100.0 / before, 1)


# -------------------------------------------------------------- 1. overview


@frappe.whitelist()
def management_overview(from_date=None, to_date=None, dealer=None):
	"""The one screen a proprietor looks at: is the month working?"""
	_require("Sales Invoice")
	from_date, to_date = _window(from_date, to_date)
	scope = _scope(dealer)

	dealer_sql, dealer_args = ("", [])
	if scope:
		dealer_sql = " and si.custom_dealer in %(scope)s"
		dealer_args = scope

	args = {"from": from_date, "to": to_date, "scope": scope or [""]}

	sales = frappe.db.sql(
		f"""
		select count(*) as invoices,
		       sum(si.base_grand_total) as revenue,
		       sum(si.base_net_total) as net,
		       sum(si.outstanding_amount) as outstanding
		from `tabSales Invoice` si
		where si.docstatus = 1 and si.is_return = 0
		  and si.posting_date between %(from)s and %(to)s
		  {dealer_sql}
		""",
		args,
		as_dict=True,
	)[0]

	purchase = frappe.db.sql(
		"""
		select count(*) as invoices,
		       sum(base_grand_total) as spend,
		       sum(outstanding_amount) as outstanding
		from `tabPurchase Invoice`
		where docstatus = 1 and is_return = 0
		  and posting_date between %(from)s and %(to)s
		""",
		args,
		as_dict=True,
	)[0]

	produced = frappe.db.sql(
		"""
		select ifnull(sum(sed.qty), 0) as qty, count(distinct se.name) as runs
		from `tabStock Entry` se
		join `tabStock Entry Detail` sed on sed.parent = se.name
		where se.docstatus = 1 and se.purpose = 'Manufacture'
		  and sed.is_finished_item = 1
		  and se.posting_date between %(from)s and %(to)s
		""",
		args,
		as_dict=True,
	)[0]

	# revenue by day, for the headline chart
	revenue_by_day = frappe.db.sql(
		f"""
		select si.posting_date as day, sum(si.base_grand_total) as total
		from `tabSales Invoice` si
		where si.docstatus = 1 and si.is_return = 0
		  and si.posting_date between %(from)s and %(to)s
		  {dealer_sql}
		group by si.posting_date
		""",
		args,
		as_dict=True,
	)

	produced_by_day = frappe.db.sql(
		"""
		select se.posting_date as day, sum(sed.qty) as total
		from `tabStock Entry` se
		join `tabStock Entry Detail` sed on sed.parent = se.name
		where se.docstatus = 1 and se.purpose = 'Manufacture'
		  and sed.is_finished_item = 1
		  and se.posting_date between %(from)s and %(to)s
		group by se.posting_date
		""",
		args,
		as_dict=True,
	)

	reg_filter = {"docstatus": 1, "sale_date": ["between", [from_date, to_date]]}
	sr_filter = {"docstatus": ["<", 2], "reported_on": ["between", [from_date, to_date]]}
	claim_filter = {"docstatus": ["<", 2], "claim_date": ["between", [from_date, to_date]]}
	if scope:
		reg_filter["dealer"] = ["in", scope]
		sr_filter["dealer"] = ["in", scope]
		claim_filter["dealer"] = ["in", scope]

	open_states = ["Open", "Assigned", "In Progress", "Awaiting Parts"]

	tested = frappe.db.sql(
		"""
		select overall_result, count(*) as n
		from `tabPump Test Certificate`
		where docstatus = 1 and date(test_date) between %(from)s and %(to)s
		group by overall_result
		""",
		args,
		as_dict=True,
	)
	tested_total = sum(cint(r.n) for r in tested)
	tested_pass = sum(cint(r.n) for r in tested if r.overall_result == "Pass")

	headcount = frappe.db.count("Employee", {"status": "Active"})
	wage_bill = flt(
		frappe.db.sql(
			"""select sum(net_pay) from `tabSalary Slip`
			where docstatus = 1 and start_date >= %(from)s and end_date <= %(to)s""",
			args,
		)[0][0]
	)
	if not wage_bill:
		# the window may not contain a whole payroll month - show the last run
		wage_bill = flt(
			frappe.db.sql(
				"""select sum(net_pay) from `tabSalary Slip` where docstatus = 1
				and start_date = (select max(start_date) from `tabSalary Slip` where docstatus = 1)"""
			)[0][0]
		)

	revenue = flt(sales.revenue)
	spend = flt(purchase.spend)

	# Gross margin is sales less the cost of what was actually sold - NOT sales
	# less what was bought. In a month where the plant builds 350 pumps and
	# ships 150, purchases include stock still sitting in FG Store, and
	# revenue-minus-purchases reports a collapse that did not happen.
	# The stock ledger already values every outward movement, so use it.
	cogs = -flt(
		frappe.db.sql(
			"""
			select sum(sle.stock_value_difference)
			from `tabStock Ledger Entry` sle
			where sle.is_cancelled = 0
			  and sle.actual_qty < 0
			  and sle.voucher_type in ('Delivery Note', 'Sales Invoice')
			  and sle.posting_date between %(from)s and %(to)s
			""",
			args,
		)[0][0]
	)
	net_sales = flt(sales.net)

	return {
		"from_date": str(from_date),
		"to_date": str(to_date),
		"dealer_scope": scope,
		"tiles": {
			"revenue": revenue,
			"invoices": cint(sales.invoices),
			"receivable": flt(sales.outstanding),
			"purchase_spend": spend,
			"payable": flt(purchase.outstanding),
			"cogs": cogs,
			"gross_profit": net_sales - cogs,
			"gross_margin_pct": _pct(net_sales - cogs, net_sales),
			"units_produced": flt(produced.qty),
			"production_runs": cint(produced.runs),
			"units_registered": frappe.db.count("Pump Registration", reg_filter),
			"complaints": frappe.db.count("Service Request", sr_filter),
			"complaints_open": frappe.db.count(
				"Service Request", dict(sr_filter, status=["in", open_states])
			),
			"claims": frappe.db.count("Kumar Warranty Claim", claim_filter),
			"test_pass_pct": _pct(tested_pass, tested_total),
			"tested": tested_total,
			"headcount": headcount,
			"wage_bill": wage_bill,
		},
		"revenue_series": _series(revenue_by_day, from_date, to_date),
		"production_series": _series(produced_by_day, from_date, to_date),
		"top_models": _top_models(from_date, to_date, scope),
		"pipeline": _pipeline(from_date, to_date, scope),
	}


def _top_models(from_date, to_date, scope, limit=8):
	dealer_sql = " and si.custom_dealer in %(scope)s" if scope else ""
	return frappe.db.sql(
		f"""
		select ifnull(i.custom_pump_model, sii.item_code) as model,
		       sum(sii.qty) as qty,
		       sum(sii.base_net_amount) as revenue
		from `tabSales Invoice Item` sii
		join `tabSales Invoice` si on si.name = sii.parent
		left join `tabItem` i on i.name = sii.item_code
		where si.docstatus = 1 and si.is_return = 0
		  and si.posting_date between %(from)s and %(to)s
		  {dealer_sql}
		group by model
		order by revenue desc
		limit {cint(limit)}
		""",
		{"from": from_date, "to": to_date, "scope": scope or [""]},
		as_dict=True,
	)


def _pipeline(from_date, to_date, scope):
	"""Order -> delivery -> invoice, so a gap in the middle is visible."""
	dealer_so = " and custom_dealer in %(scope)s" if scope else ""
	dealer_dn = " and custom_dealer in %(scope)s" if scope else ""
	dealer_si = " and custom_dealer in %(scope)s" if scope else ""
	args = {"from": from_date, "to": to_date, "scope": scope or [""]}

	def one(sql):
		row = frappe.db.sql(sql, args, as_dict=True)[0]
		return {"count": cint(row.n), "value": flt(row.total)}

	return {
		"orders": one(
			f"""select count(*) n, sum(base_grand_total) total from `tabSales Order`
			where docstatus = 1 and transaction_date between %(from)s and %(to)s {dealer_so}"""
		),
		"delivered": one(
			f"""select count(*) n, sum(base_grand_total) total from `tabDelivery Note`
			where docstatus = 1 and posting_date between %(from)s and %(to)s {dealer_dn}"""
		),
		"invoiced": one(
			f"""select count(*) n, sum(base_grand_total) total from `tabSales Invoice`
			where docstatus = 1 and is_return = 0
			and posting_date between %(from)s and %(to)s {dealer_si}"""
		),
	}


# ---------------------------------------------------- 2. dealer distribution


@frappe.whitelist()
def dealer_distribution(from_date=None, to_date=None, dealer=None):
	"""Who is selling what, where - the whole network on one screen."""
	_require("Dealer")
	from_date, to_date = _window(from_date, to_date)
	scope = _scope(dealer)

	# the same span again, immediately before, so every dealer can be read as
	# "up or down" rather than just a number with nothing to compare it to
	span = date_diff(to_date, from_date)
	prev_to = add_days(from_date, -1)
	prev_from = add_days(prev_to, -span)

	filters = {
		"scope": scope or [""],
		"from": from_date,
		"to": to_date,
		"prev_from": prev_from,
		"prev_to": prev_to,
		"today": nowdate(),
	}
	scope_sql = " and d.name in %(scope)s" if scope else ""

	rows = frappe.db.sql(
		f"""
		select
			d.name, d.dealer_name, d.dealer_type, d.city, d.state, d.pincode,
			d.parent_dealer, d.status, d.is_group, d.lft, d.rgt,
			d.is_own_outlet, d.mobile_no, d.contact_person,
			(select count(*) from `tabPump Registration` r
			   where r.dealer = d.name and r.docstatus = 1
			     and r.sale_date between %(from)s and %(to)s) as registrations,
			(select count(*) from `tabPump Registration` r
			   where r.dealer = d.name and r.docstatus = 1
			     and r.sale_date between %(prev_from)s and %(prev_to)s) as registrations_prev,
			(select count(*) from `tabPump Registration` r
			   where r.dealer = d.name and r.docstatus = 1) as registrations_all,
			(select max(r.sale_date) from `tabPump Registration` r
			   where r.dealer = d.name and r.docstatus = 1) as last_sale_date,
			(select ifnull(sum(si.base_grand_total), 0) from `tabSales Invoice` si
			   where si.custom_dealer = d.name and si.docstatus = 1 and si.is_return = 0
			     and si.posting_date between %(from)s and %(to)s) as revenue,
			(select ifnull(sum(si.base_grand_total), 0) from `tabSales Invoice` si
			   where si.custom_dealer = d.name and si.docstatus = 1 and si.is_return = 0
			     and si.posting_date between %(prev_from)s and %(prev_to)s) as revenue_prev,
			(select ifnull(sum(si.outstanding_amount), 0) from `tabSales Invoice` si
			   where si.custom_dealer = d.name and si.docstatus = 1
			     and si.is_return = 0) as outstanding,
			(select count(*) from `tabService Request` sr
			   where sr.dealer = d.name and sr.docstatus < 2
			     and date(sr.reported_on) between %(from)s and %(to)s) as complaints,
			(select count(*) from `tabKumar Warranty Claim` c
			   where c.dealer = d.name and c.docstatus < 2
			     and c.claim_date between %(from)s and %(to)s) as claims,
			(select count(*) from `tabSerial No` sn
			   where sn.custom_dealer = d.name
			     and sn.custom_warranty_expiry_date between %(today)s
			         and date_add(%(today)s, interval 30 day)) as expiring_30d
		from `tabDealer` d
		where 1 = 1 {scope_sql}
		order by revenue desc, registrations desc, d.name
		""",
		filters,
		as_dict=True,
	)

	for row in rows:
		row["complaint_rate_pct"] = _pct(row.complaints, row.registrations_all)
		row["growth_pct"] = _growth(row.registrations, row.registrations_prev)
		row["revenue_growth_pct"] = _growth(row.revenue, row.revenue_prev)
		row["avg_ticket"] = flt(row.revenue) / row.registrations if row.registrations else 0
		row["channel"] = "KUMAR Branch" if cint(row.is_own_outlet) else "Independent"
		row["days_since_sale"] = (
			date_diff(nowdate(), row.last_sale_date) if row.last_sale_date else None
		)

	# where the pumps actually landed, which is not the same as who sold them
	geography = frappe.db.sql(
		f"""
		select r.district, r.state, count(*) as units
		from `tabPump Registration` r
		{"join `tabDealer` d on d.name = r.dealer" if scope else ""}
		where r.docstatus = 1 and r.sale_date between %(from)s and %(to)s
		  and ifnull(r.district, '') != ''
		  {" and r.dealer in %(scope)s" if scope else ""}
		group by r.district, r.state
		order by units desc
		limit 25
		""",
		filters,
		as_dict=True,
	)

	application = frappe.db.sql(
		f"""
		select ifnull(application_type, 'Unspecified') as application, count(*) as units
		from `tabPump Registration`
		where docstatus = 1 and sale_date between %(from)s and %(to)s
		  {" and dealer in %(scope)s" if scope else ""}
		group by application
		order by units desc
		""",
		filters,
		as_dict=True,
	)

	by_type = {}
	for row in rows:
		key = row.dealer_type or "Unclassified"
		bucket = by_type.setdefault(key, {"dealers": 0, "registrations": 0, "revenue": 0.0})
		bucket["dealers"] += 1
		bucket["registrations"] += cint(row.registrations)
		bucket["revenue"] += flt(row.revenue)

	# The two halves of the business. Selling into the dealer network and
	# selling over our own counter carry different margins and different risk,
	# and adding them into one number hides both.
	channels = frappe.db.sql(
		f"""
		select
			case when ifnull(d.is_own_outlet, 0) = 1 then 'KUMAR Branch' else 'Independent' end
				as channel,
			count(distinct d.name) as dealers,
			count(r.name) as units
		from `tabDealer` d
		left join `tabPump Registration` r
		       on r.dealer = d.name and r.docstatus = 1
		      and r.sale_date between %(from)s and %(to)s
		where ifnull(d.is_group, 0) = 0 {scope_sql}
		group by channel
		""",
		filters,
		as_dict=True,
	)
	channel_revenue = {
		r.channel: flt(r.revenue)
		for r in frappe.db.sql(
			f"""
			select
				case when ifnull(d.is_own_outlet, 0) = 1 then 'KUMAR Branch' else 'Independent' end
					as channel,
				ifnull(sum(si.base_grand_total), 0) as revenue
			from `tabSales Invoice` si
			join `tabDealer` d on d.name = si.custom_dealer
			where si.docstatus = 1 and si.is_return = 0
			  and si.posting_date between %(from)s and %(to)s {scope_sql}
			group by channel
			""",
			filters,
			as_dict=True,
		)
	}
	for row in channels:
		row["revenue"] = channel_revenue.get(row.channel, 0.0)

	# units per day, split by channel, so a slump is visible as it happens
	trend = frappe.db.sql(
		f"""
		select
			r.sale_date as day,
			case when ifnull(d.is_own_outlet, 0) = 1 then 'KUMAR Branch' else 'Independent' end
				as channel,
			count(*) as units
		from `tabPump Registration` r
		join `tabDealer` d on d.name = r.dealer
		where r.docstatus = 1 and r.sale_date between %(from)s and %(to)s {scope_sql}
		group by r.sale_date, channel
		order by r.sale_date
		""",
		filters,
		as_dict=True,
	)
	days = sorted({str(t.day) for t in trend})
	series = {"KUMAR Branch": dict.fromkeys(days, 0), "Independent": dict.fromkeys(days, 0)}
	for t in trend:
		series.setdefault(t.channel, dict.fromkeys(days, 0))[str(t.day)] = cint(t.units)

	sellers = [r for r in rows if not cint(r.is_group)]
	return {
		"from_date": str(from_date),
		"to_date": str(to_date),
		"prev_from": str(prev_from),
		"prev_to": str(prev_to),
		"dealers": rows,
		"geography": geography,
		"application_mix": application,
		"by_type": [dict(dealer_type=k, **v) for k, v in sorted(by_type.items())],
		"channels": channels,
		"trend": {"days": days, "series": {k: [v[d] for d in days] for k, v in series.items()}},
		# the league table the branch manager actually rings people from
		"leaderboard": sorted(
			sellers, key=lambda r: cint(r.registrations), reverse=True
		)[:10],
		"needs_a_call": sorted(
			[r for r in sellers if not cint(r.registrations) and r.status == "Active"],
			key=lambda r: (r.days_since_sale is None, -(r.days_since_sale or 0)),
		),
		"totals": {
			"dealers": len(rows),
			"active": sum(1 for r in rows if r.status == "Active"),
			"registrations": sum(cint(r.registrations) for r in rows),
			"registrations_prev": sum(cint(r.registrations_prev) for r in rows),
			"growth_pct": _growth(
				sum(cint(r.registrations) for r in rows),
				sum(cint(r.registrations_prev) for r in rows),
			),
			"revenue": sum(flt(r.revenue) for r in rows),
			"revenue_prev": sum(flt(r.revenue_prev) for r in rows),
			"revenue_growth_pct": _growth(
				sum(flt(r.revenue) for r in rows), sum(flt(r.revenue_prev) for r in rows)
			),
			"outstanding": sum(flt(r.outstanding) for r in rows),
			"selling": sum(1 for r in sellers if cint(r.registrations)),
			"silent": sum(1 for r in sellers if not cint(r.registrations)),
			"complaints": sum(cint(r.complaints) for r in rows),
			"claims": sum(cint(r.claims) for r in rows),
		},
	}


# ----------------------------------------------------------- 3. sales


@frappe.whitelist()
def sales_analytics(from_date=None, to_date=None, dealer=None):
	_require("Sales Invoice")
	from_date, to_date = _window(from_date, to_date)
	scope = _scope(dealer)

	args = {"from": from_date, "to": to_date, "scope": scope or [""]}
	dealer_sql = " and si.custom_dealer in %(scope)s" if scope else ""

	by_day = frappe.db.sql(
		f"""
		select si.posting_date as day, sum(si.base_grand_total) as total
		from `tabSales Invoice` si
		where si.docstatus = 1 and si.is_return = 0
		  and si.posting_date between %(from)s and %(to)s {dealer_sql}
		group by si.posting_date
		""",
		args,
		as_dict=True,
	)

	units_by_day = frappe.db.sql(
		f"""
		select si.posting_date as day, sum(sii.qty) as total
		from `tabSales Invoice Item` sii
		join `tabSales Invoice` si on si.name = sii.parent
		where si.docstatus = 1 and si.is_return = 0
		  and si.posting_date between %(from)s and %(to)s {dealer_sql}
		group by si.posting_date
		""",
		args,
		as_dict=True,
	)

	top_dealers = frappe.db.sql(
		f"""
		select ifnull(si.custom_dealer, '(direct)') as dealer,
		       count(distinct si.name) as invoices,
		       sum(sii.qty) as units,
		       sum(si.base_grand_total) / count(distinct sii.parent) * 0 +
		         sum(sii.base_net_amount) as revenue
		from `tabSales Invoice Item` sii
		join `tabSales Invoice` si on si.name = sii.parent
		where si.docstatus = 1 and si.is_return = 0
		  and si.posting_date between %(from)s and %(to)s {dealer_sql}
		group by dealer
		order by revenue desc
		limit 15
		""",
		args,
		as_dict=True,
	)

	top_customers = frappe.db.sql(
		f"""
		select si.customer, si.customer_name,
		       count(*) as invoices,
		       sum(si.base_grand_total) as revenue,
		       sum(si.outstanding_amount) as outstanding
		from `tabSales Invoice` si
		where si.docstatus = 1 and si.is_return = 0
		  and si.posting_date between %(from)s and %(to)s {dealer_sql}
		group by si.customer, si.customer_name
		order by revenue desc
		limit 15
		""",
		args,
		as_dict=True,
	)

	by_category = frappe.db.sql(
		f"""
		select ifnull(pm.pump_category, 'Uncategorised') as category,
		       sum(sii.qty) as units, sum(sii.base_net_amount) as revenue
		from `tabSales Invoice Item` sii
		join `tabSales Invoice` si on si.name = sii.parent
		left join `tabItem` i on i.name = sii.item_code
		left join `tabPump Model` pm on pm.name = i.custom_pump_model
		where si.docstatus = 1 and si.is_return = 0
		  and si.posting_date between %(from)s and %(to)s {dealer_sql}
		group by category
		order by revenue desc
		""",
		args,
		as_dict=True,
	)

	invoices = frappe.db.sql(
		f"""
		select si.name, si.posting_date, si.customer_name, si.custom_dealer as dealer,
		       si.base_grand_total as amount, si.outstanding_amount as outstanding,
		       si.status, si.due_date
		from `tabSales Invoice` si
		where si.docstatus = 1 and si.is_return = 0
		  and si.posting_date between %(from)s and %(to)s {dealer_sql}
		order by si.posting_date desc, si.name desc
		limit 300
		""",
		args,
		as_dict=True,
	)

	ageing = frappe.db.sql(
		f"""
		select
			sum(case when datediff(curdate(), si.due_date) <= 0 then si.outstanding_amount else 0 end) as not_due,
			sum(case when datediff(curdate(), si.due_date) between 1 and 30 then si.outstanding_amount else 0 end) as d30,
			sum(case when datediff(curdate(), si.due_date) between 31 and 60 then si.outstanding_amount else 0 end) as d60,
			sum(case when datediff(curdate(), si.due_date) > 60 then si.outstanding_amount else 0 end) as d90
		from `tabSales Invoice` si
		where si.docstatus = 1 and si.is_return = 0 and si.outstanding_amount > 0 {dealer_sql}
		""",
		args,
		as_dict=True,
	)[0]

	totals = frappe.db.sql(
		f"""
		select count(*) as invoices, sum(si.base_grand_total) as revenue,
		       sum(si.base_net_total) as net, sum(si.total_taxes_and_charges) as tax,
		       sum(si.outstanding_amount) as outstanding
		from `tabSales Invoice` si
		where si.docstatus = 1 and si.is_return = 0
		  and si.posting_date between %(from)s and %(to)s {dealer_sql}
		""",
		args,
		as_dict=True,
	)[0]

	units = flt(
		frappe.db.sql(
			f"""select sum(sii.qty) from `tabSales Invoice Item` sii
			join `tabSales Invoice` si on si.name = sii.parent
			where si.docstatus = 1 and si.is_return = 0
			and si.posting_date between %(from)s and %(to)s {dealer_sql}""",
			args,
		)[0][0]
	)

	return {
		"from_date": str(from_date),
		"to_date": str(to_date),
		"tiles": {
			"revenue": flt(totals.revenue),
			"net": flt(totals.net),
			"tax": flt(totals.tax),
			"invoices": cint(totals.invoices),
			"units": units,
			"outstanding": flt(totals.outstanding),
			"avg_invoice": flt(totals.revenue) / cint(totals.invoices) if totals.invoices else 0,
			"avg_realisation": flt(totals.net) / units if units else 0,
		},
		"revenue_series": _series(by_day, from_date, to_date),
		"units_series": _series(units_by_day, from_date, to_date),
		"top_dealers": top_dealers,
		"top_customers": top_customers,
		"top_models": _top_models(from_date, to_date, scope, limit=12),
		"by_category": by_category,
		"pipeline": _pipeline(from_date, to_date, scope),
		"ageing": ageing,
		"invoices": invoices,
	}


# -------------------------------------------------------- 4. purchase


@frappe.whitelist()
def purchase_analytics(from_date=None, to_date=None):
	_require("Purchase Invoice")
	from_date, to_date = _window(from_date, to_date)
	args = {"from": from_date, "to": to_date}

	by_day = frappe.db.sql(
		"""
		select posting_date as day, sum(base_grand_total) as total
		from `tabPurchase Invoice`
		where docstatus = 1 and is_return = 0 and posting_date between %(from)s and %(to)s
		group by posting_date
		""",
		args,
		as_dict=True,
	)

	top_suppliers = frappe.db.sql(
		"""
		select pi.supplier, pi.supplier_name,
		       count(*) as invoices,
		       sum(pi.base_grand_total) as spend,
		       sum(pi.outstanding_amount) as outstanding
		from `tabPurchase Invoice` pi
		where pi.docstatus = 1 and pi.is_return = 0
		  and pi.posting_date between %(from)s and %(to)s
		group by pi.supplier, pi.supplier_name
		order by spend desc
		limit 15
		""",
		args,
		as_dict=True,
	)

	top_items = frappe.db.sql(
		"""
		select pii.item_code, pii.item_name, i.item_group,
		       sum(pii.qty) as qty, pii.uom,
		       sum(pii.base_net_amount) as value,
		       sum(pii.base_net_amount) / nullif(sum(pii.qty), 0) as avg_rate
		from `tabPurchase Invoice Item` pii
		join `tabPurchase Invoice` pi on pi.name = pii.parent
		left join `tabItem` i on i.name = pii.item_code
		where pi.docstatus = 1 and pi.is_return = 0
		  and pi.posting_date between %(from)s and %(to)s
		group by pii.item_code, pii.item_name, i.item_group, pii.uom
		order by value desc
		limit 20
		""",
		args,
		as_dict=True,
	)

	by_group = frappe.db.sql(
		"""
		select ifnull(i.item_group, 'Ungrouped') as item_group,
		       sum(pii.base_net_amount) as value
		from `tabPurchase Invoice Item` pii
		join `tabPurchase Invoice` pi on pi.name = pii.parent
		left join `tabItem` i on i.name = pii.item_code
		where pi.docstatus = 1 and pi.is_return = 0
		  and pi.posting_date between %(from)s and %(to)s
		group by item_group
		order by value desc
		""",
		args,
		as_dict=True,
	)

	# the pipeline: what is ordered, what has arrived, what is billed
	orders = frappe.db.sql(
		"""
		select count(*) as n, sum(base_grand_total) as total,
		       sum(case when status in ('To Receive and Bill', 'To Receive') then 1 else 0 end) as pending_receipt,
		       sum(case when status in ('To Bill', 'To Receive and Bill') then 1 else 0 end) as pending_bill
		from `tabPurchase Order`
		where docstatus = 1 and transaction_date between %(from)s and %(to)s
		""",
		args,
		as_dict=True,
	)[0]

	receipts = frappe.db.sql(
		"""
		select count(*) as n, sum(base_grand_total) as total
		from `tabPurchase Receipt`
		where docstatus = 1 and posting_date between %(from)s and %(to)s
		""",
		args,
		as_dict=True,
	)[0]

	requests = frappe.db.sql(
		"""
		select count(*) as n,
		       sum(case when status not in ('Stopped', 'Cancelled') and per_ordered < 100 then 1 else 0 end) as open
		from `tabMaterial Request`
		where docstatus = 1 and transaction_date between %(from)s and %(to)s
		""",
		args,
		as_dict=True,
	)[0]

	totals = frappe.db.sql(
		"""
		select count(*) as invoices, sum(base_grand_total) as spend,
		       sum(base_net_total) as net, sum(total_taxes_and_charges) as tax,
		       sum(outstanding_amount) as outstanding
		from `tabPurchase Invoice`
		where docstatus = 1 and is_return = 0 and posting_date between %(from)s and %(to)s
		""",
		args,
		as_dict=True,
	)[0]

	ageing = frappe.db.sql(
		"""
		select
			sum(case when datediff(curdate(), due_date) <= 0 then outstanding_amount else 0 end) as not_due,
			sum(case when datediff(curdate(), due_date) between 1 and 30 then outstanding_amount else 0 end) as d30,
			sum(case when datediff(curdate(), due_date) between 31 and 60 then outstanding_amount else 0 end) as d60,
			sum(case when datediff(curdate(), due_date) > 60 then outstanding_amount else 0 end) as d90
		from `tabPurchase Invoice`
		where docstatus = 1 and is_return = 0 and outstanding_amount > 0
		""",
		as_dict=True,
	)[0]

	open_orders = frappe.db.sql(
		"""
		select name, transaction_date, supplier, base_grand_total as amount,
		       status, per_received, per_billed, schedule_date
		from `tabPurchase Order`
		where docstatus = 1 and status not in ('Completed', 'Closed', 'Cancelled')
		order by transaction_date desc
		limit 200
		""",
		as_dict=True,
	)

	invoices = frappe.db.sql(
		"""
		select name, posting_date, supplier, base_grand_total as amount,
		       outstanding_amount as outstanding, status, due_date, bill_no
		from `tabPurchase Invoice`
		where docstatus = 1 and is_return = 0 and posting_date between %(from)s and %(to)s
		order by posting_date desc, name desc
		limit 300
		""",
		args,
		as_dict=True,
	)

	return {
		"from_date": str(from_date),
		"to_date": str(to_date),
		"tiles": {
			"spend": flt(totals.spend),
			"net": flt(totals.net),
			"tax": flt(totals.tax),
			"invoices": cint(totals.invoices),
			"outstanding": flt(totals.outstanding),
			"orders": cint(orders.n),
			"order_value": flt(orders.total),
			"pending_receipt": cint(orders.pending_receipt),
			"pending_bill": cint(orders.pending_bill),
			"receipts": cint(receipts.n),
			"receipt_value": flt(receipts.total),
			"requests": cint(requests.n),
			"requests_open": cint(requests.open),
			"suppliers": frappe.db.count("Supplier"),
		},
		"spend_series": _series(by_day, from_date, to_date),
		"top_suppliers": top_suppliers,
		"top_items": top_items,
		"by_group": by_group,
		"ageing": ageing,
		"open_orders": open_orders,
		"invoices": invoices,
	}


# ------------------------------------------------------ 5. production


@frappe.whitelist()
def production_daily(from_date=None, to_date=None):
	"""The shop-floor board: what came off the line, and did it pass."""
	_require("Work Order")
	from_date, to_date = _window(from_date, to_date)
	args = {"from": from_date, "to": to_date}

	produced_by_day = frappe.db.sql(
		"""
		select se.posting_date as day, sum(sed.qty) as total
		from `tabStock Entry` se
		join `tabStock Entry Detail` sed on sed.parent = se.name
		where se.docstatus = 1 and se.purpose = 'Manufacture' and sed.is_finished_item = 1
		  and se.posting_date between %(from)s and %(to)s
		group by se.posting_date
		""",
		args,
		as_dict=True,
	)

	tested_by_day = frappe.db.sql(
		"""
		select date(test_date) as day,
		       count(*) as total,
		       sum(case when overall_result = 'Pass' then 1 else 0 end) as passed
		from `tabPump Test Certificate`
		where docstatus = 1 and date(test_date) between %(from)s and %(to)s
		group by date(test_date)
		""",
		args,
		as_dict=True,
	)

	by_shift = frappe.db.sql(
		"""
		select ifnull(se.custom_shift, 'Unassigned') as shift, sum(sed.qty) as units,
		       count(distinct se.name) as runs
		from `tabStock Entry` se
		join `tabStock Entry Detail` sed on sed.parent = se.name
		where se.docstatus = 1 and se.purpose = 'Manufacture' and sed.is_finished_item = 1
		  and se.posting_date between %(from)s and %(to)s
		group by shift
		order by shift
		""",
		args,
		as_dict=True,
	)

	by_model = frappe.db.sql(
		"""
		select ifnull(i.custom_pump_model, sed.item_code) as model,
		       sum(sed.qty) as units
		from `tabStock Entry` se
		join `tabStock Entry Detail` sed on sed.parent = se.name
		left join `tabItem` i on i.name = sed.item_code
		where se.docstatus = 1 and se.purpose = 'Manufacture' and sed.is_finished_item = 1
		  and se.posting_date between %(from)s and %(to)s
		group by model
		order by units desc
		limit 15
		""",
		args,
		as_dict=True,
	)

	work_orders = frappe.db.sql(
		"""
		select wo.name, wo.production_item, wo.qty, wo.produced_qty, wo.status,
		       wo.planned_start_date, wo.expected_delivery_date,
		       wo.custom_shift as shift, wo.custom_supervisor as supervisor,
		       wo.custom_heat_no as heat_no, wo.custom_winding_batch as winding_batch,
		       i.custom_pump_model as model
		from `tabWork Order` wo
		left join `tabItem` i on i.name = wo.production_item
		where wo.docstatus = 1
		  and date(wo.planned_start_date) between %(from)s and %(to)s
		order by wo.planned_start_date desc
		limit 300
		""",
		args,
		as_dict=True,
	)

	wo_status = frappe.db.sql(
		"""
		select status, count(*) as n, sum(qty) as planned, sum(produced_qty) as produced
		from `tabWork Order`
		where docstatus = 1 and date(planned_start_date) between %(from)s and %(to)s
		group by status
		""",
		args,
		as_dict=True,
	)

	heats = frappe.db.sql(
		"""
		select heat_date as day, count(*) as heats, sum(charge_weight_kg) as charge_kg
		from `tabHeat Record`
		where heat_date between %(from)s and %(to)s
		group by heat_date
		""",
		args,
		as_dict=True,
	)

	windings = frappe.db.sql(
		"""
		select winding_date as day, sum(qty_produced) as produced,
		       sum(qty_rejected) as rejected
		from `tabWinding Batch Record`
		where winding_date between %(from)s and %(to)s
		group by winding_date
		""",
		args,
		as_dict=True,
	)

	rejects = frappe.db.sql(
		"""
		select ifnull(sum(qty_rejected), 0) as rejected, ifnull(sum(qty_produced), 0) as produced
		from `tabWinding Batch Record`
		where winding_date between %(from)s and %(to)s
		""",
		args,
		as_dict=True,
	)[0]

	tested_total = sum(cint(r.total) for r in tested_by_day)
	tested_pass = sum(cint(r.passed) for r in tested_by_day)
	produced_total = sum(flt(r.total) for r in produced_by_day)

	# how much of the month's output has already been sold
	dispatched = flt(
		frappe.db.sql(
			"""select sum(dni.qty) from `tabDelivery Note Item` dni
			join `tabDelivery Note` dn on dn.name = dni.parent
			where dn.docstatus = 1 and dn.posting_date between %(from)s and %(to)s""",
			args,
		)[0][0]
	)

	fg_stock = flt(
		frappe.db.sql(
			"""select sum(actual_qty) from `tabBin` b
			join `tabItem` i on i.name = b.item_code
			where i.custom_is_finished_pump = 1"""
		)[0][0]
	)

	days = max((getdate(to_date) - getdate(from_date)).days + 1, 1)

	return {
		"from_date": str(from_date),
		"to_date": str(to_date),
		"tiles": {
			"units_produced": produced_total,
			"daily_average": flt(produced_total / days, 1),
			"work_orders": sum(cint(r.n) for r in wo_status),
			"wo_completed": sum(cint(r.n) for r in wo_status if r.status == "Completed"),
			"wo_in_process": sum(
				cint(r.n) for r in wo_status if r.status in ("In Process", "Not Started")
			),
			"tested": tested_total,
			"test_pass_pct": _pct(tested_pass, tested_total),
			"heats": sum(cint(r.heats) for r in heats),
			"charge_kg": sum(flt(r.charge_kg) for r in heats),
			"winding_produced": flt(rejects.produced),
			"winding_reject_pct": _pct(flt(rejects.rejected), flt(rejects.produced)),
			"dispatched": dispatched,
			"fg_stock": fg_stock,
		},
		"produced_series": _series(produced_by_day, from_date, to_date),
		"tested_series": _series(tested_by_day, from_date, to_date, value="total"),
		"passed_series": _series(tested_by_day, from_date, to_date, value="passed"),
		"heat_series": _series(heats, from_date, to_date, value="heats"),
		"winding_series": _series(windings, from_date, to_date, value="produced"),
		"by_shift": by_shift,
		"by_model": by_model,
		"wo_status": wo_status,
		"work_orders": work_orders,
	}


# ------------------------------------------------------ 6. dealer cockpit


@frappe.whitelist()
def dealer_cockpit(from_date=None, to_date=None, dealer=None):
	"""What one dealer needs, and nothing else.

	The network screen is for head office - rows, ratios, rankings. A dealer
	does not run their shop off a ranking table. This returns a handful of
	plain numbers, the jobs waiting on them, and the customers worth a phone
	call this week.
	"""
	_require("Pump Registration")
	from_date, to_date = _window(from_date, to_date)
	scope = _scope(dealer)

	own = user_dealer()
	me = own.name if own else (dealer or None)
	title = frappe.db.get_value("Dealer", me, "dealer_name") if me else _("All Dealers")

	args = {"from": from_date, "to": to_date, "scope": scope or [""]}
	in_scope = " and custom_dealer in %(scope)s" if scope else ""
	reg_scope = " and dealer in %(scope)s" if scope else ""

	sold = frappe.db.sql(
		f"""
		select count(*) as units
		from `tabPump Registration`
		where docstatus = 1 and sale_date between %(from)s and %(to)s {reg_scope}
		""",
		args,
		as_dict=True,
	)[0]

	revenue = flt(
		frappe.db.sql(
			f"""select sum(base_grand_total) from `tabSales Invoice`
			where docstatus = 1 and is_return = 0
			and posting_date between %(from)s and %(to)s {in_scope}""",
			args,
		)[0][0]
	)

	outstanding = flt(
		frappe.db.sql(
			f"""select sum(outstanding_amount) from `tabSales Invoice`
			where docstatus = 1 and is_return = 0 and outstanding_amount > 0 {in_scope}""",
			args,
		)[0][0]
	)

	open_states = ["Open", "Assigned", "In Progress", "Awaiting Parts"]
	sr_filter = {"docstatus": ["<", 2], "status": ["in", open_states]}
	claim_filter = {"docstatus": ["<", 2], "workflow_state": ["in", ["Pending Review", "Under Investigation"]]}
	if scope:
		sr_filter["dealer"] = ["in", scope]
		claim_filter["dealer"] = ["in", scope]

	# the two lists a dealer actually acts on
	jobs = frappe.db.sql(
		f"""
		select sr.name, sr.serial_no, sr.complaint_category, sr.status, sr.priority,
		       sr.reported_on, sr.is_under_warranty,
		       sr.end_customer_name as customer_name
		from `tabService Request` sr
		where sr.docstatus < 2 and sr.status in ('Open', 'Assigned', 'In Progress', 'Awaiting Parts')
		  {" and sr.dealer in %(scope)s" if scope else ""}
		order by field(sr.priority, 'Critical', 'High', 'Medium', 'Low'), sr.reported_on
		limit 25
		""",
		args,
		as_dict=True,
	)

	expiring = frappe.db.sql(
		f"""
		select sn.name as serial_no, sn.custom_pump_model as model,
		       sn.custom_end_customer_name as customer,
		       sn.custom_end_customer_mobile as mobile,
		       sn.custom_warranty_expiry_date as expires_on,
		       datediff(sn.custom_warranty_expiry_date, curdate()) as days_left
		from `tabSerial No` sn
		where sn.custom_warranty_expiry_date between curdate() and date_add(curdate(), interval 45 day)
		  {" and sn.custom_dealer in %(scope)s" if scope else ""}
		order by sn.custom_warranty_expiry_date
		limit 25
		""",
		args,
		as_dict=True,
	)

	recent = frappe.db.sql(
		f"""
		select name, serial_no, sale_date, end_customer_name, end_customer_mobile,
		       pump_model, application_type, district, warranty_expiry_date
		from `tabPump Registration`
		where docstatus = 1 {reg_scope}
		order by sale_date desc, creation desc
		limit 25
		""",
		args,
		as_dict=True,
	)

	# a simple week-by-week bar is easier to read on a phone than 31 daily bars
	weekly = frappe.db.sql(
		f"""
		select yearweek(sale_date, 3) as wk, min(sale_date) as week_start, count(*) as units
		from `tabPump Registration`
		where docstatus = 1 and sale_date between %(from)s and %(to)s {reg_scope}
		group by wk order by wk
		""",
		args,
		as_dict=True,
	)

	by_application = frappe.db.sql(
		f"""
		select ifnull(application_type, 'Other') as application, count(*) as units
		from `tabPump Registration`
		where docstatus = 1 and sale_date between %(from)s and %(to)s {reg_scope}
		group by application order by units desc
		""",
		args,
		as_dict=True,
	)

	# how this month compares with the one before - the only ranking that helps
	span = (getdate(to_date) - getdate(from_date)).days + 1
	prev_args = {
		"from": add_days(from_date, -span),
		"to": add_days(from_date, -1),
		"scope": scope or [""],
	}
	previous = cint(
		frappe.db.sql(
			f"""select count(*) from `tabPump Registration`
			where docstatus = 1 and sale_date between %(from)s and %(to)s {reg_scope}""",
			prev_args,
		)[0][0]
	)

	units = cint(sold.units)
	return {
		"from_date": str(from_date),
		"to_date": str(to_date),
		"dealer": me,
		"dealer_name": title,
		"is_dealer_login": bool(own),
		"tiles": {
			"units": units,
			"previous_units": previous,
			"change_pct": _pct(units - previous, previous) if previous else None,
			"revenue": revenue,
			"outstanding": outstanding,
			"open_jobs": frappe.db.count("Service Request", sr_filter),
			"claims_waiting": frappe.db.count("Kumar Warranty Claim", claim_filter),
			"expiring_45d": len(expiring),
		},
		"weekly": weekly,
		"by_application": by_application,
		"jobs": jobs,
		"expiring": expiring,
		"recent": recent,
	}


# ------------------------------------------------------------ 7. people


@frappe.whitelist()
def people_overview(from_date=None, to_date=None):
	"""Headcount, attendance and what the month cost in wages."""
	_require("Employee")
	from_date, to_date = _window(from_date, to_date)
	args = {"from": from_date, "to": to_date}

	by_department = frappe.db.sql(
		"""
		select ifnull(department, 'Unassigned') as department, count(*) as headcount
		from `tabEmployee` where status = 'Active'
		group by department order by headcount desc
		""",
		as_dict=True,
	)

	by_grade = frappe.db.sql(
		"""
		select ifnull(grade, 'Ungraded') as grade, count(*) as headcount
		from `tabEmployee` where status = 'Active'
		group by grade order by grade
		""",
		as_dict=True,
	)

	by_branch = frappe.db.sql(
		"""
		select ifnull(branch, 'Unassigned') as branch, count(*) as headcount
		from `tabEmployee` where status = 'Active'
		group by branch order by headcount desc
		""",
		as_dict=True,
	)

	attendance = frappe.db.sql(
		"""
		select status, count(*) as n
		from `tabAttendance`
		where docstatus = 1 and attendance_date between %(from)s and %(to)s
		group by status
		""",
		args,
		as_dict=True,
	)
	att_total = sum(cint(r.n) for r in attendance)
	att_present = sum(
		cint(r.n) for r in attendance if r.status in ("Present", "Work From Home")
	)
	att_half = sum(cint(r.n) for r in attendance if r.status == "Half Day")

	attendance_by_day = frappe.db.sql(
		"""
		select attendance_date as day,
		       sum(case when status in ('Present', 'Work From Home') then 1
		                when status = 'Half Day' then 0.5 else 0 end) as total
		from `tabAttendance`
		where docstatus = 1 and attendance_date between %(from)s and %(to)s
		group by attendance_date
		""",
		args,
		as_dict=True,
	)

	payroll = frappe.db.sql(
		"""
		select start_date, end_date, count(*) as slips,
		       sum(gross_pay) as gross, sum(total_deduction) as deductions,
		       sum(net_pay) as net
		from `tabSalary Slip` where docstatus = 1
		group by start_date, end_date order by start_date desc limit 6
		""",
		as_dict=True,
	)

	payroll_by_department = frappe.db.sql(
		"""
		select ifnull(e.department, 'Unassigned') as department,
		       count(*) as slips, sum(ss.gross_pay) as gross, sum(ss.net_pay) as net
		from `tabSalary Slip` ss
		join `tabEmployee` e on e.name = ss.employee
		where ss.docstatus = 1
		  and ss.start_date = (select max(start_date) from `tabSalary Slip` where docstatus = 1)
		group by department order by net desc
		""",
		as_dict=True,
	)

	top_absent = frappe.db.sql(
		"""
		select a.employee, a.employee_name, ifnull(a.department, '') as department,
		       sum(case when a.status = 'Absent' then 1 else 0 end) as absent,
		       sum(case when a.status = 'On Leave' then 1 else 0 end) as on_leave,
		       count(*) as marked
		from `tabAttendance` a
		where a.docstatus = 1 and a.attendance_date between %(from)s and %(to)s
		group by a.employee, a.employee_name, a.department
		having absent > 0
		order by absent desc, on_leave desc
		limit 15
		""",
		args,
		as_dict=True,
	)

	employees = frappe.db.sql(
		"""
		select e.name, e.employee_name, e.designation, e.department, e.grade,
		       e.branch, e.default_shift as shift, e.date_of_joining, e.status,
		       (select ssa.base from `tabSalary Structure Assignment` ssa
		          where ssa.employee = e.name and ssa.docstatus = 1
		          order by ssa.from_date desc limit 1) as base,
		       (select ss.net_pay from `tabSalary Slip` ss
		          where ss.employee = e.name and ss.docstatus = 1
		          order by ss.start_date desc limit 1) as last_net_pay
		from `tabEmployee` e
		where e.status = 'Active'
		order by e.department, e.designation, e.employee_name
		""",
		as_dict=True,
	)

	latest = payroll[0] if payroll else {}

	return {
		"from_date": str(from_date),
		"to_date": str(to_date),
		"tiles": {
			"headcount": frappe.db.count("Employee", {"status": "Active"}),
			"departments": len(by_department),
			"attendance_marked": att_total,
			"attendance_pct": _pct(att_present + att_half * 0.5, att_total),
			"absent": sum(cint(r.n) for r in attendance if r.status == "Absent"),
			"on_leave": sum(cint(r.n) for r in attendance if r.status == "On Leave"),
			"payroll_month": str(latest.get("start_date") or ""),
			"gross": flt(latest.get("gross")),
			"deductions": flt(latest.get("deductions")),
			"net": flt(latest.get("net")),
			"slips": cint(latest.get("slips")),
			"avg_ctc": flt(latest.get("gross")) / cint(latest.get("slips"))
			if latest.get("slips")
			else 0,
		},
		"attendance_series": _series(attendance_by_day, from_date, to_date),
		"attendance_mix": attendance,
		"by_department": by_department,
		"by_grade": by_grade,
		"by_branch": by_branch,
		"payroll_runs": payroll,
		"payroll_by_department": payroll_by_department,
		"top_absent": top_absent,
		"employees": employees,
	}
