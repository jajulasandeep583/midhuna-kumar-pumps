"""The people half of the demo: a real payroll running for a month.

A pump plant is its shop floor, so the demo needs the shop floor on it - who
works which shift in which department, what they are paid, who was absent, and
what July's wage bill actually came to.

Builds, in order:
    departments -> designations -> grades -> branches -> holiday list ->
    shift types -> ~94 employees -> leave allocations and applications ->
    attendance for the month -> salary components -> salary structures ->
    structure assignments -> July salary slips

Deterministic (same seed as the rest of the demo) and idempotent.

Attendance is written with a direct insert rather than the document API. At
~2,800 rows the per-document validation costs minutes and buys nothing here -
these are flat, self-consistent records with no links to keep in step.
"""

import random

import frappe
from frappe.utils import add_days, cint, flt, get_first_day, get_last_day, getdate

from kumar_service.setup.demo import FIRST, LAST, _mobile

RNG = random.Random(20260807)

COMPANY = "Sri Lakshmi Ganapathi Engineering Works"
ABBR = "SLGEW"

# payroll runs for a completed month; the demo month ends 2026-08-07
PAYROLL_START = getdate("2026-07-01")
PAYROLL_END = getdate("2026-07-31")
ATT_START = getdate("2026-07-01")
ATT_END = getdate("2026-08-07")

HOLIDAY_LIST = "KUMAR Holidays 2026-2027"

DEPARTMENTS = [
	"Foundry", "Machine Shop", "Winding", "Assembly", "Testing & QC",
	"Stores & Dispatch", "Maintenance",
]

# (designation, department, grade, headcount)
ROSTER = [
	("Managing Director", "Management", "M2", 1),
	("General Manager - Works", "Management", "M2", 1),
	("General Manager - Sales", "Management", "M2", 1),
	("Finance Controller", "Accounts", "M1", 1),

	("Foundry Manager", "Foundry", "M1", 1),
	("Production Supervisor", "Foundry", "S3", 1),
	("Furnace Operator", "Foundry", "W3", 5),
	("Moulder", "Foundry", "W2", 6),
	("Fettler", "Foundry", "W1", 2),

	("Machine Shop Incharge", "Machine Shop", "S3", 1),
	("CNC Operator", "Machine Shop", "W3", 7),
	("Grinding Operator", "Machine Shop", "W2", 3),
	("Machine Inspector", "Machine Shop", "S1", 1),

	("Winding Supervisor", "Winding", "S3", 1),
	("Coil Winder", "Winding", "W2", 8),
	("Varnish Operator", "Winding", "W1", 2),

	("Assembly Supervisor", "Assembly", "S3", 1),
	("Fitter", "Assembly", "W3", 9),
	("Assembly Helper", "Assembly", "W1", 3),

	("Quality Manager", "Testing & QC", "M1", 1),
	("Test Engineer", "Testing & QC", "S2", 3),
	("QC Inspector", "Testing & QC", "S1", 4),

	("Stores Incharge", "Stores & Dispatch", "S3", 1),
	("Storekeeper", "Stores & Dispatch", "S1", 3),
	("Packer", "Stores & Dispatch", "W1", 3),

	("Maintenance Engineer", "Maintenance", "S2", 1),
	("Electrician", "Maintenance", "W3", 2),
	("Mechanic", "Maintenance", "W2", 1),

	("Sales Manager", "Sales", "M1", 1),
	("Area Sales Officer", "Sales", "S2", 4),
	("Sales Coordinator", "Sales", "S1", 1),

	("Service Manager", "Customer Service", "M1", 1),
	("Field Service Technician", "Customer Service", "S1", 4),

	("Purchase Manager", "Purchase", "M1", 1),
	("Purchase Executive", "Purchase", "S1", 2),

	("Accounts Manager", "Accounts", "S3", 1),
	("Accounts Executive", "Accounts", "S1", 3),

	("HR & Admin Manager", "Human Resources", "M1", 1),
	("HR Executive", "Human Resources", "S1", 1),
	("Security Guard", "Human Resources", "W1", 1),
]

# grade -> (monthly base, structure)
GRADES = {
	"W1": (14000, "KUMAR Workmen"),
	"W2": (18500, "KUMAR Workmen"),
	"W3": (22500, "KUMAR Workmen"),
	"S1": (27000, "KUMAR Staff"),
	"S2": (35000, "KUMAR Staff"),
	"S3": (46000, "KUMAR Staff"),
	"M1": (64000, "KUMAR Management"),
	"M2": (98000, "KUMAR Management"),
}

