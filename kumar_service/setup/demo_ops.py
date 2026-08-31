"""The commercial and shop-floor half of the demo month.

demo.py builds the traceability story (heats -> windings -> serials -> warranty
-> complaints). This module builds the money and machine story that the
management screens read from:

    suppliers -> Purchase Order -> Purchase Receipt -> Purchase Invoice
    BOM -> Work Order -> Manufacture Stock Entry -> serialised pumps in FG Store
    customers -> Sales Order -> Delivery Note -> Sales Invoice

Same one-month window and the same deterministic seed as demo.py, so a rebuild
tells the same story twice. Every builder is idempotent - it checks for what it
already made and skips - and every document is wrapped, because ERPNext will
legitimately refuse some of these (no stock, QC not passed) and one refusal
must not abort the run.
"""

import random
from datetime import timedelta

import frappe
from frappe.utils import add_days, cint, flt, get_datetime, getdate, now_datetime

from kumar_service.setup.demo import (
	ABBR,
	COMPANY,
	END,
	PLACES,
	START,
	_mobile,
	_name,
)

RNG = random.Random(20260807)

FG_WH = f"FG Store - {ABBR}"
STORES_WH = f"Stores - {ABBR}"
FOUNDRY_WH = f"Foundry WIP - {ABBR}"
WINDING_WH = f"Winding WIP - {ABBR}"
ASSEMBLY_WH = f"Assembly WIP - {ABBR}"
TEST_WH = f"Test Bay - {ABBR}"

ITEM_GROUP_RAW = "Raw Material"

# built by setup/demo_finance.masters(), which runs before this module
SALES_TAX_TEMPLATE = "KUMAR GST 18% - Output"
PURCHASE_TAX_TEMPLATE = "KUMAR GST 18% - Input"

# ---------------------------------------------------------------- masters

SUPPLIERS = [
	# (name, group, city, state, what they sell)
	("Sri Balaji Pig Iron & Scrap", "Raw Material", "Vijayawada", "Andhra Pradesh"),
	("Godavari Ferro Alloys", "Raw Material", "Rajahmundry", "Andhra Pradesh"),
	("Deccan Copper Wires Pvt Ltd", "Raw Material", "Hyderabad", "Telangana"),
	("Sagar Insulation & Varnish", "Raw Material", "Guntur", "Andhra Pradesh"),
	("SKF Authorised - Krishna Bearings", "Bought-out", "Vijayawada", "Andhra Pradesh"),
	("Andhra Seals & Gaskets", "Bought-out", "Tenali", "Andhra Pradesh"),
	("Epcos Capacitors - Sri Sai Agencies", "Bought-out", "Hyderabad", "Telangana"),
	("Polycab Cables - Guntur Depot", "Bought-out", "Guntur", "Andhra Pradesh"),
	("Vijaya Sheet Metal Works", "Bought-out", "Tenali", "Andhra Pradesh"),
	("Nagarjuna Paints & Coatings", "Consumable", "Guntur", "Andhra Pradesh"),
	("Kranthi Packaging Industries", "Consumable", "Tenali", "Andhra Pradesh"),
	("Ganapathi Foundry Consumables", "Consumable", "Vijayawada", "Andhra Pradesh"),
]

# purchased raw materials that do not already exist as KC- components
RAW_ITEMS = [
	# (code, name, uom, rate, supplier hint)
	("KR-PIGIRON", "Pig Iron (Foundry Grade)", "Kg", 46, "Sri Balaji Pig Iron & Scrap"),
	("KR-SCRAP", "CI Scrap", "Kg", 32, "Sri Balaji Pig Iron & Scrap"),
	("KR-FESI", "Ferro Silicon", "Kg", 118, "Godavari Ferro Alloys"),
	("KR-FEMN", "Ferro Manganese", "Kg", 96, "Godavari Ferro Alloys"),
	("KR-COPPERWIRE", "Enamelled Copper Wire", "Kg", 890, "Deccan Copper Wires Pvt Ltd"),
	("KR-VARNISH", "Insulating Varnish", "Litre", 385, "Sagar Insulation & Varnish"),
	("KR-INSULATION", "Slot Insulation Paper", "Kg", 260, "Sagar Insulation & Varnish"),
	("KR-PAINT", "Enamel Paint (KUMAR Blue)", "Litre", 240, "Nagarjuna Paints & Coatings"),
	("KR-CARTON", "Printed Carton", "Nos", 48, "Kranthi Packaging Industries"),
	("KR-SANDBINDER", "Resin Sand Binder", "Kg", 74, "Ganapathi Foundry Consumables"),
]

# which supplier is the default for each purchasable component
COMPONENT_SUPPLIER = {
	"KC-BEARING": "SKF Authorised - Krishna Bearings",
	"KC-SEAL": "Andhra Seals & Gaskets",
	"KC-CAPACITOR": "Epcos Capacitors - Sri Sai Agencies",
	"KC-CABLE": "Polycab Cables - Guntur Depot",
	"KC-TOP": "Vijaya Sheet Metal Works",
}

# the route a pump actually travels, with a believable minute cost
ROUTING = [
	("Moulding", "DISA Moulding Line", 18),
	("Melting & Pouring", "Induction Furnace", 12),
	("Fettling & Shot Blast", "Shot Blasting", 15),
	("Machining", "CNC Lathe", 22),
	("Winding", "Coil Winding Machine", 26),
	("Varnishing & Curing", "Varnish Oven", 20),
	("Assembly", "Assembly Line", 24),
	("Performance Testing", "Test Bench", 10),
	("Painting & Packing", "Paint Booth", 12),
]

CUSTOMER_SUFFIX = [
	"Agro Services", "Borewells", "Pump House", "Traders", "Agencies",
	"Engineering Works", "Farms", "Irrigation", "Hardware", "Electricals",
]


def _log(msg):
	print(f"  {msg}")


def _day(offset):
	return add_days(START, offset)


def _try(label, fn, *args, **kwargs):
	"""Run a builder step; a refusal is reported, never fatal."""
	try:
		return fn(*args, **kwargs)
	except Exception as exc:  # noqa: BLE001 - demo data, keep going
		frappe.clear_last_message()
		frappe.db.rollback()
		_log(f"! {label} skipped: {str(exc)[:120]}")
		return None


def _apply_taxes(doc, template_doctype, title):
	"""Copy a tax template onto an order.

	Setting `taxes_and_charges` alone only records which template was chosen -
	the rows have to be copied in. Everything mapped downstream (receipt,
	delivery, invoice) inherits them from here, so this is the only place GST
	needs to be applied.

	Templates name themselves '<title> - <abbr>', so the lookup is by title.
	"""
	from kumar_service.setup.demo_finance import tax_template_name

	template = tax_template_name(template_doctype, title)
	if not template:
		return
	doc.taxes_and_charges = template
	for row in frappe.get_doc(template_doctype, template).taxes:
		doc.append(
			"taxes",
			{
				"charge_type": row.charge_type,
				"account_head": row.account_head,
				"description": row.description,
				"rate": row.rate,
				"cost_center": row.cost_center,
				"add_deduct_tax": getattr(row, "add_deduct_tax", None),
				"category": getattr(row, "category", None),
			},
		)


# ------------------------------------------------------------------ setup


