"""The HR demo, made presentable: real faces, this month's roster, payroll up to last month.

demo_hr builds the people and July's payroll once. This layers on what an HR
click-through actually shows, all of it relative to TODAY so it never looks stale:

    people      a face, a gender-consistent unique name, PAN / PF / bank particulars
                and a reporting line for everyone (the org chart and the
                Employee image view both read these)
    hr login    hr@kumarpumps.local is the HR & Admin Manager - the leave approver
                for the plant, so the approval queue and the HR app have an owner
    roster      this month's Shift Assignments: the shop floor rotates A -> B -> C
                week by week, the office and supervisors stay on General
    leave       leave taken since attendance was last marked, and a few requests
                still waiting for approval
    attendance  every working day up to yesterday, with punch times, late
                entries and half days; today's check-ins so far
    payroll     slips for the last two completed months, paid on attendance, in
                the KUMAR Salary Slip print format

Payroll deliberately stops at salary slips. A Payroll Entry would post the wage
bill to the ledger, and ~Rs 29 lakh a month of salary expense against the demo's
sales would turn the finance dashboards into a loss-making company. The salary
components do carry their accounts, so a Payroll Entry run live in a demo works.

Idempotent and deterministic: run it the morning of a demo, after demo_story.

    bench --site kumarpumps.localhost execute kumar_service.setup.demo_hr_showcase.build_all

Photos are Unsplash-licensed portraits shipped in demo_assets/people (credits in
people.json), so the build needs no network.
"""

import datetime
import json
import os
import random

import frappe
from frappe.utils import (
	add_days,
	add_months,
	add_years,
	cint,
	get_datetime,
	get_first_day,
	get_last_day,
	getdate,
	now_datetime,
	nowdate,
)

from kumar_service.setup import demo_hr

COMPANY = demo_hr.COMPANY
HOLIDAY_LIST = demo_hr.HOLIDAY_LIST
HR_USER = "hr@kumarpumps.local"
ASSETS = os.path.join(os.path.dirname(__file__), "demo_assets", "people")

SHIFT_COLOURS = {"General": "Blue", "Shift A": "Green", "Shift B": "Orange", "Shift C": "Violet"}
SHIFT_HOURS = {  # start, end (end < start = runs past midnight)
	"General": (9, 18),
	"Shift A": (6, 14),
	"Shift B": (14, 22),
	"Shift C": (22, 6),
}
THREE_SHIFT = ("Shift A", "Shift B", "Shift C")
TWO_SHIFT = ("Shift A", "Shift B")
THREE_SHIFT_DEPARTMENTS = {"Foundry", "Machine Shop", "Winding", "Assembly"}

# who works the rotating shifts: operators and helpers, never their supervisors
SHOP_FLOOR = {
	"Furnace Operator", "Moulder", "Fettler", "CNC Operator", "Grinding Operator", "Coil Winder",
	"Varnish Operator", "Fitter", "Assembly Helper", "Packer", "Electrician", "Mechanic",
	"QC Inspector", "Storekeeper",
}

# designation -> the designation it reports to (every head is a single post)
REPORTS_TO = {
	"General Manager - Works": "Managing Director",
	"General Manager - Sales": "Managing Director",
	"Finance Controller": "Managing Director",
	"HR & Admin Manager": "Managing Director",
	"Foundry Manager": "General Manager - Works",
	"Machine Shop Incharge": "General Manager - Works",
	"Winding Supervisor": "General Manager - Works",
	"Assembly Supervisor": "General Manager - Works",
	"Quality Manager": "General Manager - Works",
	"Stores Incharge": "General Manager - Works",
	"Maintenance Engineer": "General Manager - Works",
	"Production Supervisor": "Foundry Manager",
	"Furnace Operator": "Production Supervisor",
	"Moulder": "Production Supervisor",
	"Fettler": "Production Supervisor",
	"CNC Operator": "Machine Shop Incharge",
	"Grinding Operator": "Machine Shop Incharge",
	"Machine Inspector": "Machine Shop Incharge",
	"Coil Winder": "Winding Supervisor",
	"Varnish Operator": "Winding Supervisor",
	"Fitter": "Assembly Supervisor",
	"Assembly Helper": "Assembly Supervisor",
	"Test Engineer": "Quality Manager",
	"QC Inspector": "Quality Manager",
	"Storekeeper": "Stores Incharge",
	"Packer": "Stores Incharge",
	"Electrician": "Maintenance Engineer",
	"Mechanic": "Maintenance Engineer",
	"Sales Manager": "General Manager - Sales",
	"Service Manager": "General Manager - Sales",
	"Area Sales Officer": "Sales Manager",
	"Sales Coordinator": "Sales Manager",
	"Field Service Technician": "Service Manager",
	"Purchase Manager": "Finance Controller",
	"Accounts Manager": "Finance Controller",
	"Purchase Executive": "Purchase Manager",
	"Accounts Executive": "Accounts Manager",
	"HR Executive": "HR & Admin Manager",
	"Security Guard": "HR & Admin Manager",
}

