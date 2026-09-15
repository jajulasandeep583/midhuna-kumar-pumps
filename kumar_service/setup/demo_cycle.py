"""Build pumps today, through the whole plant, and narrate every document.

This exists because "how does a pump actually get made here" is hard to answer
with a diagram and easy to answer by doing it. Run it and it prints the chain it
just created, document by document, so the same story can be walked on screen
afterwards.

It is also the honest test of the genealogy hook: the serials are produced by a
real Manufacture entry, and the heat and winding numbers on them are whatever
the system stamped - this module never writes them itself.

The charge is bought and burnt for the same reason. A casting that appears in
stock by Material Receipt has no past, and the pig iron it was supposedly made
from sits in Stores for ever - so the stock ledger contradicts the traceability
story on the very first question anyone asks of it. Here the metal is purchased,
issued, and destroyed, and what survives is a Batch named after the heat.

    bench --site kumarpumps.localhost execute kumar_service.setup.demo_cycle.run

Everything it creates is dated TODAY, so it also gives the Management screen
production and purchasing figures in the current month, which the seeded month
(ending 7 August) does not.
"""

import frappe
from frappe.utils import add_days, flt, nowdate

COMPANY = "Sri Lakshmi Ganapathi Engineering Works"
ABBR = "SLGEW"
FG_WH = f"FG Store - {ABBR}"
FOUNDRY_WH = f"Foundry WIP - {ABBR}"
WINDING_WH = f"Winding WIP - {ABBR}"
STORES_WH = f"Stores - {ABBR}"

QTY = 5  # a small run: enough to be real, small enough to read

# What goes into one 1200 kg heat. This is a plain grey-iron charge: pig iron
# for clean carbon, CI scrap (foundry returns plus bought scrap) for economy,
# and the two ferro-alloys that pull silicon and manganese up into the FG 200
# window - which is then what the spectro reading on the Heat Record has to
# confirm. The weights sum to CHARGE_WEIGHT on purpose; if they stop matching,
# the Heat Record is claiming a charge the stock ledger cannot account for.
CHARGE_KG = (
	("KR-PIGIRON", 660.0),
	("KR-SCRAP", 500.0),
	("KR-FESI", 24.0),
	("KR-FEMN", 16.0),
)
MOULDING_KG = (("KR-SANDBINDER", 45.0),)  # the moulds the iron is poured into
CHARGE_WEIGHT = 1200
# ~10 kg of metal per casing. Deliberately not the size of one work order: a
# heat pours far more castings than any single run uses, which is precisely why
# a bad heat is worth tracing - it is sitting in a hundred other pumps.
CASTINGS_PER_HEAT = 120

CHARGE_SUPPLIER = {
	"KR-PIGIRON": "Sri Balaji Pig Iron & Scrap",
	"KR-SCRAP": "Sri Balaji Pig Iron & Scrap",
	"KR-FESI": "Godavari Ferro Alloys",
	"KR-FEMN": "Godavari Ferro Alloys",
	"KR-SANDBINDER": "Ganapathi Foundry Consumables",
}
BUY_LOT = {  # a believable delivery, not a hand-to-mouth top-up
	"KR-PIGIRON": 5000, "KR-SCRAP": 3000,
	"KR-FESI": 200, "KR-FEMN": 150, "KR-SANDBINDER": 300,
}


def _p(step, what, name, detail=""):
	print(f"  {step}  {what:26} {name:24} {detail}")


