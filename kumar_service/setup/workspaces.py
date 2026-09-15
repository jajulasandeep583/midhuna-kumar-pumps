"""Five workspaces, each opening with its own How to Use guide.

The guide is a paragraph block at the top of the workspace, so the person who
lands on the icon reads what the screen is for before they touch anything.
"""

import json

import frappe

MODULE = "Kumar Service"


def _guide(title, purpose, steps, watch_outs=None):
	items = "".join(f"<li>{s}</li>" for s in steps)
	watch = ""
	if watch_outs:
		w = "".join(f"<li>{x}</li>" for x in watch_outs)
		watch = (
			"<p style='margin:10px 0 4px'><b>Watch out for</b></p>"
			f"<ul style='margin:0 0 4px 18px'>{w}</ul>"
		)
	return (
		"<div style='border:1px solid var(--border-color);border-radius:8px;"
		"padding:14px 16px;background:var(--fg-color)'>"
		f"<p style='margin:0 0 6px'><b>How to use {title}</b></p>"
		f"<p style='margin:0 0 8px;color:var(--text-muted)'>{purpose}</p>"
		"<p style='margin:10px 0 4px'><b>Do this, in order</b></p>"
		f"<ol style='margin:0 0 4px 18px'>{items}</ol>"
		f"{watch}"
		"</div>"
	)