def ensure_supporting_masters():
	"""Supplier groups, item group, UOMs and the warehouses purchase needs."""
	for group in ("Raw Material", "Bought-out", "Consumable"):
		if not frappe.db.exists("Supplier Group", group):
			frappe.get_doc(
				{
					"doctype": "Supplier Group",
					"supplier_group_name": group,
					"parent_supplier_group": "All Supplier Groups",
					"is_group": 0,
				}
			).insert(ignore_permissions=True)

	if not frappe.db.exists("Item Group", ITEM_GROUP_RAW):
		frappe.get_doc(
			{
				"doctype": "Item Group",
				"item_group_name": ITEM_GROUP_RAW,
				"parent_item_group": "All Item Groups",
				"is_group": 0,
			}
		).insert(ignore_permissions=True)

	for uom in ("Kg", "Litre", "Nos"):
		if not frappe.db.exists("UOM", uom):
			frappe.get_doc({"doctype": "UOM", "uom_name": uom}).insert(ignore_permissions=True)

	root = frappe.db.get_value(
		"Warehouse", {"company": COMPANY, "is_group": 1, "parent_warehouse": ""}
	)
	if not frappe.db.exists("Warehouse", STORES_WH):
		frappe.get_doc(
			{
				"doctype": "Warehouse",
				"warehouse_name": "Stores",
				"company": COMPANY,
				"parent_warehouse": root,
				"is_group": 0,
			}
		).insert(ignore_permissions=True)

	# the shop floor needs the two workstations the routing above names
	for name, rate in (("Assembly Line", 650), ("Test Bench", 550), ("Paint Booth", 450)):
		if not frappe.db.exists("Workstation", name):
			frappe.get_doc(
				{
					"doctype": "Workstation",
					"workstation_name": name,
					"hour_rate_electricity": rate / 100.0,
					"hour_rate": rate / 100.0,
				}
			).insert(ignore_permissions=True)

	frappe.db.commit()


def suppliers():
	made = []
	for name, group, city, state in SUPPLIERS:
		if frappe.db.exists("Supplier", name):
			made.append(name)
			continue
		doc = frappe.get_doc(
			{
				"doctype": "Supplier",
				"supplier_name": name,
				"supplier_group": group,
				"supplier_type": "Company",
				"country": "India",
				"mobile_no": _mobile(),
			}
		)
		doc.flags.ignore_permissions = True
		doc.flags.ignore_mandatory = True
		doc.insert(ignore_permissions=True)
		made.append(doc.name)
	frappe.db.commit()
	return made


def raw_items():
	made = []
	for code, name, uom, rate, supplier in RAW_ITEMS:
		if frappe.db.exists("Item", code):
			made.append(code)
			continue
		doc = frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": code,
				"item_name": name,
				"item_group": ITEM_GROUP_RAW,
				"stock_uom": uom,
				"is_stock_item": 1,
				"is_purchase_item": 1,
				"is_sales_item": 0,
				"custom_trace_group": "NA",
				"valuation_rate": rate,
				"last_purchase_rate": rate,
			}
		)
		if frappe.db.exists("Supplier", supplier):
			doc.append("supplier_items", {"supplier": supplier})
		doc.flags.ignore_permissions = True
		doc.insert(ignore_permissions=True)
		made.append(doc.name)

	# make the bought-out KC- components purchasable and give them a supplier
	for code, supplier in COMPONENT_SUPPLIER.items():
		if not frappe.db.exists("Item", code):
			continue
		item = frappe.get_doc("Item", code)
		changed = False
		if not item.is_purchase_item:
			item.is_purchase_item = 1
			changed = True
		if frappe.db.exists("Supplier", supplier) and not item.supplier_items:
			item.append("supplier_items", {"supplier": supplier})
			changed = True
		if changed:
			item.flags.ignore_permissions = True
			item.save(ignore_permissions=True)

	frappe.db.commit()
	return made


# ------------------------------------------------------------------- BOM


def _bom_lines(hp):
	"""Component list for one pump, scaled by horsepower."""
	copper = round(0.55 + hp * 0.42, 3)
	return [
		("KC-CASING", 1),
		("KC-STATOR", 1),
		("KC-ROTOR", 1),
		("KC-IMPELLER", 1),
		("KC-SHAFT", 1),
		("KC-BEARING", 2),
		("KC-SEAL", 1),
		("KC-TOP", 1),
		("KR-COPPERWIRE", copper),
		("KR-VARNISH", round(0.12 + hp * 0.03, 3)),
		("KR-PAINT", round(0.08 + hp * 0.02, 3)),
		("KR-CARTON", 1),
	]


def boms(limit=24):
	"""One submitted BOM per finished pump item, with the real routing on it."""
	items = frappe.get_all(
		"Item",
		filters={"custom_is_finished_pump": 1},
		fields=["name", "custom_pump_model"],
		order_by="name",
		limit=limit,
	)
	made = []
	for item in items:
		existing = frappe.db.get_value(
			"BOM", {"item": item.name, "docstatus": 1, "is_active": 1}, "name"
		)
		if existing:
			made.append(existing)
			continue

		hp = flt(frappe.db.get_value("Pump Model", item.custom_pump_model, "hp")) or 1.0
		phase = frappe.db.get_value("Pump Model", item.custom_pump_model, "phase")

		def _build():
			bom = frappe.new_doc("BOM")
			bom.item = item.name
			bom.company = COMPANY
			bom.quantity = 1
			bom.is_active = 1
			bom.is_default = 1
			bom.with_operations = 1
			bom.currency = "INR"
			bom.rm_cost_as_per = "Valuation Rate"

			for op, workstation, minutes in ROUTING:
				if not frappe.db.exists("Operation", op):
					continue
				if not frappe.db.exists("Workstation", workstation):
					continue
				bom.append(
					"operations",
					{
						"operation": op,
						"workstation": workstation,
						"time_in_mins": minutes,
						"hour_rate": flt(
							frappe.db.get_value("Workstation", workstation, "hour_rate") or 6
						),
					},
				)

			for code, qty in _bom_lines(hp):
				if not frappe.db.exists("Item", code):
					continue
				bom.append(
					"items",
					{
						"item_code": code,
						"qty": qty,
						"rate": flt(frappe.db.get_value("Item", code, "valuation_rate")),
					},
				)
			# single-phase machines carry a run capacitor, three-phase do not
			if phase == "Single Phase" and frappe.db.exists("Item", "KC-CAPACITOR"):
				bom.append(
					"items",
					{
						"item_code": "KC-CAPACITOR",
						"qty": 1,
						"rate": flt(frappe.db.get_value("Item", "KC-CAPACITOR", "valuation_rate")),
					},
				)

			bom.flags.ignore_permissions = True
			bom.insert(ignore_permissions=True)
			bom.submit()
			return bom.name

		name = _try(f"BOM {item.name}", _build)
		if name:
			made.append(name)
			frappe.db.commit()
	return made


# -------------------------------------------------------------- purchase


