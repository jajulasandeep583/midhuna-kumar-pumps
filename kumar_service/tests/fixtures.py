"""Fixtures shared by the kumar_service test suite.

Every record made here carries the `_KT` prefix, so anything that survives a
crashed run is obvious in the list view and trivially removable. Under
`IntegrationTestCase` the whole class runs inside one transaction that is
rolled back at teardown, so in a normal run nothing is left behind at all.

Nothing here leans on the demo data - the suite must pass on an empty site as
well as on the seeded one.
"""

import frappe
from frappe.utils import add_days, nowdate

PREFIX = "_KT"

CATEGORY = f"{PREFIX} Test Category"
MODEL = f"{PREFIX}-MODEL-A"
PUMP_ITEM = f"{PREFIX}-PUMP-ITEM"
SPARE_ITEM = f"{PREFIX}-SPARE-ITEM"

DEALER_INDEPENDENT = f"{PREFIX} Dealer Independent"
DEALER_OWN = f"{PREFIX} Dealer Branch"
DEALER_RIVAL = f"{PREFIX} Dealer Rival"
TECHNICIAN = f"{PREFIX} Technician"

DEALER_USER = "_kt.dealer@kumartest.local"
RIVAL_USER = "_kt.rival@kumartest.local"
OUTSIDER_USER = "_kt.outsider@kumartest.local"

# Every link target of the KUMAR doctypes. Listing them as
# IGNORE_TEST_RECORD_DEPENDENCIES in each test module stops frappe's automatic
# test-record generator from walking into ERPNext - importing erpnext's own
# test modules has side effects (test_fiscal_year creates a Fiscal Year that
# collides with the live one) and would fail the run before it started.
LINK_DEPENDENCIES = [
	"Batch",
	"Customer",
	"Dealer",
	"Employee",
	"Item",
	"Kumar Warranty Claim",
	"Pump Category",
	"Pump Model",
	"Pump Registration",
	"Pump Test Certificate",
	"Sales Invoice",
	"Serial No",
	"Service Request",
	"Service Technician",
	"Service Visit",
	"Territory",
	"UOM",
	"User",
	"Workflow State",
	"Workstation",
]

_serial_counter = [0]


def _insert(doc):
	doc.flags.ignore_permissions = True
	doc.insert(ignore_permissions=True)
	return doc


def company():
	return frappe.defaults.get_defaults().get("company") or frappe.db.get_value("Company", {}, "name")


HSN_PUMP = "841370"
HSN_PUMP_PART = "84139190"


def _hsn(code):
	"""None on a site without india_compliance, where the field does not exist."""
	if not frappe.db.table_exists("GST HSN Code"):
		return None
	return code if frappe.db.exists("GST HSN Code", code) else None


def item_group():
	for group in ("Finished Pumps", "Products", "All Item Groups"):
		if frappe.db.exists("Item Group", group):
			return group
	return frappe.db.get_value("Item Group", {"is_group": 0}, "name")


def pump_category():
	if not frappe.db.exists("Pump Category", CATEGORY):
		_insert(
			frappe.get_doc(
				{
					"doctype": "Pump Category",
					"category_name": CATEGORY,
					"abbr": "KTC",
					"default_warranty_months": 18,
				}
			)
		)
	return CATEGORY


def pump_item(item_code=PUMP_ITEM, serialised=True):
	if not frappe.db.exists("Item", item_code):
		_insert(
			frappe.get_doc(
				{
					"doctype": "Item",
					"item_code": item_code,
					"item_name": item_code,
					"item_group": item_group(),
					"stock_uom": "Nos",
					"is_stock_item": 1,
					"has_serial_no": 1 if serialised else 0,
					"custom_is_finished_pump": 1 if serialised else 0,
					# india_compliance makes this mandatory; without it every
					# fixture that touches an Item fails on a GST-enabled site
					"gst_hsn_code": _hsn(HSN_PUMP),
				}
			)
		)
	return item_code


def spare_item():
	if not frappe.db.exists("Item", SPARE_ITEM):
		_insert(
			frappe.get_doc(
				{
					"doctype": "Item",
					"item_code": SPARE_ITEM,
					"item_name": SPARE_ITEM,
					"item_group": item_group(),
					"stock_uom": "Nos",
					"is_stock_item": 1,
					"valuation_rate": 250,
					"gst_hsn_code": _hsn(HSN_PUMP_PART),
				}
			)
		)
	return SPARE_ITEM


def pump_model(warranty_months=0):
	"""Warranty months left at 0 on purpose, so the category default is what
	resolves - that is the fallback chain the warranty engine is built on."""
	if not frappe.db.exists("Pump Model", MODEL):
		_insert(
			frappe.get_doc(
				{
					"doctype": "Pump Model",
					"model_code": MODEL,
					"pump_category": pump_category(),
					"item": pump_item(),
					"hp": 5.0,
					"phase": "Three Phase",
					"warranty_months": warranty_months,
					"bis_standard": "IS 8034",
				}
			)
		)
	return MODEL


def dealer(name=DEALER_INDEPENDENT, is_own_outlet=0, parent=None, portal_user=None):
	if not frappe.db.exists("Dealer", name):
		_insert(
			frappe.get_doc(
				{
					"doctype": "Dealer",
					"dealer_name": name,
					"dealer_type": "Branch Office" if is_own_outlet else "Dealer",
					"is_own_outlet": is_own_outlet,
					"parent_dealer": parent,
					"status": "Active",
					"mobile_no": "9876543210",
					"state": "Andhra Pradesh",
					"portal_user": portal_user,
				}
			)
		)
	elif portal_user and not frappe.db.get_value("Dealer", name, "portal_user"):
		frappe.db.set_value("Dealer", name, "portal_user", portal_user)
	return name