BRANCHES = ["Tenali Plant", "Guntur Sales Office", "Vijayawada Branch"]

SHIFTS = [
	("General", "09:00:00", "18:00:00"),
	("Shift A", "06:00:00", "14:00:00"),
	("Shift B", "14:00:00", "22:00:00"),
	("Shift C", "22:00:00", "06:00:00"),
]

# AP / Telangana holidays inside the fiscal year
FESTIVALS = [
	("2026-04-14", "Dr. B.R. Ambedkar Jayanti"),
	("2026-05-01", "May Day"),
	("2026-06-15", "Bakrid"),
	("2026-08-15", "Independence Day"),
	("2026-08-26", "Vinayaka Chavithi"),
	("2026-10-02", "Gandhi Jayanti"),
	("2026-10-20", "Vijaya Dashami"),
	("2026-11-08", "Deepavali"),
	("2026-12-25", "Christmas"),
	("2027-01-14", "Sankranti"),
	("2027-01-15", "Kanuma"),
	("2027-01-26", "Republic Day"),
	("2027-03-11", "Holi"),
]

# (component, type, abbr, formula, condition, depends_on_payment_days)
COMPONENTS = [
	("Basic", "Earning", "B", "base * 0.50", None, 1),
	("Dearness Allowance", "Earning", "DA", "base * 0.20", None, 1),
	("House Rent Allowance", "Earning", "HRA", "base * 0.15", None, 1),
	("Conveyance Allowance", "Earning", "CA", "1600", None, 1),
	("Medical Allowance", "Earning", "MA", "1250", None, 1),
	("Special Allowance", "Earning", "SA", "base * 0.10", None, 1),
	("Production Incentive", "Earning", "PI", "base * 0.06", None, 0),
	("Provident Fund", "Deduction", "PF", "1800 if B * 0.12 > 1800 else B * 0.12", None, 0),
	("ESI Contribution", "Deduction", "ESIC", "base * 0.0075", "base < 21000", 0),
	("Professional Tax", "Deduction", "PT", "200", None, 0),
	("Income Tax", "Deduction", "IT", "base * 0.05", "base > 60000", 0),
]

STRUCTURES = {
	"KUMAR Workmen": {
		"earnings": ["Basic", "Dearness Allowance", "House Rent Allowance",
			"Conveyance Allowance", "Production Incentive"],
		"deductions": ["Provident Fund", "ESI Contribution", "Professional Tax"],
	},
	"KUMAR Staff": {
		"earnings": ["Basic", "Dearness Allowance", "House Rent Allowance",
			"Conveyance Allowance", "Medical Allowance", "Special Allowance"],
		"deductions": ["Provident Fund", "ESI Contribution", "Professional Tax"],
	},
	"KUMAR Management": {
		"earnings": ["Basic", "Dearness Allowance", "House Rent Allowance",
			"Conveyance Allowance", "Medical Allowance", "Special Allowance"],
		"deductions": ["Provident Fund", "Professional Tax", "Income Tax"],
	},
}


def _log(msg):
	print(f"  {msg}")


def _try(label, fn, *args, **kwargs):
	try:
		return fn(*args, **kwargs)
	except Exception as exc:  # noqa: BLE001 - demo data, keep going
		frappe.clear_last_message()
		frappe.db.rollback()
		_log(f"! {label} skipped: {str(exc)[:130]}")
		return None


def _dept(name):
	"""Departments are company-scoped and named '<name> - <abbr>'."""
	full = f"{name} - {ABBR}"
	return full if frappe.db.exists("Department", full) else None


# ---------------------------------------------------------------- masters


def departments():
	for name in DEPARTMENTS:
		if _dept(name):
			continue
		frappe.get_doc(
			{
				"doctype": "Department",
				"department_name": name,
				"company": COMPANY,
				"parent_department": "All Departments",
				"is_group": 0,
			}
		).insert(ignore_permissions=True)
	frappe.db.commit()


def designations():
	for designation, *_rest in ROSTER:
		if not frappe.db.exists("Designation", designation):
			frappe.get_doc(
				{"doctype": "Designation", "designation_name": designation}
			).insert(ignore_permissions=True)
	frappe.db.commit()


