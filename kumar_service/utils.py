"""Shared helpers: settings access, warranty maths, QR rendering."""

import base64
import io
import re

import frappe
from frappe.utils import add_months, cint, getdate, nowdate

SETTINGS = "Kumar Service Settings"

# How the pump reached the end customer. Not the same question as "how was this
# record typed in" (registration_source) - this one decides whose invoice the
# customer walks away holding, and therefore which fields on the registration
# are real.
#
#   CH_DIRECT - a KUMAR-owned outlet sold it. ONE invoice, ours, to the
#               customer. It is in our books, with our GSTIN.
#   CH_DEALER - an independent firm sold it. TWO invoices: ours to the dealer
#               (our books), and the dealer's own to the customer (their
#               letterhead, their GSTIN, never our books). We record only the
#               number of the second, as the customer's proof of purchase.
#
# The warranty is ours in both cases - see kumar_service.warranty.
CH_DIRECT = "Direct - KUMAR Invoice"
CH_DEALER = "Through Dealer - Dealer's Own Invoice"


def sale_channel_for(dealer):
	"""The channel a given outlet sells through. Ownership decides it."""
	if dealer and frappe.db.get_value("Dealer", dealer, "is_own_outlet"):
		return CH_DIRECT
	return CH_DEALER


def settings():
	return frappe.get_cached_doc(SETTINGS)


def setting(key, default=None):
	value = frappe.db.get_single_value(SETTINGS, key)
	return default if value in (None, "") else value


def warranty_months_for(pump_model=None, item_code=None):
	"""Item override beats model, model beats category, category beats settings."""
	if item_code:
		months = frappe.db.get_value("Item", item_code, "custom_warranty_months")
		if cint(months):
			return cint(months)

	if pump_model:
		months, category = frappe.db.get_value(
			"Pump Model", pump_model, ["warranty_months", "pump_category"]
		) or (0, None)
		if cint(months):
			return cint(months)
		if category:
			months = frappe.db.get_value("Pump Category", category, "default_warranty_months")
			if cint(months):
				return cint(months)

	return cint(setting("default_warranty_months", 12)) or 12


def warranty_dates(sale_date, manufacturing_date, months):
	"""Returns (start, expiry) honouring the Sale Date / Manufacturing Date setting."""
	basis = sale_date
	if setting("warranty_from", "Sale Date") == "Manufacturing Date" and manufacturing_date:
		basis = manufacturing_date
	if not basis:
		return None, None
	return getdate(basis), add_months(getdate(basis), cint(months))


def warranty_status_for(expiry, registered=True):
	if not registered or not expiry:
		return "Not Registered"
	expiry = getdate(expiry)
	today = getdate(nowdate())
	if expiry < today:
		return "Expired"
	if (expiry - today).days <= 30:
		return "Expiring Soon"
	return "In Warranty"


def qr_url_for(serial_no):
	base = setting("qr_base_url", "https://kumarpumps.co.in/warranty-check")
	return f"{base}?sn={serial_no}"


def qr_base64(data):
	"""PNG data URI for a QR code. Returns '' if the qrcode lib is unavailable."""
	try:
		import qrcode
	except ImportError:
		return ""

	img = qrcode.make(data, box_size=4, border=2)
	buf = io.BytesIO()
	img.save(buf, format="PNG")
	return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def validate_serial_format(serial_no):
	pattern = setting("serial_format_template")
	if not pattern:
		return True
	try:
		return bool(re.match(pattern, serial_no or ""))
	except re.error:
		return True


def validate_mobile(number, fieldlabel="Mobile"):
	if number and not re.match(r"^[6-9]\d{9}$", str(number).strip()):
		frappe.throw(
			frappe._("{0} must be 10 digits starting with 6-9").format(fieldlabel),
			title=frappe._("Invalid Mobile Number"),
		)


def user_dealer(user=None):
	"""The Dealer record this login belongs to, if any."""
	user = user or frappe.session.user
	return frappe.db.get_value("Dealer", {"portal_user": user}, ["name", "lft", "rgt"], as_dict=True)


def dealer_and_descendants(dealer):
	d = frappe.db.get_value("Dealer", dealer, ["lft", "rgt"], as_dict=True)
	if not d:
		return [dealer]
	return frappe.get_all(
		"Dealer", filters={"lft": [">=", d.lft], "rgt": ["<=", d.rgt]}, pluck="name"
	) or [dealer]