def technician(dealer_name=None):
	if not frappe.db.exists("Service Technician", TECHNICIAN):
		_insert(
			frappe.get_doc(
				{
					"doctype": "Service Technician",
					"technician_name": TECHNICIAN,
					"dealer": dealer_name or dealer(),
					"mobile_no": "9876500000",
					"is_active": 1,
				}
			)
		)
	return TECHNICIAN


def serial_no(qc_status="Passed", manufactured_days_ago=90, model=None, item_code=None):
	"""A finished pump serial, already through QC and sitting in stock."""
	_serial_counter[0] += 1
	name = f"{PREFIX}-SN-{frappe.generate_hash(length=6).upper()}-{_serial_counter[0]:04d}"
	doc = frappe.get_doc(
		{
			"doctype": "Serial No",
			"serial_no": name,
			"item_code": item_code or pump_item(),
			"company": company(),
			"custom_pump_model": model or pump_model(),
			"custom_manufacturing_date": add_days(nowdate(), -manufactured_days_ago),
			"custom_qc_status": qc_status,
			"custom_warranty_status": "Not Registered",
		}
	)
	return _insert(doc).name


def user(email, roles=(), first_name=None):
	if not frappe.db.exists("User", email):
		doc = frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": first_name or email.split("@")[0],
				"send_welcome_email": 0,
				"user_type": "System User",
			}
		)
		_insert(doc)
	doc = frappe.get_doc("User", email)
	existing = {r.role for r in doc.roles}
	for role in roles:
		if role not in existing and frappe.db.exists("Role", role):
			doc.append("roles", {"role": role})
	doc.flags.ignore_permissions = True
	doc.save(ignore_permissions=True)
	return email


def dealer_login():
	"""An independent dealer with a portal login of its own."""
	email = user(DEALER_USER, roles=["Dealer"])
	return dealer(DEALER_INDEPENDENT, is_own_outlet=0, portal_user=email), email


def rival_login():
	"""A second, unrelated dealer - the one whose records must stay invisible."""
	email = user(RIVAL_USER, roles=["Dealer"])
	return dealer(DEALER_RIVAL, is_own_outlet=0, portal_user=email), email


def outsider():
	"""A logged-in user with no KUMAR role at all."""
	return user(OUTSIDER_USER)


def registration(dealer_name=None, serial=None, submit=False, **overrides):
	"""A through-the-dealer registration: the customer holds the DEALER's own
	invoice, so only its number is recorded."""
	values = {
		"doctype": "Pump Registration",
		"serial_no": serial or serial_no(),
		"dealer": dealer_name or dealer(),
		"sale_date": add_days(nowdate(), -5),
		"invoice_no": "D/2026/0001",
		"dealer_invoice_date": add_days(nowdate(), -5),
		"end_customer_name": "_KT Customer",
		"end_customer_mobile": "9812345678",
		"registration_source": "Desk",
	}
	values.update(overrides)
	doc = frappe.get_doc(values)
	doc.flags.ignore_permissions = True
	doc.insert(ignore_permissions=True)
	if submit:
		doc.submit()
	return doc


# Deleted parents before their children would fail, so this is the order the
# suite tears down in.
PURGE_ORDER = (
	"Service Visit",
	"Kumar Warranty Claim",
	"Service Request",
	"Pump Registration",
	"Pump Test Certificate",
	"Serial No",
	"Heat Record",
	"Winding Batch Record",
	"Batch",
	"Pump Model",
	"Pump Category",
	"Service Technician",
	"Dealer",
	"Item",
	"File",
	"User",
)


def purge():
	"""Remove everything the suite made.

	`IntegrationTestCase` rolls its transaction back at class teardown, which
	covers almost all of this. The import worker commits on purpose though -
	a background job that has written 3,000 rows should not lose them because
	row 3,001 was bad - so anything it touched survives the rollback and has to
	be cleared out by hand.
	"""
	removed = 0
	for doctype in PURGE_ORDER:
		if not frappe.db.exists("DocType", doctype):
			continue
		for name in frappe.get_all(doctype, filters={"name": ["like", "\\_KT%"]}, pluck="name"):
			removed += _force_delete(doctype, name)
		for name in frappe.get_all(doctype, filters={"name": ["like", "\\_kt%"]}, pluck="name"):
			removed += _force_delete(doctype, name)
	frappe.db.commit()
	return removed


def _force_delete(doctype, name):
	try:
		doc = frappe.get_doc(doctype, name)
		if doc.meta.is_submittable and doc.docstatus == 1:
			doc.flags.ignore_permissions = True
			doc.cancel()
		frappe.delete_doc(
			doctype, name, force=True, ignore_permissions=True, delete_permanently=True
		)
		return 1
	except Exception:
		return 0


def service_request(serial=None, submit=False, **overrides):
	values = {
		"doctype": "Service Request",
		"serial_no": serial or serial_no(),
		"complaint_category": "No Discharge",
		"complaint_description": "Pump runs but delivers no water.",
		"priority": "High",
	}
	values.update(overrides)
	doc = frappe.get_doc(values)
	doc.flags.ignore_permissions = True
	doc.insert(ignore_permissions=True)
	if submit:
		doc.submit()
	return doc
