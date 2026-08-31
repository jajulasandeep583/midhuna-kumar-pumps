"""Row-level isolation for dealers.

A dealer login must see its own records and those of its sub-dealers, and
nothing else. The tree makes that a range query rather than a recursive walk.

Never trust a `dealer` value posted from the client - it is always re-derived
from the session user here.
"""

import frappe

from kumar_service.utils import dealer_and_descendants, user_dealer

FULL_ACCESS_ROLES = (
	"System Manager",
	"Administrator",
	"Service Manager",
	"Warranty Approver",
	"Quality Engineer",
	"Production Manager",
	"Dealer Manager",
)


def has_full_access(user=None):
	user = user or frappe.session.user
	if user == "Administrator":
		return True
	return any(role in frappe.get_roles(user) for role in FULL_ACCESS_ROLES)


def _scoped_condition(user, doctype, fieldname="dealer"):
	if has_full_access(user):
		return ""

	d = user_dealer(user)
	if not d:
		# a non-dealer, non-manager user (e.g. a technician) sees everything
		# assigned through other means, not filtered by dealer
		if "Service Technician" in frappe.get_roles(user):
			return ""
		return "1=0"

	names = dealer_and_descendants(d.name)
	quoted = ", ".join(frappe.db.escape(n) for n in names)
	return f"`tab{doctype}`.`{fieldname}` in ({quoted})"


def service_request_query(user=None, doctype=None):
	return _scoped_condition(user, "Service Request")


def pump_registration_query(user=None, doctype=None):
	return _scoped_condition(user, "Pump Registration")


def warranty_claim_query(user=None, doctype=None):
	return _scoped_condition(user, "Kumar Warranty Claim")


def serial_no_query(user=None, doctype=None):
	return _scoped_condition(user, "Serial No", "custom_dealer")


def dealer_query(user=None, doctype=None):
	"""A dealer sees itself and its descendants in the Dealer list."""
	if has_full_access(user):
		return ""
	d = user_dealer(user)
	if not d:
		return ""
	names = dealer_and_descendants(d.name)
	quoted = ", ".join(frappe.db.escape(n) for n in names)
	return f"`tabDealer`.`name` in ({quoted})"


def _doc_allowed(doc, user, fieldname="dealer"):
	if has_full_access(user):
		return True
	d = user_dealer(user)
	if not d:
		return "Service Technician" in frappe.get_roles(user)
	return doc.get(fieldname) in dealer_and_descendants(d.name)


def service_visit_query(user=None, doctype=None):
	"""A Service Visit belongs to whoever owns its Service Request.

	Service Visit carries no `dealer` field of its own, so it was left out of
	the scoping entirely: every dealer in the network could list all of them,
	and read another dealer's customer, technician and site findings. It is
	scoped through its parent ticket instead.
	"""
	if has_full_access(user):
		return ""
	d = user_dealer(user)
	if not d:
		if "Service Technician" in frappe.get_roles(user):
			return ""
		return "1=0"
	names = dealer_and_descendants(d.name)
	quoted = ", ".join(frappe.db.escape(n) for n in names)
	return (
		"`tabService Visit`.`service_request` in ("
		f"select `name` from `tabService Request` where `dealer` in ({quoted}))"
	)


def service_visit_has_permission(doc, user=None, permission_type=None):
	user = user or frappe.session.user
	if has_full_access(user):
		return True
	d = user_dealer(user)
	if not d:
		return "Service Technician" in frappe.get_roles(user)
	sr = doc.get("service_request") if hasattr(doc, "get") else None
	if not sr:
		return False
	owner_dealer = frappe.db.get_value("Service Request", sr, "dealer")
	return owner_dealer in dealer_and_descendants(d.name)


def _serial_scoped(user, doctype):
	"""Scope a doctype that links a pump but carries no dealer of its own."""
	if has_full_access(user):
		return ""
	d = user_dealer(user)
	if not d:
		if "Service Technician" in frappe.get_roles(user):
			return ""
		return "1=0"
	names = dealer_and_descendants(d.name)
	quoted = ", ".join(frappe.db.escape(n) for n in names)
	return (
		f"`tab{doctype}`.`serial_no` in ("
		f"select `name` from `tabSerial No` where `custom_dealer` in ({quoted}))"
	)


def test_certificate_query(user=None, doctype=None):
	"""The factory QC record for a pump, scoped to the pumps you sold.

	This is the works test sheet - duty points, test date, the bench it ran on.
	Useful to the dealer who sold that pump and to nobody else; unscoped it let
	any dealer read the test record of every pump the factory has ever built.
	"""
	return _serial_scoped(user, "Pump Test Certificate")


def test_certificate_has_permission(doc, user=None, permission_type=None):
	user = user or frappe.session.user
	if has_full_access(user):
		return True
	d = user_dealer(user)
	if not d:
		return "Service Technician" in frappe.get_roles(user)
	serial = doc.get("serial_no") if hasattr(doc, "get") else None
	if not serial:
		return False
	owner = frappe.db.get_value("Serial No", serial, "custom_dealer")
	return owner in dealer_and_descendants(d.name)


def serial_no_has_permission(doc, user=None, permission_type=None):
	"""A dealer may read the serials their own tree sold, and nothing else.

	serial_no_query already scoped the LIST, but there was no document-level
	rule and the Dealer role held no Serial No permission at all - so the desk's
	claim and registration pages died on "does not have doctype access" the
	moment anything went through the ORM rather than frappe.db.get_value.

	Read only. A dealer never writes a serial: the pump is created in the plant
	and the sale is recorded through Pump Registration, which has its own rules.
	"""
	user = user or frappe.session.user
	if has_full_access(user):
		return True
	d = user_dealer(user)
	if not d:
		return "Service Technician" in frappe.get_roles(user)
	if permission_type and permission_type not in ("read", "select"):
		return False
	owner = doc.get("custom_dealer") if hasattr(doc, "get") else None
	if not owner:
		# an unsold serial still sitting in the plant belongs to nobody yet
		return False
	return owner in dealer_and_descendants(d.name)


def dealer_has_permission(doc, user=None, permission_type=None):
	"""The same rule `dealer_query` applies to the list, applied to one document.

	Without this, the list was scoped but a direct fetch of
	/api/resource/Dealer/<name> was not - the Dealer doctype grants the Dealer
	role read, and a document read consults has_permission, not the query
	condition. Any dealer could therefore read a competitor's GSTIN, mobile
	number and credit limit by name.

	A Service Technician is deliberately not given the blanket access
	`_doc_allowed` grants them elsewhere: they need the ticket they are working,
	not the commercial terms of the outlet that sold the pump.
	"""
	user = user or frappe.session.user
	if has_full_access(user):
		return True
	d = user_dealer(user)
	if not d:
		return False
	name = doc.get("name") if hasattr(doc, "get") else doc
	return name in dealer_and_descendants(d.name)


def service_request_has_permission(doc, user=None, permission_type=None):
	return _doc_allowed(doc, user or frappe.session.user)


def pump_registration_has_permission(doc, user=None, permission_type=None):
	return _doc_allowed(doc, user or frappe.session.user)


def warranty_claim_has_permission(doc, user=None, permission_type=None):
	return _doc_allowed(doc, user or frappe.session.user)
