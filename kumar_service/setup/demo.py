"""One month of believable operating data for the KUMAR demo site.

Deterministic (seeded RNG) so a rebuild tells the same story every time.

Shape of the month:
  foundry heats -> winding lots -> pumps built and tested -> sold through the
  dealer network -> a realistic tail of complaints, visits and claims, with one
  bad heat deliberately over-represented so Batch Defect Analysis has something
  to find.
"""

import random

import frappe
from frappe.utils import add_days, add_to_date, cint, flt, getdate, nowdate

RNG = random.Random(20260807)

COMPANY = "Sri Lakshmi Ganapathi Engineering Works"
ABBR = "SLGEW"

FIRST = ["Ramesh", "Suresh", "Venkata", "Lakshmi", "Naga", "Srinivas", "Anil", "Prasad",
	"Bhaskar", "Ravi", "Krishna", "Sita", "Padma", "Mohan", "Gopal", "Chandra",
	"Hari", "Satya", "Durga", "Kotesh"]
LAST = ["Reddy", "Naidu", "Rao", "Sharma", "Chowdary", "Varma", "Prasad", "Kumar",
	"Babu", "Murthy", "Goud", "Patnaik", "Das", "Nair", "Pillai"]

PLACES = [
	("Tenali", "Guntur", "Andhra Pradesh", "522201"),
	("Guntur", "Guntur", "Andhra Pradesh", "522001"),
	("Vijayawada", "Krishna", "Andhra Pradesh", "520001"),
	("Eluru", "West Godavari", "Andhra Pradesh", "534001"),
	("Nellore", "Nellore", "Andhra Pradesh", "524002"),
	("Ongole", "Prakasam", "Andhra Pradesh", "523001"),
	("Hyderabad", "Rangareddy", "Telangana", "500018"),
	("Karimnagar", "Karimnagar", "Telangana", "505001"),
	("Visakhapatnam", "Visakhapatnam", "Andhra Pradesh", "530016"),
	("Rajahmundry", "East Godavari", "Andhra Pradesh", "533101"),
]

SPEC = {
	"C": (3.10, 3.60),
	"Si": (1.80, 2.40),
	"Mn": (0.50, 0.90),
	"S": (0.02, 0.12),
	"P": (0.02, 0.15),
	"Cu": (0.10, 0.50),
}

COMPLAINTS = [
	("No Discharge", "Manufacturing Defect"),
	("Low Discharge", "Wear & Tear"),
	("Motor Burnt", "Voltage Fluctuation"),
	("Noise & Vibration", "Manufacturing Defect"),
	("Leakage", "Seal Failure" and "Manufacturing Defect"),
	("Tripping", "Voltage Fluctuation"),
	("Seal Failure", "Wear & Tear"),
	("Bearing Failure", "Manufacturing Defect"),
	("Impeller Damage", "Water Quality"),
	("Cable Fault", "Installation Error"),
	("Installation Issue", "Installation Error"),
]

END = getdate("2026-08-07")
START = add_days(END, -30)

FG_WH = f"FG Store - {ABBR}"
FOUNDRY_WH = f"Foundry WIP - {ABBR}"
ASSEMBLY_WH = f"Assembly WIP - {ABBR}"
WINDING_WH = f"Winding WIP - {ABBR}"


def _name():
	return f"{RNG.choice(FIRST)} {RNG.choice(LAST)}"


def _mobile():
	return f"{RNG.choice('6789')}{RNG.randint(100000000, 999999999)}"[:10]


def _day(offset=None):
	return add_days(START, offset if offset is not None else RNG.randint(0, 30))


def make_serial(item_code, work_order=None, pump_model=None, mfg_date=None, qc="Pending",
		heat=None, winding=None, rotor=None):
	"""Create one Serial No with KUMAR identity fields."""
	if not pump_model:
		pump_model = frappe.db.get_value("Item", item_code, "custom_pump_model")

	series = frappe.db.get_value("Item", item_code, "serial_no_series")
	serial_no = (
		frappe.model.naming.make_autoname(series) if series else frappe.generate_hash(length=10)
	)

	doc = frappe.get_doc(
		{
			"doctype": "Serial No",
			"serial_no": serial_no,
			"item_code": item_code,
			"custom_pump_model": pump_model,
			"custom_manufacturing_date": mfg_date or getdate(),
			"custom_work_order": work_order,
			"custom_qc_status": qc,
			"custom_warranty_status": "Not Registered",
			"custom_heat_no": heat,
			"custom_winding_batch": winding,
			"custom_rotor_batch": rotor,
		}
	)
	doc.flags.ignore_permissions = True
	doc.flags.ignore_mandatory = True
	doc.insert(ignore_permissions=True)
	return doc.name