# the photo's apparent age decides the date of birth, not the other way round
AGE_BANDS = {"y": (24, 33), "m": (34, 46), "s": (47, 57)}


def _log(msg):
	print(f"  {msg}")


def _dept_name(dept):
	return (dept or "").rsplit(" - ", 1)[0]


# ------------------------------------------------------------------ people


def _manifest():
	with open(os.path.join(ASSETS, "people.json")) as f:
		return json.load(f)


def _fifth_technician():
	"""The Service Technician list names five technicians, but two of them -
	Ravi Kumar and Prasad Gupta - pointed at the same employee. Give Prasad
	his own employee record, paid and with leave like everyone else."""
	tech = "Prasad Gupta"
	if not frappe.db.exists("Service Technician", tech):
		return None
	current = frappe.db.get_value("Service Technician", tech, "employee")
	if current and frappe.db.count("Service Technician", {"employee": current}) == 1:
		return current

	emp = frappe.get_doc(
		{
			"doctype": "Employee",
			"first_name": "Prasad",
			"last_name": "Gupta",
			"gender": "Male",
			"date_of_birth": "1994-03-11",
			"date_of_joining": "2021-06-14",
			"status": "Active",
			"company": COMPANY,
			"designation": "Field Service Technician",
			"department": demo_hr._dept("Customer Service"),
			"grade": "S1",
			"branch": "Tenali Plant",
			"default_shift": "General",
			"holiday_list": HOLIDAY_LIST,
			"employment_type": "Full-time" if frappe.db.exists("Employment Type", "Full-time") else None,
			"cell_number": frappe.db.get_value("Service Technician", tech, "mobile_no"),
		}
	)
	emp.flags.ignore_mandatory = True
	emp.insert(ignore_permissions=True)
	frappe.db.set_value("Service Technician", tech, "employee", emp.name, update_modified=False)

	demo_hr.structure_assignments()
	for leave_type, days in {"Casual Leave": 12, "Sick Leave": 8, "Privilege Leave": 15}.items():
		alloc = frappe.get_doc(
			{
				"doctype": "Leave Allocation",
				"employee": emp.name,
				"leave_type": leave_type,
				"from_date": "2026-04-01",
				"to_date": "2027-03-31",
				"new_leaves_allocated": days,
				"company": COMPANY,
			}
		)
		alloc.insert(ignore_permissions=True)
		alloc.submit()
	frappe.db.commit()
	_log(f"field technician Prasad Gupta -> {emp.name}")
	return emp.name


def _birth_date(employee, band, joined):
	rng = random.Random(f"dob-{employee}")
	low, high = AGE_BANDS.get(band, AGE_BANDS["m"])
	# a fixed anchor, so a birthday does not move every time the demo is rebuilt
	dob = add_days(add_years(getdate("2026-09-01"), -rng.randint(low, high)), -rng.randint(0, 364))
	# nobody joined before they were nineteen
	latest = add_years(getdate(joined), -19)
	if getdate(dob) > getdate(latest):
		dob = add_days(latest, -rng.randint(30, 900))
	return dob