def purchase_cycle(orders=85):
	"""Material Request -> PO -> Purchase Receipt -> Purchase Invoice, day by day.

	Roughly a fifth of the orders are deliberately left at an earlier stage so
	the purchase screen has a real pipeline instead of everything closed.
	"""
	buyable = [c for c, _s in COMPONENT_SUPPLIER.items() if frappe.db.exists("Item", c)]
	buyable += [r[0] for r in RAW_ITEMS if frappe.db.exists("Item", r[0])]
	if not buyable:
		return {}

	by_supplier = {}
	for code in buyable:
		sup = COMPONENT_SUPPLIER.get(code)
		if not sup:
			sup = next((r[4] for r in RAW_ITEMS if r[0] == code), None)
		if sup and frappe.db.exists("Supplier", sup):
			by_supplier.setdefault(sup, []).append(code)

	counts = {"mr": 0, "po": 0, "pr": 0, "pi": 0}
	supplier_list = sorted(by_supplier)

	# resume rather than duplicate: whatever is already on the site stands
	done = frappe.db.count("Purchase Order")
	if done >= orders:
		_log(f"{done} purchase orders already present - nothing to add")
		return counts

	for i in range(done, orders):
		supplier = supplier_list[i % len(supplier_list)]
		codes = by_supplier[supplier]
		order_day = _day(min(30, int(i * 30 / max(orders - 1, 1))))
		ref = f"KUMAR/PO/{i + 1:04d}"

		picks = RNG.sample(codes, min(len(codes), RNG.randint(1, 3)))
		lines = []
		for code in picks:
			uom = frappe.db.get_value("Item", code, "stock_uom")
			qty = RNG.choice([25, 50, 100, 200, 400]) if uom in ("Kg", "Litre") else RNG.choice(
				[20, 40, 60, 100, 150]
			)
			rate = flt(frappe.db.get_value("Item", code, "valuation_rate")) or 100
			# a little price movement so the trend chart is not a flat line
			rate = flt(rate * RNG.uniform(0.96, 1.09), 2)
			lines.append((code, qty, rate))

		stage = RNG.random()

		# --- Material Request (the demand signal)
		def _mr():
			mr = frappe.new_doc("Material Request")
			mr.material_request_type = "Purchase"
			mr.company = COMPANY
			mr.transaction_date = add_days(order_day, -2)
			mr.schedule_date = add_days(order_day, 5)
			for code, qty, rate in lines:
				mr.append(
					"items",
					{
						"item_code": code,
						"qty": qty,
						"schedule_date": add_days(order_day, 5),
						"warehouse": STORES_WH,
						"rate": rate,
					},
				)
			mr.flags.ignore_permissions = True
			mr.insert(ignore_permissions=True)
			mr.submit()
			return mr.name

		mr_name = _try(f"MR {ref}", _mr)
		if mr_name:
			counts["mr"] += 1

		if stage < 0.08:
			# demand raised, not yet ordered
			frappe.db.commit()
			continue

		# --- Purchase Order
		def _po():
			po = frappe.new_doc("Purchase Order")
			po.supplier = supplier
			po.company = COMPANY
			po.transaction_date = order_day
			po.schedule_date = add_days(order_day, 6)
			po.currency = "INR"
			po.conversion_rate = 1
			for code, qty, rate in lines:
				po.append(
					"items",
					{
						"item_code": code,
						"qty": qty,
						"rate": rate,
						"warehouse": STORES_WH,
						"schedule_date": add_days(order_day, 6),
					},
				)
			_apply_taxes(po, "Purchase Taxes and Charges Template", PURCHASE_TAX_TEMPLATE)
			po.flags.ignore_permissions = True
			po.insert(ignore_permissions=True)
			po.submit()
			return po.name

		po_name = _try(f"PO {ref}", _po)
		if not po_name:
			continue
		counts["po"] += 1

		if stage < 0.24:
			# ordered, still awaiting delivery
			frappe.db.commit()
			continue

		# --- Purchase Receipt
		recv_day = add_days(order_day, RNG.randint(2, 7))
		if getdate(recv_day) > END:
			recv_day = END

		def _pr():
			from erpnext.buying.doctype.purchase_order.purchase_order import make_purchase_receipt

			pr = make_purchase_receipt(po_name)
			pr.posting_date = recv_day
			pr.set_posting_time = 1
			pr.flags.ignore_permissions = True
			pr.insert(ignore_permissions=True)
			pr.submit()
			return pr.name

		pr_name = _try(f"PR for {ref}", _pr)
		if not pr_name:
			continue
		counts["pr"] += 1

		if stage < 0.42:
			# goods in, bill not yet booked - this is the GRN-pending pile
			frappe.db.commit()
			continue

		# --- Purchase Invoice
		def _pi():
			from erpnext.stock.doctype.purchase_receipt.purchase_receipt import make_purchase_invoice

			pi = make_purchase_invoice(pr_name)
			pi.posting_date = add_days(recv_day, RNG.randint(0, 4))
			if getdate(pi.posting_date) > END:
				pi.posting_date = END
			pi.set_posting_time = 1
			pi.bill_no = f"INV/{supplier[:3].upper()}/{RNG.randint(1000, 9999)}"
			pi.bill_date = pi.posting_date
			pi.due_date = add_days(pi.posting_date, 30)
			pi.flags.ignore_permissions = True
			pi.insert(ignore_permissions=True)
			pi.submit()
			return pi.name

		if _try(f"PI for {ref}", _pi):
			counts["pi"] += 1
		frappe.db.commit()

	return counts


# ------------------------------------------------------------ production


def top_up_components(qty_each=900):
	"""Put enough of every BOM component in Stores that Work Orders can run.

	Purchases cover the bought-out side, but the foundry and winding items are
	made in-house and the demo has no upstream entry for them.
	"""
	codes = ["KC-CASING", "KC-STATOR", "KC-ROTOR", "KC-IMPELLER", "KC-SHAFT",
		"KC-BEARING", "KC-SEAL", "KC-CAPACITOR", "KC-TOP",
		"KR-COPPERWIRE", "KR-VARNISH", "KR-PAINT", "KR-CARTON"]

	def _receipt():
		se = frappe.new_doc("Stock Entry")
		se.stock_entry_type = "Material Receipt"
		se.company = COMPANY
		se.posting_date = _day(0)
		se.set_posting_time = 1
		for code in codes:
			if not frappe.db.exists("Item", code):
				continue
			se.append(
				"items",
				{
					"item_code": code,
					"qty": qty_each,
					"t_warehouse": STORES_WH,
					"basic_rate": flt(frappe.db.get_value("Item", code, "valuation_rate")) or 100,
				},
			)
		se.flags.ignore_permissions = True
		se.insert(ignore_permissions=True)
		se.submit()
		return se.name

	# one top-up is enough; a second would just inflate stock
	if frappe.db.exists(
		"Stock Entry Detail",
		{"t_warehouse": STORES_WH, "item_code": "KC-CASING", "docstatus": 1},
	):
		return None
	return _try("component top-up", _receipt)


