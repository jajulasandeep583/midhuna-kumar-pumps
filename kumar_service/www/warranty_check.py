"""Public warranty check.

Deliberately thin: model, HP, warranty status and expiry. Never the dealer, the
customer, the price or the genealogy. Rate limited because it is unauthenticated.
"""

import frappe
from frappe import _

no_cache = 1

RATE_LIMIT_PER_MINUTE = 10


def get_context(context):
	from kumar_service.i18n import apply_language

	context.no_cache = 1
	# language first: the title and every message below is translated
	apply_language(context)
	context.title = _("KUMAR Pumps - Warranty Check")
	context.result = None
	context.error = None

	serial_no = (frappe.form_dict.get("sn") or "").strip()
	context.serial_no = serial_no

	if not serial_no:
		return context

	if _rate_limited():
		context.error = _("Too many lookups from this address. Please wait a minute and try again.")
		return context

	from kumar_service.warranty import check_warranty

	data = check_warranty(serial_no)
	if not data.get("found"):
		context.error = _("No pump found with serial number {0}. Check the nameplate and try again.").format(
			serial_no
		)
		return context

	context.result = data
	return context


def _rate_limited():
	ip = frappe.local.request_ip or "unknown"
	key = f"kumar-warranty-check:{ip}"
	cache = frappe.cache()
	hits = cache.get_value(key) or 0
	if int(hits) >= RATE_LIMIT_PER_MINUTE:
		return True
	cache.set_value(key, int(hits) + 1, expires_in_sec=60)
	return False
