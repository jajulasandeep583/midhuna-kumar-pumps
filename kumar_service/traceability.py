"""Manufacturing genealogy: pump <-> heat, winding lot, rotor lot.

ERPNext v15+ keeps serials and batches in a Serial and Batch Bundle, not on the
stock child row, so everything here reads through the bundle.
"""

import frappe
from frappe import _
from frappe.utils import cint, flt

from kumar_service.utils import setting

CONSUMED_BATCH_MAP = {
	"Casing": "custom_heat_no",
	"Stator": "custom_winding_batch",
	"Rotor": "custom_rotor_batch",
}

GENEALOGY_FIELDS = ("custom_heat_no", "custom_winding_batch", "custom_rotor_batch")


def _bundle_serials(bundle):
	if not bundle:
		return []
	return frappe.get_all(
		"Serial and Batch Entry",
		filters={"parent": bundle, "serial_no": ["is", "set"]},
		pluck="serial_no",
	)


def _bundle_batches(bundle):
	if not bundle:
		return []
	return frappe.get_all(
		"Serial and Batch Entry",
		filters={"parent": bundle, "batch_no": ["is", "set"]},
		pluck="batch_no",
	)


def row_serials(row):
	"""Serials on a stock row, whichever way they were entered.

	A bundle is the v15+ way, but with `use_serial_batch_fields` the row keeps
	plain text in `serial_no` and the bundle may not be readable yet at the
	moment our hook runs - so read both.
	"""
	serials = _bundle_serials(row.get("serial_and_batch_bundle"))
	if serials:
		return serials
	text = row.get("serial_no") or ""
	return [s.strip() for s in text.replace(",", "\n").split("\n") if s.strip()]


def row_batches(row):
	batches = _bundle_batches(row.get("serial_and_batch_bundle"))
	if batches:
		return batches
	return [row.get("batch_no")] if row.get("batch_no") else []


def capture_genealogy(doc, method=None):
	"""Stamp consumed batch numbers onto every serial the entry produced."""
	if doc.purpose not in ("Manufacture", "Repack"):
		return
	if not cint(setting("enable_heat_traceability", 1)):
		return

	produced, consumed = [], {}
	# which pump model each produced serial belongs to; serials created by
	# ERPNext's own bundle carry the item but not the KUMAR identity fields
	model_of = {}

	for row in doc.items:
		if row.t_warehouse and not row.s_warehouse:
			serials = row_serials(row)
			produced += serials
			model = frappe.db.get_value("Item", row.item_code, "custom_pump_model")
			if model:
				for sn in serials:
					model_of[sn] = model
		elif row.s_warehouse and not row.t_warehouse:
			group = frappe.db.get_value("Item", row.item_code, "custom_trace_group")
			field = CONSUMED_BATCH_MAP.get(group)
			if not field:
				continue
			batches = row_batches(row)
			if batches:
				consumed[field] = batches[0]

	# a Manufacture entry can also declare the heat directly on the header
	if doc.get("custom_heat_no"):
		consumed.setdefault("custom_heat_no", doc.custom_heat_no)

	if not produced:
		return

	payload = dict(consumed)
	if doc.get("work_order"):
		payload["custom_work_order"] = doc.work_order
	payload["custom_manufacturing_date"] = doc.posting_date

	for sn in produced:
		row_payload = dict(payload)
		# without the model the unit cannot be test-certified, looked up or
		# given a warranty - it is the first thing every other screen reads
		if model_of.get(sn):
			row_payload["custom_pump_model"] = model_of[sn]
		row_payload.setdefault("custom_qc_status", "Pending")
		frappe.db.set_value("Serial No", sn, row_payload, update_modified=False)

	if consumed:
		frappe.db.set_value("Stock Entry", doc.name, "custom_traceability_verified", 1,
			update_modified=False)
	else:
		frappe.msgprint(
			_("This entry produced {0} serialised unit(s) but consumed no traceable batches. "
			  "Genealogy for these units will be incomplete.").format(len(produced)),
			title=_("Traceability Gap"),
			indicator="orange",
		)


def clear_genealogy(doc, method=None):
	if doc.purpose not in ("Manufacture", "Repack"):
		return
	for row in doc.items:
		if row.t_warehouse and not row.s_warehouse:
			for sn in _bundle_serials(row.serial_and_batch_bundle):
				frappe.db.set_value(
					"Serial No",
					sn,
					{f: None for f in (*GENEALOGY_FIELDS, "custom_work_order")},
					update_modified=False,
				)
	frappe.db.set_value("Stock Entry", doc.name, "custom_traceability_verified", 0, update_modified=False)


def validate_qc_before_dispatch(doc, method=None):
	"""No pump leaves the plant unless its test certificate passed."""
	if not cint(setting("enforce_qc_before_dispatch", 1)):
		return

	outward = doc.doctype == "Delivery Note" or (
		doc.doctype == "Stock Entry" and doc.purpose in ("Material Issue", "Send to Subcontractor")
	)
	if not outward:
		return

	blocked = []
	for row in doc.items:
		if not frappe.db.get_value("Item", row.item_code, "custom_is_finished_pump"):
			continue
		for sn in row_serials(row):
			status = frappe.db.get_value("Serial No", sn, "custom_qc_status")
			if status != "Passed":
				blocked.append((sn, status or "Pending"))

	if blocked:
		rows = "".join(f"<li><b>{sn}</b> - QC status: {st}</li>" for sn, st in blocked[:20])
		frappe.throw(
			_("These units cannot be dispatched until their Pump Test Certificate passes:<ul>{0}</ul>").format(rows),
			title=_("QC Not Passed"),
		)


