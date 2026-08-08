"""End-to-end check that the demo company actually holds together.

    bench --site kumar.local execute kumar_service.setup.verify.run

Checks the things a screenshot cannot: that every document chain was really
created and submitted, that the money reconciles, and that all seven dashboard
endpoints answer with data rather than an exception. Read-only.
"""

import frappe
from frappe.utils import flt

WINDOW = ("2026-07-08", "2026-08-07")

COUNT_DOCTYPES = [
	"Supplier", "Material Request", "Purchase Order", "Purchase Receipt", "Purchase Invoice",
	"BOM", "Work Order", "Stock Entry", "Serial No", "Pump Test Certificate",
	"Customer", "Sales Order", "Delivery Note", "Sales Invoice", "Payment Entry",
	"Journal Entry", "Employee", "Attendance", "Leave Allocation", "Leave Application",
	"Salary Structure", "Salary Structure Assignment", "Salary Slip",
	"Pump Registration", "Service Request", "Service Visit", "Kumar Warranty Claim",
	"Heat Record", "Winding Batch Record", "Dealer", "Pump Model", "Address", "Cost Center",
]

PAGES = [
	"management-dashboard", "dealer-network", "my-business", "sales-analytics",
	"purchase-analytics", "production-daily", "people-payroll", "pump-lookup",
	"historical-import",
]

ENDPOINTS = [
	"management_overview", "dealer_distribution", "sales_analytics",
	"purchase_analytics", "production_daily", "dealer_cockpit", "people_overview",
]