# ------------------------------------------------------------------ builders


def build_heats(count=26):
	"""Foundry melts. One is deliberately marginal so a defect cluster exists."""
	made = []
	bad_index = 7
	for i in range(count):
		heat_no = f"HT-{(add_days(START, i)).strftime('%y%m%d')}-{i + 1:03d}"
		if frappe.db.exists("Heat Record", {"heat_no": heat_no}):
			made.append(heat_no)
			continue

		doc = frappe.new_doc("Heat Record")
		doc.heat_no = heat_no
		doc.heat_date = add_days(START, i)
		doc.furnace = "Induction Furnace"
		doc.shift = RNG.choice("ABC")
		doc.charge_weight_kg = RNG.randint(900, 1400)
		doc.tapping_temperature_c = RNG.randint(1480, 1520)
		doc.target_grade = "FG 200"

		marginal = i == bad_index
		for element, (lo, hi) in SPEC.items():
			if marginal and element == "S":
				value = round(hi + 0.03, 4)  # sulphur high - brittle castings
			else:
				value = round(RNG.uniform(lo + 0.02, hi - 0.02), 4)
			doc.append(
				"spectro_readings",
				{"element": element, "value_pct": value, "spec_min": lo, "spec_max": hi},
			)

		doc.grade_achieved = "FG 200"
		doc.status = "Approved for Pouring"
		if marginal:
			doc.override_reason = (
				"Sulphur marginally high. Released for non-critical castings on lab advice."
			)
		doc.flags.ignore_permissions = True
		doc.insert(ignore_permissions=True)
		made.append(heat_no)
	return made, made[bad_index]


def build_winding_batches(count=22):
	made = []
	models = frappe.get_all("Pump Model", pluck="name", limit=40)
	for i in range(count):
		batch_no = f"WD-{(add_days(START, i)).strftime('%y%m')}-{i + 1:04d}"
		if frappe.db.exists("Winding Batch Record", {"batch_no": batch_no}):
			made.append(batch_no)
			continue

		produced = RNG.randint(40, 120)
		rejected = RNG.randint(0, 4)
		doc = frappe.get_doc(
			{
				"doctype": "Winding Batch Record",
				"batch_no": batch_no,
				"winding_date": add_days(START, i),
				"machine": "Coil Winding Machine",
				"pump_model": RNG.choice(models) if models else None,
				"wire_gauge_swg": RNG.choice(["19", "20", "21", "22"]),
				"turns_per_coil": RNG.randint(60, 140),
				"oven_temp_c": RNG.randint(130, 160),
				"cure_duration_min": RNG.choice([90, 120, 150]),
				"ir_test_mohm": round(RNG.uniform(120, 500), 1),
				"hipot_test_kv": round(RNG.uniform(1.8, 2.5), 2),
				"winding_resistance_ohm": round(RNG.uniform(2.5, 12.0), 2),
				"qty_produced": produced,
				"qty_passed": produced - rejected,
				"qty_rejected": rejected,
				"rejection_reason": "Inter-turn short found at HiPot" if rejected else None,
			}
		)
		doc.flags.ignore_permissions = True
		doc.insert(ignore_permissions=True)
		made.append(batch_no)
	return made


def receive_components(heats, windings):
	"""Put batched components into stock so a real Manufacture entry can consume them."""
	rows = []
	for heat in heats[:6]:
		rows.append(("KC-CASING", heat, 40, FOUNDRY_WH))
	for wd in windings[:6]:
		rows.append(("KC-STATOR", wd, 40, WINDING_WH))

	made = []
	for item, batch, qty, warehouse in rows:
		if frappe.db.exists(
			"Stock Entry Detail", {"item_code": item, "batch_no": batch, "docstatus": 1}
		):
			continue
		se = frappe.new_doc("Stock Entry")
		se.stock_entry_type = "Material Receipt"
		se.company = COMPANY
		se.posting_date = add_days(START, 1)
		se.set_posting_time = 1
		se.append(
			"items",
			{
				"item_code": item,
				"qty": qty,
				"t_warehouse": warehouse,
				"basic_rate": frappe.db.get_value("Item", item, "valuation_rate") or 100,
				"use_serial_batch_fields": 1,
				"batch_no": batch,
			},
		)
		# rotor and other unbatched components
		se.flags.ignore_permissions = True
		se.insert(ignore_permissions=True)
		se.submit()
		made.append(se.name)
	return made