def grades():
	for code, (base, _structure) in GRADES.items():
		if frappe.db.exists("Employee Grade", code):
			continue
		frappe.get_doc(
			{"doctype": "Employee Grade", "__newname": code, "default_base_pay": base}
		).insert(ignore_permissions=True)
	frappe.db.commit()


def branches():
	for name in BRANCHES:
		if not frappe.db.exists("Branch", name):
			frappe.get_doc({"doctype": "Branch", "branch": name}).insert(ignore_permissions=True)
	frappe.db.commit()


def assign_holiday_list():
	"""HRMS v16 reads the holiday list from a Holiday List Assignment.

	It overrides ERPNext's `employee_holiday_list` hook with an implementation
	that ignores both `Employee.holiday_list` and `Company.default_holiday_list`
	and looks only at submitted Holiday List Assignment records. Without one,
	every leave application and every salary slip is refused with "No Holiday
	List was found" even though both fields are correctly filled in.

	One company-wide assignment covers everybody.
	"""
	if not frappe.db.exists("DocType", "Holiday List Assignment"):
		return None
	if frappe.db.exists(
		"Holiday List Assignment",
		{"assigned_to": COMPANY, "holiday_list": HOLIDAY_LIST, "docstatus": 1},
	):
		return None

	def _assign():
		doc = frappe.new_doc("Holiday List Assignment")
		doc.update(
			{
				"holiday_list": HOLIDAY_LIST,
				"applicable_for": "Company",
				"assigned_to": COMPANY,
				"from_date": "2026-04-01",
			}
		)
		doc.flags.ignore_permissions = True
		doc.insert(ignore_permissions=True)
		doc.submit()
		return doc.name

	name = _try("holiday list assignment", _assign)
	frappe.db.commit()
	frappe.clear_cache()
	return name


def holiday_list():
	if frappe.db.exists("Holiday List", HOLIDAY_LIST):
		if frappe.db.get_value("Company", COMPANY, "default_holiday_list") != HOLIDAY_LIST:
			frappe.db.set_value("Company", COMPANY, "default_holiday_list", HOLIDAY_LIST)
			frappe.db.commit()
			frappe.clear_cache()
		assign_holiday_list()
		return HOLIDAY_LIST

	doc = frappe.new_doc("Holiday List")
	doc.holiday_list_name = HOLIDAY_LIST
	doc.from_date = "2026-04-01"
	doc.to_date = "2027-03-31"

	festival_days = set()
	for date, description in FESTIVALS:
		doc.append("holidays", {"holiday_date": date, "description": description})
		festival_days.add(getdate(date))

	# every Sunday, minus any that is already a festival
	day = getdate("2026-04-01")
	while day <= getdate("2027-03-31"):
		if day.weekday() == 6 and day not in festival_days:
			doc.append("holidays", {"holiday_date": day, "description": "Sunday", "weekly_off": 1})
		day = add_days(day, 1)

	doc.flags.ignore_permissions = True
	doc.insert(ignore_permissions=True)
	frappe.db.set_value("Company", COMPANY, "default_holiday_list", HOLIDAY_LIST)
	frappe.db.commit()

	# HRMS resolves the holiday list through `get_cached_value`, so a company
	# that was cached before this write keeps answering "no holiday list" and
	# every leave application and salary slip in the same run is refused.
	frappe.clear_cache()
	assign_holiday_list()
	return doc.name


def shift_types():
	for name, start, end in SHIFTS:
		if frappe.db.exists("Shift Type", name):
			continue
		frappe.get_doc(
			{
				"doctype": "Shift Type",
				"__newname": name,
				"start_time": start,
				"end_time": end,
				"holiday_list": HOLIDAY_LIST,
			}
		).insert(ignore_permissions=True)
	frappe.db.commit()


# -------------------------------------------------------------- employees


