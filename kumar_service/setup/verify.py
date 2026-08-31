"""End-to-end check that the demo company actually holds together.

    bench --site kumar.local execute kumar_service.setup.verify.run

Checks the things a screenshot cannot: that every document chain was really
created and submitted, that the money reconciles, and that all seven dashboard
endpoints answer with data rather than an exception. Read-only.
"""

import re

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
	"service_command_centre",
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
	print("DEALER PORTAL ACTIONS")
	print("=" * 92)

	from kumar_service import portal_api

	# A dealer must be able to do the whole job here. Anything that only works
	# in the desk is, for a dealer, broken.
	original_user = frappe.session.user
	logins = frappe.get_all(
		"Dealer",
		filters={"portal_user": ["!=", ""], "status": "Active"},
		fields=["name", "portal_user"],
	)
	check("there are dealer logins to test", bool(logins), f"{len(logins)} logins")

	read_only_fail, isolation_fail = [], []
	for login in logins:
		try:
			frappe.set_user(login.portal_user)
			opts = portal_api.portal_options()
			tickets = portal_api.my_tickets(limit=5)
			contacts = portal_api.my_contacts()
			if not opts.get("complaint_categories"):
				read_only_fail.append(f"{login.name}: no complaint categories")
			if "tickets" not in tickets:
				read_only_fail.append(f"{login.name}: no ticket list")
			if not contacts.get("contacts"):
				read_only_fail.append(f"{login.name}: nobody to call")

			# A pump this dealer did NOT sell must be refused outright - this is
			# the check that stops one dealer reading another's customer list.
			foreign = frappe.db.sql(
				"""select r.serial_no from `tabPump Registration` r
				   where r.docstatus = 1 and r.dealer not in (
				       select d2.name from `tabDealer` d2, `tabDealer` d1
				       where d1.name = %(me)s and d2.lft >= d1.lft and d2.rgt <= d1.rgt)
				   limit 1""",
				{"me": login.name},
			)
			if foreign:
				try:
					portal_api.pump_snapshot(foreign[0][0])
					isolation_fail.append(f"{login.name} could read {foreign[0][0]}")
				except frappe.PermissionError:
					pass
				except Exception as exc:  # noqa: BLE001
					isolation_fail.append(f"{login.name}: {type(exc).__name__}")
		except Exception as exc:  # noqa: BLE001
			read_only_fail.append(f"{login.name}: {str(exc)[:50]}")
		finally:
			frappe.set_user(original_user)

	check("every dealer login can read its own portal data", not read_only_fail,
		str(read_only_fail[:2]))
	check("a dealer cannot read another dealer's pump", not isolation_fail,
		str(isolation_fail[:2]))

	# The portal must not send a dealer into the desk.
	portal_html = frappe.read_file(
		frappe.get_app_path("kumar_service", "www", "dealer_portal.html")
	) or ""
	desk_links = re.findall(r'href="(/app/[^"]*)"', portal_html)
	check("the portal has no desk links", not desk_links, str(desk_links[:3]))

	for needed in ("raise_complaint", "raise_claim", "ticket_detail", "pump_snapshot"):
		check(f"the portal wires up portal_api.{needed}",
			f"portal_api.{needed}" in portal_html)

	# The scoped snapshot exists precisely because the desk one ignores
	# permissions; if the portal ever drifts back to it, say so.
	check("the portal does not use the permission-ignoring desk snapshot",
		"api.get_pump_snapshot" not in portal_html)

	# The canvas fix. Without a tinted page, white cards on frappe's white web
	# shell read as one blank sheet - which is exactly how this screen looked
	# before, and the sort of thing no unit test would ever notice.
	# Two layout faults reported from a screenshot, both worth guarding: the page
	# read as white, and the content sat in an A4-width column on a wide monitor.
	check("the portal tints the page behind its cards",
		"linear-gradient(180deg, #cfe0f2" in portal_html)
	check("the portal is not stuck in frappe's reading column",
		"max-width:none !important" in portal_html)
	check("the portal still bounds its text width", "max-width:1560px" in portal_html)
	check("the portal carries an announcements strip", "kp-notices" in portal_html)
	check("the portal carries the brand banner row", "kp-banners" in portal_html)
	check("long announcement lists collapse", "kp-notice-toggle" in portal_html)
	# The product-family tiles are filters, not decoration.
	check("the family tiles filter the sales list", "kp-fam-pick" in portal_html)
	check("the sales list can filter by family", 'id="ks-category"' in portal_html)
	# Filters where a dealer is already looking, not only on another tab.
	for control in ("kr-search", "kr-from", "kr-to", "kr-clear"):
		check(f"Recent Registrations has the {control} filter",
			f'id="{control}"' in portal_html)

	# The urgent notice must never be the one hidden behind the toggle - the
	# template shows two and collapses the rest, so ordering is load-bearing.
	original_user = frappe.session.user
	misordered = []
	for login in frappe.get_all(
		"Dealer", filters={"portal_user": ["!=", ""], "status": "Active"},
		fields=["name", "portal_user"], limit=4,
	):
		try:
			frappe.set_user(login.portal_user)
			from kumar_service.www.dealer_portal import get_context as portal_context

			ctx = frappe._dict()
			portal_context(ctx)
			tones = [n["tone"] for n in (ctx.notices or [])]
			if "bad" in tones and tones.index("bad") > 1:
				misordered.append(f"{login.name}: bad at {tones.index('bad')}")
		except Exception as exc:  # noqa: BLE001
			misordered.append(f"{login.name}: {type(exc).__name__}")
		finally:
			frappe.set_user(original_user)
	check("an urgent announcement is never collapsed out of sight", not misordered,
		str(misordered[:2]))

	# The login page is the first screen anyone sees, and it is the riskiest thing
	# we override - it extends frappe's own template, so frappe's login sections
	# must still be reachable through super(). If any of this drifts, nobody can
	# log in at all, so it is checked hard.
	login_html = frappe.read_file(
		frappe.get_app_path("kumar_service", "www", "login.html")
	) or ""
	check("the login page extends frappe's, rather than replacing it",
		'{% extends "frappe/www/login.html" %}' in login_html)
	check("the login page emits frappe's own login sections", "super()" in login_html)
	check("the login page does not hand-roll a login form",
		"api/method/login" not in login_html and "<form" not in login_html)
	for needed in ("kl-grid", "kl-panel", "Which login do I use?", "kl-pillars"):
		check(f"the login page carries {needed}", needed in login_html)

	login_py = frappe.read_file(
		frappe.get_app_path("kumar_service", "www", "login.py")
	) or ""
	check("the login controller delegates to frappe's",
		"frappe.www.login import get_context" in login_py)

	# and it must actually build, for a guest.
	#
	# frappe's login controller reads `frappe.local.request.args` for the
	# redirect-to parameter, and there is no request in a script, so stub one -
	# without it this check fails on its own harness rather than on the page.
	original_user = frappe.session.user
	# Whether the attribute EXISTED matters, not just its value: leaving
	# `frappe.local.request = None` behind breaks the later print checks, which do
	# `frappe.request.environ`. Absent and None are different things here.
	had_request = hasattr(frappe.local, "request")
	original_request = getattr(frappe.local, "request", None)
	try:
		frappe.set_user("Guest")
		frappe.local.request = frappe._dict(args=frappe._dict(), path="/login", method="GET")

		from kumar_service.www.login import get_context as login_context

		ctx = frappe._dict()
		login_context(ctx)
		check("the login page builds for a guest", bool(ctx.get("kumar_pillars")),
			f"{ctx.get('kumar_models')} models quoted")
		# frappe's controller has to have run, or the form has no context at all
		check("frappe's login context came through", "provider_logins" in ctx,
			f"app_name={ctx.get('app_name')}")
	except Exception as exc:  # noqa: BLE001
		check("the login page builds for a guest", False,
			f"{type(exc).__name__}: {str(exc)[:60]}")
	finally:
		if had_request:
			frappe.local.request = original_request
		else:
			try:
				del frappe.local.request
			except AttributeError:
				pass
		frappe.set_user(original_user)

	# Same treatment on the other two public pages, or the brand falls apart the
	# moment a visitor moves between them.
	for page in ("home.html", "warranty_check.html"):
		page_html = frappe.read_file(
			frappe.get_app_path("kumar_service", "www", page)
		) or ""
		check(f"/{page} tints its canvas too", "background-attachment: fixed" in page_html)
	check("the portal hides frappe's duplicate page header",
		"page-header-wrapper" in portal_html)
	check("the tab bar sticks while scrolling", "position:sticky" in portal_html)
	check("dropdowns are styled rather than native", "appearance:none" in portal_html)
	for control in ("kc-pick", "kw-pick", "kp-tsearch", "kp-tstatus", "kp-tclear"):
		check(f"the portal has the {control} control", f'id="{control}"' in portal_html)

	# The company side of the portal: staff must be able to see what dealers
	# raised, and tell portal from desk.
	requests_report = "Dealer Requests and Claims"
	check("the dealer-requests report exists", frappe.db.exists("Report", requests_report))
	if frappe.db.exists("Report", requests_report):
		try:
			report = frappe.get_doc("Report", requests_report)
			cols, rows = report.execute_script_report(filters={})[:2]
			check("the dealer-requests report returns columns and rows",
				len(cols) > 10 and len(rows) > 0, f"{len(cols)} cols / {len(rows)} rows")
			sources = {r.get("raised_from") for r in rows}
			check("it distinguishes portal-raised from desk-raised",
				"Portal" in sources and "Desk" in sources, str(sorted(sources)))
			kinds = {r.get("kind") for r in rows}
			check("it covers both complaints and claims",
				kinds == {"Complaint", "Warranty Claim"}, str(sorted(kinds)))
			# a filter that does not filter is worse than no filter
			_c, only_claims = report.execute_script_report(filters={"kind": "Warranty Claim"})[:2]
			leaked = [r for r in only_claims if r.get("kind") != "Warranty Claim"]
			check("its Type filter actually filters", not leaked, f"{len(only_claims)} rows")
			_c, only_portal = report.execute_script_report(filters={"source": "Portal"})[:2]
			leaked = [r for r in only_portal if r.get("raised_from") != "Portal"]
			check("its Raised From filter actually filters", not leaked,
				f"{len(only_portal)} portal rows")
		except Exception as exc:  # noqa: BLE001
			check("the dealer-requests report runs", False, str(exc)[:70])

	print()
	print("=" * 92)
	print("THE DEALER CONVERSATION, BOTH WAYS")
	print("=" * 92)

	from kumar_service import portal_api, staff_api

	# A portal that only takes messages in is half a system. These checks are
	# about the return leg: KUMAR answering, and the dealer seeing it.
	logins = frappe.get_all(
		"Dealer", filters={"portal_user": ["!=", ""], "status": "Active"},
		fields=["name", "portal_user"],
	)
	check("enough dealers have a portal login to demo the network", len(logins) >= 5,
		f"{len(logins)} logins")

	threads = frappe.db.count(
		"Comment",
		{"comment_type": "Comment",
		 "reference_doctype": ["in", ["Service Request", "Kumar Warranty Claim"]]},
	)
	check("there are real conversations on the demo tickets", threads > 20,
		f"{threads} messages")

	staff_user = (
		frappe.db.get_value("User", {"name": ["like", "service.manager@%"]}, "name")
		or "Administrator"
	)
	original_user = frappe.session.user
	try:
		frappe.set_user(staff_user)
		queue = staff_api.dealer_conversations(state="all")
		summary = queue["summary"]
		check("the staff queue answers", summary.get("total", 0) > 0, str(summary))
		check("the queue separates who owes whom a reply",
			summary.get("waiting", 0) > 0 and summary.get("answered", 0) > 0,
			f"{summary.get('waiting')} waiting / {summary.get('answered')} answered")
		check("the queue rolls up per dealer", bool(queue.get("dealers")),
			f"{len(queue.get('dealers') or [])} dealers")
		# whoever KUMAR owes a reply to must sort first, or the screen is a list
		# rather than a queue
		waiting_first = staff_api.dealer_conversations(state="all")["tickets"][:1]
		check("the ticket KUMAR owes a reply to sorts first",
			bool(waiting_first) and waiting_first[0]["conversation"] == "waiting",
			waiting_first[0]["conversation"] if waiting_first else "-")
	except Exception as exc:  # noqa: BLE001
		check("the staff queue answers", False, str(exc)[:70])
	finally:
		frappe.set_user(original_user)

	# A dealer must be able to read its own thread, and must be refused both the
	# staff endpoint and another dealer's thread.
	leaks = []
	for login in logins:
		try:
			frappe.set_user(login.portal_user)
			mine = frappe.get_all(
				"Service Request",
				filters={"dealer": ["in", frappe.get_all(
					"Dealer",
					filters={"lft": [">=", frappe.db.get_value("Dealer", login.name, "lft")],
					         "rgt": ["<=", frappe.db.get_value("Dealer", login.name, "rgt")]},
					pluck="name")], "docstatus": ["<", 2]},
				pluck="name", limit=1,
			)
			if mine:
				portal_api.ticket_thread("complaint", mine[0])
			try:
				staff_api.dealer_conversations()
				leaks.append(f"{login.name} reached the staff queue")
			except frappe.PermissionError:
				pass
		except frappe.PermissionError as exc:
			leaks.append(f"{login.name} refused its own thread: {exc}")
		except Exception as exc:  # noqa: BLE001
			leaks.append(f"{login.name}: {type(exc).__name__}")
		finally:
			frappe.set_user(original_user)
	check("dealers read their own thread and cannot reach KUMAR's queue", not leaks,
		str(leaks[:2]))

	conv_js = frappe.read_file(
		frappe.get_app_path("kumar_service", "kumar_service", "page", "dealer_conversations",
			"dealer_conversations.js")
	) or ""
	check("the conversations page calls the staff reply endpoint",
		"staff_api.reply_to_dealer" in conv_js)
	check("the conversations page can record the SLA first response",
		"mark_responded" in conv_js)
	check("the portal lets the dealer write back", "portal_api.post_reply" in portal_html)
	check("the portal shows the thread", "portal_api.ticket_thread" in portal_html)

	reply_js = frappe.read_file(
		frappe.get_app_path("kumar_service", "public", "js", "dealer_reply.js")
	) or ""
	check("the Service Request form has a Reply to Dealer button",
		"Reply to Dealer" in reply_js and "Service Request" in reply_js)

	bundle = frappe.read_file(
		frappe.get_app_path("kumar_service", "public", "js", "kumar.bundle.js")
	) or ""
	check("the reply button is loaded by the desk bundle", "dealer_reply.js" in bundle)

	# The chat panel that used to be asserted here is gone: KUMAR Pumps Desk
	# owns the conversation now, and running two chat UIs over one comment
	# thread was worse than either on its own.

	css = frappe.read_file(
		frappe.get_app_path("kumar_service", "public", "css", "kumar.bundle.css")
	) or ""
	for needed in (".kumar-attachments",):
		check(f"the chat panel is styled: {needed}", needed in css)

	# Attachments have to be visible in the DESK, not only in our own screens:
	# once on the ticket for the Attachments sidebar (which is also what makes a
	# private file readable by staff), and once inside the comment HTML for
	# frappe's own timeline.
	portal_py = frappe.read_file(frappe.get_app_path("kumar_service", "portal_api.py")) or ""
	check("attachments are rendered into the comment for the desk timeline",
		"_write_attachment_block" in portal_py)
	check("the message keeps its link to its files", "_parse_attachments" in portal_py)

	# A File row still stuck on a Comment is invisible in the desk: it appears in
	# no Attachments sidebar, and a private one 403s for staff. This is the exact
	# state the first cut left behind.
	stranded = frappe.db.count("File", {"attached_to_doctype": "Comment"})
	check("no attachment is stranded on a Comment", stranded == 0,
		f"{stranded} would be invisible in the desk")

	# Every file a message points at must exist, or the timeline shows a broken
	# image and the chat panel a dead link.
	broken = 0
	for content in frappe.db.sql_list(
		"""select content from `tabComment`
		   where comment_type = 'Comment' and content like %s""",
		f"%{portal_api.ATTACH_MARKER}%",
	):
		for a in portal_api._parse_attachments(content):
			if not frappe.db.exists("File", {"file_url": a["file_url"]}):
				broken += 1
	check("every attachment a message points at still exists", broken == 0,
		f"{broken} broken links")

	print()
	print("=" * 92)
	print("BRANDING")
	print("=" * 92)

	from kumar_service.setup import branding

	ws = frappe.get_single("Website Settings")
	check("app name is KUMAR, not Frappe", ws.app_name == branding.APP_NAME, ws.app_name or "-")
	check("the desk navbar carries the KUMAR mark",
		frappe.db.get_single_value("Navbar Settings", "app_logo") == branding.MARK)
	check("favicon and splash are set", bool(ws.favicon and ws.splash_image))
	check("System Settings app_name says KUMAR too",
		frappe.db.get_single_value("System Settings", "app_name") == branding.APP_NAME,
		frappe.db.get_single_value("System Settings", "app_name") or "-")
	check("the website theme is ours", ws.website_theme == "KUMAR", ws.website_theme or "-")
	# Every logo path must resolve on disk, or the navbar shows a broken image
	# and that is the first thing anyone sees.
	import os

	from frappe import get_app_path

	missing_assets = [
		path
		for path in (branding.LOGO, branding.MARK, branding.TILE, branding.SPLASH)
		if not os.path.exists(
			os.path.join(get_app_path("kumar_service"), "public", path.split("/assets/kumar_service/")[1])
		)
	]
	check("every branded image exists on disk", not missing_assets, str(missing_assets))

	company_desc = frappe.db.get_value("Company", branding.COMPANY, "company_description")
	check("the company record tells the company's story", bool(company_desc),
		f"{len(company_desc or '')} chars")

	print()
	print("=" * 92)
	print("PUBLIC PAGES AND TELUGU")
	print("=" * 92)

	check("the site opens on the KUMAR landing page", ws.home_page == "home", ws.home_page or "-")

	# Render each public page the way a visitor gets it, in both languages. This
	# is the check that would have caught an untranslated status badge.
	from frappe.translate import print_language

	original = frappe.session.user
	for route, module in (("home", "home"), ("warranty-check", "warranty_check")):
		for lang in ("en", "te"):
			label = f"/{route} renders in {lang}"
			try:
				with print_language(lang):
					controller = frappe.get_module(f"kumar_service.www.{module}")
					ctx = frappe._dict()
					controller.get_context(ctx)
					check(label, bool(ctx.get("title")), ctx.get("title") or "")
			except Exception as exc:  # noqa: BLE001
				check(label, False, str(exc)[:70])
	frappe.set_user(original)

	te = frappe.translate.get_all_translations("te")
	check("the Telugu language is enabled on the site",
		bool(frappe.db.get_value("Language", "te", "enabled")))
	check("the shipped te.csv actually loads", len(te) > 900, f"{len(te)} strings")

	# The two certificates are acceptance criterion #10: they must print in
	# Telugu, not merely be translatable in principle.
	for doctype, fmt, probe in (
		("Pump Registration", "KUMAR Warranty Certificate", "వారంటీ సర్టిఫికెట్"),
		("Pump Test Certificate", "KUMAR Pump Test Certificate", "పంప్ టెస్ట్ సర్టిఫికెట్"),
	):
		name = frappe.get_all(doctype, filters={"docstatus": 1}, limit=1, pluck="name")
		label = f"{fmt} prints in Telugu"
		if not name:
			check(label, False, "nothing submitted to print")
			continue
		try:
			with print_language("te"):
				html = frappe.get_print(doctype, name[0], print_format=fmt, no_letterhead=0)
			check(label, probe in html and 'k-wrap k-te' in html, name[0])
		except Exception as exc:  # noqa: BLE001
			check(label, False, str(exc)[:70])

	# A translation whose placeholders do not match its source crashes at
	# .format() time, in front of whoever triggered the message.


	bad_placeholders = [
		src
		for src, dst in te.items()
		if sorted(re.findall(r"\{\d+\}", src)) != sorted(re.findall(r"\{\d+\}", dst))
	]
	check("no Telugu string drops a {0} placeholder", not bad_placeholders,
		str(bad_placeholders[:3]))

	print()
	print("=" * 92)
	print("CATALOGUE AGAINST THE BROCHURE")
	print("=" * 92)

	families = dict(
		frappe.db.sql("select family_code, count(*) from `tabPump Model` group by family_code")
	)
	for family in ("V3", "V4", "V6", "V8", "OW", "JM", "SMB", "HMB", "PP", "BP"):
		check(f"family {family} is in the catalogue", families.get(family, 0) > 0,
			f"{families.get(family, 0)} models")

	# Borewell runs a copper rotor, openwell an aluminium one. Getting this
	# backwards puts the wrong rotor on a test certificate.
	wrong_rotor = frappe.get_all(
		"Pump Model",
		filters={"family_code": "OW", "rotor_type": ["!=", "Aluminium Die Cast"]},
		pluck="name",
	)
	check("openwell models run an aluminium rotor", not wrong_rotor, str(wrong_rotor))
	copper_wrong = frappe.get_all(
		"Pump Model",
		filters={"family_code": ["in", ["V3", "V4", "V6", "V8"]], "rotor_type": ["!=", "Copper"]},
		pluck="name",
	)
	check("borewell submersibles run a copper rotor", not copper_wrong, str(copper_wrong))

	# Each Pump Model must have its stock Item, or it cannot be built or sold.
	modelless = one(
		"""select count(*) from `tabPump Model` m
		   where m.is_active = 1 and (m.item is null or m.item = ''
		         or not exists (select 1 from `tabItem` i where i.name = m.item))"""
	)
	check("every active model has a real stock Item", modelless == 0, f"{modelless} without")

	print()
	print("=" * 92)
	print(f"RESULT: {len(passed)} passed, {len(failed)} failed")
	if failed:
		for item in failed:
			print("  FAILED:", item)
	print("=" * 92)
	return not failed