def _attach_photo(employee, photo):
	file_name = f"{employee}-{photo}"
	current = frappe.db.get_value("Employee", employee, "image") or ""
	if current.endswith(file_name):
		return False

	file_url = frappe.db.get_value(
		"File",
		{"attached_to_doctype": "Employee", "attached_to_name": employee, "file_name": file_name},
		"file_url",
	)
	if not file_url:
		with open(os.path.join(ASSETS, photo), "rb") as f:
			content = f.read()
		file = frappe.get_doc(
			{
				"doctype": "File",
				"file_name": file_name,
				"attached_to_doctype": "Employee",
				"attached_to_name": employee,
				"attached_to_field": "image",
				"is_private": 0,
				"content": content,
			}
		)
		file.insert(ignore_permissions=True)
		file_url = file.file_url
	frappe.db.set_value("Employee", employee, "image", file_url, update_modified=False)
	return True


def _spread_names():
	"""employee_name is copied onto every HR document; keep the copies in step
	after a rename, or the attendance list and the payslip disagree on who it is."""
	tables = frappe.db.sql_list(
		"""
		select c1.table_name from information_schema.columns c1
		join information_schema.columns c2
		  on c2.table_schema = c1.table_schema and c2.table_name = c1.table_name
		 and c2.column_name = 'employee'
		where c1.table_schema = database() and c1.column_name = 'employee_name'
		  and c1.table_name <> 'tabEmployee'
		"""
	)
	for table in tables:
		frappe.db.sql(
			f"""update `{table}` t join `tabEmployee` e on e.name = t.employee
			set t.employee_name = e.employee_name
			where not (t.employee_name <=> e.employee_name)"""
		)


def people():
	fifth = _fifth_technician()
	photos = 0
	for row in _manifest():
		employee = fifth if row["employee"] == "tech:Prasad Gupta" else row["employee"]
		if not employee or not frappe.db.exists("Employee", employee):
			continue
		joined = frappe.db.get_value("Employee", employee, "date_of_joining")
		frappe.db.set_value(
			"Employee",
			employee,
			{
				"first_name": row["first_name"],
				"middle_name": None,
				"last_name": row["last_name"],
				"employee_name": f"{row['first_name']} {row['last_name']}",
				"gender": row["gender"],
				"date_of_birth": _birth_date(employee, row["age"], joined),
				"pan_number": row["pan_number"],
				"provident_fund_account": row["provident_fund_account"],
				"salary_mode": "Bank",
				"bank_name": row["bank_name"],
				"bank_ac_no": row["bank_ac_no"],
				"ifsc_code": row["ifsc_code"],
			},
			update_modified=False,
		)
		if _attach_photo(employee, row["photo"]):
			photos += 1
	_spread_names()
	frappe.db.commit()
	_log(f"{len(_manifest())} people named, {photos} new photos")


def hierarchy():
	"""Reporting lines, so Organizational Chart draws the plant, not 96 orphans."""
	staff = frappe.get_all("Employee", filters={"status": "Active"}, fields=["name", "designation"])
	head = {}
	for e in staff:
		head.setdefault(e.designation, e.name)
	changed = 0
	for e in staff:
		boss = head.get(REPORTS_TO.get(e.designation))
		if frappe.db.get_value("Employee", e.name, "reports_to") != boss:
			frappe.db.set_value("Employee", e.name, "reports_to", boss, update_modified=False)
			changed += 1
	if changed:
		from frappe.utils.nestedset import rebuild_tree

		rebuild_tree("Employee")
	frappe.db.commit()
	_log(f"{changed} reporting lines set")