def manufacture_runs(heats, windings, runs=3, per_run=5):
	"""Real Manufacture entries so the genealogy hook is exercised end to end."""
	model_items = frappe.get_all(
		"Item", filters={"custom_is_finished_pump": 1}, pluck="name", limit=30
	)
	made = []
	for i in range(runs):
		item = model_items[i % len(model_items)]
		heat, winding = heats[i], windings[i]

		se = frappe.new_doc("Stock Entry")
		se.stock_entry_type = "Manufacture"
		se.company = COMPANY
		se.posting_date = add_days(START, 3 + i)
		se.set_posting_time = 1
		se.custom_shift = RNG.choice("ABC")
		se.append(
			"items",
			{
				"item_code": "KC-CASING",
				"qty": per_run,
				"s_warehouse": FOUNDRY_WH,
				"use_serial_batch_fields": 1,
				"batch_no": heat,
			},
		)
		se.append(
			"items",
			{
				"item_code": "KC-STATOR",
				"qty": per_run,
				"s_warehouse": WINDING_WH,
				"use_serial_batch_fields": 1,
				"batch_no": winding,
			},
		)
		se.append(
			"items",
			{
				"item_code": item,
				"qty": per_run,
				"t_warehouse": FG_WH,
				"is_finished_item": 1,
				"basic_rate": frappe.db.get_value("Item", item, "valuation_rate") or 5000,
				"use_serial_batch_fields": 1,
			},
		)
		se.flags.ignore_permissions = True
		se.insert(ignore_permissions=True)
		se.submit()
		made.append(se.name)
	return made


def build_serials(total=320, heats=None, windings=None, bad_heat=None):
	"""Historical production: serials with genealogy already attached."""
	items = frappe.get_all(
		"Item",
		filters={"custom_is_finished_pump": 1},
		fields=["name", "custom_pump_model"],
		limit=40,
	)
	if not items:
		return []

	made = []
	for i in range(total):
		item = RNG.choice(items)
		# the marginal heat is over-represented so a cluster is findable
		heat = bad_heat if (bad_heat and i % 9 == 0) else RNG.choice(heats)
		serial = make_serial(
			item.name,
			pump_model=item.custom_pump_model,
			mfg_date=_day(RNG.randint(0, 24)),
			qc="Pending",
			heat=heat,
			winding=RNG.choice(windings),
		)
		made.append(serial)
	return made


def test_certificates(serials, pass_rate=0.97):
	made = []
	for serial in serials:
		if frappe.db.exists("Pump Test Certificate", {"serial_no": serial, "docstatus": 1}):
			continue
		mfg = frappe.db.get_value("Serial No", serial, "custom_manufacturing_date")
		passed = RNG.random() < pass_rate
		doc = frappe.new_doc("Pump Test Certificate")
		doc.serial_no = serial
		doc.test_date = add_to_date(getdate(mfg or nowdate()), hours=RNG.randint(9, 17))
		doc.test_bench = "Test Bench"
		doc.supply_voltage_v = RNG.choice([230, 415])
		doc.frequency_hz = 50
		doc.no_load_current_a = round(RNG.uniform(1.2, 4.5), 2)
		doc.full_load_current_a = round(RNG.uniform(4.0, 12.0), 2)
		doc.insulation_resistance_mohm = round(RNG.uniform(60, 400), 1)
		doc.hipot_voltage_kv = 2.0
		doc.hipot_result = "Pass" if passed else "Fail"
		doc.hydrostatic_test_pressure = round(RNG.uniform(8, 16), 1)
		doc.hydrostatic_result = "Pass"
		doc.vibration_mm_s = round(RNG.uniform(0.8, 4.2), 2)
		doc.noise_db = round(RNG.uniform(56, 78), 1)
		doc.overall_result = "Pass" if passed else "Rework"
		for head, disch in ((6, 100), (12, 70), (20, 35)):
			doc.append(
				"duty_points",
				{
					"head_m": head,
					"discharge_lpm": disch + RNG.randint(-6, 6),
					"input_power_kw": round(RNG.uniform(0.4, 5.5), 2),
					"current_a": round(RNG.uniform(3, 11), 2),
					"speed_rpm": RNG.choice([1440, 2880]),
					"efficiency_pct": round(RNG.uniform(42, 68), 1),
					"is_duty_point": 1 if head == 12 else 0,
				},
			)
		doc.flags.ignore_permissions = True
		doc.insert(ignore_permissions=True)
		doc.submit()
		made.append(doc.name)
	return made


