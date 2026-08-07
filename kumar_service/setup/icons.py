"""Give every KUMAR doctype, workspace, shortcut and sidebar link its own icon.

The glyphs live in public/icons/kumar-icons.svg and are loaded through the
app_include_icons hook, so they colour themselves like any other desk icon and
follow the light/dark theme.
"""

import frappe

DOCTYPE_ICONS = {
	# masters
	"Pump Category": "kumar-category",
	"Pump Model": "kumar-model",
	"Dealer": "kumar-dealer",
	"Service Technician": "kumar-technician",
	"Kumar Service Settings": "kumar-settings",
	# sales & warranty
	"Pump Registration": "kumar-registration",
	"Kumar Warranty Claim": "kumar-claim",
	# service
	"Service Request": "kumar-complaint",
	"Service Visit": "kumar-visit",
	# plant
	"Heat Record": "kumar-heat",
	"Winding Batch Record": "kumar-winding",
	"Pump Test Certificate": "kumar-test",
}

WORKSPACE_ICONS = {
	"Management": "kumar-management",
	"Dealer Desk": "kumar-dealer",
	"Service Desk": "kumar-service",
	"Warranty": "kumar-warranty",
	"Traceability": "kumar-trace",
	# the building, not a pump - the pump is one of the things made inside it
	"Production": "kumar-factory",
	# not the settings gear: this screen has a Settings link of its own, and a
	# screen that draws the same glyph as one of its children reads as a
	# duplicate rather than a parent
	"Masters": "kumar-masters",
}

# What an unmapped link falls back to. It used to be "kumar-pump", which put
# two dozen identical pumps down the Production sidebar and told the reader
# nothing about any of them.
FALLBACK_ICON = "kumar-list"

# Plain URLs that belong in a workspace's sidebar. The dealer portal is not a
# desk page - it is a website route - so nothing in the workspace's own links
# can point at it, and without this it is only reachable by typing the address.
EXTRA_SIDEBAR_LINKS = {
	"Dealer Desk": [
		{"label": "Dealer Portal", "url": "/dealer-portal", "icon": "kumar-shop"},
		{"label": "Warranty Check", "url": "/warranty-check", "icon": "kumar-qr"},
	],
	"Management": [
		{"label": "Dealer Portal", "url": "/dealer-portal", "icon": "kumar-shop"},
	],
	"Service Desk": [
		{"label": "Warranty Check", "url": "/warranty-check", "icon": "kumar-qr"},
	],
}

# the order they should read in the desk sidebar
SIDEBAR_ORDER = [
	"Management",
	"Dealer Desk",
	"Service Desk",
	"Warranty",
	"Traceability",
	"Production",
	"Masters",
]

