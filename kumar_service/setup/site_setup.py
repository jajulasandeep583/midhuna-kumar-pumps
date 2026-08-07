"""One-shot ERPNext setup-wizard completion for the KUMAR Pumps demo site."""

import frappe

COMPANY = "Sri Lakshmi Ganapathi Engineering Works"
ABBR = "SLGEW"


def run():
	if frappe.db.get_single_value("System Settings", "setup_complete"):
		print("setup already complete")
		return

	from frappe.desk.page.setup_wizard.setup_wizard import setup_complete

	args = {
		"language": "English (United States)",
		"country": "India",
		"timezone": "Asia/Kolkata",
		"currency": "INR",
		"full_name": "KUMAR Admin",
		"email": "admin@kumarpumps.local",
		"password": "admin",
		"company_name": COMPANY,
		"company_abbr": ABBR,
		"company_tagline": "KUMAR Pumps & Motors - Tenali",
		"chart_of_accounts": "Standard with Numbers",
		"fy_start_date": "2026-04-01",
		"fy_end_date": "2027-03-31",
		"bank_account": "Cash",
		"domains": ["Manufacturing"],
		"setup_demo": 0,
	}

	setup_complete(args)
	frappe.db.commit()
	print("setup wizard complete:", frappe.db.get_single_value("System Settings", "setup_complete"))
	print("company:", frappe.get_all("Company", pluck="name"))
