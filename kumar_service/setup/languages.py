"""Make Telugu selectable on this site.

The app ships ``kumar_service/translations/te.csv``, but shipping the strings is
only half of it: frappe hides a Language whose ``enabled`` flag is 0 from the
System Settings dropdown, the User form and the print view's language selector,
so nobody could ever pick Telugu even though every string was translated. The
``te`` Language record exists on a fresh site - it just arrives disabled.
"""

import frappe

LANGUAGES = ("te",)


def build_all():
	for code in LANGUAGES:
		if not frappe.db.exists("Language", code):
			# A site whose Language fixtures were never loaded.
			doc = frappe.new_doc("Language")
			doc.update({"language_code": code, "language_name": "తెలుగు", "enabled": 1})
			doc.insert(ignore_permissions=True)
			continue

		if not frappe.db.get_value("Language", code, "enabled"):
			frappe.db.set_value("Language", code, "enabled", 1)

	# The merged translation dict is cached per language; a freshly shipped or
	# edited te.csv is invisible until that cache is dropped.
	frappe.cache.delete_key("merged_translations")
	frappe.cache.delete_key("lang_full_dict")