def hr_login():
	"""HR & Admin Manager gets hr@kumarpumps.local and approves the plant's leave."""
	from kumar_service.setup import demo

	demo.staff_logins()
	manager = frappe.db.get_value(
		"Employee", {"designation": "HR & Admin Manager", "status": "Active"},
		["name", "first_name", "last_name", "image"], as_dict=True,
	)
	if not manager or not frappe.db.exists("User", HR_USER):
		return
	frappe.db.set_value(
		"User", HR_USER,
		{"first_name": manager.first_name, "last_name": manager.last_name, "user_image": manager.image},
		update_modified=False,
	)
	frappe.db.set_value(
		"Employee", manager.name,
		{"user_id": HR_USER, "company_email": HR_USER, "prefered_contact_email": "Company Email",
		 "prefered_email": HR_USER, "create_user_permission": 0},
		update_modified=False,
	)
	# everybody's leave, shift and expense requests land with HR; HR's own go to the admin
	frappe.db.sql(
		"""update `tabEmployee` set leave_approver = %(hr)s, shift_request_approver = %(hr)s,
		expense_approver = %(hr)s where name <> %(me)s""",
		{"hr": HR_USER, "me": manager.name},
	)
	frappe.db.set_value(
		"Employee", manager.name,
		{"leave_approver": "admin@kumarpumps.local", "shift_request_approver": "admin@kumarpumps.local"},
		update_modified=False,
	)
	frappe.db.commit()
	_log(f"{HR_USER} -> {manager.name} {manager.first_name} {manager.last_name}")


# ------------------------------------------------------------------ shifts


def shift_types():
	for name, colour in SHIFT_COLOURS.items():
		if frappe.db.exists("Shift Type", name):
			frappe.db.set_value("Shift Type", name, {"color": colour, "holiday_list": HOLIDAY_LIST},
				update_modified=False)
	# supervisors, managers and office staff are on General, whatever demo_hr drew for them
	for emp in _staff():
		if not _cycle(emp) and emp.default_shift != "General":
			frappe.db.set_value("Employee", emp.name, "default_shift", "General", update_modified=False)
	frappe.db.commit()


def _cycle(emp):
	"""The shifts this person rotates through, or None for a General-shift post."""
	if emp.designation not in SHOP_FLOOR or emp.default_shift not in THREE_SHIFT:
		return None
	if _dept_name(emp.department) in THREE_SHIFT_DEPARTMENTS:
		return THREE_SHIFT
	return TWO_SHIFT


def shift_on(emp, day):
	"""Weekly forward rotation (morning -> afternoon -> night), anchored on the ISO
	week so it runs on seamlessly from one month into the next."""
	cycle = _cycle(emp)
	if not cycle:
		return "General"
	start = cycle.index(emp.default_shift) if emp.default_shift in cycle else 0
	week = getdate(day).isocalendar()[1]
	return cycle[(start + week) % len(cycle)]


def _staff():
	return frappe.get_all(
		"Employee",
		filters={"status": "Active", "company": COMPANY},
		fields=["name", "employee_name", "designation", "department", "default_shift", "company",
			"date_of_joining"],
		order_by="name",
	)


def roster(month_start=None):
	"""This month's Shift Assignments - what the HR Roster page (/hr/roster) draws."""
	month_start = getdate(month_start or get_first_day(nowdate()))
	month_end = get_last_day(month_start)
	made = 0
	for emp in _staff():
		if frappe.db.exists(
			"Shift Assignment",
			{"employee": emp.name, "docstatus": 1, "start_date": ["between", [month_start, month_end]]},
		):
			continue
		# one block per week, merged where the shift does not change
		blocks = []
		day = month_start
		while day <= month_end:
			shift = shift_on(emp, day)
			if blocks and blocks[-1][2] == shift:
				blocks[-1][1] = day
			else:
				blocks.append([day, day, shift])
			day = add_days(day, 1)
		for start, end, shift in blocks:
			doc = frappe.get_doc(
				{
					"doctype": "Shift Assignment",
					"employee": emp.name,
					"shift_type": shift,
					"company": COMPANY,
					"start_date": start,
					"end_date": end,
					"status": "Active",
				}
			)
			doc.insert(ignore_permissions=True)
			doc.submit()
			made += 1
		frappe.db.commit()
	_log(f"{made} shift assignments for {month_start.strftime('%B %Y')}")
	return made


# ------------------------------------------------------------------- leave


def _holidays():
	return {getdate(d) for d in frappe.get_all("Holiday", filters={"parent": HOLIDAY_LIST}, pluck="holiday_date")}