def employees():
	"""~94 people across the plant, the office and the field."""
	if frappe.db.count("Employee") >= 90:
		_log("employees already present")
		return frappe.get_all("Employee", pluck="name")

	made = []
	for designation, department, grade, headcount in ROSTER:
		dept = _dept(department)
		for _n in range(headcount):
			gender = "Female" if RNG.random() < 0.18 else "Male"
			first = RNG.choice(FIRST)
			last = RNG.choice(LAST)

			# shop floor runs shifts; office and field do not
			if department in ("Foundry", "Machine Shop", "Winding", "Assembly"):
				shift = RNG.choice(["Shift A", "Shift A", "Shift B", "Shift C"])
				branch = "Tenali Plant"
			elif department in ("Testing & QC", "Stores & Dispatch", "Maintenance"):
				shift = RNG.choice(["General", "Shift A", "Shift B"])
				branch = "Tenali Plant"
			elif department == "Sales":
				shift = "General"
				branch = RNG.choice(["Guntur Sales Office", "Vijayawada Branch"])
			else:
				shift = "General"
				branch = "Tenali Plant"

			joined = add_days(getdate("2026-07-01"), -RNG.randint(200, 5200))

			def _make():
				doc = frappe.new_doc("Employee")
				doc.update(
					{
						"first_name": first,
						"last_name": last,
						"employee_name": f"{first} {last}",
						"gender": gender,
						"date_of_birth": add_days(joined, -RNG.randint(7300, 14600)),
						"date_of_joining": joined,
						"status": "Active",
						"company": COMPANY,
						"designation": designation,
						"department": dept,
						"grade": grade,
						"branch": branch,
						"default_shift": shift,
						"holiday_list": HOLIDAY_LIST,
						"employment_type": "Full-time"
						if frappe.db.exists("Employment Type", "Full-time")
						else None,
						"cell_number": _mobile(),
						"blood_group": RNG.choice(["A+", "B+", "O+", "AB+", "O-", "A-"]),
						"marital_status": RNG.choice(["Married", "Married", "Single"]),
					}
				)
				doc.flags.ignore_permissions = True
				doc.flags.ignore_mandatory = True
				doc.insert(ignore_permissions=True)
				return doc.name

			name = _try(f"employee {first} {last}", _make)
			if name:
				made.append(name)
		frappe.db.commit()
	return made


# ------------------------------------------------------------------ leave


def leave_setup():
	"""Allocate the year's leave, then take a believable slice of it."""
	staff = frappe.get_all(
		"Employee", filters={"status": "Active"}, fields=["name", "date_of_joining"]
	)
	if not staff:
		return 0, 0

	quota = {"Casual Leave": 12, "Sick Leave": 8, "Privilege Leave": 15}
	allocated = 0

	for emp in staff:
		for leave_type, days in quota.items():
			if not frappe.db.exists("Leave Type", leave_type):
				continue
			if frappe.db.exists(
				"Leave Allocation",
				{"employee": emp.name, "leave_type": leave_type, "docstatus": 1},
			):
				continue

			def _alloc():
				doc = frappe.new_doc("Leave Allocation")
				doc.update(
					{
						"employee": emp.name,
						"leave_type": leave_type,
						"from_date": "2026-04-01",
						"to_date": "2027-03-31",
						"new_leaves_allocated": days,
						"company": COMPANY,
					}
				)
				doc.flags.ignore_permissions = True
				doc.insert(ignore_permissions=True)
				doc.submit()
				return doc.name

			if _try(f"leave allocation {emp.name}", _alloc):
				allocated += 1
		frappe.db.commit()

	# a handful of actual applications inside the demo month
	applied = 0
	for emp in RNG.sample(staff, min(26, len(staff))):
		leave_type = RNG.choice(["Casual Leave", "Sick Leave"])
		start = add_days(ATT_START, RNG.randint(2, 30))
		length = RNG.choice([1, 1, 1, 2, 2, 3])
		end = add_days(start, length - 1)
		if getdate(end) > ATT_END:
			continue

		def _apply():
			doc = frappe.new_doc("Leave Application")
			doc.update(
				{
					"employee": emp.name,
					"leave_type": leave_type,
					"from_date": start,
					"to_date": end,
					"posting_date": add_days(start, -2),
					"company": COMPANY,
					"status": "Approved",
					"description": RNG.choice(
						["Family function", "Not well", "Personal work",
						 "Village visit", "Medical checkup"]
					),
				}
			)
			doc.flags.ignore_permissions = True
			doc.insert(ignore_permissions=True)
			doc.submit()
			return doc.name

		if _try(f"leave application {emp.name}", _apply):
			applied += 1
		frappe.db.commit()

	return allocated, applied


# ------------------------------------------------------------- attendance