def run():
	passed, failed = [], []

	def check(label, condition, detail=""):
		(passed if condition else failed).append(label)
		print(f"{'PASS' if condition else 'FAIL'}  {label:46s} {detail}")

	def one(sql, args=None):
		return frappe.db.sql(sql, args or {})[0][0] or 0

	print("=" * 92)
	print("RECORD COUNTS")
	print("=" * 92)
	for dt in COUNT_DOCTYPES:
		try:
			print(f"  {dt:32s} {frappe.db.count(dt):6d}")
		except Exception as exc:  # noqa: BLE001
			print(f"  {dt:32s} ERR {str(exc)[:40]}")

	print()
	print("=" * 92)
	print("DOCUMENT CHAINS")
	print("=" * 92)

	check("suppliers on file", frappe.db.count("Supplier") >= 10, str(frappe.db.count("Supplier")))
	check("purchase orders submitted",
		frappe.db.count("Purchase Order", {"docstatus": 1}) >= 30,
		str(frappe.db.count("Purchase Order", {"docstatus": 1})))
	check("purchase invoices submitted",
		frappe.db.count("Purchase Invoice", {"docstatus": 1}) >= 15,
		str(frappe.db.count("Purchase Invoice", {"docstatus": 1})))
	check("BOMs active",
		frappe.db.count("BOM", {"docstatus": 1, "is_active": 1}) >= 20,
		str(frappe.db.count("BOM", {"docstatus": 1, "is_active": 1})))

	statuses = frappe.db.sql(
		"select status, count(*) n from `tabWork Order` where docstatus=1 group by status",
		as_dict=True,
	)
	check("work orders show a real status mix", len(statuses) >= 2, str(statuses))

	produced = one(
		"""select ifnull(sum(sed.qty),0) from `tabStock Entry` se
		join `tabStock Entry Detail` sed on sed.parent=se.name
		where se.docstatus=1 and se.purpose='Manufacture' and sed.is_finished_item=1"""
	)
	check("units manufactured", produced >= 200, f"{produced:.0f}")

	check("sales orders submitted", frappe.db.count("Sales Order", {"docstatus": 1}) >= 50,
		str(frappe.db.count("Sales Order", {"docstatus": 1})))
	check("delivery notes submitted", frappe.db.count("Delivery Note", {"docstatus": 1}) >= 40,
		str(frappe.db.count("Delivery Note", {"docstatus": 1})))
	check("sales invoices submitted", frappe.db.count("Sales Invoice", {"docstatus": 1}) >= 50,
		str(frappe.db.count("Sales Invoice", {"docstatus": 1})))

	print()
	print("=" * 92)
	print("MONEY")
	print("=" * 92)

	revenue = one("""select ifnull(sum(base_grand_total),0) from `tabSales Invoice`
		where docstatus=1 and is_return=0""")
	sales_tax = one("""select ifnull(sum(total_taxes_and_charges),0) from `tabSales Invoice`
		where docstatus=1 and is_return=0""")
	spend = one("""select ifnull(sum(base_grand_total),0) from `tabPurchase Invoice`
		where docstatus=1 and is_return=0""")
	input_tax = one("""select ifnull(sum(total_taxes_and_charges),0) from `tabPurchase Invoice`
		where docstatus=1 and is_return=0""")
	ar = one("select ifnull(sum(outstanding_amount),0) from `tabSales Invoice` where docstatus=1")
	ap = one("select ifnull(sum(outstanding_amount),0) from `tabPurchase Invoice` where docstatus=1")

	check("revenue booked", revenue > 0, f"Rs {revenue:,.0f}")
	check("output GST charged", sales_tax > 0, f"Rs {sales_tax:,.0f}")
	check("purchases booked", spend > 0, f"Rs {spend:,.0f}")
	check("input GST recorded", input_tax > 0, f"Rs {input_tax:,.0f}")
	check("receivable is a tail, not the whole book", 0 < ar < revenue, f"Rs {ar:,.0f}")
	check("payable is a tail, not the whole book", 0 < ap < spend, f"Rs {ap:,.0f}")
	check("customer receipts exist",
		frappe.db.count("Payment Entry", {"docstatus": 1, "payment_type": "Receive"}) > 0,
		str(frappe.db.count("Payment Entry", {"docstatus": 1, "payment_type": "Receive"})))
	check("supplier payments exist",
		frappe.db.count("Payment Entry", {"docstatus": 1, "payment_type": "Pay"}) > 0,
		str(frappe.db.count("Payment Entry", {"docstatus": 1, "payment_type": "Pay"})))
	check("overhead journals posted", frappe.db.count("Journal Entry", {"docstatus": 1}) >= 5,
		str(frappe.db.count("Journal Entry", {"docstatus": 1})))

	print()
	print("=" * 92)
	print("PEOPLE")
	print("=" * 92)

	check("employees on roll", frappe.db.count("Employee", {"status": "Active"}) >= 90,
		str(frappe.db.count("Employee", {"status": "Active"})))
	check("attendance marked", frappe.db.count("Attendance", {"docstatus": 1}) > 2000,
		str(frappe.db.count("Attendance", {"docstatus": 1})))

	slips = frappe.db.sql(
		"""select count(*), ifnull(sum(gross_pay),0), ifnull(sum(total_deduction),0),
		ifnull(sum(net_pay),0) from `tabSalary Slip` where docstatus=1"""
	)[0]
	check("salary slips submitted", slips[0] >= 80, f"{slips[0]} slips")
	check("wage bill computed", flt(slips[3]) > 0,
		f"gross {slips[1]:,.0f} - deductions {slips[2]:,.0f} = net {slips[3]:,.0f}")

	print()
	print("=" * 92)
	print("DEALER NETWORK")
	print("=" * 92)

	selling = frappe.db.sql(
		"""select count(*) from (
			select d.name from `tabDealer` d
			join `tabPump Registration` r on r.dealer = d.name and r.docstatus = 1
			group by d.name) x"""
	)[0][0]
	check("more than a couple of dealers are actually selling", selling >= 8,
		f"{selling} dealers with sales")

	print()
	print("=" * 92)
	print("THE TWO SALE CHANNELS")
	print("=" * 92)

	from kumar_service.utils import CH_DEALER, CH_DIRECT

	own = frappe.db.count("Dealer", {"is_own_outlet": 1})
	indep = frappe.db.count("Dealer", {"is_own_outlet": 0, "is_group": 0})
	check("outlets are split into ours and theirs", own >= 4 and indep >= 6,
		f"{own} KUMAR-owned, {indep} independent")

	no_account = frappe.db.count(
		"Dealer", {"is_own_outlet": 0, "is_group": 0, "customer": ["is", "not set"]}
	)
	check("every independent dealer has a trade account to bill", no_account == 0,
		f"{no_account} without one")

	# A trade invoice bills the dealer it names. This is the one that used to be
	# fiction: customer and dealer were rolled independently, so the same buyer
	# turned up under three dealers and revenue per dealer meant nothing.
	mismatch = one(
		"""select count(*) from `tabSales Invoice` si
		   join `tabCustomer` c on c.name = si.customer
		   where si.docstatus = 1 and si.custom_sale_channel = 'Trade - Sold to Dealer'
		     and ifnull(c.custom_dealer, '') != ifnull(si.custom_dealer, '')"""
	)
	check("every trade invoice bills the dealer it names", mismatch == 0,
		f"{mismatch} mismatched")

	split = one("select count(*) from (select customer from `tabSales Invoice` "
		"where docstatus = 1 and custom_sale_channel = 'Trade - Sold to Dealer' "
		"group by customer having count(distinct custom_dealer) > 1) x")
	check("no trade customer appears under two dealers", split == 0, f"{split} split")

	trade_inv = frappe.db.count(
		"Sales Invoice", {"docstatus": 1, "custom_sale_channel": "Trade - Sold to Dealer"}
	)
	direct_inv = frappe.db.count(
		"Sales Invoice", {"docstatus": 1, "custom_sale_channel": "Direct - Sold to End Customer"}
	)
	check("both channels carry real invoices", trade_inv >= 20 and direct_inv >= 10,
		f"{trade_inv} trade, {direct_inv} direct")

	# each channel's proof of sale to the end customer
	no_dealer_inv = frappe.db.count(
		"Pump Registration",
		{"docstatus": 1, "sale_channel": CH_DEALER, "invoice_no": ["is", "not set"]},
	)
	check("dealer sales carry the dealer's own invoice", no_dealer_inv == 0,
		f"{no_dealer_inv} without one")

	no_kumar_inv = frappe.db.count(
		"Pump Registration",
		{"docstatus": 1, "sale_channel": CH_DIRECT, "sales_invoice": ["is", "not set"]},
	)
	check("direct sales carry our own invoice", no_kumar_inv == 0,
		f"{no_kumar_inv} without one")

	contradicts = one(
		"""select count(*) from `tabPump Registration` r
		   join `tabDealer` d on d.name = r.dealer
		   where r.docstatus = 1
		     and ((d.is_own_outlet = 1 and r.sale_channel = %(dealer)s)
		       or (d.is_own_outlet = 0 and r.sale_channel = %(direct)s))""",
		{"dealer": CH_DEALER, "direct": CH_DIRECT},
	)
	check("no registration contradicts who owns the outlet", contradicts == 0,
		f"{contradicts} contradicting")

	# the manufacturing date used to fall back to the row's creation timestamp,
	# which is the moment the builder ran - so July sales looked like sales
	# before the pump existed
	time_travel = one(
		"""select count(*) from `tabPump Registration`
		   where docstatus = 1 and manufacturing_date is not null
		     and sale_date < manufacturing_date"""
	)
	check("nothing was sold before it was manufactured", time_travel == 0,
		f"{time_travel} impossible")

	print()
	print("=" * 92)
	print("DASHBOARD ENDPOINTS")
	print("=" * 92)

	from kumar_service import dashboard

	for name in ENDPOINTS:
		try:
			fn = getattr(dashboard, name)
			result = fn(from_date=WINDOW[0], to_date=WINDOW[1])
			check(f"endpoint {name}", bool(result),
				f"{len(result)} keys, {len(result.get('tiles', {}))} tiles")
		except Exception as exc:  # noqa: BLE001
			check(f"endpoint {name}", False, str(exc)[:110])

	print()
	print("=" * 92)
	print("PAGES AND WORKSPACES")
	print("=" * 92)

	for page in PAGES:
		check(f"page {page}", bool(frappe.db.exists("Page", page)))

	from kumar_service.setup.workspaces import WORKSPACES

	expected = {ws["label"] for ws in WORKSPACES}
	actual = set(frappe.get_all("Workspace", filters={"module": "Kumar Service"}, pluck="name"))
	check("workspaces match the code, with no strays", actual == expected,
		f"{len(actual)} present" + (f", unexpected {actual - expected}" if actual - expected else ""))

	print()
	print("=" * 92)
	print("ICONS")
	print("=" * 92)

	import pathlib
	import re

	from kumar_service.setup.desktop_icons import TILES
	from kumar_service.setup.icons import FALLBACK_ICON, WORKSPACE_ICONS

	sprite = pathlib.Path(
		frappe.get_app_path("kumar_service"), "public", "icons", "kumar-icons.svg"
	).read_text(encoding="utf-8")
	symbols = set(re.findall(r'id="(icon-kumar-[^"]+)"', sprite))

	used = {r[0] for r in frappe.db.sql(
		"select distinct icon from `tabWorkspace Sidebar Item` where icon like 'kumar-%%'")}
	absent = sorted(i for i in used if f"icon-{i}" not in symbols)
	check("every sidebar glyph exists in the sprite", not absent, f"{len(used)} in use, {absent}")

	# a screen and one of its own links drawing the same glyph reads as a
	# duplicate rather than a parent
	clashes = []
	for ws in WORKSPACE_ICONS:
		rows = frappe.db.sql(
			"select label, icon from `tabWorkspace Sidebar Item` where parent=%s order by idx",
			(ws,), as_dict=True)
		if rows and any(r.icon == rows[0].icon for r in rows[1:]):
			clashes.append(ws)
	check("no screen shares its glyph with its own links", not clashes, str(clashes))

	# the fallback existing is fine; a link still sitting on it means we never
	# gave that link a glyph of its own
	on_fallback = one(
		"select count(*) from `tabWorkspace Sidebar Item` where icon = %(i)s", {"i": FALLBACK_ICON})
	check("no link left on the neutral fallback", on_fallback == 0, f"{on_fallback} unmapped")

	strays = [r.label for r in frappe.get_all(
		"Desktop Icon", filters={"icon": ["like", "kumar-%"]}, fields=["label", "app"])
		if not (r.label in TILES and r.app == "kumar_service")]
	check("no stale KUMAR tiles on the apps screen", not strays, str(strays))

	# renaming a workspace used to leave its JSON behind, and `bench migrate`
	# re-imports every workspace file - so the deleted screen came straight back
	ws_root = pathlib.Path(frappe.get_app_path("kumar_service")) / "kumar_service" / "workspace"
	orphans = []
	for folder in sorted(p for p in ws_root.iterdir() if p.is_dir()):
		definition = folder / f"{folder.name}.json"
		if definition.exists():
			import json as _json

			if _json.loads(definition.read_text(encoding="utf-8")).get("label") not in expected:
				orphans.append(folder.name)
	check("no orphaned workspace json to resurrect on migrate", not orphans, str(orphans))

	print()
	print("=" * 92)
	print("DEALER PORTAL AND PERFORMANCE")
	print("=" * 92)

	from kumar_service.setup.icons import EXTRA_SIDEBAR_LINKS

	wanted_urls = {(ws, e["url"]) for ws, links in EXTRA_SIDEBAR_LINKS.items() for e in links}
	live_urls = {
		(r[0], r[1])
		for r in frappe.db.sql(
			"select parent, url from `tabWorkspace Sidebar Item` where link_type = 'URL'")
	}
	check("portal links are in the desk sidebar", wanted_urls <= live_urls,
		f"{len(wanted_urls & live_urls)}/{len(wanted_urls)}")

	dd = dashboard.dealer_distribution(from_date=WINDOW[0], to_date=WINDOW[1])
	for key in ("channels", "trend", "leaderboard", "needs_a_call"):
		check(f"dealer_distribution returns {key}", key in dd)

	both = {c["channel"] for c in dd.get("channels", [])}
	check("both sale channels appear on the network screen",
		both == {"Independent", "KUMAR Branch"}, str(sorted(both)))

	check("the trend has a point for every day in the window",
		len(dd["trend"]["days"]) > 20, f"{len(dd['trend']['days'])} days")

	# a percentage off a tiny base reads as a broken screen
	silly = [
		r["dealer_name"] for r in dd["dealers"]
		if r.get("growth_pct") is not None and abs(r["growth_pct"]) > 1000
	]
	check("no absurd growth percentages", not silly, str(silly[:3]))

	# every dealer login must get a working portal, with a rank
	from kumar_service.www.dealer_portal import get_context

	original = frappe.session.user
	portal_fail = []
	for login in frappe.get_all(
		"Dealer", filters={"portal_user": ["is", "set"]}, fields=["name", "portal_user"]
	):
		try:
			frappe.set_user(login.portal_user)
			ctx = frappe._dict()
			get_context(ctx)
			perf = ctx.get("performance") or {}
			if ctx.get("not_a_dealer") or perf.get("rank") is None:
				portal_fail.append(f"{login.name}(rank={perf.get('rank')})")
		except Exception as exc:  # noqa: BLE001
			portal_fail.append(f"{login.name}: {str(exc)[:50]}")
		finally:
			frappe.set_user(original)
	check("every dealer login gets a ranked portal", not portal_fail, str(portal_fail))

	print()
	print("=" * 92)
	print("INDEXES AND MIGRATION TOOLING")
	print("=" * 92)

	from kumar_service.setup import indexes

	absent = indexes.missing()
	check("every hot column is indexed", not absent,
		str([f"{dt}.{'+'.join(f)}" for dt, f in absent]))

	from kumar_service import migration

	template = migration.template_rows()
	check("the historical-serial import template is shipped", bool(template),
		f"{len(template[0]) if template else 0} columns")

	dry = migration.dry_run(rows=template[1:])
	check("the import template validates against its own sample rows",
		dry["errors"] == 0, f"{dry['ok']} ok / {dry['errors']} errors")

	recon = frappe.get_all("Report", filters={"name": "Stock vs Registration Reconciliation"})
	check("the reconciliation report exists", bool(recon))

	print()
	print("=" * 92)
	print(f"RESULT: {len(passed)} passed, {len(failed)} failed")
	if failed:
		for item in failed:
			print("  FAILED:", item)
	print("=" * 92)
	return not failed