WORKSPACES = [
	{
		# The owner's screen. The Command Centre at /kumar-desk/manage answers
		# "what needs me today"; this answers the other half of the question a
		# proprietor asks - what did the network SELL, what is it holding, and
		# what is the warranty costing me - in ERPNext's own reports, because
		# those are the ones the accountant already trusts.
		"name": "Kumar Management",
		"label": "Management",
		"title_text": "Management",
		"icon": "dashboard",
		"sequence": 2,
		"roles": ["Dealer Manager", "Service Manager", "Warranty Approver", "Accounts User",
			"System Manager"],
		"number_cards": [
			"Pumps sold this month",
			"Pumps built this month",
			"Purchases this month",
			"Claims raised this month",
			"Warranty cost this month",
			"Complaints this month",
		],
		"guide": _guide(
			"Management",
			"Sales by dealer, stock on hand, and what the warranty is costing - the numbers a "
			"proprietor asks for, drawn from the same records the plant and the desk already keep. "
			"Nothing here is entered twice.",
			[
				"<b>Dealer Performance</b> - one row per outlet: what they sold, what came back "
				"and what they claimed. This is the dealer-wise sales picture.",
				"<b>Stock Balance</b> and <b>Stock Ledger</b> - what is on hand, by warehouse and "
				"item, and every movement behind it.",
				"<b>Warranty Cost Analysis</b> - what settled claims have cost, by month and model.",
				"<b>Command Centre</b> opens the live service desk at /kumar-desk/manage, where "
				"past-due work and claims waiting on a decision are actionable rather than reported.",
			],
			[
				"Stock Balance counts what is in the warehouse. Pumps already dispatched to a dealer "
				"have left KUMAR's stock - the Dealer Network table is where those live.",
				"A pump sold but never registered shows in <b>Stock vs Registration "
				"Reconciliation</b>; it is the gap between what left the plant and what a dealer "
				"admitted selling.",
			],
		),
		"shortcuts": [
			# plain "&", not the entity: this label is rendered as TEXT in the
			# sidebar rail, where "&amp;" shows up literally
			("Production and Sales Summary", "Report", "Production & Sales", "orange"),
			("Dealer Performance", "Report", "Dealer-wise Sales", "green"),
			("Stock Balance", "Report", "Stock Balance", "blue"),
			("Warranty Cost Analysis", "Report", "Warranty Cost", "orange"),
			("Dealer Requests and Claims", "Report", "Requests & Claims", "grey"),
			("Dealer", "DocType", "Dealer Network", "blue"),
		],
		"links": [
			("What the month did", ["Production and Sales Summary", "Dealer Performance",
				"Model Reliability"]),
			("Sales & Dealers", ["Dealer", "Pump Registration", "Sales Invoice", "Delivery Note",
				"Customer"]),
			("Stock on Hand", ["Stock Balance", "Stock Ledger", "Stock Projected Qty", "Item",
				"Warehouse"]),
			("What it is costing", ["Warranty Cost Analysis", "Dealer Performance",
				"Dealer Requests and Claims", "Model Reliability",
				"Stock vs Registration Reconciliation"]),
		],
	},
	{
		"name": "Kumar Dealer Desk",
		"label": "Dealer Desk",
		"title_text": "Dealer Desk",
		"icon": "retail",
		"sequence": 1,
		"roles": ["Dealer", "Dealer Manager", "Service Manager", "System Manager"],
		"guide": _guide(
			"the Dealer Desk",
			"This is the dealer's whole job in one screen: record the sale of a pump so its "
			"warranty starts, and raise a complaint when a customer calls. Registering a pump is "
			"what generates the warranty certificate in KUMAR Pumps' name.",
			[
				"<b>Register Pump</b> - scan or type the serial from the nameplate. Model, HP and "
				"manufacturing date fill themselves. Add the customer's name and mobile, the sale date "
				"and the installation address, then Submit.",
				"The warranty expiry is calculated for you from the model's warranty period. "
				"Print the <b>Warranty Certificate</b> from the print icon - it carries the QR code.",
				"<b>New Service Request</b> - enter the serial and the warranty banner tells you "
				"immediately whether the visit is free or chargeable.",
				"<b>My Registrations</b> and <b>My Claims</b> show only your own network's records.",
			],
			[
				"A serial can only be registered once. If the customer changes, amend the existing "
				"registration rather than creating a second one.",
				"The mobile number must be a real 10-digit number - it is what the warranty is traced by.",
			],
		),
		"shortcuts": [
			# the dealer's own screen comes first - it is where they should live
			("my-business", "Page", "My Business", "green"),
			("pump-lookup", "Page", "Pump Lookup", "blue"),
			("Pump Registration", "DocType", "Register Pump", "green"),
			("Service Request", "DocType", "New Service Request", "orange"),
			("Kumar Warranty Claim", "DocType", "My Claims", "blue"),
			("Serial No", "DocType", "Warranty Lookup", "grey"),
		],
		"links": [
			("Sales & Registration", ["Pump Registration", "Serial No", "Sales Invoice", "Delivery Note"]),
			("Service", ["Service Request", "Service Visit", "Kumar Warranty Claim"]),
		],
	},
	{
		"name": "Kumar Warranty",
		"label": "Warranty",
		"title_text": "Warranty &amp; Claims",
		"icon": "file",
		"sequence": 3,
		"roles": ["Warranty Approver", "Quality Engineer", "Accounts User", "Service Manager", "System Manager"],
		"guide": _guide(
			"Warranty & Claims",
			"Where a dealer's claim is checked and settled, and where warranty exposure is watched. "
			"Each claim carries the pump's heat number and winding batch, which is what makes it "
			"possible to spot a bad batch instead of arguing about one pump.",
			[
				"A dealer submits a claim; it lands in <b>Pending Claims</b>.",
				"Service Manager reviews it into Under Investigation. Quality Engineer approves or "
				"rejects on the evidence - photos, technician report, root cause.",
				"Approved claims go to Accounts to <b>Settle</b>, optionally against a credit note.",
				"Check <b>Batch Defect Analysis</b> whenever two claims share a heat or winding batch.",
			],
			[
				"Rejecting without a root cause loses the only information the factory would get.",
				"<b>Warranty Expiring (30d)</b> is a sales list, not a problem list - it is the AMC "
				"and replacement opportunity.",
			],
		),
		"shortcuts": [
			("Kumar Warranty Claim", "DocType", "Pending Claims", "orange"),
			("Warranty Expiring Soon", "Report", "Warranty Expiring (30d)", "red"),
			("Batch Defect Analysis", "Report", "Batch Defect Analysis", "purple"),
			("Warranty Cost Analysis", "Report", "Warranty Cost", "blue"),
		],
		"links": [
			("Claims", ["Kumar Warranty Claim", "Service Request"]),
			("Reports", ["Warranty Expiring Soon", "Warranty Cost Analysis", "Unregistered Stock",
				"Stock vs Registration Reconciliation", "Dealer Requests and Claims"]),
		],
	},
	{
		"name": "Kumar Traceability",
		"label": "Traceability",
		"title_text": "Traceability &amp; Quality",
		"icon": "quality",
		"sequence": 4,
		"roles": ["Quality Engineer", "Production Manager", "Foundry Operator", "System Manager"],
		"guide": _guide(
			"Traceability & Quality",
			"The factory half. A pump's identity is built here: which melt its casing came from, "
			"which winding lot its stator came from, and whether it passed test. Get this right and "
			"any field failure can be traced back to a root batch.",
			[
				"<b>Heat Record</b> - log the melt, enter spectrometer readings, and only then set "
				"status to Approved for Pouring. Out-of-spec elements block approval unless a Quality "
				"Engineer records an override reason.",
				"<b>Winding Batch</b> - log the stator lot with its IR and HiPot readings.",
				"Assembly consumes those batches in a Manufacture Stock Entry. The heat and winding "
				"numbers are stamped onto every serial produced automatically - no typing.",
				"<b>Test Certificate</b> - one per unit. On submit it sets the serial's QC status, and "
				"a unit that has not passed cannot be put on a Delivery Note.",
				"<b>Trace a Serial</b> for one pump's ancestry; <b>Batch Defect Analysis</b> for the "
				"reverse - every pump built from a suspect batch.",
			],
			[
				"Approving a heat with an override is a deliberate, recorded act. Use it rarely.",
				"If a Manufacture entry warns that no traceable batches were consumed, fix it before "
				"submitting - that gap is permanent.",
			],
		),
		"shortcuts": [
			("Heat Record", "DocType", "Heat Record", "red"),
			("Winding Batch Record", "DocType", "Winding Batch", "orange"),
			("Pump Test Certificate", "DocType", "Test Certificate", "green"),
			("Batch Defect Analysis", "Report", "Batch Defect Analysis", "purple"),
			("Serial Genealogy", "Report", "Trace a Serial", "blue"),
		],
		"links": [
			("Foundry & Winding", ["Heat Record", "Winding Batch Record", "Batch"]),
			("Test & Dispatch", ["Pump Test Certificate", "Serial No", "Stock Entry", "Work Order"]),
			("Reports", ["Batch Defect Analysis", "Serial Genealogy", "Heat Chemistry Log",
				"Model Reliability", "Unregistered Stock"]),
		],
	},
	{
		"name": "Kumar Stock and Manufacturing",
		"label": "Production",
		"title_text": "Stock &amp; Manufacturing",
		"icon": "kumar-pump",
		"sequence": 5,
		"roles": ["Production Manager", "Quality Engineer", "System Manager", "Foundry Operator"],
		"guide": _guide(
			"Stock &amp; Manufacturing",
			"The ERPNext side of the plant, in the order a pump is actually built: buy the "
			"components, melt and wind, raise a Work Order against a BOM, consume the batches, "
			"produce a serialised pump, test it, then dispatch it. Nothing here is a KUMAR "
			"invention - it is standard ERPNext, wired so the serial and batch numbers flow.",
			[
				"<b>Item</b> - a finished pump has <i>Has Serial No</i> with the series "
				"<code>KP-&lt;MODEL&gt;-.YY..MM.-.#####</code>; casings, stators and rotors have "
				"<i>Has Batch No</i>. The <b>Traceability Group</b> field on the item is what tells "
				"the genealogy hook which slot a consumed part fills.",
				"<b>Purchase Order &rarr; Purchase Receipt</b> for bought-out parts (bearings, "
				"seals, capacitors). Supplier lots come in as batches.",
				"<b>BOM</b> then <b>Work Order</b> for a production run. Print the <b>Route Card</b> "
				"from the Work Order and let it travel with the job.",
				"<b>Stock Entry (Manufacture)</b> consumes the casing and stator batches and "
				"produces the pump. Serial numbers are generated here, and the heat and winding "
				"numbers are stamped onto each one automatically.",
				"<b>Pump Test Certificate</b> per unit, then <b>Delivery Note</b> / "
				"<b>Sales Invoice</b>. A unit that has not passed test cannot be delivered.",
				"<b>Stock Ledger</b>, <b>Stock Balance</b> and <b>Batch-wise Balance History</b> "
				"answer where anything is; <b>Serial No</b> answers what one unit is.",
			],
			[
				"Do not type serials into the old text field - v16 keeps them in a Serial and Batch "
				"Bundle. Use the scan button or the bundle selector.",
				"A Manufacture entry that consumes no traceable batch will warn you. Fix it before "
				"submitting; that gap cannot be filled in later.",
			],
		),
		# The rail, grouped by the shop that does the work rather than as one
		# flat numbered list. The foundry and the winding shop run on their own
		# rhythm and their records belong to no work order, so they collapse
		# together; the run and its output are the other two groups.
		# DISABLED. frappe's "Sidebar Item Group" type exists in the doctype but
		# the v16 rail did not render the children under it - the whole
		# Production rail collapsed to a single line. Kept here because the
		# grouping is right; re-enable only after watching it render.
		# (group label, icon, [(link_type, target, label), ...])
		"_sidebar_groups_disabled": [
			("Foundry & Winding shop", "kumar-heat", [
				("DocType", "Heat Record", "Heat Record (melt)"),
				("DocType", "Winding Batch Record", "Winding Batch Record"),
				("DocType", "Batch", "Batches"),
				("DocType", "Workstation", "Workstations"),
			]),
			("The production run", "kumar-factory", [
				("DocType", "BOM", "1. BOM"),
				("DocType", "Work Order", "2. Work Order"),
				("DocType", "Job Card", "3. Job Card"),
				("DocType", "Stock Entry", "4. Manufacture"),
			]),
			("What comes out", "kumar-serial", [
				("DocType", "Serial No", "5. Serial No"),
				("DocType", "Pump Test Certificate", "6. Test Certificate"),
				("DocType", "Delivery Note", "7. Dispatch"),
			]),
			("Reports", "kumar-report", [
				("Report", "Production and Sales Summary", "Production & Sales"),
				("Report", "Batch Defect Analysis", "Batch Defect Analysis"),
				("Report", "Serial Genealogy", "Serial Genealogy"),
			]),
		],
		# The rail, in the order a pump is actually built, so it can be walked top
		# to bottom on screen: the metal arrives, the run is authorised, the two
		# shops do their work, the batches are consumed, a serialised pump comes
		# out and is proved. The foundry and winding steps each get BOTH their
		# quality record and the stock entry that moved the material, because
		# "where is the melt" and "where did the pig iron go" are different
		# questions and the demo gets asked both.
		# (link_type, target-or-url, label)
		"rail": [
			("DocType", "Purchase Receipt", "1 · Raw material in"),
			("DocType", "BOM", "2 · BOM"),
			("DocType", "Work Order", "3 · Work Order"),
			("DocType", "Job Card", "4 · Job Card"),
			("DocType", "Heat Record", "5 · Foundry · Heat Record"),
			("URL", "/desk/stock-entry?stock_entry_type=Foundry%20Melt",
				"6 · Foundry · Melt entries"),
			("DocType", "Winding Batch Record", "7 · Winding · Batch Record"),
			("URL", "/desk/stock-entry?stock_entry_type=Winding%20Output",
				"8 · Winding · Stator entries"),
			("DocType", "Stock Entry", "9 · Manufacture"),
			("DocType", "Serial No", "10 · Serial No"),
			("DocType", "Pump Test Certificate", "11 · Test Certificate"),
		],
		# In the order a pump is actually built, so the rail can be walked top to
		# bottom in a demo: what it is made of, what authorises the run, what the
		# shop floor works to, what the melt and the winding were, what comes out
		# with a serial, and what proves it passed.
		"shortcuts": [
			("BOM", "DocType", "1. BOM", "grey"),
			("Work Order", "DocType", "2. Work Order", "orange"),
			("Job Card", "DocType", "3. Job Card", "orange"),
			("Heat Record", "DocType", "4. Heat (melt)", "red"),
			("Winding Batch Record", "DocType", "5. Winding lot", "purple"),
			("Stock Entry", "DocType", "6. Manufacture", "blue"),
			("Serial No", "DocType", "7. Serial No", "green"),
			("Pump Test Certificate", "DocType", "8. Test Certificate", "green"),
		],
		"links": [
			# the run itself, in sequence
			("1 · Plan the run", ["BOM", "Production Plan", "Work Order", "Job Card",
				"Routing", "Operation", "Workstation"]),
			# what KUMAR records that ERPNext does not - and it belongs HERE, beside
			# the run it feeds, not only under Traceability
			("2 · Batches that go in", ["Heat Record", "Winding Batch Record", "Batch",
				"Serial and Batch Bundle"]),
			("3 · Build and test", ["Stock Entry", "Serial No", "Pump Test Certificate"]),
			("4 · Dispatch", ["Delivery Note", "Sales Invoice", "Packing Slip"]),
			("5 · Reports", ["Production and Sales Summary", "Work Order Summary",
				"Job Card Summary", "Batch Defect Analysis", "Serial Genealogy",
				"Stock vs Registration Reconciliation"]),
			# The foundry and the winding shop are their own shops - they run on
			# their own rhythm and their records belong to nobody's work order -
			# so they get a card of their own rather than being buried in stock.
			("Foundry & Winding shop", ["Heat Record", "Winding Batch Record", "Batch",
				"Workstation", "Operation"]),
			# What the run is configured FROM. An operator asks "where do I add a
			# model / an operation / a workstation" and it should be one group,
			# not scattered between here and Masters.
			("Setup · what the run is built from", ["Item", "BOM", "Operation", "Workstation",
				"Routing", "Pump Model", "Pump Category", "Warehouse", "Item Group", "UOM"]),
			("Stock Transactions", ["Purchase Receipt", "Material Request",
				"Stock Reconciliation"]),
			("Stock Masters", ["Batch", "Serial No", "Serial and Batch Bundle"]),
			("Buying & Selling", ["Purchase Order", "Supplier", "Sales Order",
				"Sales Invoice", "Customer", "Quotation"]),
			("Stock Reports", ["Stock Ledger", "Stock Balance", "Stock Projected Qty",
				"Batch-Wise Balance History", "Serial No Ledger", "Stock Ageing",
				"Item-wise Price List Rate"]),
			("Manufacturing Reports", ["Work Order Summary", "BOM Explorer",
				"Production Planning Report", "Job Card Summary"]),
		],
	},
	{
		"name": "Kumar Masters",
		"label": "Masters",
		"title_text": "KUMAR Masters",
		"icon": "kumar-settings",
		"sequence": 6,
		"roles": ["System Manager", "Production Manager", "Dealer Manager"],
		"guide": _guide(
			"KUMAR Masters",
			"The catalogue and the network. Change things here and the rest of the system follows - "
			"warranty periods, model specs, who a dealer reports to.",
			[
				"<b>Pump Category</b> sets the default warranty months for a whole family.",
				"<b>Pump Model</b> holds the real specs from the brochure and can override the "
				"category's warranty. Each model points at one stock Item.",
				"<b>Dealer Tree</b> is a hierarchy: Branch - Distributor - Dealer - Sub-Dealer. A "
				"dealer login sees its own records and everything below it, nothing sideways.",
				"<b>Settings</b> holds every assumption - SLA hours, warranty basis, QC enforcement, "
				"QR base URL. Nothing is hardcoded.",
				"<b>Historical Serial Import</b> is for go-live: download the CSV template, fill in "
				"the pumps you built and sold before this system existed, check the file, then "
				"import. Rows with a sale date come in as submitted registrations with the warranty "
				"already running.",
				"<b>Stock vs Registration Reconciliation</b> is the list of loose ends afterwards - "
				"above all the pumps that have LEFT the building with no registration behind them, "
				"so their warranty never started.",
			],
			[
				"Give a dealer a login by setting <b>Portal User</b> on the Dealer record. That single "
				"field is what row-level access is derived from.",
				"Always run the check step before importing. A registration is submitted, so a wrong "
				"warranty date can only be cancelled and amended afterwards, never quietly deleted.",
			],
		),
		"shortcuts": [
			("Pump Model", "DocType", "Pump Model", "blue"),
			("Pump Category", "DocType", "Pump Category", "green"),
			("Dealer", "DocType", "Dealer Tree", "orange"),
			("Kumar Service Settings", "DocType", "Settings", "grey"),
			("historical-import", "Page", "Historical Import", "purple"),
		],
		"links": [
			("Catalogue", ["Pump Model", "Pump Category", "Item"]),
			("Network", ["Dealer", "Service Technician", "Customer"]),
			("Configuration", ["Kumar Service Settings"]),
			("Data Migration", ["Stock vs Registration Reconciliation", "Unregistered Stock"]),
		],
	},
]


