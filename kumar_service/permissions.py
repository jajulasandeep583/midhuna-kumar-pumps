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


def service_request_has_permission(doc, user=None, permission_type=None):
	return _doc_allowed(doc, user or frappe.session.user)


def pump_registration_has_permission(doc, user=None, permission_type=None):
	return _doc_allowed(doc, user or frappe.session.user)


def warranty_claim_has_permission(doc, user=None, permission_type=None):
	return _doc_allowed(doc, user or frappe.session.user)