def _apply_leave(emp, leave_type, start, end, reason, status="Approved", posting=None):
	doc = frappe.get_doc(
		{
			"doctype": "Leave Application",
			"employee": emp,
			"leave_type": leave_type,
			"from_date": start,
			"to_date": end,
			"posting_date": posting or add_days(start, -2),
			"company": COMPANY,
			"status": status,
			"leave_approver": HR_USER if frappe.db.exists("User", HR_USER) else None,
			"description": reason,
			"follow_via_email": 0,
		}
	)
	doc.insert(ignore_permissions=True)
	if status == "Approved":
		doc.submit()
	return doc.name


def _last_marked():
	"""The last day the whole plant was marked. Not simply the latest attendance:
	approving a leave marks its own days, and those run ahead of the rest."""
	quorum = max(1, frappe.db.count("Employee", {"status": "Active"}) // 2)
	return frappe.db.sql(
		"""select max(day) from (
			select attendance_date as day from `tabAttendance` where docstatus = 1
			group by attendance_date having count(*) >= %s) marked""",
		quorum,
	)[0][0]


def past_leave():
	"""Leave taken in the days attendance is about to be marked for - a little of
	it unpaid, so the payslips show loss of pay where it really happened."""
	last = _last_marked()
	start = add_days(last, 1) if last else get_first_day(add_months(nowdate(), -1))
	end = add_days(nowdate(), -1)
	if getdate(start) > getdate(end):
		return 0
	holidays = _holidays()
	staff = _staff()
	rng = random.Random(f"leave-{start}-{end}")
	reasons = {
		"Casual Leave": ["Family function", "Personal work", "Village visit", "Bank and RTO work",
			"Brother's engagement"],
		"Sick Leave": ["Fever", "Viral fever - doctor advised rest", "Back pain", "Medical checkup"],
		"Privilege Leave": ["Family trip to Tirupati", "Daughter's admission at Guntur", "House shifting"],
		"Leave Without Pay": ["Extended stay at native place", "Personal - no balance left"],
	}
	# draw the whole plan first, so a re-run over the same days draws the same plan
	plan = []
	day = getdate(start)
	while day <= getdate(end):
		if day not in holidays:
			for emp in staff:
				if rng.random() >= 0.0075:
					continue
				leave_type = rng.choices(list(reasons), weights=[50, 30, 12, 8])[0]
				last_day = min(add_days(day, rng.choice([0, 0, 0, 1, 1, 2])), getdate(end))
				plan.append((emp.name, day, getdate(last_day), leave_type, rng.choice(reasons[leave_type])))
		day = add_days(day, 1)

	busy = {}
	made = 0
	for employee, first_day, last_day, leave_type, reason in plan:
		if busy.get(employee, datetime.date.min) >= first_day or frappe.db.exists(
			"Leave Application",
			{"employee": employee, "docstatus": ["!=", 2], "from_date": ["<=", last_day],
			 "to_date": [">=", first_day]},
		):
			continue
		try:
			_apply_leave(employee, leave_type, first_day, last_day, reason)
			frappe.db.commit()
			made += 1
			busy[employee] = last_day
		except Exception as exc:  # noqa: BLE001 - a clash just means no leave that day
			frappe.db.rollback()
			frappe.clear_last_message()
			_log(f"! leave {employee} {first_day}: {str(exc)[:90]}")
	frappe.db.commit()
	_log(f"{made} leave applications taken {start} .. {end}")
	return made


def pending_leave(target=6):
	"""A few requests waiting for HR, starting from the day after tomorrow."""
	open_now = frappe.db.count(
		"Leave Application", {"docstatus": 0, "status": "Open", "from_date": [">", nowdate()]}
	)
	if open_now >= target:
		return 0
	asks = [
		("Casual Leave", 1, "Sister's wedding at Ongole"),
		("Privilege Leave", 3, "Family trip to Tirupati"),
		("Sick Leave", 1, "Dental surgery - appointment fixed"),
		("Casual Leave", 2, "House warming ceremony at native village"),
		("Casual Leave", 1, "Children's school annual day"),
		("Privilege Leave", 2, "Father's cataract operation at Vijayawada"),
	]
	holidays = _holidays()
	rng = random.Random(f"pending-{nowdate()}")
	staff = [e for e in _staff() if e.designation != "HR & Admin Manager"]
	made = 0
	for leave_type, length, reason in asks[open_now:target]:
		start = add_days(nowdate(), rng.randint(2, 12))
		while getdate(start) in holidays:
			start = add_days(start, 1)
		emp = rng.choice(staff)
		try:
			_apply_leave(emp.name, leave_type, start, add_days(start, length - 1), reason,
				status="Open", posting=nowdate())
			frappe.db.commit()
			made += 1
		except Exception as exc:  # noqa: BLE001
			frappe.db.rollback()
			frappe.clear_last_message()
			_log(f"! pending leave {emp.name}: {str(exc)[:90]}")
	frappe.db.commit()
	_log(f"{made} leave requests waiting for approval")
	return made


# -------------------------------------------------------------- attendance


def _punch(day, shift, rng, half=False):
	"""Realistic in/out times for a shift: most people a few minutes early, some late."""
	start_h, end_h = SHIFT_HOURS.get(shift, SHIFT_HOURS["General"])
	shift_start = datetime.datetime.combine(getdate(day), datetime.time(start_h))
	shift_end = datetime.datetime.combine(getdate(day), datetime.time(end_h))
	if end_h < start_h:
		shift_end += datetime.timedelta(days=1)
	late = rng.random() < 0.06
	in_time = shift_start + datetime.timedelta(minutes=rng.randint(11, 38) if late else rng.randint(-14, 6))
	if half:
		out_time = in_time + datetime.timedelta(minutes=rng.randint(235, 275))
	else:
		out_time = shift_end + datetime.timedelta(minutes=rng.randint(-4, 28))
	hours = round((out_time - in_time).total_seconds() / 3600, 2)
	return in_time, out_time, hours, 1 if late else 0


def attendance():
	"""Mark every working day since the last marked one, up to yesterday."""
	# half days are half absent - without this the payroll pays them in full
	frappe.db.sql(
		"""update `tabAttendance` set half_day_status = 'Absent'
		where status = 'Half Day' and ifnull(half_day_status, '') = ''"""
	)

	last = _last_marked()
	start = add_days(last, 1) if last else get_first_day(add_months(nowdate(), -1))
	end = add_days(nowdate(), -1)
	if getdate(start) > getdate(end):
		_log("attendance already up to date")
		return 0

	holidays = _holidays()
	staff = _staff()
	marked = {
		(r.employee, getdate(r.attendance_date))
		for r in frappe.get_all(
			"Attendance",
			filters={"attendance_date": ["between", [start, end]], "docstatus": ["!=", 2]},
			fields=["employee", "attendance_date"],
		)
	}
	# days covered by a request not yet decided stay unmarked, or approving it later fails
	undecided = set()
	for la in frappe.get_all("Leave Application", filters={"docstatus": 0, "to_date": [">=", start]},
			fields=["employee", "from_date", "to_date"]):
		day = getdate(la.from_date)
		while day <= getdate(la.to_date):
			undecided.add((la.employee, day))
			day = add_days(day, 1)

	serials = {}

	def _next_name(day):
		prefix = f"HR-ATT-{getdate(day).year}-"
		if prefix not in serials:
			top = frappe.db.sql(
				"""select max(cast(substring(name, %s) as unsigned)) from `tabAttendance`
				where name like %s and length(name) = %s""",
				(len(prefix) + 1, prefix + "%", len(prefix) + 6),
			)[0][0]
			serials[prefix] = cint(top)
		serials[prefix] += 1
		return f"{prefix}{serials[prefix]:06d}"

	now = frappe.utils.now()
	rows = []
	day = getdate(start)
	while day <= getdate(end):
		if day in holidays:
			day = add_days(day, 1)
			continue
		rng = random.Random(f"att-{day}")
		for emp in staff:
			key = (emp.name, day)
			if key in marked or key in undecided or getdate(emp.date_of_joining) > day:
				continue
			shift = shift_on(emp, day)
			roll = rng.random()
			status = "Present" if roll < 0.945 else ("Absent" if roll < 0.975 else "Half Day")
			in_time = out_time = None
			hours, late = 0, 0
			if status != "Absent":
				in_time, out_time, hours, late = _punch(day, shift, rng, half=status == "Half Day")
			rows.append(
				(
					_next_name(day), emp.name, emp.employee_name, status, day, emp.company or COMPANY,
					emp.department, shift, in_time, out_time, hours, late, 0,
					"Absent" if status == "Half Day" else None,
					1, "Administrator", now, now, "Administrator", "HR-ATT-.YYYY.-",
				)
			)
		day = add_days(day, 1)

	if rows:
		frappe.db.bulk_insert(
			"Attendance",
			fields=[
				"name", "employee", "employee_name", "status", "attendance_date", "company",
				"department", "shift", "in_time", "out_time", "working_hours", "late_entry",
				"early_exit", "half_day_status", "docstatus", "owner", "creation", "modified",
				"modified_by", "naming_series",
			],
			values=rows,
			chunk_size=500,
		)
	frappe.db.commit()
	_log(f"{len(rows)} attendance rows {start} .. {end}")
	return len(rows)


def todays_checkins():
	"""Today's punches so far, as the biometric device would have sent them."""
	today = getdate(nowdate())
	if frappe.db.exists("Employee Checkin", {"time": [">=", get_datetime(today)]}):
		return 0
	now = now_datetime()
	if today in _holidays():
		return 0
	on_leave = {
		la.employee
		for la in frappe.get_all(
			"Leave Application",
			filters={"docstatus": 1, "status": "Approved", "from_date": ["<=", today], "to_date": [">=", today]},
			fields=["employee"],
		)
	}
	rng = random.Random(f"checkin-{today}")
	made = 0
	for emp in _staff():
		if emp.name in on_leave or rng.random() < 0.05:
			continue
		shift = shift_on(emp, today)
		# a night shift that started yesterday evening has an IN yesterday and an OUT this morning
		shift_day = add_days(today, -1) if shift == "Shift C" and now.hour < 22 else today
		in_time, out_time, _hours, _late = _punch(shift_day, shift, rng)
		for log_type, when in (("IN", in_time), ("OUT", out_time)):
			if when > now:
				continue
			doc = frappe.get_doc(
				{
					"doctype": "Employee Checkin",
					"employee": emp.name,
					"log_type": log_type,
					"time": when,
					"device_id": "Tenali Gate 1 - Biometric" if _dept_name(emp.department) not in
						("Sales",) else "HR Mobile App",
					"skip_auto_attendance": 1,
				}
			)
			doc.insert(ignore_permissions=True)
			made += 1
	frappe.db.commit()
	_log(f"{made} check-ins today")
	return made


# ----------------------------------------------------------------- payroll


def _account(name, number, parent):
	existing = frappe.db.get_value("Account", {"account_name": name, "company": COMPANY}, "name")
	if existing:
		return existing
	if frappe.db.exists("Account", {"account_number": number, "company": COMPANY}):
		number = None
	doc = frappe.get_doc(
		{
			"doctype": "Account",
			"account_name": name,
			"account_number": number,
			"parent_account": parent,
			"company": COMPANY,
			"root_type": "Liability",
			"is_group": 0,
		}
	)
	doc.insert(ignore_permissions=True)
	_log(f"account {doc.name}")
	return doc.name


def payroll_setup():
	settings = frappe.get_single("Payroll Settings")
	settings.payroll_based_on = "Attendance"
	settings.consider_unmarked_attendance_as = "Present"
	settings.show_leave_balances_in_salary_slip = 1
	# there is no outgoing Email Account on the demo site: mailing the payslip on
	# submit renders a PDF and fails the submit for anyone who has an email address
	settings.email_salary_slip_to_employee = 0
	settings.flags.ignore_permissions = True
	settings.save()

	# every component knows its ledger, so a Payroll Entry run live does not stop
	# on "Please set account in Salary Component"
	parent = frappe.db.get_value("Account", {"company": COMPANY, "account_name": "Duties and Taxes"}, "name")
	salary = frappe.db.get_value("Account", {"company": COMPANY, "account_name": "Salary", "is_group": 0}, "name")
	tds = frappe.db.get_value("Account", {"company": COMPANY, "account_number": "2310"}, "name")
	accounts = {"Provident Fund": _account("PF Payable", "2311", parent),
		"ESI Contribution": _account("ESI Payable", "2312", parent),
		"Professional Tax": _account("Professional Tax Payable", "2313", parent),
		"Income Tax": tds}
	for component, kind in frappe.get_all("Salary Component", fields=["name", "type"], as_list=True):
		account = salary if kind == "Earning" else accounts.get(component)
		if not account:
			continue
		doc = frappe.get_doc("Salary Component", component)
		row = next((a for a in doc.accounts if a.company == COMPANY), None)
		if row and row.account == account:
			continue
		if row:
			row.account = account
		else:
			doc.append("accounts", {"company": COMPANY, "account": account})
		doc.flags.ignore_permissions = True
		doc.save()
	frappe.db.commit()


def _retire_misnamed_slips():
	"""demo_hr once built slips named 'Sal Slip/None/00042' - the employee was
	filled in after the name was fixed. They are rebuilt below under proper names."""
	names = frappe.get_all("Salary Slip", filters={"name": ["like", "Sal Slip/None/%"]}, pluck="name")
	for name in names:
		doc = frappe.get_doc("Salary Slip", name)
		if doc.docstatus == 1:
			doc.flags.ignore_permissions = True
			doc.cancel()
		frappe.delete_doc("Salary Slip", name, ignore_permissions=True, force=True)
	if names:
		frappe.db.delete("Deleted Document", {"deleted_doctype": "Salary Slip",
			"deleted_name": ["like", "Sal Slip/None/%"]})
		frappe.db.commit()
		_log(f"{len(names)} misnamed slips retired")


def payroll_months(count=2):
	"""The last `count` completed months, oldest first."""
	months = []
	start = get_first_day(add_months(nowdate(), -1))
	for _ in range(count):
		if getdate(start) >= getdate("2026-04-01"):  # structures start with the fiscal year
			months.append((getdate(start), get_last_day(start)))
		start = get_first_day(add_months(start, -1))
	return list(reversed(months))


def salary_slips():
	_retire_misnamed_slips()
	assignments = frappe.get_all(
		"Salary Structure Assignment",
		filters={"docstatus": 1, "company": COMPANY},
		fields=["employee", "salary_structure"],
		order_by="from_date desc",
	)
	structure = {}
	for a in assignments:
		structure.setdefault(a.employee, a.salary_structure)
	active = set(frappe.get_all("Employee", filters={"status": "Active"}, pluck="name"))

	total = 0
	for start, end in payroll_months():
		made = 0
		for employee in sorted(structure):
			if employee not in active or frappe.db.exists(
				"Salary Slip", {"employee": employee, "start_date": start, "docstatus": ["!=", 2]}
			):
				continue
			try:
				slip = frappe.get_doc(
					{
						"doctype": "Salary Slip",
						"employee": employee,
						"company": COMPANY,
						"salary_structure": structure[employee],
						"start_date": start,
						"end_date": end,
						"posting_date": end,
						"payroll_frequency": "Monthly",
						"currency": "INR",
						"exchange_rate": 1,
					}
				)
				slip.insert(ignore_permissions=True)
				slip.submit()
				# commit each one: a rollback on the next failure must not take this with it
				frappe.db.commit()
				made += 1
			except Exception as exc:  # noqa: BLE001
				frappe.db.rollback()
				frappe.clear_last_message()
				_log(f"! slip {employee} {start}: {str(exc)[:110]}")
		total += made
		_log(f"{made} salary slips for {start.strftime('%B %Y')}")
	return total


# --------------------------------------------------------------------- run


def build_all():
	from kumar_service.setup import print_formats

	frappe.flags.mute_emails = True

	print("people: names, faces, particulars...")
	people()
	hierarchy()
	print("HR login...")
	hr_login()
	print("shift colours and this month's roster...")
	shift_types()
	roster()
	print("leave...")
	past_leave()
	pending_leave()
	print("attendance...")
	attendance()
	todays_checkins()
	print("payroll...")
	payroll_setup()
	salary_slips()
	print("print formats...")
	print_formats.build_all()
	frappe.db.commit()
	print("HR SHOWCASE DONE")
