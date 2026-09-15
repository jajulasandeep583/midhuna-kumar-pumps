"""Build pumps today, through the whole plant, and narrate every document.

This exists because "how does a pump actually get made here" is hard to answer
with a diagram and easy to answer by doing it. Run it and it prints the chain it
just created, document by document, so the same story can be walked on screen
afterwards.

It is also the honest test of the genealogy hook: the serials are produced by a
real Manufacture entry, and the heat and winding numbers on them are whatever
the system stamped - this module never writes them itself.

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

QTY = 5  # a small run: enough to be real, small enough to read


def _p(step, what, name, detail=""):
	print(f"  {step}  {what:26} {name:24} {detail}")


def run(qty=None):
	qty = int(qty or QTY)
	today = nowdate()
	# seconds, not minutes: heat_no is unique, and two runs in one minute clashed
	stamp = frappe.utils.now_datetime().strftime("%y%m%d%H%M%S")
	made = {}

	print(f"\nONE PRODUCTION CYCLE - {today}\n" + "=" * 74)

	# ---------------------------------------------------------------- 1 melt
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
	_p("1.", "FOUNDRY pours a melt", heat.name, f"heat_no {heat_no}, all elements in spec")

	# ------------------------------------------------------------- 2 winding
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
	_p("2.", "WINDING SHOP winds a lot", wind.name, f"batch_no {wd_no}, IR 310.5, HiPot 2.2kV")

	# both shops' output reaches stores as a BATCH named after the record
	_receive("KC-CASING", heat_no, qty, FOUNDRY_WH, today)
	_receive("KC-STATOR", wd_no, qty, WINDING_WH, today)
	from kumar_service.traceability import link_batch_records

	link_batch_records()
	_p("3.", "STORES receive the batches", f"{heat_no} / {wd_no}", "castings and stators in stock")

	# ---------------------------------------------------------- 4 work order
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
	_p("4.", "PRODUCTION raises a run", wo.name, f"{qty} x {item} on {bom}")
	if ops:
		print(f"       operations from the BOM: {' -> '.join(ops)}")
		jobs = frappe.get_all("Job Card", filters={"work_order": wo.name}, pluck="name")
		_p("5.", "JOB CARDS for the shop floor", f"{len(jobs)} cards", "one per operation")

	# ----------------------------------------------------------- 6 manufacture
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
	_p("6.", "STORES build the pumps", se.name, "consumes the two batches, produces serials")

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

	# --------------------------------------------------------- 7 test bench
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
	_p("7.", "TEST BENCH certifies each", f"{len(certs)} certificates", "QC status written onto the serial")

	passed = frappe.db.count("Serial No", {"name": ["in", serials], "custom_qc_status": "Passed"})
	print(f"\n       serials now QC Passed: {passed} of {len(serials)} - these may be dispatched")
	print("       (a serial that had failed would be refused by Delivery Note)")

	frappe.db.commit()
	print("\n" + "=" * 74)
	print("created:", {k: (len(v) if isinstance(v, list) else v) for k, v in made.items()})
	return made


def _receive(item, batch, qty, warehouse, posting_date):
	"""Put a batched component into stock, creating the Batch if needed."""
	if not frappe.db.exists("Batch", batch):
		b = frappe.get_doc({"doctype": "Batch", "batch_id": batch, "item": item})
		b.flags.ignore_permissions = True
		b.insert(ignore_permissions=True)
	se = frappe.new_doc("Stock Entry")
	se.stock_entry_type = "Material Receipt"
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
