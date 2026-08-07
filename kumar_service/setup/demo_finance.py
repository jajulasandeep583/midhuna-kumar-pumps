"""The accounting the plant actually runs on.

Two halves, because order matters:

  `masters()`  runs BEFORE the sales and purchase cycles - GST accounts, tax
               templates, cost centres, payment terms and addresses have to
               exist before an invoice can carry them.

  `settle()`   runs AFTER - money against the invoices (Payment Entries) and
               the overheads a factory pays every month (Journal Entries), so
               the receivable and payable ageing is a real curve rather than
               every bill sitting unpaid.

The site was created on the standard chart of accounts, not the India one, so
the GST ledgers are created here under Duties and Taxes.
"""

import random

import frappe
from frappe.utils import add_days, flt, getdate

from kumar_service.setup.demo import END, PLACES, START

RNG = random.Random(20260807)

COMPANY = "Sri Lakshmi Ganapathi Engineering Works"
ABBR = "SLGEW"

DUTIES = f"2300 - Duties and Taxes - {ABBR}"
TAX_ASSETS = f"1500 - Tax Assets - {ABBR}"

GST_RATE = 18.0  # pumps and motors, HSN 8413

OUTPUT_TAXES = [
	("Output CGST", 9.0),
	("Output SGST", 9.0),
]
INPUT_TAXES = [
	("Input CGST", 9.0),
	("Input SGST", 9.0),
]

SALES_TEMPLATE = "KUMAR GST 18% - Output"
PURCHASE_TEMPLATE = "KUMAR GST 18% - Input"

COST_CENTRES = [
	"Foundry", "Machine Shop", "Winding", "Assembly",
	"Testing & QC", "Stores & Dispatch", "Sales & Service", "Administration",
]

# the overheads a pump plant pays every month
# (description, expense account fragment, monthly amount, cost centre)
OVERHEADS = [
	("Electricity - APSPDCL, factory supply", "Utility Expenses", 486000, "Foundry"),
	("Factory shed rent - Industrial Estate, Sultanabad", "Office Rent", 175000, "Administration"),
	("Outward freight - dealer despatches", "Freight and Forwarding Charges", 92000, "Sales & Service"),
	("Telephone and internet", "Telephone Expenses", 18400, "Administration"),
	("Printing and stationery", "Print and Stationery", 12600, "Administration"),
	("Plant maintenance and spares", "Office Maintenance Expenses", 74500, "Machine Shop"),
	("Sales travel - Andhra and Telangana territory", "Travel Expenses", 63800, "Sales & Service"),
	("Dealer scheme and promotion", "Marketing Expenses", 55000, "Sales & Service"),
	("Bank charges and processing fees", "Bank Charges", 8900, "Administration"),
]


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


def _account(fragment, root_type="Expense"):
	"""Find a leaf account by the readable part of its name."""
	return frappe.db.get_value(
		"Account",
		{"company": COMPANY, "account_name": fragment, "is_group": 0, "root_type": root_type},
		"name",
	)


def _cash_account():
	return (
		frappe.db.get_value(
			"Account", {"company": COMPANY, "account_type": "Bank", "is_group": 0}, "name"
		)
		or frappe.db.get_value(
			"Account", {"company": COMPANY, "account_type": "Cash", "is_group": 0}, "name"
		)
	)


# ---------------------------------------------------------------- masters


def gst_accounts():
	made = {}
	for label, _rate in OUTPUT_TAXES:
		name = f"{label} - {ABBR}"
		if not frappe.db.exists("Account", name):
			frappe.get_doc(
				{
					"doctype": "Account",
					"account_name": label,
					"parent_account": DUTIES,
					"company": COMPANY,
					"account_type": "Tax",
					"root_type": "Liability",
					"is_group": 0,
					"tax_rate": _rate,
				}
			).insert(ignore_permissions=True)
		made[label] = name

	parent = TAX_ASSETS if frappe.db.exists("Account", TAX_ASSETS) else DUTIES
	for label, _rate in INPUT_TAXES:
		name = f"{label} - {ABBR}"
		if not frappe.db.exists("Account", name):
			frappe.get_doc(
				{
					"doctype": "Account",
					"account_name": label,
					"parent_account": parent,
					"company": COMPANY,
					"account_type": "Tax",
					"root_type": "Asset" if parent == TAX_ASSETS else "Liability",
					"is_group": 0,
					"tax_rate": _rate,
				}
			).insert(ignore_permissions=True)
		made[label] = name

	frappe.db.commit()
	return made


