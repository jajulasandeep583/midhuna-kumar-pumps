"""Warranty engine: stamp the serial, keep status honest, issue the certificate."""

import frappe
from frappe import _
from frappe.utils import cint, getdate, nowdate

from kumar_service.traceability import row_serials
from kumar_service.utils import (
	qr_url_for,
	warranty_dates,
	warranty_months_for,
	warranty_status_for,
)


def apply_registration(reg, revert=False):
	"""Write (or undo) a registration onto its Serial No."""
	if revert:
		payload = {
			"custom_dealer": None,
			"custom_registration": None,
			"custom_sale_date": None,
			"custom_warranty_start_date": None,
			"custom_warranty_expiry_date": None,
			"custom_warranty_status": "Not Registered",
			"custom_end_customer_name": None,
			"custom_end_customer_mobile": None,
			"custom_installation_pincode": None,
		}
	else:
		payload = {
			"custom_dealer": reg.dealer,
			"custom_registration": reg.name,
			"custom_sale_date": reg.sale_date,
			"custom_warranty_start_date": reg.warranty_start_date,
			"custom_warranty_expiry_date": reg.warranty_expiry_date,
			"custom_warranty_status": warranty_status_for(reg.warranty_expiry_date),
			"custom_end_customer_name": reg.end_customer_name,
			"custom_end_customer_mobile": reg.end_customer_mobile,
			"custom_installation_pincode": reg.pincode,
			"custom_qr_url": qr_url_for(reg.serial_no),
		}

	frappe.db.set_value("Serial No", reg.serial_no, payload, update_modified=False)


def compute_for_registration(reg):
	"""Fill model/warranty fields on a Pump Registration before save."""
	sn = frappe.db.get_value(
		"Serial No",
		reg.serial_no,
		["item_code", "custom_pump_model", "custom_manufacturing_date"],
		as_dict=True,
	)
	if not sn:
		frappe.throw(_("Serial number {0} does not exist").format(reg.serial_no))

	reg.item_code = sn.item_code
	reg.pump_model = sn.custom_pump_model
	reg.manufacturing_date = sn.custom_manufacturing_date

	if reg.pump_model:
		model = frappe.db.get_value("Pump Model", reg.pump_model, ["hp", "phase"], as_dict=True)
		if model:
			reg.hp = model.hp
			reg.phase = model.phase

	reg.warranty_months = warranty_months_for(reg.pump_model, reg.item_code)
	start, expiry = warranty_dates(reg.sale_date, reg.manufacturing_date, reg.warranty_months)
	reg.warranty_start_date = start
	reg.warranty_expiry_date = expiry
	reg.qr_url = qr_url_for(reg.serial_no)
	if not reg.warranty_card_no:
		reg.warranty_card_no = f"KWC-{reg.serial_no}"
	if not reg.registered_by:
		reg.registered_by = frappe.session.user


def auto_register_from_invoice(doc, method=None):
	"""Optionally raise a Pump Registration for every serial on a Sales Invoice."""
	if not cint(doc.get("custom_auto_register_pumps")):
		return

	dealer = doc.get("custom_dealer") or frappe.db.get_value("Customer", doc.customer, "custom_dealer")
	if not dealer:
		frappe.msgprint(
			_("Auto-registration skipped: no Dealer on the invoice or customer."),
			indicator="orange",
		)
		return

	made = []
	for row in doc.items:
		if not frappe.db.get_value("Item", row.item_code, "custom_is_finished_pump"):
			continue
		for sn in row_serials(row):
			if frappe.db.exists("Pump Registration", {"serial_no": sn, "docstatus": 1}):
				continue
			reg = frappe.new_doc("Pump Registration")
			reg.update(
				{
					"serial_no": sn,
					"dealer": dealer,
					"sale_date": doc.posting_date,
					"invoice_no": doc.name,
					"sales_invoice": doc.name,
					"registration_source": "Auto from Invoice",
					"end_customer_name": doc.customer_name or doc.customer,
					"end_customer_mobile": (doc.contact_mobile or "").strip() or "9999999999",
				}
			)
			reg.flags.ignore_permissions = True
			reg.insert(ignore_permissions=True)
			reg.submit()
			made.append(reg.name)

	if made:
		frappe.db.set_value(
			"Sales Invoice",
			doc.name,
			"custom_warranty_note",
			_("{0} pump(s) registered and warranty started: {1}").format(len(made), ", ".join(made[:5])),
			update_modified=False,
		)
		frappe.msgprint(
			_("Registered {0} pump(s) and started their warranty.").format(len(made)),
			indicator="green",
		)


def refresh_status(serial_no):
	"""Recompute one serial's warranty status. Returns the new status."""
	sn = frappe.db.get_value(
		"Serial No",
		serial_no,
		["custom_warranty_expiry_date", "custom_registration", "custom_warranty_status"],
		as_dict=True,
	)
	if not sn:
		return None
	if sn.custom_warranty_status == "Void":
		return "Void"

	status = warranty_status_for(sn.custom_warranty_expiry_date, bool(sn.custom_registration))
	if status != sn.custom_warranty_status:
		frappe.db.set_value("Serial No", serial_no, "custom_warranty_status", status,
			update_modified=False)
	return status


@frappe.whitelist()
def check_warranty(serial_no):
	"""Deliberately thin - this is what the public page is allowed to see.

	No dealer, no customer, no genealogy, no price.
	"""
	sn = frappe.db.get_value(
		"Serial No",
		serial_no,
		["name", "custom_pump_model", "custom_manufacturing_date",
		 "custom_warranty_expiry_date", "custom_warranty_status", "custom_registration"],
		as_dict=True,
	)
	if not sn:
		return {"found": False, "serial_no": serial_no}

	model = {}
	if sn.custom_pump_model:
		model = frappe.db.get_value(
			"Pump Model", sn.custom_pump_model,
			["model_code", "hp", "phase", "bis_standard", "pump_category"], as_dict=True
		) or {}

	expiry = sn.custom_warranty_expiry_date
	status = warranty_status_for(expiry, bool(sn.custom_registration))
	days_remaining = (getdate(expiry) - getdate(nowdate())).days if expiry else None

	return {
		"found": True,
		"serial_no": sn.name,
		"model_code": model.get("model_code"),
		"category": model.get("pump_category"),
		"hp": model.get("hp"),
		"phase": model.get("phase"),
		"bis_standard": model.get("bis_standard"),
		"manufacturing_date": sn.custom_manufacturing_date,
		"warranty_status": status,
		"warranty_expiry_date": expiry,
		"days_remaining": days_remaining,
		"is_registered": bool(sn.custom_registration),
	}