def run(qty=None):
	qty = int(qty or QTY)
	today = nowdate()
	# seconds, not minutes: heat_no is unique, and two runs in one minute clashed
	stamp = frappe.utils.now_datetime().strftime("%y%m%d%H%M%S")
	made = {}

	print(f"\nONE PRODUCTION CYCLE - {today}\n" + "=" * 74)

	# ------------------------------------------------------------ 1 buy charge
	bought = _buy_charge(today)
	if bought:
		_p("1.", "STORES buy the charge", ", ".join(bought), "pig iron, scrap, ferro-alloys")
		made["purchases"] = bought
	else:
		_p("1.", "STORES already hold charge", "-", "enough pig iron and scrap for this heat")

	# ---------------------------------------------------------------- 2 melt
	heat_no = f"HT-{stamp}"
	heat = frappe.get_doc({
		"doctype": "Heat Record",
		"heat_no": heat_no,
		"heat_date": today,
		"furnace": "Induction Furnace",
		"shift": "A",
		"charge_weight_kg": 1200,
		"tapping_temperature_c": 1495,
		"target_grade": "FG 200",
		"grade_achieved": "FG 200",
		"status": "Approved for Pouring",
		"spectro_readings": [
			{"element": "C", "value_pct": 3.35, "spec_min": 3.10, "spec_max": 3.60},
			{"element": "Si", "value_pct": 2.10, "spec_min": 1.80, "spec_max": 2.40},
			{"element": "Mn", "value_pct": 0.70, "spec_min": 0.50, "spec_max": 0.90},
			{"element": "S", "value_pct": 0.06, "spec_min": 0.02, "spec_max": 0.12},
			{"element": "P", "value_pct": 0.08, "spec_min": 0.02, "spec_max": 0.15},
			{"element": "Cu", "value_pct": 0.30, "spec_min": 0.10, "spec_max": 0.50},
		],
	})
	heat.flags.ignore_permissions = True
	heat.insert(ignore_permissions=True)
	made["heat"] = heat.name
	_p("2.", "FOUNDRY melts the charge", heat.name, f"heat_no {heat_no}, all elements in spec")

	# the charge is burnt and the castings are poured: this is where the heat
	# number stops being a lab reference and becomes a stock batch
	made["melt"] = _melt(heat_no, today)
	_p("3.", "FOUNDRY pours the castings", made["melt"],
		f"{CHARGE_WEIGHT}kg charge consumed -> {CASTINGS_PER_HEAT} x KC-CASING, batch {heat_no}")

	# ------------------------------------------------------------- 4 winding
	wd_no = f"WD-{stamp}"
	wind = frappe.get_doc({
		"doctype": "Winding Batch Record",
		"batch_no": wd_no,
		"winding_date": today,
		"machine": "Coil Winding Machine",
		"wire_gauge_swg": "21",
		"turns_per_coil": 95,
		"oven_temp_c": 150,
		"cure_duration_min": 120,
		"ir_test_mohm": 310.5,
		"hipot_test_kv": 2.2,
		"winding_resistance_ohm": 6.4,
		"qty_produced": qty + 2,
		"qty_passed": qty + 2,
		"qty_rejected": 0,
	})
	wind.flags.ignore_permissions = True
	wind.insert(ignore_permissions=True)
	made["winding"] = wind.name
	_p("4.", "WINDING SHOP winds a lot", wind.name, f"batch_no {wd_no}, IR 310.5, HiPot 2.2kV")

	# the stator's copper and varnish are costed on the pump BOM, so the winding
	# shop's output only has to reach stock - as a BATCH named after the record
	_receive("KC-STATOR", wd_no, qty, WINDING_WH, today,
		entry_type="Winding Output", stamp={"custom_winding_batch": wd_no})
	from kumar_service.traceability import link_batch_records

	link_batch_records()
	_p("5.", "STORES hold both batches", f"{heat_no} / {wd_no}",
		"each batch points back at its own quality record")

	# ---------------------------------------------------------- 6 work order
	# pick the BOM first and take its item: choosing a finished pump and then
	# hunting for its BOM lands on a model that has none, and Work Order refuses
	# to save without one
	bom, item = frappe.db.get_value(
		"BOM", {"is_active": 1, "is_default": 1, "docstatus": 1}, ["name", "item"]
	) or (None, None)
	if not bom:
		frappe.throw("No active default BOM on this site - cannot raise a Work Order.")
	wo = frappe.get_doc({
		"doctype": "Work Order",
		"production_item": item,
		"bom_no": bom,
		"qty": qty,
		"company": COMPANY,
		"fg_warehouse": FG_WH,
		"wip_warehouse": FOUNDRY_WH,
		"planned_start_date": frappe.utils.now_datetime(),
	})
	wo.flags.ignore_permissions = True
	wo.insert(ignore_permissions=True)
	wo.submit()
	made["work_order"] = wo.name
	ops = [o.operation for o in (wo.operations or [])]
	_p("6.", "PRODUCTION raises a run", wo.name, f"{qty} x {item} on {bom}")
	if ops:
		print(f"       operations from the BOM: {' -> '.join(ops)}")
		jobs = frappe.get_all("Job Card", filters={"work_order": wo.name}, pluck="name")
		_p("7.", "JOB CARDS for the shop floor", f"{len(jobs)} cards", "one per operation")

	# ----------------------------------------------------------- 8 manufacture
	se = frappe.new_doc("Stock Entry")
	se.stock_entry_type = "Manufacture"
	se.company = COMPANY
	se.work_order = wo.name
	se.from_bom = 1
	se.bom_no = bom
	se.fg_completed_qty = qty
	se.posting_date = today
	se.set_posting_time = 1
	se.append("items", {"item_code": "KC-CASING", "qty": qty, "s_warehouse": FOUNDRY_WH,
		"use_serial_batch_fields": 1, "batch_no": heat_no})
	se.append("items", {"item_code": "KC-STATOR", "qty": qty, "s_warehouse": WINDING_WH,
		"use_serial_batch_fields": 1, "batch_no": wd_no})
	se.append("items", {"item_code": item, "qty": qty, "t_warehouse": FG_WH,
		"is_finished_item": 1, "use_serial_batch_fields": 1,
		"basic_rate": flt(frappe.db.get_value("Item", item, "valuation_rate")) or 5000})
	se.flags.ignore_permissions = True
	se.insert(ignore_permissions=True)
	se.submit()
	made["manufacture"] = se.name
	_p("8.", "STORES build the pumps", se.name, "consumes the two batches, produces serials")

	# what the HOOK stamped - read back, never written here
	serials = []
	for row in se.items:
		if row.t_warehouse and not row.s_warehouse:
			from kumar_service.traceability import row_serials

			serials += row_serials(row)
	made["serials"] = serials
	print()
	for sn in serials:
		v = frappe.db.get_value("Serial No", sn,
			["custom_heat_no", "custom_winding_batch", "custom_work_order", "custom_qc_status"],
			as_dict=True) or {}
		print(f"       {sn:34} heat={v.get('custom_heat_no') or '-':16} "
			f"winding={v.get('custom_winding_batch') or '-':16} "
			f"wo={v.get('custom_work_order') or '-':20} qc={v.get('custom_qc_status')}")

	# --------------------------------------------------------- 9 test bench
	certs = []
	for sn in serials:
		model = frappe.db.get_value("Serial No", sn, "custom_pump_model")
		c = frappe.get_doc({
			"doctype": "Pump Test Certificate",
			"serial_no": sn,
			"pump_model": model,
			"test_date": frappe.utils.now_datetime(),
			"test_bench": "Test Bench",
			"bis_standard_ref": "IS 9079",
			"supply_voltage_v": 415,
			"frequency_hz": 50,
			"no_load_current_a": 3.6,
			"full_load_current_a": 9.8,
			"insulation_resistance_mohm": 290.0,
			"hipot_voltage_kv": 2.0,
			"hipot_result": "Pass",
			"hydrostatic_test_pressure": 13.0,
			"hydrostatic_result": "Pass",
			"vibration_mm_s": 2.1,
			"noise_db": 72.0,
			"overall_result": "Pass",
		})
		c.flags.ignore_permissions = True
		c.insert(ignore_permissions=True)
		c.submit()
		certs.append(c.name)
	made["certificates"] = certs
	_p("9.", "TEST BENCH certifies each", f"{len(certs)} certificates", "QC status written onto the serial")

	passed = frappe.db.count("Serial No", {"name": ["in", serials], "custom_qc_status": "Passed"})
	print(f"\n       serials now QC Passed: {passed} of {len(serials)} - these may be dispatched")
	print("       (a serial that had failed would be refused by Delivery Note)")

	frappe.db.commit()
	print("\n" + "=" * 74)
	print("created:", {k: (len(v) if isinstance(v, list) else v) for k, v in made.items()})
	return made