def work_orders(count=56, heats=None, windings=None):
	"""A month of production runs, finishing most of them into FG Store.

	The Manufacture entry is what generates the serial numbers, so this is also
	where the sellable stock comes from.
	"""
	bom_rows = frappe.get_all(
		"BOM",
		filters={"docstatus": 1, "is_active": 1},
		fields=["name", "item"],
		order_by="creation",
	)
	if not bom_rows:
		_log("! no BOMs - skipping work orders")
		return {}

	heats = heats or frappe.get_all("Heat Record", pluck="heat_no", limit=30)
	windings = windings or frappe.get_all("Winding Batch Record", pluck="batch_no", limit=30)

	supervisors = frappe.get_all(
		"Employee",
		filters={"designation": ["in", ["Production Supervisor", "Shift Supervisor", "Foreman"]]},
		pluck="name",
	) or frappe.get_all("Employee", filters={"status": "Active"}, pluck="name", limit=10)

	counts = {"wo": 0, "manufactured": 0, "serials": 0}

	done = frappe.db.count("Work Order")
	for i in range(done, count):
		bom = bom_rows[i % len(bom_rows)]
		ref = f"KUMAR/WO/{i + 1:04d}"

		# spread the runs across the month, heavier midweek
		day = _day(min(29, int(i * 29 / max(count - 1, 1))))
		qty = RNG.choice([4, 5, 6, 8, 10, 12])
		shift = RNG.choice("ABC")

		def _wo():
			wo = frappe.new_doc("Work Order")
			wo.production_item = bom.item
			wo.bom_no = bom.name
			wo.company = COMPANY
			wo.qty = qty
			wo.planned_start_date = f"{day} 08:00:00"
			wo.expected_delivery_date = add_days(day, 2)
			wo.source_warehouse = STORES_WH
			wo.wip_warehouse = ASSEMBLY_WH
			wo.fg_warehouse = FG_WH
			wo.skip_transfer = 1
			wo.use_multi_level_bom = 0
			wo.custom_shift = shift
			wo.custom_supervisor = RNG.choice(supervisors) if supervisors else None
			wo.custom_heat_no = RNG.choice(heats) if heats else None
			wo.custom_winding_batch = RNG.choice(windings) if windings else None
			wo.flags.ignore_permissions = True
			wo.insert(ignore_permissions=True)
			wo.submit()
			return wo.name

		if _try(f"WO {ref}", _wo):
			counts["wo"] += 1
			frappe.db.commit()

	# Finishing is a separate pass over whatever is open, not something bolted
	# onto creation. A Manufacture entry can fail for reasons that have nothing
	# to do with the order (a missing account, no component stock); when it
	# does, the order is left open and this pass picks it up on the next run
	# instead of the run being stuck at Not Started forever.
	counts.update(finish_work_orders())
	return counts