def registrations(serials, count=190):
	dealers = frappe.get_all(
		"Dealer", filters={"is_group": 0, "status": "Active"}, pluck="name"
	) or frappe.get_all("Dealer", pluck="name")

	made = []
	for serial in serials[:count]:
		if frappe.db.exists("Pump Registration", {"serial_no": serial, "docstatus": 1}):
			continue
		mfg = frappe.db.get_value("Serial No", serial, "custom_manufacturing_date")
		sale = add_days(getdate(mfg or START), RNG.randint(1, 6))
		if getdate(sale) > END:
			sale = END
		city, district, state, pincode = RNG.choice(PLACES)

		doc = frappe.new_doc("Pump Registration")
		doc.update(
			{
				"serial_no": serial,
				"dealer": RNG.choice(dealers),
				"sale_date": sale,
				"invoice_no": f"DL/{RNG.randint(1000, 9999)}",
				"end_customer_name": _name(),
				"end_customer_mobile": _mobile(),
				"application_type": RNG.choice(
					["Agriculture", "Agriculture", "Domestic", "Industrial", "Commercial"]
				),
				"installation_address": f"H.No {RNG.randint(1, 200)}, {city}",
				"district": district,
				"state": state,
				"pincode": pincode,
				"registration_source": RNG.choice(["Dealer Portal", "Desk", "Mobile"]),
				"borewell_depth_ft": RNG.choice([0, 0, 180, 240, 300, 420]),
				"static_water_level_ft": RNG.choice([0, 0, 60, 90, 120]),
			}
		)
		doc.flags.ignore_permissions = True
		doc.insert(ignore_permissions=True)
		doc.submit()
		made.append(doc.name)
	return made