def attendance():
	"""One row per employee per working day, written straight to the table.

	Marking ~2,800 attendances through the document API takes minutes and adds
	nothing: the rows are flat and we already know they are consistent.
	"""
	if frappe.db.count("Attendance") > 100:
		_log("attendance already present")
		return 0

	staff = frappe.get_all(
		"Employee",
		filters={"status": "Active"},
		fields=["name", "employee_name", "department", "default_shift", "company"],
	)
	if not staff:
		return 0

	holidays = set(
		frappe.get_all(
			"Holiday", filters={"parent": HOLIDAY_LIST}, pluck="holiday_date"
		)
	)
	holidays = {getdate(h) for h in holidays}

	on_leave = {}
	for row in frappe.get_all(
		"Leave Application",
		filters={"docstatus": 1},
		fields=["employee", "from_date", "to_date"],
	):
		day = getdate(row.from_date)
		while day <= getdate(row.to_date):
			on_leave.setdefault(row.employee, set()).add(day)
			day = add_days(day, 1)

	now = frappe.utils.now()
	rows = []
	serial = 0
	day = ATT_START
	while day <= ATT_END:
		if day in holidays:
			day = add_days(day, 1)
			continue
		for emp in staff:
			serial += 1
			if day in on_leave.get(emp.name, ()):
				status = "On Leave"
			else:
				roll = RNG.random()
				if roll < 0.941:
					status = "Present"
				elif roll < 0.973:
					status = "Absent"
				else:
					status = "Half Day"
			rows.append(
				(
					f"HR-ATT-2026-{serial:06d}",
					emp.name,
					emp.employee_name,
					status,
					day,
					emp.company or COMPANY,
					emp.department,
					emp.default_shift,
					1,
					"Administrator",
					now,
					now,
					"Administrator",
					"HR-ATT-.YYYY.-",
				)
			)
		day = add_days(day, 1)

	if not rows:
		return 0

	frappe.db.bulk_insert(
		"Attendance",
		fields=[
			"name", "employee", "employee_name", "status", "attendance_date",
			"company", "department", "shift", "docstatus", "owner", "creation",
			"modified", "modified_by", "naming_series",
		],
		values=rows,
		chunk_size=500,
	)
	frappe.db.commit()
	return len(rows)


# ---------------------------------------------------------------- payroll


def salary_components():
	for name, ctype, abbr, formula, condition, depends in COMPONENTS:
		exists = frappe.db.exists("Salary Component", name)
		doc = frappe.get_doc("Salary Component", name) if exists else frappe.new_doc(
			"Salary Component"
		)
		doc.update(
			{
				"salary_component": name,
				"salary_component_abbr": abbr,
				"type": ctype,
				"depends_on_payment_days": depends,
				"amount_based_on_formula": 1,
				"formula": formula,
				"condition": condition or "",
				"is_tax_applicable": 1 if ctype == "Earning" else 0,
				"round_to_the_nearest_integer": 1,
			}
		)
		doc.flags.ignore_permissions = True
		if exists:
			doc.save(ignore_permissions=True)
		else:
			doc.insert(ignore_permissions=True)
	frappe.db.commit()


def salary_structures():
	made = []
	for name, parts in STRUCTURES.items():
		if frappe.db.exists("Salary Structure", name):
			made.append(name)
			continue

		def _build():
			doc = frappe.new_doc("Salary Structure")
			doc.update(
				{
					"__newname": name,
					"company": COMPANY,
					"is_active": "Yes",
					"currency": "INR",
					"payroll_frequency": "Monthly",
					"salary_slip_based_on_timesheet": 0,
					"payment_account": frappe.db.get_value(
						"Account", {"company": COMPANY, "account_type": "Cash", "is_group": 0}, "name"
					),
				}
			)
			for component in parts["earnings"]:
				row = next(c for c in COMPONENTS if c[0] == component)
				doc.append(
					"earnings",
					{
						"salary_component": component,
						"abbr": row[2],
						"amount_based_on_formula": 1,
						"formula": row[3],
						"condition": row[4] or "",
						"depends_on_payment_days": row[5],
					},
				)
			for component in parts["deductions"]:
				row = next(c for c in COMPONENTS if c[0] == component)
				doc.append(
					"deductions",
					{
						"salary_component": component,
						"abbr": row[2],
						"amount_based_on_formula": 1,
						"formula": row[3],
						"condition": row[4] or "",
						"depends_on_payment_days": row[5],
					},
				)
			doc.flags.ignore_permissions = True
			doc.insert(ignore_permissions=True)
			doc.submit()
			return doc.name

		result = _try(f"salary structure {name}", _build)
		if result:
			made.append(result)
		frappe.db.commit()
	return made