# anything else that shows up as a link, shortcut or report label
EXTRA_ICONS = {
	# standard doctypes we link to
	"Serial No": "kumar-serial",
	"Batch": "kumar-winding",
	"Item": "kumar-pump",
	"Customer": "kumar-dealer",
	"Sales Invoice": "kumar-claim",
	"Delivery Note": "kumar-visit",
	"Stock Entry": "kumar-warehouse",
	"Work Order": "kumar-motor",
	# reports
	"Warranty Expiring Soon": "kumar-warranty",
	"Unregistered Stock": "kumar-serial",
	"SLA Compliance": "kumar-report",
	"Heat Chemistry Log": "kumar-heat",
	"Technician Productivity": "kumar-technician",
	"Batch Defect Analysis": "kumar-quality",
	"Serial Genealogy": "kumar-trace",
	"Dealer Performance": "kumar-dealer",
	"Model Reliability": "kumar-model",
	"Warranty Cost Analysis": "kumar-claim",
	# desk pages
	"Pump Lookup": "kumar-qr",
	"pump-lookup": "kumar-qr",
	"Management Dashboard": "kumar-report",
	"management-dashboard": "kumar-report",
	"Sales Analytics": "kumar-sales",
	"sales-analytics": "kumar-sales",
	"Purchase Analytics": "kumar-purchase",
	"purchase-analytics": "kumar-purchase",
	"Daily Production": "kumar-production",
	"production-daily": "kumar-production",
	"Dealer Network": "kumar-dealer",
	"dealer-network": "kumar-dealer",
	"People & Payroll": "kumar-people",
	"people-payroll": "kumar-people",
	"My Business": "kumar-shop",
	"my-business": "kumar-shop",
	# management link groups and the standard doctypes they point at
	"Sales": "kumar-sales",
	"Purchase": "kumar-purchase",
	"Plant": "kumar-production",
	"People": "kumar-people",
	"Money": "kumar-payroll",
	"Sales Order": "kumar-sales",
	"Purchase Order": "kumar-purchase",
	"Purchase Invoice": "kumar-purchase",
	"Purchase Receipt": "kumar-purchase",
	"Material Request": "kumar-purchase",
	"Supplier": "kumar-purchase",
	"BOM": "kumar-production",
	"Employee": "kumar-people",
	"Attendance": "kumar-people",
	"Salary Slip": "kumar-payroll",
	"Salary Structure": "kumar-payroll",
	"Leave Application": "kumar-people",
	"Payment Entry": "kumar-payroll",
	"Journal Entry": "kumar-payroll",
	# shortcut labels
	"Register Pump": "kumar-registration",
	"New Service Request": "kumar-complaint",
	"My Claims": "kumar-claim",
	"Warranty Lookup": "kumar-qr",
	"Open Requests": "kumar-complaint",
	"Today's Visits": "kumar-visit",
	"Technicians": "kumar-technician",
	"Pending Claims": "kumar-claim",
	"Warranty Expiring (30d)": "kumar-report",
	"Warranty Cost": "kumar-claim",
	"Heat Record": "kumar-heat",
	"Winding Batch": "kumar-winding",
	"Test Certificate": "kumar-certificate",
	"Trace a Serial": "kumar-qr",
	"Dealer Tree": "kumar-dealer",
	"Settings": "kumar-settings",
	"Items": "kumar-pump",
	"Pump Model": "kumar-model",
	"Pump Category": "kumar-category",
	# link-group headings
	"Sales & Registration": "kumar-registration",
	"Service": "kumar-service",
	"Analysis": "kumar-report",
	"Claims": "kumar-claim",
	"Reports": "kumar-report",
	"Foundry & Winding": "kumar-heat",
	"Test & Dispatch": "kumar-test",
	"Catalogue": "kumar-model",
	"Network": "kumar-dealer",
	"Configuration": "kumar-settings",
	# The standard stock and manufacturing side of the Production screen. Every
	# one of these used to hit the fallback, so the whole sidebar was pumps.
	"Job Card": "kumar-production",
	"Production Plan": "kumar-production",
	"Workstation": "kumar-production",
	"Operation": "kumar-production",
	"Routing": "kumar-production",
	"Warehouse": "kumar-warehouse",
	"Stock Reconciliation": "kumar-warehouse",
	"Packing Slip": "kumar-warehouse",
	"Item Group": "kumar-category",
	"UOM": "kumar-category",
	"Serial and Batch Bundle": "kumar-serial",
	"Quotation": "kumar-sales",
	"Stock Ledger": "kumar-report",
	"Stock Balance": "kumar-report",
	"Stock Projected Qty": "kumar-report",
	"Batch-Wise Balance History": "kumar-report",
	"Serial No Ledger": "kumar-report",
	"Stock Ageing": "kumar-report",
	"Item-wise Price List Rate": "kumar-report",
	"Work Order Summary": "kumar-report",
	"BOM Explorer": "kumar-report",
	"Production Planning Report": "kumar-report",
	"Job Card Summary": "kumar-report",
	# the standard finance reports on the Management screen
	"Accounts Receivable": "kumar-report",
	"Accounts Payable": "kumar-report",
	"General Ledger": "kumar-report",
	"Profit and Loss Statement": "kumar-report",
	# link-group headings on the stock screen
	"Make": "kumar-production",
	"Move": "kumar-warehouse",
	"Stock Masters": "kumar-category",
	"Buying & Selling": "kumar-sales",
	"Stock Reports": "kumar-report",
	"Manufacturing Reports": "kumar-report",
}


def icon_for(label):
	return (
		DOCTYPE_ICONS.get(label)
		or EXTRA_ICONS.get(label)
		or WORKSPACE_ICONS.get(label)
	)