def _block(btype, data):
	return {"id": frappe.generate_hash(length=10), "type": btype, "data": data}


def ensure_sidebars():
	"""Give every KUMAR workspace a Workspace Sidebar of its own.

	v16 navigates by Workspace Sidebar, not by Workspace: the apps-screen tile
	and the left rail both resolve through it, and a workspace without one is
	unreachable - frappe answers the tile click with "Icon is not correctly
	configured". Frappe builds these during its own v16 migration, so a
	workspace THIS file adds afterwards never gets one. Hence this.

	Idempotent, and it never edits a sidebar that already exists - those carry
	whatever the user has since arranged.
	"""
	from kumar_service.setup.icons import WORKSPACE_ICONS

	made = []
	for ws in WORKSPACES:
		label = ws["label"]
		if not frappe.db.exists("Workspace", label):
			continue
		icon = WORKSPACE_ICONS.get(label, ws.get("icon"))

		# Rebuilt every run, not created-once. Skipping an existing sidebar meant
		# a shortcut added to this file afterwards never reached the rail - the
		# workspace had it and the sidebar did not, which is precisely how the
		# Management reports ended up invisible in the nav.
		existing = frappe.db.exists("Workspace Sidebar", label)
		doc = frappe.get_doc("Workspace Sidebar", existing) if existing else frappe.new_doc(
			"Workspace Sidebar"
		)
		doc.update({"title": label, "header_icon": ws.get("icon"), "module": MODULE})
		doc.set("items", [])
		# the first item IS the workspace - that is what the tile opens
		doc.append("items", {
			"label": label, "link_type": "Workspace", "type": "Link", "link_to": label,
			"icon": icon, "collapsible": 1,
		})
		def exists(kind, target):
			return bool(
				(kind == "Report" and frappe.db.exists("Report", target))
				or (kind == "DocType" and frappe.db.exists("DocType", target))
				or (kind == "Page" and frappe.db.exists("Page", target))
			)

		groups = ws.get("sidebar_groups")
		if groups:
			# a collapsible header per shop, with its records folded underneath -
			# nine entries in a flat list is a wall, three groups is a process
			for group_label, group_icon, children in groups:
				rows = [(k, t, text) for k, t, text in children if exists(k, t)]
				if not rows:
					continue
				doc.append("items", {
					"label": group_label, "type": "Sidebar Item Group",
					"icon": group_icon, "collapsible": 1, "show_arrow": 1,
				})
				for kind, target, text in rows:
					doc.append("items", {
						"label": text, "link_type": kind, "type": "Link", "link_to": target,
						"icon": group_icon, "child": 1, "indent": 1, "collapsible": 1,
					})
		elif ws.get("rail"):
			# An explicit rail, where the shortcuts are not enough: a filtered
			# list is a URL, not a doctype, and the foundry and winding steps are
			# only findable as filters. Flat and numbered - v16 renders no
			# children under a group (see _sidebar_groups_disabled), so the shop
			# name goes in the label and the order carries the process.
			for kind, target, text in ws["rail"]:
				if kind == "URL":
					doc.append("items", {
						"label": text, "link_type": "URL", "type": "Link", "url": target,
						"icon": WORKSPACE_ICONS.get(text) or icon, "child": 1, "indent": 1,
					})
					continue
				if not exists(kind, target):
					continue
				doc.append("items", {
					"label": text, "link_type": kind, "type": "Link", "link_to": target,
					"icon": WORKSPACE_ICONS.get(text) or icon, "child": 1, "indent": 1,
				})
		else:
			# then its shortcuts, so the rail is useful rather than a single line
			for target, kind, text, _colour in ws.get("shortcuts", []):
				if not exists(kind, target):
					continue
				doc.append("items", {
					"label": text, "link_type": kind, "type": "Link", "link_to": target,
					"icon": WORKSPACE_ICONS.get(text) or icon, "child": 1, "indent": 1,
				})
		doc.flags.ignore_permissions = True
		if existing:
			doc.save(ignore_permissions=True)
		else:
			doc.insert(ignore_permissions=True, set_name=label)
			made.append(label)
	if made:
		print(f"  + created {len(made)} workspace sidebar(s): {', '.join(made)}")
	return made