def structure_assignments():
	staff = frappe.get_all(
		"Employee", filters={"status": "Active"}, fields=["name", "grade", "date_of_joining"]
	)
	assigned = 0
	for emp in staff:
		base, structure = GRADES.get(emp.grade, (20000, "KUMAR Workmen"))
		if not frappe.db.exists("Salary Structure", structure):
			continue
		if frappe.db.exists(
			"Salary Structure Assignment", {"employee": emp.name, "docstatus": 1}
		):
			continue

		# a little spread so everyone on a grade is not paid to the rupee
		pay = flt(base * RNG.uniform(0.94, 1.12), 0)
		from_date = max(getdate(emp.date_of_joining), getdate("2026-04-01"))

		def _assign():
			doc = frappe.new_doc("Salary Structure Assignment")
			doc.update(
				{
					"employee": emp.name,
					"salary_structure": structure,
					"from_date": from_date,
					"company": COMPANY,
					"currency": "INR",
					"base": pay,
					"variable": 0,
				}
			)
			doc.flags.ignore_permissions = True
			doc.insert(ignore_permissions=True)
			doc.submit()
			return doc.name

		if _try(f"salary assignment {emp.name}", _assign):
			assigned += 1
		frappe.db.commit()
	return assigned


def salary_slips():
	"""July's payroll, one submitted slip per employee."""
	if frappe.db.count("Salary Slip") > 10:
		_log("salary slips already present")
		return 0

	staff = frappe.get_all(
		"Salary Structure Assignment",
		filters={"docstatus": 1},
		fields=["employee", "salary_structure"],
		group_by="employee",
	)
	made = 0
	for row in staff:
		def _slip():
			doc = frappe.new_doc("Salary Slip")
			doc.update(
				{
					"employee": row.employee,
					"company": COMPANY,
					"salary_structure": row.salary_structure,
					"start_date": PAYROLL_START,
					"end_date": PAYROLL_END,
					"posting_date": add_days(PAYROLL_END, 1),
					"payroll_frequency": "Monthly",
					"currency": "INR",
					"exchange_rate": 1,
				}
			)
			doc.flags.ignore_permissions = True
			doc.insert(ignore_permissions=True)
			doc.submit()
			return doc.name

		if _try(f"salary slip {row.employee}", _slip):
			made += 1
		if made % 20 == 0:
			frappe.db.commit()
	frappe.db.commit()
	return made


def link_service_technicians():
	"""Point the existing Service Technician records at real Employee records."""
	if not frappe.db.has_column("Service Technician", "employee"):
		return 0

	field_techs = frappe.get_all(
		"Employee",
		filters={"designation": "Field Service Technician", "status": "Active"},
		pluck="name",
	)
	if not field_techs:
		return 0

	linked = 0
	for i, tech in enumerate(frappe.get_all("Service Technician", pluck="name")):
		if frappe.db.get_value("Service Technician", tech, "employee"):
			continue
		frappe.db.set_value(
			"Service Technician", tech, "employee", field_techs[i % len(field_techs)],
			update_modified=False,
		)
		linked += 1
	frappe.db.commit()
	return linked


# -------------------------------------------------------------------- run


def build_all():
	frappe.flags.mute_emails = True

	print("departments, designations, grades, branches...")
	departments()
	designations()
	grades()
	branches()

	print("holiday list and shifts...")
	holiday_list()
	shift_types()

	print("employees...")
	print(f"  {len(employees())}")

	print("leave allocations and applications...")
	print(f"  {leave_setup()}")

	print("attendance...")
	print(f"  {attendance()} rows")

	print("salary components and structures...")
	salary_components()
	print(f"  {salary_structures()}")

	print("salary structure assignments...")
	print(f"  {structure_assignments()}")

	print("salary slips (July 2026)...")
	print(f"  {salary_slips()}")

	print("linking service technicians to employees...")
	print(f"  {link_service_technicians()}")

	frappe.db.commit()
	print("DEMO HR DONE")