def install():
	n_dt = 0
	for dt, icon in DOCTYPE_ICONS.items():
		if frappe.db.exists("DocType", dt):
			frappe.db.set_value("DocType", dt, "icon", icon, update_modified=False)
			n_dt += 1

	n_ws = 0
	for ws, icon in WORKSPACE_ICONS.items():
		if not frappe.db.exists("Workspace", ws):
			continue
		doc = frappe.get_doc("Workspace", ws)
		doc.icon = icon
		for row in doc.links:
			ic = icon_for(row.label) or icon_for(row.link_to)
			if ic:
				row.icon = ic
		for row in doc.shortcuts:
			ic = icon_for(row.label) or icon_for(row.link_to)
			if ic:
				row.icon = ic
		doc.flags.ignore_permissions = True
		doc.flags.ignore_links = True
		doc.save(ignore_permissions=True)
		n_ws += 1

	# The desk sidebar renders Workspace Sidebar Item rows, not the Workspace
	# itself - these are what actually put a glyph next to the name.
	n_side = 0
	if frappe.db.exists("DocType", "Workspace Sidebar Item"):
		for ws, icon in WORKSPACE_ICONS.items():
			rows = frappe.get_all(
				"Workspace Sidebar Item", filters={"link_to": ws}, fields=["name", "label"]
			)
			for row in rows:
				# leave the per-workspace "Home" row alone; it is meant to read as home
				value = icon if row.label != "Home" else "home"
				frappe.db.set_value(
					"Workspace Sidebar Item", row.name, "icon", value, update_modified=False
				)
				n_side += 1

	n_side += build_app_sidebar()

	frappe.db.commit()
	frappe.clear_cache()
	print(f"  + icons: {n_dt} doctypes, {n_ws} workspaces, {n_side} sidebar rows")


def build_app_sidebar():
	"""List every KUMAR workspace, with its icon, inside each workspace's sidebar.

	Frappe's auto-generated sidebar gives a workspace a single "Home" row, so
	the other workspaces never appear and no icon is ever drawn next to them.
	Adding one row per workspace is what makes the glyphs show up in the nav.
	"""
	if not frappe.db.exists("DocType", "Workspace Sidebar"):
		return 0

	present = [ws for ws in SIDEBAR_ORDER if frappe.db.exists("Workspace", ws)]
	if not present:
		return 0

	# learn the child-table fieldname from a real doc rather than assuming it
	sample = frappe.get_doc("Workspace Sidebar", present[0])
	table_field = next(
		(df.fieldname for df in sample.meta.fields
		 if df.fieldtype == "Table" and df.options == "Workspace Sidebar Item"),
		None,
	)
	if not table_field:
		return 0

	written = 0
	for sidebar in present:
		ws_doc = frappe.get_doc("Workspace", sidebar)
		doc = frappe.get_doc("Workspace Sidebar", sidebar)
		doc.set(table_field, [])

		# 1. the screen itself
		doc.append(table_field, {
			"label": sidebar, "type": "Link", "link_type": "Workspace",
			"link_to": sidebar, "icon": WORKSPACE_ICONS.get(sidebar, FALLBACK_ICON),
		})
		written += 1

		# 2. THIS workspace's own work - its shortcuts and links, nothing else.
		# Listing every workspace in every sidebar is what made all six desks
		# read identically.
		seen = {sidebar}
		for row in list(ws_doc.shortcuts) + [r for r in ws_doc.links if r.type == "Link"]:
			target = row.link_to
			if not target or target in seen:
				continue
			seen.add(target)
			link_type = getattr(row, "link_type", None) or getattr(row, "type", None)
			if link_type not in ("DocType", "Report", "Page", "Dashboard"):
				link_type = "Report" if frappe.db.exists("Report", target) else (
					"Page" if frappe.db.exists("Page", target) else "DocType")
			doc.append(table_field, {
				"label": row.label or target,
				"type": "Link",
				"link_type": link_type,
				"link_to": target,
				"icon": icon_for(row.label) or icon_for(target) or FALLBACK_ICON,
			})
			written += 1

		# 3. the website routes that belong on this desk. link_type "URL" is
		# what makes frappe route out of the desk app to a portal page.
		for extra in EXTRA_SIDEBAR_LINKS.get(sidebar, []):
			doc.append(table_field, {
				"label": extra["label"],
				"type": "Link",
				"link_type": "URL",
				"url": extra["url"],
				"icon": extra.get("icon", FALLBACK_ICON),
			})
			written += 1

		# last row on every sidebar: the guide for THIS screen, which lives at the
		# bottom of the workspace itself
		doc.append(table_field, {
			"label": "How to Use",
			"type": "Link",
			"link_type": "Workspace",
			"link_to": sidebar,
			"icon": "kumar-guide",
		})
		written += 1

		doc.flags.ignore_permissions = True
		doc.flags.ignore_links = True
		doc.save(ignore_permissions=True)
	return written


run = install