def retag_shop_steps():
	"""Name the shop step on entries that were posted before the types existed.

	The Production rail finds the foundry's and the winding shop's work by
	stock_entry_type, so an entry posted as a plain "Manufacture" is invisible to
	it - the link opens an empty list, which is worse than no link. Retagged in
	place rather than re-posted: both new types carry the same `purpose` as the
	one being replaced, so nothing about the ledger, the valuation or the GL
	changes - only the label the list groups by.

		bench --site kumarpumps.localhost execute \\
			kumar_service.setup.demo_cycle.retag_shop_steps
	"""
	melts = frappe.db.sql_list("""
		select distinct sed.parent from `tabStock Entry Detail` sed
		inner join `tabStock Entry` se on se.name = sed.parent
		where sed.item_code = 'KR-PIGIRON' and sed.s_warehouse is not null
		  and se.docstatus = 1 and se.purpose = 'Manufacture'
		  and se.stock_entry_type != 'Foundry Melt'
	""")
	stators = frappe.db.sql_list("""
		select distinct sed.parent from `tabStock Entry Detail` sed
		inner join `tabStock Entry` se on se.name = sed.parent
		where sed.item_code = 'KC-STATOR' and sed.t_warehouse = %s
		  and se.docstatus = 1 and se.purpose = 'Material Receipt'
		  and se.stock_entry_type != 'Winding Output'
	""", WINDING_WH)

	for name in melts:
		frappe.db.set_value("Stock Entry", name, "stock_entry_type", "Foundry Melt",
			update_modified=False)
	for name in stators:
		frappe.db.set_value("Stock Entry", name, "stock_entry_type", "Winding Output",
			update_modified=False)

	# and carry the batch onto the entry's own traceability field. These two
	# entries PRODUCE their batch rather than consuming one, so the genealogy
	# hook - which reads what was consumed - never fills them in. Scanned by
	# type rather than by what was just retagged, so a second run still repairs
	# anything the first one left blank.
	_stamp_produced_batch("Foundry Melt", "KC-CASING", "custom_heat_no")
	_stamp_produced_batch("Winding Output", "KC-STATOR", "custom_winding_batch")

	frappe.db.commit()
	print(f"  + retagged {len(melts)} melt(s) and {len(stators)} winding output(s)")
	return {"melts": melts, "stators": stators}