def tax_template_name(doctype, title):
	"""A tax template names itself '<title> - <abbr>', so look it up by title."""
	return frappe.db.get_value(doctype, {"title": title, "company": COMPANY}, "name")


def tax_templates():
	accounts = gst_accounts()

	if not tax_template_name("Sales Taxes and Charges Template", SALES_TEMPLATE):
		doc = frappe.new_doc("Sales Taxes and Charges Template")
		doc.title = SALES_TEMPLATE
		doc.company = COMPANY
		doc.is_default = 1
		for label, rate in OUTPUT_TAXES:
			doc.append(
				"taxes",
				{
					"charge_type": "On Net Total",
					"account_head": accounts[label],
					"description": f"{label} @ {rate}%",
					"rate": rate,
				},
			)
		doc.flags.ignore_permissions = True
		doc.insert(ignore_permissions=True)

	if not tax_template_name("Purchase Taxes and Charges Template", PURCHASE_TEMPLATE):
		doc = frappe.new_doc("Purchase Taxes and Charges Template")
		doc.title = PURCHASE_TEMPLATE
		doc.company = COMPANY
		doc.is_default = 1
		for label, rate in INPUT_TAXES:
			doc.append(
				"taxes",
				{
					"charge_type": "On Net Total",
					"add_deduct_tax": "Add",
					"category": "Total",
					"account_head": accounts[label],
					"description": f"{label} @ {rate}%",
					"rate": rate,
				},
			)
		doc.flags.ignore_permissions = True
		doc.insert(ignore_permissions=True)

	frappe.db.commit()


def cost_centres():
	# the root's parent is NULL, not '' - matching on '' finds nothing
	root = frappe.db.get_value(
		"Cost Center",
		{"company": COMPANY, "is_group": 1, "parent_cost_center": ["in", ["", None]]},
	)
	if not root:
		return 0
	made = 0
	for name in COST_CENTRES:
		full = f"{name} - {ABBR}"
		if frappe.db.exists("Cost Center", full):
			continue
		frappe.get_doc(
			{
				"doctype": "Cost Center",
				"cost_center_name": name,
				"parent_cost_center": root,
				"company": COMPANY,
				"is_group": 0,
			}
		).insert(ignore_permissions=True)
		made += 1
	frappe.db.commit()
	return made


def payment_terms():
	for name, days in (("KUMAR Net 30", 30), ("KUMAR Net 15", 15), ("KUMAR Advance", 0)):
		if frappe.db.exists("Payment Term", name):
			continue
		frappe.get_doc(
			{
				"doctype": "Payment Term",
				"payment_term_name": name,
				"due_date_based_on": "Day(s) after invoice date",
				"credit_days": days,
				"invoice_portion": 100,
			}
		).insert(ignore_permissions=True)

	if not frappe.db.exists("Terms and Conditions", "KUMAR Standard Terms"):
		frappe.get_doc(
			{
				"doctype": "Terms and Conditions",
				"title": "KUMAR Standard Terms",
				"selling": 1,
				"buying": 1,
				"terms": (
					"1. Goods once sold will not be taken back except under warranty.\n"
					"2. Warranty covers manufacturing defects only, from the date of sale.\n"
					"3. Payment within 30 days of invoice date. Interest at 18% p.a. thereafter.\n"
					"4. Transit damage must be reported within 48 hours of receipt.\n"
					"5. Subject to Tenali jurisdiction."
				),
			}
		).insert(ignore_permissions=True)
	frappe.db.commit()