def service_activity(registered_serials, bad_heat=None):
	techs = frappe.get_all("Service Technician", pluck="name")
	requests, visits, claims = [], [], []

	# pumps from the marginal heat fail more often - that is the story the
	# Batch Defect Analysis report is meant to surface
	bad_serials = (
		frappe.get_all(
			"Serial No",
			filters={"custom_heat_no": bad_heat, "custom_registration": ["is", "set"]},
			pluck="name",
			limit=14,
		)
		if bad_heat
		else []
	)
	pool = bad_serials + RNG.sample(
		registered_serials, min(28, len(registered_serials))
	)

	for serial in pool:
		complaint, root = RNG.choice(COMPLAINTS)
		if serial in bad_serials:
			complaint, root = RNG.choice(
				[("Noise & Vibration", "Manufacturing Defect"), ("Bearing Failure", "Manufacturing Defect")]
			)

		reported = add_to_date(_day(RNG.randint(6, 30)), hours=RNG.randint(9, 18))
		sr = frappe.new_doc("Service Request")
		sr.update(
			{
				"serial_no": serial,
				"complaint_category": complaint,
				"complaint_description": f"Customer reports: {complaint.lower()}. Attended on call.",
				"priority": RNG.choice(["Low", "Medium", "Medium", "High", "Critical"]),
				"reported_on": reported,
				"assigned_technician": RNG.choice(techs) if techs else None,
			}
		)

		roll = RNG.random()
		if roll < 0.6:
			sr.status = "Closed"
			sr.first_response_on = add_to_date(reported, hours=RNG.randint(1, 20))
			sr.resolved_on = add_to_date(reported, hours=RNG.randint(20, 70))
			sr.root_cause = root
			sr.resolution_summary = "Attended, part replaced, pump running to spec."
		elif roll < 0.75:
			sr.status = "In Progress"
			sr.first_response_on = add_to_date(reported, hours=RNG.randint(1, 26))
		elif roll < 0.85:
			sr.status = "Awaiting Parts"
			sr.first_response_on = add_to_date(reported, hours=RNG.randint(1, 30))
		else:
			sr.status = "Open"

		sr.flags.ignore_permissions = True
		sr.insert(ignore_permissions=True)
		sr.submit()
		requests.append(sr.name)

		if sr.status in ("Closed", "In Progress"):
			visit = frappe.new_doc("Service Visit")
			visit.update(
				{
					"service_request": sr.name,
					"technician": sr.assigned_technician,
					"visit_date": getdate(sr.first_response_on or reported),
					"visit_type": RNG.choice(["On-Site", "On-Site", "Workshop"]),
					"findings": f"Found {complaint.lower()}; root cause {root.lower()}.",
					"action_taken": "Replaced defective part and re-tested at site.",
					"labour_charge": RNG.choice([0, 250, 350, 500]),
					"customer_rating": RNG.choice([3, 4, 4, 5, 5]),
					"customer_feedback": RNG.choice(
						["Prompt service", "Satisfied", "Took a while but resolved", "Good response"]
					),
				}
			)
			part = RNG.choice(["KC-SEAL", "KC-BEARING", "KC-CAPACITOR", "KC-IMPELLER"])
			visit.append(
				"parts_used",
				{
					"item_code": part,
					"qty": 1,
					"rate": frappe.db.get_value("Item", part, "valuation_rate") or 150,
					"is_warranty_replacement": 1 if sr.is_under_warranty else 0,
					"defective_part_returned": 1 if sr.is_under_warranty else 0,
				},
			)
			visit.flags.ignore_permissions = True
			visit.insert(ignore_permissions=True)
			visit.submit()
			visits.append(visit.name)

		if sr.is_under_warranty and sr.root_cause == "Manufacturing Defect":
			claim = frappe.new_doc("Kumar Warranty Claim")
			claim.update(
				{
					"service_request": sr.name,
					"serial_no": serial,
					"claim_date": getdate(sr.resolved_on or reported),
					"claim_type": RNG.choice(
						["Part Replacement", "Part Replacement", "Repair Reimbursement"]
					),
					"root_cause": "Manufacturing Defect",
					"technician_report": "Defect confirmed on inspection; unit within warranty.",
				}
			)
			part = RNG.choice(["KC-BEARING", "KC-IMPELLER", "KC-STATOR"])
			claim.append(
				"defective_parts",
				{
					"item_code": part,
					"qty": 1,
					"rate": frappe.db.get_value("Item", part, "valuation_rate") or 500,
					"defect_observed": "Premature failure within warranty period",
				},
			)
			claim.flags.ignore_permissions = True
			claim.insert(ignore_permissions=True)
			claim.submit()

			# move some claims along the workflow so the queue is not all Draft
			state = RNG.choice(
				["Pending Review", "Pending Review", "Under Investigation", "Approved", "Settled", "Rejected"]
			)
			claim.db_set("workflow_state", state, update_modified=False)
			if state in ("Approved", "Settled"):
				claim.db_set("approved_amount", claim.claim_amount, update_modified=False)
			if state == "Settled":
				claim.db_set("settled_on", add_days(claim.claim_date, 6), update_modified=False)
			claims.append(claim.name)

	return requests, visits, claims


def sales_invoices(count=10):
	"""A few real invoices with the KUMAR dispatch fields filled in."""
	serials = frappe.get_all(
		"Serial No",
		filters={"warehouse": FG_WH, "custom_registration": ["is", "not set"]},
		pluck="name",
		limit=count * 2,
	)
	if not serials:
		return []

	dealers = frappe.get_all("Dealer", filters={"is_group": 0}, pluck="name")
	made = []
	for i in range(min(count, len(serials))):
		serial = serials[i]
		item = frappe.db.get_value("Serial No", serial, "item_code")
		dealer = RNG.choice(dealers)
		customer = _ensure_customer(dealer)

		si = frappe.new_doc("Sales Invoice")
		si.customer = customer
		si.company = COMPANY
		si.posting_date = add_days(END, -RNG.randint(1, 20))
		si.set_posting_time = 1
		si.due_date = add_days(si.posting_date, 30)
		si.update_stock = 1
		si.custom_dealer = dealer
		si.custom_dispatch_through = RNG.choice(["VRL Logistics", "Own Vehicle", "Kranthi Transports"])
		si.custom_lr_no = f"LR-{RNG.randint(10000, 99999)}"
		si.custom_vehicle_no = f"AP{RNG.randint(10, 39)}{RNG.choice('ABCXY')}{RNG.randint(1000, 9999)}"
		si.append(
			"items",
			{
				"item_code": item,
				"qty": 1,
				"warehouse": FG_WH,
				"rate": frappe.db.get_value("Item", item, "standard_rate") or 8000,
				"use_serial_batch_fields": 1,
				"serial_no": serial,
			},
		)
		si.flags.ignore_permissions = True
		try:
			si.insert(ignore_permissions=True)
			si.submit()
			made.append(si.name)
		except Exception as exc:  # stock or QC gating may legitimately refuse
			frappe.clear_last_message()
			print(f"  invoice for {serial} skipped: {str(exc)[:90]}")
	return made