def _stamp_produced_batch(entry_type, item, fieldname):
	from kumar_service.traceability import row_batches

	if not frappe.get_meta("Stock Entry").has_field(fieldname):
		return
	entries = frappe.get_all("Stock Entry", pluck="name", filters={
		"stock_entry_type": entry_type, "docstatus": 1, fieldname: ["is", "not set"],
	})
	for name in entries:
		doc = frappe.get_doc("Stock Entry", name)
		for row in doc.items:
			if row.item_code != item or not row.t_warehouse:
				continue
			batches = row_batches(row)
			if batches:
				frappe.db.set_value("Stock Entry", name, fieldname, batches[0],
					update_modified=False)
			break


def _stock(item, warehouse=None):
	return flt(frappe.db.get_value(
		"Bin", {"item_code": item, "warehouse": warehouse or STORES_WH}, "actual_qty"))


def _buy_charge(posting_date):
	"""Buy whatever the melt is short of, as a real Purchase Receipt.

	The melt below issues pig iron and scrap OUT of Stores, so the store has to
	hold them first - and that is the point of this step rather than a
	convenience. "Where did the pig iron go" is a question the stock ledger has
	to answer, and it can only answer it if the metal was bought in one document
	and burnt in another.
	"""
	short = {
		item: BUY_LOT.get(item, kg * 10)
		for item, kg in CHARGE_KG + MOULDING_KG
		if _stock(item) < kg
	}
	if not short:
		return []

	by_supplier = {}
	for item, qty in short.items():
		by_supplier.setdefault(CHARGE_SUPPLIER[item], []).append((item, qty))

	receipts = []
	for supplier, rows in sorted(by_supplier.items()):
		pr = frappe.new_doc("Purchase Receipt")
		# match the seeded receipts: a lone PR-26-00001 among MAT-PRE-2026-000xx
		# reads as something a script did rather than something the plant did
		pr.naming_series = "MAT-PRE-.YYYY.-"
		pr.supplier = supplier
		pr.company = COMPANY
		pr.posting_date = posting_date
		pr.set_posting_time = 1
		for item, qty in rows:
			pr.append("items", {
				"item_code": item,
				"qty": qty,
				"warehouse": STORES_WH,
				"rate": flt(frappe.db.get_value("Item", item, "valuation_rate")) or 50,
			})
		pr.flags.ignore_permissions = True
		pr.insert(ignore_permissions=True)
		pr.submit()
		receipts.append(pr.name)
	return receipts