def addresses():
	"""A registered office plus addresses for the trading partners."""
	made = 0
	if not frappe.db.exists("Address", {"address_title": COMPANY}):
		frappe.get_doc(
			{
				"doctype": "Address",
				"address_title": COMPANY,
				"address_type": "Office",
				"address_line1": "Plot 9-14 & 17-24, Industrial Estate",
				"address_line2": "Sultanabad",
				"city": "Tenali",
				"state": "Andhra Pradesh",
				"pincode": "522202",
				"country": "India",
				"is_primary_address": 1,
				"links": [{"link_doctype": "Company", "link_name": COMPANY}],
			}
		).insert(ignore_permissions=True)
		made += 1

	targets = [("Supplier", s) for s in frappe.get_all("Supplier", pluck="name")]
	targets += [("Dealer", d) for d in frappe.get_all("Dealer", filters={"is_group": 0}, pluck="name")]
	targets += [
		("Customer", c)
		for c in frappe.get_all("Customer", pluck="name", limit=40)
	]

	for doctype, name in targets:
		title = f"{name} - Address"
		if frappe.db.exists("Address", {"address_title": name}):
			continue
		city, district, state, pincode = RNG.choice(PLACES)

		def _make():
			frappe.get_doc(
				{
					"doctype": "Address",
					"address_title": name,
					"address_type": "Billing",
					"address_line1": f"D.No {RNG.randint(1, 90)}-{RNG.randint(1, 40)}-"
					f"{RNG.randint(1, 200)}, {RNG.choice(['Main Road', 'Bazaar Street', 'Ring Road', 'Market Yard'])}",
					"city": city,
					"state": state,
					"pincode": pincode,
					"country": "India",
					"is_primary_address": 1,
					"links": [{"link_doctype": doctype, "link_name": name}],
				}
			).insert(ignore_permissions=True)
			return True

		if _try(f"address for {title}", _make):
			made += 1
	frappe.db.commit()
	return made


def production_accounts():
	"""Give the company somewhere to book factory operating cost.

	A BOM with operations makes ERPNext add an `additional_costs` row to every
	Manufacture entry, and that row takes its account from
	`Company.default_operating_cost_account`. If that field is blank the row
	has no account and the entry is refused with a bare "Account is required" -
	so every Work Order silently stays at Not Started and nothing is ever
	produced.
	"""
	if frappe.db.get_value("Company", COMPANY, "default_operating_cost_account"):
		return None

	name = f"Factory Operating Cost - {ABBR}"
	if not frappe.db.exists("Account", name):
		cogs = f"5111 - Cost of Goods Sold - {ABBR}"
		parent = frappe.db.get_value("Account", cogs, "parent_account") or frappe.db.get_value(
			"Account", {"company": COMPANY, "root_type": "Expense", "is_group": 1}, "name"
		)
		if not parent:
			return None
		frappe.get_doc(
			{
				"doctype": "Account",
				"account_name": "Factory Operating Cost",
				"parent_account": parent,
				"company": COMPANY,
				"root_type": "Expense",
				"is_group": 0,
			}
		).insert(ignore_permissions=True)

	frappe.db.set_value("Company", COMPANY, "default_operating_cost_account", name)
	frappe.db.commit()
	frappe.clear_cache()
	return name


def masters():
	print("  tax accounts and templates...")
	_try("tax templates", tax_templates)
	print(f"  cost centres: {_try('cost centres', cost_centres)}")
	print(f"  operating cost account: {_try('operating cost account', production_accounts)}")
	_try("payment terms", payment_terms)
	frappe.db.commit()


# ----------------------------------------------------------------- settle


def _payment_for(doctype, name, posting_date, ratio=1.0):
	from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry

	pe = get_payment_entry(doctype, name)
	pe.posting_date = posting_date
	pe.reference_no = f"{'NEFT' if RNG.random() < 0.7 else 'CHQ'}-{RNG.randint(100000, 999999)}"
	pe.reference_date = posting_date
	pe.mode_of_payment = RNG.choice(["Bank Draft", "Cash", "Wire Transfer"]) \
		if frappe.db.exists("Mode of Payment", "Wire Transfer") else None

	if ratio < 1.0:
		full = flt(pe.paid_amount)
		part = flt(full * ratio, 2)
		pe.paid_amount = part
		pe.received_amount = part
		for row in pe.references:
			row.allocated_amount = flt(flt(row.allocated_amount) * ratio, 2)

	pe.flags.ignore_permissions = True
	pe.insert(ignore_permissions=True)
	pe.submit()
	return pe.name