def _ensure_customer(dealer):
	name = f"{dealer} (Trade)"
	if frappe.db.exists("Customer", name):
		return name
	doc = frappe.get_doc(
		{
			"doctype": "Customer",
			"customer_name": name,
			"customer_group": frappe.db.get_value("Customer Group", {"is_group": 0}, "name")
			or "All Customer Groups",
			"territory": frappe.db.get_value("Territory", {"is_group": 0}, "name") or "All Territories",
			"custom_dealer": dealer,
		}
	)
	doc.flags.ignore_permissions = True
	doc.insert(ignore_permissions=True)
	return doc.name


def dealer_logins():
	"""Give three dealers a real login so row-level isolation can be demonstrated."""
	people = [
		("dealer.vijayawada@kumarpumps.local", "Aruna Jyothi Distributors - Vijayawada", "Vijayawada Branch"),
		("dealer.venkateswara@kumarpumps.local", "Sri Venkateswara Pump Center", "Venkateswara Pumps"),
		("dealer.deccan@kumarpumps.local", "Deccan Pumps & Motors", "Deccan Pumps"),
	]
	made = []
	for email, dealer, full_name in people:
		if not frappe.db.exists("Dealer", dealer):
			continue
		if not frappe.db.exists("User", email):
			user = frappe.get_doc(
				{
					"doctype": "User",
					"email": email,
					"first_name": full_name,
					"send_welcome_email": 0,
					"user_type": "System User",
					"new_password": "Kumar@12345",
				}
			)
			user.append("roles", {"role": "Dealer"})
			user.flags.ignore_permissions = True
			user.insert(ignore_permissions=True)
		frappe.db.set_value("Dealer", dealer, "portal_user", email, update_modified=False)
		made.append((email, dealer))
	return made


def staff_logins():
	people = [
		("service.manager@kumarpumps.local", "Service Manager", ["Service Manager", "Service Technician"]),
		("quality@kumarpumps.local", "Quality Engineer", ["Quality Engineer", "Production Manager"]),
		("warranty@kumarpumps.local", "Warranty Approver", ["Warranty Approver", "Accounts User"]),
	]
	made = []
	for email, full_name, roles in people:
		if frappe.db.exists("User", email):
			made.append(email)
			continue
		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": full_name,
				"send_welcome_email": 0,
				"user_type": "System User",
				"new_password": "Kumar@12345",
			}
		)
		for role in roles:
			if frappe.db.exists("Role", role):
				user.append("roles", {"role": role})
		user.flags.ignore_permissions = True
		user.insert(ignore_permissions=True)
		made.append(email)
	return made


def build_all():
	frappe.flags.mute_emails = True
	print("heats...")
	heats, bad_heat = build_heats()
	print(f"  {len(heats)} heats, marginal heat = {bad_heat}")

	print("winding batches...")
	windings = build_winding_batches()
	print(f"  {len(windings)}")

	print("component receipts...")
	print(f"  {len(receive_components(heats, windings))} stock entries")

	print("manufacture runs (genealogy hook)...")
	print(f"  {len(manufacture_runs(heats, windings))} entries")

	print("historical serials...")
	serials = build_serials(heats=heats, windings=windings, bad_heat=bad_heat)
	print(f"  {len(serials)}")

	print("test certificates...")
	print(f"  {len(test_certificates(serials[:260]))}")

	print("registrations...")
	regs = registrations([s for s in serials if
		frappe.db.get_value('Serial No', s, 'custom_qc_status') == 'Passed'])
	print(f"  {len(regs)}")

	registered = frappe.get_all(
		"Serial No", filters={"custom_registration": ["is", "set"]}, pluck="name"
	)
	print("service activity...")
	reqs, visits, claims = service_activity(registered, bad_heat)
	print(f"  {len(reqs)} requests, {len(visits)} visits, {len(claims)} claims")

	print("sales invoices...")
	print(f"  {len(sales_invoices())}")

	print("logins...")
	print(f"  dealers: {dealer_logins()}")
	print(f"  staff:   {staff_logins()}")

	frappe.db.commit()
	print("DEMO DONE")
