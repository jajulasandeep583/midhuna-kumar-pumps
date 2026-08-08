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
		"name": "Kumar Management",
		"label": "Management",
		"title_text": "Management",
		"icon": "kumar-management",
		"sequence": 0,
		"roles": ["System Manager", "Dealer Manager", "Service Manager",
			"Production Manager", "Accounts User"],
		"guide": _guide(
			"Management",
			"Six screens that read the same month from six angles. Nothing here is typed in - "
			"every number is computed from the documents the plant and the dealers are already "
			"raising, so if a figure looks wrong the answer is always in the document behind it. "
			"Click any row to open the document it came from.",
			[
				"<b>Management Dashboard</b> is the daily one: revenue, spend, margin, output, "
				"quality, complaints and the wage bill on one screen. It answers <i>how are we "
				"doing</i>; the other five answer <i>why</i>.",
				"<b>Sales Analytics</b> - revenue by day, best models, top dealers and customers, "
				"and the receivable ageing. The order-to-invoice funnel shows where a sale is "
				"stuck: ordered but not delivered, or delivered but not billed.",
				"<b>Purchase Analytics</b> - spend by supplier and material, what has been ordered "
				"and not received, and what has been received and not billed.",
				"<b>Daily Production</b> - units built per day against units tested and passed, "
				"split by shift, with the foundry and winding lines underneath.",
				"<b>Dealer Network</b> - every dealer ranked, with a fault rate per dealer and the "
				"districts the pumps actually landed in. Silent dealers are the ones to ring.",
				"<b>People &amp; Payroll</b> - headcount by department, attendance for the period, "
				"and what the last payroll run cost.",
			],
			[
				"Every screen defaults to the last 30 days. Change the period at the top - the "
				"whole screen, tiles and tables included, moves with it.",
				"Money tiles are shortened to lakhs and crores so they read at a glance; hover for "
				"the exact rupee figure.",
				"A dealer login never sees this workspace. Dealers get <b>My Business</b>, which "
				"shows only their own network.",
			],
		),
		"shortcuts": [
			("management-dashboard", "Page", "Management Dashboard", "blue"),
			("sales-analytics", "Page", "Sales Analytics", "green"),
			("purchase-analytics", "Page", "Purchase Analytics", "orange"),
			("production-daily", "Page", "Daily Production", "purple"),
			("dealer-network", "Page", "Dealer Network", "blue"),
			("people-payroll", "Page", "People & Payroll", "grey"),
		],
		"links": [
			("Sales", ["Sales Invoice", "Sales Order", "Delivery Note", "Customer", "Dealer"]),
			("Purchase", ["Purchase Invoice", "Purchase Order", "Purchase Receipt",
				"Material Request", "Supplier"]),
			("Plant", ["Work Order", "Stock Entry", "BOM", "Pump Test Certificate",
				"Heat Record", "Winding Batch Record"]),
			("People", ["Employee", "Attendance", "Salary Slip", "Leave Application",
				"Salary Structure"]),
			("Money", ["Payment Entry", "Journal Entry", "Accounts Receivable",
				"Accounts Payable", "General Ledger", "Profit and Loss Statement"]),
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
		"name": "Kumar Service Desk",
		"label": "Service Desk",
		"title_text": "Service Desk",
		"icon": "support",
		"sequence": 2,
		"roles": ["Service Manager", "Service Technician", "System Manager"],
		"guide": _guide(
			"the Service Desk",
			"Everything after a customer complains: triage it, put a technician on it, and close it "
			"inside the SLA the company promises (24 hours to respond).",
			[
				"Open the complaint from <b>Open Requests</b>. The pump's full history is already on "
				"the form - check <b>Repeat Failure</b> before assuming it is a fresh fault.",
				"Set <b>Technician</b> and <b>Service Centre</b>, then set status to Assigned. "
				"The response clock stops when you fill <b>First Response</b>.",
				"The technician records what happened in a <b>Service Visit</b>: findings, parts used, "
				"labour. Warranty jobs default to non-chargeable.",
				"Close the request with a <b>Root Cause</b>. That field is what feeds the Pareto chart "
				"and tells the factory what to fix.",
			],
			[
				"<b>SLA Breaches</b> is the list to clear first thing every morning.",
				"If the root cause is a Manufacturing Defect, raise a Warranty Claim so the batch gets "
				"analysed - otherwise the plant never learns.",
			],
		),
		"shortcuts": [
			# first, because answering the dealers is the job
			("dealer-conversations", "Page", "Dealer Conversations", "green"),
			("pump-lookup", "Page", "Pump Lookup", "blue"),
			("Service Request", "DocType", "Open Requests", "red"),
			("Service Visit", "DocType", "Today's Visits", "orange"),
			("Service Technician", "DocType", "Technicians", "blue"),
			("SLA Compliance", "Report", "SLA Compliance", "purple"),
			# the company side of the dealer portal
			("Dealer Requests & Claims", "Report", "Dealer Requests", "green"),
		],
		"links": [
			("Service", ["Service Request", "Service Visit", "Service Technician"]),
			("Analysis", ["Dealer Performance", "Technician Productivity", "Model Reliability",
				"Dealer Requests & Claims"]),
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
				"Stock vs Registration Reconciliation", "Dealer Requests & Claims"]),
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
		"shortcuts": [
			("Stock Entry", "DocType", "Stock Entry", "blue"),
			("Work Order", "DocType", "Work Order", "orange"),
			("Serial No", "DocType", "Serial No", "green"),
			("Batch", "DocType", "Batch", "purple"),
			("Item", "DocType", "Items", "grey"),
		],
		"links": [
			("Manufacturing", ["BOM", "Work Order", "Job Card", "Production Plan",
				"Workstation", "Operation", "Routing"]),
			("Stock Transactions", ["Stock Entry", "Delivery Note", "Purchase Receipt",
				"Material Request", "Stock Reconciliation", "Packing Slip"]),
			("Stock Masters", ["Item", "Item Group", "Warehouse", "Batch", "Serial No",
				"UOM", "Serial and Batch Bundle"]),
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


def build_all():
	for ws in WORKSPACES:
		_make(ws)
	prune_stale()
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
		_block("header", {"text": "<span class='h4'><b>Shortcuts</b></span>", "col": 12}),
	]
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