def build_all():
	# cards first: _make() only attaches a card that already exists
	ensure_number_cards()
	for ws in WORKSPACES:
		_make(ws)
	prune_stale()
	ensure_sidebars()
	frappe.db.commit()


def prune_stale():
	"""Drop KUMAR workspaces that this file no longer defines.

	A Workspace takes its name from its `label`. An earlier build named them
	from the longer display title instead, which left a second copy of four
	screens behind - "Warranty" and "Warranty & Claims" both in the sidebar,
	and so on. Nothing points at the strays, but they double the nav.

	Only workspaces in this module are considered, so a workspace someone
	built by hand in another module is never touched.
	"""
	wanted = {ws["label"] for ws in WORKSPACES}
	removed = []
	for name in frappe.get_all("Workspace", filters={"module": MODULE}, pluck="name"):
		if name in wanted:
			continue
		frappe.delete_doc(
			"Workspace", name, force=True, ignore_permissions=True, delete_permanently=True
		)
		removed.append(name)
	if removed:
		print(f"  + removed {len(removed)} stale workspace(s): {', '.join(removed)}")

	removed += prune_stale_files(wanted)
	return removed


def prune_stale_files(wanted=None):
	"""Delete the JSON a stale workspace left behind on disk.

	Deleting the record is not enough. A standard Workspace ships as a folder of
	JSON in the app, and Frappe re-imports every one of those on `bench migrate`
	- so a screen deleted here came straight back on the next migrate, and
	"KUMAR Masters" reappeared in the sidebar next to "Masters". Take the file
	out and it stays gone.
	"""
	import json
	import shutil
	from pathlib import Path

	wanted = wanted if wanted is not None else {ws["label"] for ws in WORKSPACES}
	root = Path(frappe.get_app_path("kumar_service")) / "kumar_service" / "workspace"
	if not root.is_dir():
		return []

	removed = []
	for folder in sorted(root.iterdir()):
		definition = folder / f"{folder.name}.json"
		if not folder.is_dir() or not definition.exists():
			continue
		try:
			label = json.loads(definition.read_text(encoding="utf-8")).get("label")
		except (OSError, ValueError):
			continue
		if label in wanted:
			continue
		shutil.rmtree(folder, ignore_errors=True)
		removed.append(f"{folder.name}.json")

	if removed:
		print(f"  + removed {len(removed)} orphaned workspace file(s): {', '.join(removed)}")
	return removed


