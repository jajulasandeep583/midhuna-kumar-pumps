"""Serial Genealogy.

Converted from a database Script Report to a standard, file-based one.
Script Reports keep their python in the Report record and run it through
safe_exec, which frappe v16 only permits when server_script_enabled is set
in common_site_config - a bench-wide switch that lets any System Manager on
any site on the bench execute arbitrary python. This report needed none of
that: as a file it is ordinary app code, it travels in git, and it can be
reviewed and tested like everything else.
"""

import frappe
from frappe import _
from frappe.utils import add_days, cint, flt, getdate, now_datetime, nowdate


def execute(filters=None):
	filters = frappe._dict(filters or {})

	columns = [
		{"label": "Attribute", "fieldname": "attribute", "fieldtype": "Data", "width": 220},
		{"label": "Value", "fieldname": "value", "fieldtype": "Data", "width": 320},
	]

	rows = []
	serial = filters.get("serial_no")
	if serial:
		t = frappe.db.get_value("Serial No", serial, [
			"name", "item_code", "custom_pump_model", "custom_manufacturing_date",
			"custom_work_order", "custom_heat_no", "custom_winding_batch",
			"custom_rotor_batch", "custom_test_certificate", "custom_qc_status"], as_dict=True) or {}

		heat = {}
		if t.get("custom_heat_no"):
			heat_record = frappe.db.get_value("Batch", t.get("custom_heat_no"), "custom_heat_record")
			if heat_record:
				heat = frappe.db.get_value("Heat Record", heat_record, [
					"heat_date", "furnace", "target_grade", "grade_achieved",
					"carbon_equivalent", "all_within_spec"], as_dict=True) or {}

		wind = {}
		if t.get("custom_winding_batch"):
			wind = frappe.db.get_value("Winding Batch Record", {"batch_no": t.get("custom_winding_batch")}, [
				"winding_date", "machine", "wire_gauge_swg", "turns_per_coil",
				"ir_test_mohm", "hipot_test_kv"], as_dict=True) or {}

		cert = {}
		if t.get("custom_test_certificate"):
			cert = frappe.db.get_value("Pump Test Certificate", t.get("custom_test_certificate"), [
				"name", "test_date", "overall_result", "vibration_mm_s", "noise_db"], as_dict=True) or {}

		t["heat_batch"] = t.get("custom_heat_no")
		t["winding_batch"] = t.get("custom_winding_batch")
		t["rotor_batch"] = t.get("custom_rotor_batch")
		t["pump_model"] = t.get("custom_pump_model")
		t["manufacturing_date"] = t.get("custom_manufacturing_date")
		t["work_order"] = t.get("custom_work_order")
		t["qc_status"] = t.get("custom_qc_status")
		t["serial_no"] = t.get("name")

		pairs = [
			("Serial No", t.get("serial_no")),
			("Item", t.get("item_code")),
			("Pump Model", t.get("pump_model")),
			("Manufactured On", t.get("manufacturing_date")),
			("Work Order", t.get("work_order")),
			("QC Status", t.get("qc_status")),
			("--- Casing ---", ""),
			("Heat Batch", t.get("heat_batch")),
			("Heat Date", heat.get("heat_date")),
			("Furnace", heat.get("furnace")),
			("Target Grade", heat.get("target_grade")),
			("Grade Achieved", heat.get("grade_achieved")),
			("Carbon Equivalent", heat.get("carbon_equivalent")),
			("All Elements In Spec", "Yes" if heat.get("all_within_spec") else "No"),
			("--- Stator ---", ""),
			("Winding Batch", t.get("winding_batch")),
			("Winding Date", wind.get("winding_date")),
			("Machine", wind.get("machine")),
			("Wire Gauge (SWG)", wind.get("wire_gauge_swg")),
			("Turns per Coil", wind.get("turns_per_coil")),
			("IR Test (Mohm)", wind.get("ir_test_mohm")),
			("HiPot (kV)", wind.get("hipot_test_kv")),
			("--- Test ---", ""),
			("Test Certificate", cert.get("name")),
			("Test Date", cert.get("test_date")),
			("Overall Result", cert.get("overall_result")),
			("Vibration (mm/s)", cert.get("vibration_mm_s")),
			("Noise (dB)", cert.get("noise_db")),
		]
		for k, v in pairs:
			rows.append({"attribute": k, "value": "" if v is None else str(v)})
	return columns, rows