def finish_work_orders(leave_open_ratio=0.14):
	"""Run Manufacture entries against open Work Orders.

	A slice is deliberately left unfinished so the shop-floor board has a real
	in-progress column rather than everything sitting Completed.
	"""
	open_orders = frappe.get_all(
		"Work Order",
		filters={"docstatus": 1, "status": ["in", ["Not Started", "In Process"]]},
		fields=["name", "qty", "produced_qty", "planned_start_date", "custom_shift"],
		order_by="planned_start_date",
	)
	counts = {"manufactured": 0, "serials": 0}

	for wo in open_orders:
		remaining = flt(wo.qty) - flt(wo.produced_qty)
		if remaining <= 0:
			continue

		roll = RNG.random()
		if roll < leave_open_ratio:
			continue

		made_qty = remaining if roll > 0.24 else max(1, int(remaining // 2))
		finish_day = add_days(getdate(wo.planned_start_date), RNG.randint(1, 3))
		if getdate(finish_day) > END:
			finish_day = END

		def _manufacture():
			from erpnext.manufacturing.doctype.work_order.work_order import make_stock_entry

			se = frappe.get_doc(make_stock_entry(wo.name, "Manufacture", made_qty))
			se.posting_date = finish_day
			se.set_posting_time = 1
			se.custom_shift = wo.custom_shift or RNG.choice("ABC")
			for row in se.items:
				if row.is_finished_item:
					row.use_serial_batch_fields = 1
			se.flags.ignore_permissions = True
			se.insert(ignore_permissions=True)
			se.submit()
			return se

		if _try(f"Manufacture for {wo.name}", _manufacture):
			counts["manufactured"] += 1
			counts["serials"] += cint(made_qty)
			frappe.db.commit()

	return counts


def rebalance_dealer_network():
	"""Spread the month's trade across every dealer that can actually sell.

	The seeded tree used to flag every branch and distributor as a group, and
	`registrations()` only picks non-group dealers - so the entire month landed
	on the two leaves and the network screen showed fifteen dealers with zero
	against their name. Once the group flags are corrected there are a dozen
	real dealers, and the history has to be redistributed to match, or the
	screen stays just as empty.

	Deterministic and weighted: a branch office moves more pumps than a
	village sub-dealer, which is what the ranking is supposed to show.
	"""
	# Only independent outlets belong here. A registration is a DEALER telling
	# us they sold a pump on their own invoice; our own branches do not report
	# sales that way - theirs come off our invoices, in direct_registrations().
	sellers = frappe.get_all(
		"Dealer",
		filters={"is_group": 0, "status": "Active", "is_own_outlet": 0},
		fields=["name", "dealer_type"],
		order_by="name",
	)
	if len(sellers) < 3:
		_log("! not enough independent leaf dealers to rebalance - check the tree's group flags")
		return {}

	weight = {
		"Branch Office": 5,
		"Authorised Distributor": 4,
		"Dealer": 3,
		"Sub-Dealer": 2,
		"Service Centre": 1,
	}
	pool = []
	for row in sellers:
		pool += [row.name] * weight.get(row.dealer_type, 2)

	regs = frappe.get_all(
		"Pump Registration",
		filters={"docstatus": 1},
		fields=["name", "serial_no"],
		order_by="sale_date, creation",
	)
	if not regs:
		return {}

	rng = random.Random(20260807)
	moved = 0
	for reg in regs:
		dealer = rng.choice(pool)
		if frappe.db.get_value("Pump Registration", reg.name, "dealer") == dealer:
			continue
		frappe.db.set_value("Pump Registration", reg.name, "dealer", dealer,
			update_modified=False)
		if reg.serial_no:
			frappe.db.set_value("Serial No", reg.serial_no, "custom_dealer", dealer,
				update_modified=False)
		moved += 1

	# complaints and claims follow the pump, not the other way round
	frappe.db.sql(
		"""
		update `tabService Request` sr
		join `tabSerial No` sn on sn.name = sr.serial_no
		set sr.dealer = sn.custom_dealer
		where ifnull(sn.custom_dealer, '') != ''
		"""
	)
	frappe.db.sql(
		"""
		update `tabKumar Warranty Claim` c
		join `tabSerial No` sn on sn.name = c.serial_no
		set c.dealer = sn.custom_dealer
		where ifnull(sn.custom_dealer, '') != ''
		"""
	)

	# The trade documents are NOT rebalanced. Who a Sales Invoice belongs to is
	# already decided by who it bills, and reassigning that at random is what
	# made the dealer revenue column fiction - the same end customer used to
	# appear under three different dealers. Repair any document whose dealer
	# disagrees with its customer instead.
	docs = repair_document_dealers()

	frappe.db.commit()
	return {"sellers": len(sellers), "registrations_moved": moved, "documents": docs}


def repair_document_dealers():
	"""Make every trade document's dealer agree with who it actually bills.

	A sale to a dealer's trade account belongs to that dealer, full stop. A
	sale to a member of the public went over one of our own counters, so it
	belongs to a branch - and it stays put if it already names one.
	"""
	by_customer = {
		c.name: c.custom_dealer
		for c in frappe.get_all(
			"Customer", filters={"custom_dealer": ["is", "set"]}, fields=["name", "custom_dealer"]
		)
	}
	branches = frappe.get_all(
		"Dealer", filters={"is_group": 0, "status": "Active", "is_own_outlet": 1}, pluck="name"
	)
	if not branches:
		_log("! no KUMAR-owned branches - direct sales have nobody to belong to")

	rng = random.Random(20260807)
	fixed = 0
	for doctype in ("Sales Order", "Delivery Note", "Sales Invoice"):
		for row in frappe.get_all(
			doctype,
			filters={"docstatus": ["<", 2]},
			fields=["name", "customer", "custom_dealer", "custom_sale_channel"],
		):
			dealer = by_customer.get(row.customer)
			channel = "Trade - Sold to Dealer"
			if not dealer:
				channel = "Direct - Sold to End Customer"
				# keep an existing branch; only invent one if it names nobody
				# sensible, so a rerun does not reshuffle the numbers
				dealer = row.custom_dealer if row.custom_dealer in branches else None
				dealer = dealer or (rng.choice(branches) if branches else None)

			if not dealer:
				continue
			if row.custom_dealer == dealer and row.custom_sale_channel == channel:
				continue
			frappe.db.set_value(
				doctype,
				row.name,
				{"custom_dealer": dealer, "custom_sale_channel": channel},
				update_modified=False,
			)
			fixed += 1
	return fixed


def settle_registration_paperwork():
	"""Give every dealer-channel registration the dealer's own invoice.

	This is the document the end customer actually holds. It is on the
	dealer's letterhead under the dealer's GSTIN, we never raise it and it
	never touches our books - but it is the proof a claim stands on, so the
	registration has to carry its number.
	"""
	from kumar_service.utils import CH_DEALER

	own = set(frappe.get_all("Dealer", filters={"is_own_outlet": 1}, pluck="name"))
	codes = {
		d.name: (d.dealer_code or "DLR")
		for d in frappe.get_all("Dealer", fields=["name", "dealer_code"])
	}

	rng = random.Random(20260807)
	seq = {}
	touched = 0
	for reg in frappe.get_all(
		"Pump Registration",
		filters={"docstatus": 1},
		fields=["name", "dealer", "sale_date", "invoice_no", "sale_channel"],
		order_by="sale_date, creation",
	):
		if reg.dealer in own:
			# handled by direct_registrations(); nothing to invent here
			continue

		seq[reg.dealer] = seq.get(reg.dealer, 0) + 1
		# a shop bills the customer the same day or a day either side
		inv_date = add_days(reg.sale_date, -rng.choice([0, 0, 0, 1]))
		if getdate(inv_date) < getdate(START):
			inv_date = reg.sale_date

		# Each shop's bill book is its own, so the number has to carry the
		# dealer's code. Keep a number that already does; replace the generic
		# ones the first demo seeded, which looked like they all came from the
		# same book.
		code = codes.get(reg.dealer, "DLR")
		number = reg.invoice_no
		if not number or not number.startswith(f"{code}/"):
			number = f"{code}/26-27/{seq[reg.dealer]:04d}"

		values = {
			"sale_channel": CH_DEALER,
			"invoice_no": number,
			"dealer_invoice_date": inv_date,
			"dealer_gstin": frappe.db.get_value("Dealer", reg.dealer, "gstin"),
		}
		frappe.db.set_value("Pump Registration", reg.name, values, update_modified=False)
		touched += 1

	# and nothing left claiming to be a direct sale without our invoice on it
	frappe.db.sql(
		"""
		update `tabPump Registration`
		set sale_channel = %s
		where docstatus = 1 and ifnull(sale_channel, '') = '' and ifnull(sales_invoice, '') = ''
		""",
		(CH_DEALER,),
	)
	frappe.db.commit()
	_log(f"dealer-invoice paperwork on {touched} registrations")
	return touched


def direct_registrations(limit=40):
	"""Register the pumps our own branches sold over the counter.

	These are the other half of the story: one invoice, ours, straight to the
	end customer. The registration is not a dealer telling us something - it
	falls out of our own Sales Invoice, so it carries a real link to it.
	"""
	from kumar_service.traceability import row_serials
	from kumar_service.utils import CH_DIRECT

	invoices = frappe.get_all(
		"Sales Invoice",
		filters={"docstatus": 1, "custom_sale_channel": "Direct - Sold to End Customer"},
		fields=["name", "customer", "customer_name", "posting_date", "custom_dealer"],
		order_by="posting_date",
	)
	if not invoices:
		_log("! no direct sales invoices - nothing to register")
		return 0

	rng = random.Random(20260807)
	made = 0
	for inv in invoices:
		if made >= limit:
			break
		si = frappe.get_doc("Sales Invoice", inv.name)
		for row in si.items:
			for serial in row_serials(row.as_dict()):
				if made >= limit:
					break
				if not frappe.db.exists("Serial No", serial):
					continue
				if frappe.db.exists(
					"Pump Registration", {"serial_no": serial, "docstatus": 1}
				):
					continue
				if not frappe.db.get_value("Serial No", serial, "custom_pump_model"):
					continue

				city, district, state, pincode = PLACES[made % len(PLACES)]

				def _reg():
					doc = frappe.new_doc("Pump Registration")
					doc.serial_no = serial
					doc.dealer = inv.custom_dealer
					doc.sale_channel = CH_DIRECT
					doc.sale_date = inv.posting_date
					doc.sales_invoice = inv.name
					doc.registration_source = "Auto from Invoice"
					doc.end_customer_name = inv.customer_name or inv.customer
					doc.end_customer_mobile = _mobile()
					doc.application_type = rng.choice(
						["Agriculture", "Agriculture", "Domestic", "Industrial", "Commercial"]
					)
					doc.installation_address = f"{district} Mandal"
					doc.district = district
					doc.state = state
					doc.pincode = pincode
					doc.flags.ignore_permissions = True
					doc.insert(ignore_permissions=True)
					doc.submit()
					return doc.name

				if _try(f"direct registration for {serial}", _reg):
					made += 1
					frappe.db.commit()

	_log(f"{made} direct (KUMAR-invoiced) registrations")
	return made


def backfill_serial_identity():
	"""Give every produced serial its pump model and manufacturing date.

	ERPNext creates the serial rows itself when a Manufacture entry is
	submitted; the KUMAR identity fields are stamped by the genealogy hook.
	Anything produced before that hook knew about the model needs filling in,
	and without a model a unit cannot even be test-certified.
	"""
	rows = frappe.db.sql(
		"""
		select sn.name, sn.item_code, i.custom_pump_model
		from `tabSerial No` sn
		join `tabItem` i on i.name = sn.item_code
		where ifnull(sn.custom_pump_model, '') = ''
		  and ifnull(i.custom_pump_model, '') != ''
		""",
		as_dict=True,
	)
	made_on = _manufactured_on()
	for row in rows:
		payload = {"custom_pump_model": row.custom_pump_model}
		if not frappe.db.get_value("Serial No", row.name, "custom_manufacturing_date"):
			payload["custom_manufacturing_date"] = made_on.get(row.name)
		if not frappe.db.get_value("Serial No", row.name, "custom_qc_status"):
			payload["custom_qc_status"] = "Pending"
		frappe.db.set_value("Serial No", row.name, payload, update_modified=False)

	repair_manufacturing_dates(made_on)
	frappe.db.commit()
	return len(rows)


def _manufactured_on():
	"""When each serial was actually built.

	`Serial No.creation` is the wall-clock second the demo builder ran, which
	is today - so using it dated every pump today and made a July sale look
	like a sale before manufacture. The truth is on the Manufacture entry that
	produced the serial; ERPNext copies its date onto `posting_date`, and the
	bundle is the fallback for rows written before that was populated.
	"""
	made = {
		r.name: r.posting_date
		for r in frappe.db.sql(
			"select name, posting_date from `tabSerial No` where posting_date is not null",
			as_dict=True,
		)
	}
	for r in frappe.db.sql(
		"""
		select sbe.serial_no as name, min(se.posting_date) as posting_date
		from `tabSerial and Batch Entry` sbe
		join `tabSerial and Batch Bundle` sbb on sbb.name = sbe.parent
		join `tabStock Entry` se on se.name = sbb.voucher_no
		where sbb.voucher_type = 'Stock Entry' and se.purpose = 'Manufacture'
		  and se.docstatus = 1
		group by sbe.serial_no
		""",
		as_dict=True,
	):
		made.setdefault(r.name, r.posting_date)
	return made


def repair_manufacturing_dates(made_on=None):
	"""Undo the damage the old `creation` fallback did.

	A pump dated today cannot be sold in July, so every backdated
	registration against one of these was refused. Only move a serial whose
	recorded date is later than the day it was actually built.
	"""
	made_on = made_on if made_on is not None else _manufactured_on()
	fixed = 0
	for name, mfg in frappe.db.sql(
		"select name, custom_manufacturing_date from `tabSerial No` "
		"where custom_manufacturing_date is not null",
		as_list=True,
	):
		real = made_on.get(name)
		if not real or getdate(mfg) <= getdate(real):
			continue
		frappe.db.set_value("Serial No", name, "custom_manufacturing_date", real,
			update_modified=False)
		fixed += 1
	if fixed:
		_log(f"corrected the manufacturing date on {fixed} serial(s)")
	return fixed


def certify_new_serials(pass_rate=0.97, limit=800):
	"""Test-certify everything produced above so it is dispatchable."""
	from kumar_service.setup.demo import test_certificates

	backfilled = backfill_serial_identity()
	if backfilled:
		_log(f"backfilled model on {backfilled} serial(s)")

	pending = frappe.get_all(
		"Serial No",
		filters={
			"custom_qc_status": ["!=", "Passed"],
			"warehouse": FG_WH,
			"custom_pump_model": ["is", "set"],
		},
		pluck="name",
		limit=limit,
	)
	if not pending:
		return []

	made = []
	for serial in pending:
		result = _try(f"test certificate {serial}", test_certificates, [serial], pass_rate)
		if result:
			made += result
		frappe.db.commit()
	return made


# ------------------------------------------------------------------ sales


def customers(count=36):
	"""Real end customers, so sales is not ten invoices to two trade accounts."""
	group = frappe.db.get_value("Customer Group", {"is_group": 0}, "name") or "All Customer Groups"
	territory = frappe.db.get_value("Territory", {"is_group": 0}, "name") or "All Territories"

	made = []
	for i in range(count):
		city, district, state, pincode = PLACES[i % len(PLACES)]
		name = f"{_name().split()[0]} {RNG.choice(CUSTOMER_SUFFIX)} - {city}"
		if frappe.db.exists("Customer", name):
			made.append(name)
			continue
		doc = frappe.get_doc(
			{
				"doctype": "Customer",
				"customer_name": name,
				"customer_group": group,
				"territory": territory,
				"customer_type": "Company",
				"mobile_no": _mobile(),
			}
		)
		doc.flags.ignore_permissions = True
		doc.flags.ignore_mandatory = True
		doc.insert(ignore_permissions=True)
		made.append(doc.name)
	frappe.db.commit()
	return made


def sales_cycle(orders=110):
	"""Sales Order -> Delivery Note -> Sales Invoice against real serialised stock.

	A slice is left as an open order and another as delivered-not-billed, so
	the sales screen shows a pipeline rather than a pile of closed invoices.
	"""
	cust_list = frappe.get_all(
		"Customer",
		filters={"customer_name": ["like", "%- %"], "custom_dealer": ["is", "not set"]},
		pluck="name",
	) or frappe.get_all("Customer", pluck="name")

	# Two genuinely different sales, so two pools.
	#
	#   trade  - we invoice an independent dealer. They then sell on to the
	#            public on their own invoice, which never reaches our books.
	#   direct - one of our own branches sells to the public. That invoice IS
	#            ours, and it is the one the customer keeps.
	#
	# Pairing customer and dealer at random (which is what this used to do)
	# made both columns fiction: the same end customer appeared under three
	# different dealers, so revenue per dealer meant nothing.
	trade = frappe.get_all(
		"Dealer",
		filters={"is_group": 0, "status": "Active", "is_own_outlet": 0, "customer": ["is", "set"]},
		fields=["name", "customer"],
	)
	own = frappe.get_all(
		"Dealer",
		filters={"is_group": 0, "status": "Active", "is_own_outlet": 1},
		pluck="name",
	)
	if not (trade or (own and cust_list)):
		_log("! no sellable dealers - run masters.dealer_tree() first")
		return {}

	counts = {"so": 0, "dn": 0, "si": 0, "units": 0}

	# cancelled orders are not sales - counting them made a rebuild after a
	# teardown believe the month was already there and stop after a handful
	done = frappe.db.count("Sales Order", {"docstatus": ["<", 2]})
	if done >= orders:
		_log(f"{done} live sales orders already present - nothing to add")
		return counts

	for i in range(done, orders):
		ref = f"KUMAR/SO/{i + 1:04d}"

		# only sell what is actually in FG Store and has passed test
		available = frappe.db.sql(
			"""
			select sn.name, sn.item_code
			from `tabSerial No` sn
			where sn.warehouse = %s
			  and sn.custom_qc_status = 'Passed'
			  and ifnull(sn.custom_registration, '') = ''
			  and sn.status in ('Active', 'Inactive')
			order by sn.creation
			limit 6
			""",
			(FG_WH,),
			as_dict=True,
		)
		if not available:
			_log(f"  no dispatchable stock left at order {i + 1} - stopping sales")
			break

		qty = min(len(available), RNG.choice([1, 1, 2, 2, 3]))
		picked = available[:qty]
		# one order line per item code, serials grouped under it
		by_item = {}
		for row in picked:
			by_item.setdefault(row.item_code, []).append(row.name)

		# roughly seven in ten pumps leave the factory into the dealer network;
		# the rest go out over our own branch counters
		if trade and (not own or not cust_list or RNG.random() < 0.7):
			row = RNG.choice(trade)
			dealer, customer, channel = row.name, row.customer, "Trade - Sold to Dealer"
		else:
			dealer = RNG.choice(own)
			customer = RNG.choice(cust_list)
			channel = "Direct - Sold to End Customer"

		order_day = _day(min(30, int(i * 30 / max(orders - 1, 1))))

		def _so():
			so = frappe.new_doc("Sales Order")
			so.customer = customer
			so.company = COMPANY
			so.transaction_date = order_day
			so.delivery_date = add_days(order_day, 4)
			so.currency = "INR"
			so.conversion_rate = 1
			so.custom_dealer = dealer
			so.custom_sale_channel = channel
			for item_code, serial_list in by_item.items():
				so.append(
					"items",
					{
						"item_code": item_code,
						"qty": len(serial_list),
						"rate": flt(frappe.db.get_value("Item", item_code, "standard_rate")) or 8000,
						"warehouse": FG_WH,
						"delivery_date": add_days(order_day, 4),
					},
				)
			_apply_taxes(so, "Sales Taxes and Charges Template", SALES_TAX_TEMPLATE)
			so.flags.ignore_permissions = True
			so.insert(ignore_permissions=True)
			so.submit()
			return so.name

		so_name = _try(f"SO {ref}", _so)
		if not so_name:
			continue
		counts["so"] += 1
		frappe.db.commit()

		stage = RNG.random()
		if stage < 0.12:
			continue  # open order, not yet dispatched

		deliver_day = add_days(order_day, RNG.randint(1, 5))
		if getdate(deliver_day) > END:
			deliver_day = END

		def _dn():
			from erpnext.selling.doctype.sales_order.sales_order import make_delivery_note

			dn = frappe.get_doc(make_delivery_note(so_name))
			dn.posting_date = deliver_day
			dn.set_posting_time = 1
			dn.custom_dealer = dealer
			dn.custom_sale_channel = channel
			dn.custom_dispatch_through = RNG.choice(
				["VRL Logistics", "Own Vehicle", "Kranthi Transports", "Sri Sai Road Lines"]
			)
			dn.custom_lr_no = f"LR-{RNG.randint(10000, 99999)}"
			dn.custom_vehicle_no = (
				f"AP{RNG.randint(10, 39)}{RNG.choice('ABCXY')}{RNG.randint(1000, 9999)}"
			)
			for row in dn.items:
				row.use_serial_batch_fields = 1
				row.serial_no = "\n".join(by_item.get(row.item_code, []))
				row.warehouse = FG_WH
			dn.flags.ignore_permissions = True
			dn.insert(ignore_permissions=True)
			dn.submit()
			return dn.name

		dn_name = _try(f"DN for {ref}", _dn)
		if not dn_name:
			continue
		counts["dn"] += 1
		counts["units"] += qty
		frappe.db.commit()

		if stage < 0.26:
			continue  # delivered, not yet invoiced

		def _si():
			from erpnext.stock.doctype.delivery_note.delivery_note import make_sales_invoice

			si = frappe.get_doc(make_sales_invoice(dn_name))
			si.posting_date = add_days(deliver_day, RNG.randint(0, 3))
			if getdate(si.posting_date) > END:
				si.posting_date = END
			si.set_posting_time = 1
			si.due_date = add_days(si.posting_date, 30)
			si.custom_dealer = dealer
			si.custom_sale_channel = channel
			si.flags.ignore_permissions = True
			si.insert(ignore_permissions=True)
			si.submit()
			return si.name

		if _try(f"SI for {ref}", _si):
			counts["si"] += 1
		frappe.db.commit()

	return counts


# -------------------------------------------------------------------- run


def attribute_portal_requests(portal_share=0.55):
	"""Mark a realistic share of dealer complaints and claims as portal-raised.

	The demo builder creates everything as Administrator, so every row in the
	"Dealer Requests and Claims" report read "Desk" - which is not what the company
	would actually see, because a dealer with a portal login raises complaints
	from the portal, not by ringing the branch to type it in for them.

	`owner` is what identifies the channel (the report checks it against the
	Dealer.portal_user list), so that is what gets set. Deterministic seed, so a
	rebuild produces the same split.

	Only touches documents whose dealer HAS a portal login - a dealer without one
	genuinely cannot have raised it themselves.
	"""
	rng = random.Random(20260807)

	logins = {
		row.name: row.portal_user
		for row in frappe.get_all(
			"Dealer", filters={"portal_user": ["!=", ""]}, fields=["name", "portal_user"]
		)
	}
	if not logins:
		return 0

	# A group dealer's own sub-dealers work through the parent's login here: the
	# sub-dealer has no login of its own in this demo.
	def login_for(dealer):
		seen = 0
		while dealer and seen < 8:
			if dealer in logins:
				return logins[dealer]
			dealer = frappe.db.get_value("Dealer", dealer, "parent_dealer")
			seen += 1
		return None

	changed = 0
	for doctype in ("Service Request", "Kumar Warranty Claim"):
		for row in frappe.get_all(
			doctype, filters={"docstatus": ["<", 2]}, fields=["name", "dealer", "owner"]
		):
			if rng.random() > portal_share:
				continue
			user = login_for(row.dealer)
			if not user or row.owner == user:
				continue
			# set_value, not a save: touching `owner` through the document API on a
			# submitted doc is refused, and nothing else about the record changes.
			frappe.db.set_value(doctype, row.name, "owner", user, update_modified=False)
			changed += 1

	frappe.db.commit()
	print(f"  {changed} requests/claims attributed to the dealer portal")
	return changed


#: Conversations that read like a service desk rather than lorem ipsum. Each is
#: (who said it, what they said); "dealer" is posted as the dealer's portal login
#: and "kumar" as the service manager, which is what makes the thread render on
#: the correct side in both the portal and the Dealer Conversations screen.
DEMO_THREADS = (
	(
		("kumar", "Technician assigned. He will reach the village tomorrow before noon. "
			"This pump is in warranty so there is nothing to pay."),
		("dealer", "Customer is in the field till Thursday. Please tell him to come after 4pm."),
		("kumar", "Noted. Visit moved to Thursday evening."),
	),
	(
		("kumar", "Please bring the pump to the Vijayawada service centre - the winding has "
			"to be tested on the bench, it cannot be done at site."),
		("dealer", "Sending it by lorry tomorrow."),
	),
	(
		("dealer", "Customer is asking for an update. It has been four days now."),
	),
	(
		("kumar", "Claim approved. A credit note will come with your next statement."),
	),
	(
		("dealer", "Third pump from the same lot with the same noise. Please check the batch."),
		("kumar", "Quality has pulled the heat record and is checking the other units built "
			"from it. We will come back to you on Monday."),
	),
	(
		("kumar", "Inspected. The cable was cut during installation, so this is not a "
			"manufacturing defect - the visit is chargeable."),
		("dealer", "Understood, customer has agreed to pay."),
	),
	# Weighting matters: three of the threads above end with the DEALER speaking,
	# which puts the ticket in KUMAR's "waiting on us" queue. Left unbalanced the
	# demo showed 34 of 60 tickets waiting, which reads as a company that does not
	# answer its dealers. These two end with KUMAR.
	(
		("dealer", "Pump replaced and installed. Customer is happy."),
		("kumar", "Thank you. Closing this one - the replacement carries the balance "
			"of the original warranty."),
	),
	(
		("dealer", "Can you send two spare seals with the next despatch?"),
		("kumar", "Added to your next despatch, no charge - both are warranty items."),
	),
)


def seed_dealer_conversations(limit=22):
	"""Put real conversations on some dealer tickets.

	Without these, the portal's Messages button and the whole Dealer
	Conversations screen are empty on the demo site - which makes the one feature
	that shows KUMAR answering its dealers look unbuilt.

	Deliberately leaves a mix behind: some threads where the dealer spoke last
	(so KUMAR's queue has real work in it), some answered, and plenty with no
	conversation at all.
	"""
	from kumar_service.portal_api import add_reply

	rng = random.Random(20260808)
	service_manager = (
		frappe.db.get_value("User", {"name": ["like", "service.manager@%"]}, "name")
		or "Administrator"
	)

	def portal_login(dealer):
		hops = 0
		while dealer and hops < 8:
			user = frappe.db.get_value("Dealer", dealer, "portal_user")
			if user:
				return user
			dealer = frappe.db.get_value("Dealer", dealer, "parent_dealer")
			hops += 1
		return None

	candidates = []
	for doctype in ("Service Request", "Kumar Warranty Claim"):
		for row in frappe.get_all(
			doctype, filters={"docstatus": ["<", 2]}, fields=["name", "dealer"], limit=120
		):
			candidates.append((doctype, row.name, row.dealer))
	rng.shuffle(candidates)

	original = frappe.session.user
	made = 0
	try:
		for doctype, name, dealer in candidates:
			if made >= limit:
				break
			if frappe.db.exists(
				"Comment",
				{"reference_doctype": doctype, "reference_name": name, "comment_type": "Comment"},
			):
				continue
			dealer_user = portal_login(dealer)
			if not dealer_user:
				continue

			for side, text in rng.choice(DEMO_THREADS):
				# post as the right person: `owner` is what decides which side of
				# the conversation a message lands on
				frappe.set_user(dealer_user if side == "dealer" else service_manager)
				add_reply(doctype, name, text)
			made += 1
	finally:
		frappe.set_user(original)

	frappe.db.commit()
	print(f"  {made} tickets given a conversation")
	return made


def build_all():
	frappe.flags.mute_emails = True

	print("supporting masters...")
	ensure_supporting_masters()

	print("suppliers...")
	print(f"  {len(suppliers())}")

	print("raw material items...")
	print(f"  {len(raw_items())}")

	print("BOMs...")
	print(f"  {len(boms())}")

	print("purchase cycle...")
	print(f"  {purchase_cycle()}")

	print("component top-up for production...")
	top_up_components()

	print("work orders and manufacture...")
	print(f"  {work_orders()}")

	print("test certificates for new production...")
	print(f"  {len(certify_new_serials())}")

	print("customers...")
	print(f"  {len(customers())}")

	print("sales cycle...")
	print(f"  {sales_cycle()}")

	print("spreading the month across the dealer network...")
	print(f"  {rebalance_dealer_network()}")

	# the two channels, made real. Order matters: the dealer-channel paperwork
	# is stamped on the registrations the rebalance just settled, and the
	# direct ones are then raised off our own invoices.
	print("dealer-invoice paperwork...")
	settle_registration_paperwork()

	print("direct (branch-counter) registrations...")
	direct_registrations()

	print("attributing dealer requests to the portal...")
	attribute_portal_requests()

	print("first responses on the complaints...")
	settle_service_responses()

	print("resolution dates inside the promised window...")
	settle_service_sla()

	print("conversations between KUMAR and the dealers...")
	seed_dealer_conversations()

	frappe.db.commit()
	print("DEMO OPS DONE")


def settle_service_sla(on_time_share=0.85):
	"""Pull resolution dates inside the promised window for most complaints.

	`settle_service_responses` fixes the response leg; this fixes the resolution
	leg. The seeded data closed complaints on a date chosen for the story, with no
	regard for `resolution_due_on`, so 31 of 43 came out "Failed" and the command
	centre reported a service desk that misses almost everything. A real desk
	closes most complaints inside the window it promised and misses a minority.

	Only moves `resolved_on` EARLIER, never later, and never before the first
	response - so no complaint is made to look resolved before it was answered.
	"""
	rng = random.Random(20260809)
	rows = frappe.get_all(
		"Service Request",
		filters={"docstatus": ["<", 2], "resolved_on": ["is", "set"]},
		fields=["name", "reported_on", "first_response_on", "resolved_on", "resolution_due_on"],
	)

	touched = 0
	for r in rows:
		if not (r.resolved_on and r.resolution_due_on and r.reported_on):
			continue
		resolved = get_datetime(r.resolved_on)
		due = get_datetime(r.resolution_due_on)
		earliest = get_datetime(r.first_response_on or r.reported_on)

		if resolved <= due:
			sla = "Fulfilled"
			stamp = resolved
		elif rng.random() <= on_time_share:
			# bring it inside the window, somewhere after the first response
			span = max((due - earliest).total_seconds(), 60)
			stamp = earliest + timedelta(seconds=rng.uniform(span * 0.35, span * 0.95))
			sla = "Fulfilled"
		else:
			# a genuine miss - the command centre should have some of these
			stamp = resolved
			sla = "Failed"

		if stamp == resolved and sla == "Failed":
			# nothing to change, but make sure the status agrees with the dates
			frappe.db.set_value("Service Request", r.name, "sla_status", "Failed",
				update_modified=False)
			continue

		frappe.db.set_value(
			"Service Request",
			r.name,
			{"resolved_on": stamp, "sla_status": sla},
			update_modified=False,
		)
		touched += 1

	frappe.db.commit()
	print(f"  {touched} complaints brought inside the resolution window")
	return touched


def settle_service_responses(answered_share=0.88, on_time_share=0.9):
	"""Give the demo's complaints a believable response history.

	Every seeded Service Request had `first_response_on` empty, so the command
	centre reported an 11.9% SLA and 43 unanswered complaints - which is not a
	demo of a working service desk, it is a demo of a broken one. A real desk
	answers most complaints inside the promised window, misses a few, and has a
	handful genuinely still waiting.

	Writes with db.set_value and re-derives `sla_status` with the controller's own
	rule, because `first_response_on` has no allow_on_submit and validate() will
	not run on a submitted request.
	"""
	rng = random.Random(20260809)
	rows = frappe.get_all(
		"Service Request",
		filters={"docstatus": ["<", 2]},
		fields=["name", "reported_on", "response_due_on", "resolution_due_on",
		        "resolved_on", "first_response_on"],
	)

	touched = 0
	for r in rows:
		if r.first_response_on or not r.reported_on:
			continue
		# a few are genuinely still unanswered - that is what the "no reply yet"
		# tile on the command centre is for
		if rng.random() > answered_share:
			continue

		reported = get_datetime(r.reported_on)
		due = get_datetime(r.response_due_on) if r.response_due_on else None

		if due and rng.random() <= on_time_share:
			# answered inside the window, somewhere between the call and the deadline
			span = max((due - reported).total_seconds(), 60)
			stamp = reported + timedelta(seconds=rng.uniform(span * 0.1, span * 0.85))
		else:
			base = due or reported
			stamp = base + timedelta(hours=rng.uniform(2, 30))

		# never after it was resolved, and never in the future
		if r.resolved_on:
			stamp = min(stamp, get_datetime(r.resolved_on))
		stamp = min(stamp, now_datetime())
		if stamp < reported:
			stamp = reported + timedelta(minutes=20)

		# the controller's rule: resolution outcome wins, else response timing
		if r.resolved_on and r.resolution_due_on:
			met = get_datetime(r.resolved_on) <= get_datetime(r.resolution_due_on)
			sla = "Fulfilled" if met else "Failed"
		elif due:
			sla = "Responded" if stamp <= due else "Failed"
		else:
			sla = "Responded"

		frappe.db.set_value(
			"Service Request",
			r.name,
			{"first_response_on": stamp, "sla_status": sla},
			update_modified=False,
		)
		touched += 1

	frappe.db.commit()
	print(f"  {touched} complaints given a first response")
	return touched