def mark_dispatched(doc, method=None):
	dealer = doc.get("custom_dealer")
	if not dealer:
		return
	for row in doc.items:
		for sn in row_serials(row):
			frappe.db.set_value("Serial No", sn, "custom_dealer", dealer, update_modified=False)


# ------------------------------------------------------------------ trace API


@frappe.whitelist()
def trace_backward(serial_no):
	"""Pump -> heat, winding lot, work order, test certificate."""
	frappe.has_permission("Serial No", "read", throw=True)

	sn = frappe.db.get_value(
		"Serial No",
		serial_no,
		[
			"name", "item_code", "custom_pump_model", "custom_manufacturing_date",
			"custom_work_order", "custom_heat_no", "custom_winding_batch",
			"custom_rotor_batch", "custom_test_certificate", "custom_qc_status",
		],
		as_dict=True,
	)
	if not sn:
		frappe.throw(_("Serial number {0} not found").format(serial_no), frappe.DoesNotExistError)

	heat = {}
	if sn.custom_heat_no:
		heat_record = frappe.db.get_value("Batch", sn.custom_heat_no, "custom_heat_record")
		if heat_record:
			heat = frappe.db.get_value(
				"Heat Record",
				heat_record,
				["name", "heat_no", "heat_date", "furnace", "target_grade", "grade_achieved",
				 "carbon_equivalent", "status", "all_within_spec"],
				as_dict=True,
			) or {}

	winding = {}
	if sn.custom_winding_batch:
		winding = frappe.db.get_value(
			"Winding Batch Record",
			{"batch_no": sn.custom_winding_batch},
			["name", "batch_no", "winding_date", "machine", "wire_gauge_swg", "turns_per_coil",
			 "ir_test_mohm", "hipot_test_kv", "qty_produced", "qty_rejected"],
			as_dict=True,
		) or {}

	certificate = {}
	if sn.custom_test_certificate:
		certificate = frappe.db.get_value(
			"Pump Test Certificate",
			sn.custom_test_certificate,
			["name", "test_date", "overall_result", "hipot_result", "hydrostatic_result",
			 "insulation_resistance_mohm", "vibration_mm_s", "noise_db"],
			as_dict=True,
		) or {}

	return {
		"serial_no": sn.name,
		"item_code": sn.item_code,
		"pump_model": sn.custom_pump_model,
		"manufacturing_date": sn.custom_manufacturing_date,
		"work_order": sn.custom_work_order,
		"qc_status": sn.custom_qc_status,
		"heat": heat,
		"heat_batch": sn.custom_heat_no,
		"winding": winding,
		"winding_batch": sn.custom_winding_batch,
		"rotor_batch": sn.custom_rotor_batch,
		"test_certificate": certificate,
	}


@frappe.whitelist()
def trace_forward(batch_no):
	"""Heat or winding batch -> every pump built from it, and how they are behaving.

	This is the recall / defect-cluster query.
	"""
	frappe.has_permission("Serial No", "read", throw=True)

	serials = frappe.get_all(
		"Serial No",
		filters=[
			["custom_heat_no", "=", batch_no],
		],
		pluck="name",
	) or []
	serials += frappe.get_all("Serial No", filters={"custom_winding_batch": batch_no}, pluck="name")
	serials += frappe.get_all("Serial No", filters={"custom_rotor_batch": batch_no}, pluck="name")
	serials = sorted(set(serials))

	if not serials:
		return {
			"batch_no": batch_no, "total_units": 0, "registered": 0, "with_complaints": 0,
			"failure_rate_pct": 0.0, "by_category": [], "serials": [], "above_threshold": False,
		}

	registered = frappe.db.count("Serial No", {"name": ["in", serials], "custom_registration": ["is", "set"]})

	requests = frappe.get_all(
		"Service Request",
		filters={"serial_no": ["in", serials], "docstatus": ["<", 2]},
		fields=["name", "serial_no", "complaint_category", "status", "root_cause", "reported_on"],
	)
	affected = {r.serial_no for r in requests}

	by_category = {}
	for r in requests:
		by_category[r.complaint_category] = by_category.get(r.complaint_category, 0) + 1

	failure_rate = flt(len(affected) * 100.0 / len(serials), 2)
	threshold = flt(setting("batch_failure_threshold_pct", 5))

	return {
		"batch_no": batch_no,
		"total_units": len(serials),
		"registered": registered,
		"with_complaints": len(affected),
		"complaint_count": len(requests),
		"failure_rate_pct": failure_rate,
		"threshold_pct": threshold,
		"above_threshold": failure_rate > threshold,
		"by_category": sorted(
			[{"complaint_category": k, "count": v} for k, v in by_category.items()],
			key=lambda x: -x["count"],
		),
		"serials": serials[:500],
		"affected_serials": sorted(affected),
	}