#: The four numbers a proprietor wants before anything else, as Number Cards on
#: the Management screen. Each is a live count or sum against a doctype with a
#: this-month filter, so they move on their own - no script, nothing to refresh.
#:
#: (card label, doctype, function, field, filters, colour)
MANAGEMENT_CARDS = [
	("Pumps sold this month", "Pump Registration", "Count", None,
		[["Pump Registration", "sale_date", "Timespan", "this month", False],
		 ["Pump Registration", "docstatus", "=", 1, False]], "#16A34A"),
	("Pumps built this month", "Serial No", "Count", None,
		[["Serial No", "custom_manufacturing_date", "Timespan", "this month", False]], "#1D4ED8"),
	("Claims raised this month", "Kumar Warranty Claim", "Count", None,
		[["Kumar Warranty Claim", "claim_date", "Timespan", "this month", False],
		 ["Kumar Warranty Claim", "docstatus", "<", 2, False]], "#C2410C"),
	("Warranty cost this month", "Kumar Warranty Claim", "Sum", "claim_amount",
		[["Kumar Warranty Claim", "claim_date", "Timespan", "this month", False],
		 ["Kumar Warranty Claim", "docstatus", "<", 2, False]], "#B91C1C"),
	("Purchases this month", "Purchase Invoice", "Sum", "grand_total",
		[["Purchase Invoice", "posting_date", "Timespan", "this month", False],
		 ["Purchase Invoice", "docstatus", "=", 1, False]], "#475569"),
	("Complaints this month", "Service Request", "Count", None,
		[["Service Request", "reported_on", "Timespan", "this month", False],
		 ["Service Request", "docstatus", "<", 2, False]], "#A16207"),
]