def _melt(heat_no, posting_date):
	"""Burn the charge, pour the castings, name the batch after the heat.

	This single document is the whole traceability trick, and it is the step the
	demo was missing: without it a casting appeared in stock by Material Receipt,
	out of nothing, while the pig iron sat in Stores for ever - so the stock
	ledger flatly contradicted the story being told over it.

	What it does is a one-way conversion. The pig iron, scrap and ferro-alloys go
	OUT of Stores and do not come back; anyone reading the ledger can see which
	heat consumed them. What comes back IN is a *different item* - a casting -
	carrying a Batch whose id IS the heat number. That is the only "transfer"
	there is: the metal is destroyed, and its identity survives as a batch id,
	which is how the heat eventually reaches the pump's serial number.
	"""
	if not frappe.db.exists("Batch", heat_no):
		b = frappe.get_doc({"doctype": "Batch", "batch_id": heat_no, "item": "KC-CASING"})
		b.flags.ignore_permissions = True
		b.insert(ignore_permissions=True)

	se = frappe.new_doc("Stock Entry")
	# a named type, so the Stock Entry list says "Foundry Melt" instead of a
	# fiftieth identical "Manufacture" - and so the rail can filter to it
	se.stock_entry_type = "Foundry Melt" if frappe.db.exists(
		"Stock Entry Type", "Foundry Melt") else "Manufacture"
	se.custom_heat_no = heat_no
	se.company = COMPANY
	se.posting_date = posting_date
	se.set_posting_time = 1
	se.fg_completed_qty = CASTINGS_PER_HEAT
	for item, kg in CHARGE_KG + MOULDING_KG:
		se.append("items", {"item_code": item, "qty": kg, "s_warehouse": STORES_WH})
	# no basic_rate on the casting: the charge's value is what it costs, and
	# letting ERPNext divide it is the only way the two sides stay honest
	se.append("items", {
		"item_code": "KC-CASING",
		"qty": CASTINGS_PER_HEAT,
		"t_warehouse": FOUNDRY_WH,
		"is_finished_item": 1,
		"use_serial_batch_fields": 1,
		"batch_no": heat_no,
	})
	se.flags.ignore_permissions = True
	se.insert(ignore_permissions=True)
	se.submit()
	return se.name


def _receive(item, batch, qty, warehouse, posting_date, entry_type=None, stamp=None):
	"""Put a batched component into stock, creating the Batch if needed.

	`entry_type` names the shop step on the document (see STOCK_ENTRY_TYPES) and
	`stamp` writes the batch onto the entry's own traceability field, so the
	entry can be found by what it made rather than only by reading its rows.
	"""
	if not frappe.db.exists("Batch", batch):
		b = frappe.get_doc({"doctype": "Batch", "batch_id": batch, "item": item})
		b.flags.ignore_permissions = True
		b.insert(ignore_permissions=True)
	se = frappe.new_doc("Stock Entry")
	se.stock_entry_type = (
		entry_type if entry_type and frappe.db.exists("Stock Entry Type", entry_type)
		else "Material Receipt"
	)
	if stamp:
		se.update(stamp)
	se.company = COMPANY
	se.posting_date = posting_date
	se.set_posting_time = 1
	se.append("items", {
		"item_code": item, "qty": qty, "t_warehouse": warehouse,
		"basic_rate": flt(frappe.db.get_value("Item", item, "valuation_rate")) or 100,
		"use_serial_batch_fields": 1, "batch_no": batch,
	})
	se.flags.ignore_permissions = True
	se.insert(ignore_permissions=True)
	se.submit()
	return se.name