def receive_payments():
	"""Collect against most sales invoices; leave a real ageing tail unpaid."""
	invoices = frappe.get_all(
		"Sales Invoice",
		filters={"docstatus": 1, "outstanding_amount": [">", 0]},
		fields=["name", "posting_date", "grand_total"],
		order_by="posting_date",
	)
	made = 0
	for inv in invoices:
		roll = RNG.random()
		if roll < 0.28:
			continue  # still outstanding - this is the receivable
		ratio = 1.0 if roll > 0.42 else RNG.choice([0.4, 0.5, 0.6])
		pay_day = add_days(getdate(inv.posting_date), RNG.randint(2, 22))
		if getdate(pay_day) > END:
			pay_day = END
		if _try(f"receipt for {inv.name}", _payment_for, "Sales Invoice", inv.name, pay_day, ratio):
			made += 1
			frappe.db.commit()
	return made


def pay_suppliers():
	invoices = frappe.get_all(
		"Purchase Invoice",
		filters={"docstatus": 1, "outstanding_amount": [">", 0]},
		fields=["name", "posting_date", "grand_total"],
		order_by="posting_date",
	)
	made = 0
	for inv in invoices:
		roll = RNG.random()
		if roll < 0.32:
			continue  # unpaid - this is the payable
		ratio = 1.0 if roll > 0.46 else RNG.choice([0.5, 0.7])
		pay_day = add_days(getdate(inv.posting_date), RNG.randint(3, 25))
		if getdate(pay_day) > END:
			pay_day = END
		if _try(f"payment for {inv.name}", _payment_for, "Purchase Invoice", inv.name, pay_day, ratio):
			made += 1
			frappe.db.commit()
	return made


def expense_journals():
	"""The overheads that never appear on a purchase invoice."""
	cash = _cash_account()
	if not cash:
		_log("! no bank/cash account - skipping overheads")
		return 0

	made = 0
	for description, account_name, amount, centre in OVERHEADS:
		account = _account(account_name)
		if not account:
			_log(f"! no account for {account_name}")
			continue

		post_day = add_days(START, RNG.randint(18, 29))
		if frappe.db.exists("Journal Entry", {"user_remark": description, "docstatus": 1}):
			continue

		cost_center = f"{centre} - {ABBR}"
		if not frappe.db.exists("Cost Center", cost_center):
			cost_center = frappe.db.get_value("Company", COMPANY, "cost_center")

		def _je():
			je = frappe.new_doc("Journal Entry")
			je.voucher_type = "Journal Entry"
			je.company = COMPANY
			je.posting_date = post_day
			je.user_remark = description
			je.append(
				"accounts",
				{"account": account, "debit_in_account_currency": amount, "cost_center": cost_center},
			)
			je.append("accounts", {"account": cash, "credit_in_account_currency": amount})
			je.flags.ignore_permissions = True
			je.insert(ignore_permissions=True)
			je.submit()
			return je.name

		if _try(f"overhead {account_name}", _je):
			made += 1
			frappe.db.commit()

	# the July wage bill, booked from the salary slips that were actually run
	wage_bill = flt(
		frappe.db.sql(
			"select sum(net_pay) from `tabSalary Slip` where docstatus = 1"
		)[0][0]
	)
	salary_account = _account("Salary")
	if wage_bill and salary_account and not frappe.db.exists(
		"Journal Entry", {"user_remark": "July 2026 wages and salaries", "docstatus": 1}
	):
		def _wages():
			je = frappe.new_doc("Journal Entry")
			je.voucher_type = "Journal Entry"
			je.company = COMPANY
			je.posting_date = getdate("2026-08-01")
			je.user_remark = "July 2026 wages and salaries"
			je.append(
				"accounts",
				{
					"account": salary_account,
					"debit_in_account_currency": wage_bill,
					"cost_center": frappe.db.get_value("Company", COMPANY, "cost_center"),
				},
			)
			je.append("accounts", {"account": cash, "credit_in_account_currency": wage_bill})
			je.flags.ignore_permissions = True
			je.insert(ignore_permissions=True)
			je.submit()
			return je.name

		if _try("wage bill journal", _wages):
			made += 1
			frappe.db.commit()

	return made


def settle():
	print("  addresses...")
	print(f"    {addresses()}")
	print("  customer receipts...")
	print(f"    {receive_payments()}")
	print("  supplier payments...")
	print(f"    {pay_suppliers()}")
	print("  overhead journals...")
	print(f"    {expense_journals()}")
	frappe.db.commit()