def ensure_number_cards():
	"""Create the Management number cards. Safe to run again.

	Rebuilt every run rather than skipped-if-present: the filters are the whole
	point of the card, and a card left behind with last month's definition is
	worse than no card.
	"""
	made = []
	for label, doctype, function, based_on, filters, colour in MANAGEMENT_CARDS:
		if not frappe.db.exists("DocType", doctype):
			continue
		values = {
			"label": label,
			"type": "Document Type",
			"document_type": doctype,
			"function": function,
			"aggregate_function_based_on": based_on,
			"filters_json": json.dumps(filters),
			"is_public": 1,
			"show_percentage_stats": 1,
			"stats_time_interval": "Monthly",
			"color": colour,
			"module": MODULE,
		}
		existing = frappe.db.exists("Number Card", label)
		if existing:
			doc = frappe.get_doc("Number Card", existing)
			doc.update(values)
			doc.flags.ignore_permissions = True
			doc.save(ignore_permissions=True)
		else:
			doc = frappe.new_doc("Number Card")
			doc.update(values)
			doc.flags.ignore_permissions = True
			doc.insert(ignore_permissions=True, set_name=label)
		made.append(label)
	if made:
		print(f"  + number cards: {len(made)}")
	return made


def _make(ws):
	# a Workspace names itself from its label, so that is the identity to check
	name = ws["label"]
	doc = (
		frappe.get_doc("Workspace", name)
		if frappe.db.exists("Workspace", name)
		else frappe.new_doc("Workspace")
	)

	doc.update(
		{
			"name": name,
			"title": name,
			"label": ws["label"],
			"module": MODULE,
			"icon": ws["icon"],
			"public": 1,
			"is_hidden": 0,
			"sequence_id": ws["sequence"],
		}
	)

	# Work first, reading material last: the guide sits at the BOTTOM so the
	# screen opens on what people came to do.
	content = [
		_block("header", {"text": f"<span class='h4'><b>{ws['title_text']}</b></span>", "col": 12}),
	]

	# Number cards first, where a manager's eye lands. Only the screens that ask
	# for them get them - a shop-floor rail does not need this month's turnover.
	cards = ws.get("number_cards") or []
	if cards:
		content.append(_block("header", {"text": "<span class='h4'><b>This month</b></span>", "col": 12}))
		for card in cards:
			content.append(_block("number_card", {"number_card_name": card, "col": 4}))
		content.append(_block("spacer", {"col": 12}))

	content.append(_block("header", {"text": "<span class='h4'><b>Shortcuts</b></span>", "col": 12}))
	for label, *_rest in ((s[2],) for s in ws["shortcuts"]):
		content.append(_block("shortcut", {"shortcut_name": label, "col": 3}))

	content.append(_block("spacer", {"col": 12}))
	content.append(_block("header", {"text": "<span class='h4'><b>Reports & Masters</b></span>", "col": 12}))
	for card_label, _items in ws["links"]:
		content.append(_block("card", {"card_name": card_label, "col": 4}))

	content.append(_block("spacer", {"col": 12}))
	content.append(_block("header", {"text": "<span class='h4'><b>How to use this screen</b></span>", "col": 12}))
	content.append(_block("paragraph", {"text": ws["guide"], "col": 12}))

	doc.content = json.dumps(content)

	doc.set("shortcuts", [])
	for link_to, link_type, label, color in ws["shortcuts"]:
		if link_type == "DocType" and not frappe.db.exists("DocType", link_to):
			continue
		if link_type == "Report" and not frappe.db.exists("Report", link_to):
			continue
		if link_type == "Page" and not frappe.db.exists("Page", link_to):
			continue
		doc.append(
			"shortcuts",
			{"type": link_type, "link_to": link_to, "label": label, "color": color},
		)

	doc.set("links", [])
	for card_label, items in ws["links"]:
		doc.append(
			"links",
			{
				"label": card_label,
				"type": "Card Break",
				"link_count": 0,
				"onboard": 0,
				"hidden": 0,
			},
		)
		count = 0
		for item in items:
			link_type = "Report" if frappe.db.exists("Report", item) else "DocType"
			if link_type == "DocType" and not frappe.db.exists("DocType", item):
				continue
			row = {
				"label": item,
				"type": "Link",
				"link_type": link_type,
				"link_to": item,
				"hidden": 0,
				"onboard": 0,
				"is_query_report": 1 if link_type == "Report" else 0,
			}
			if link_type == "Report":
				row["dependencies"] = frappe.db.get_value("Report", item, "ref_doctype")
			doc.append("links", row)
			count += 1
		doc.links[-(count + 1)].link_count = count

	doc.set("number_cards", [])
	for card in ws.get("number_cards") or []:
		if frappe.db.exists("Number Card", card):
			doc.append("number_cards", {"number_card_name": card, "label": card})

	doc.set("roles", [])
	for role in ws["roles"]:
		if frappe.db.exists("Role", role):
			doc.append("roles", {"role": role})

	doc.flags.ignore_permissions = True
	doc.flags.ignore_links = True
	if frappe.db.exists("Workspace", name):
		doc.save(ignore_permissions=True)
	else:
		doc.insert(ignore_permissions=True)
