"""Small helpers shared by every setup module.

Everything here is idempotent: setup can be re-run on a live site without
duplicating records or losing edits made in the UI.
"""

import frappe

MODULE = "Kumar Service"


def f(fieldname, label, fieldtype="Data", **kw):
	"""Build a docfield dict without the boilerplate."""
	d = {"fieldname": fieldname, "label": label, "fieldtype": fieldtype}
	d.update(kw)
	return d


def section(fieldname, label=""):
	return {"fieldname": fieldname, "label": label, "fieldtype": "Section Break"}


def column(fieldname):
	return {"fieldname": fieldname, "fieldtype": "Column Break"}


def make_doctype(
	name,
	fields,
	*,
	autoname=None,
	naming_rule=None,
	is_submittable=0,
	istable=0,
	issingle=0,
	is_tree=0,
	nsm_parent_field=None,
	title_field=None,
	search_fields=None,
	sort_field="modified",
	sort_order="DESC",
	permissions=None,
	track_changes=1,
	description=None,
):
	"""Create or update a DocType. Existing fields are replaced, data is kept."""
	exists = frappe.db.exists("DocType", name)
	doc = frappe.get_doc("DocType", name) if exists else frappe.new_doc("DocType")

	doc.update(
		{
			"doctype": "DocType",
			"name": name,
			"module": MODULE,
			"custom": 0,
			"is_submittable": is_submittable,
			"istable": istable,
			"issingle": issingle,
			"is_tree": is_tree,
			"track_changes": track_changes,
			"sort_field": sort_field,
			"sort_order": sort_order,
			"description": description,
		}
	)
	if is_tree:
		doc.nsm_parent_field = nsm_parent_field or f"parent_{frappe.scrub(name)}"
	if autoname:
		doc.autoname = autoname
	if naming_rule:
		doc.naming_rule = naming_rule
	if title_field:
		doc.title_field = title_field
	if search_fields:
		doc.search_fields = search_fields

	doc.set("fields", [])
	for idx, fld in enumerate(fields, start=1):
		fld = dict(fld)
		fld["idx"] = idx
		doc.append("fields", fld)

	if not istable:
		doc.set("permissions", [])
		for p in permissions or default_permissions():
			p = dict(p)
			if not is_submittable:
				# frappe rejects submit/cancel/amend rights on a non-submittable DocType
				for key in ("submit", "cancel", "amend"):
					p.pop(key, None)
			doc.append("permissions", p)

	doc.flags.ignore_permissions = True
	doc.flags.ignore_version = True
	if exists:
		doc.save(ignore_permissions=True)
	else:
		doc.insert(ignore_permissions=True)
	return doc


def perm(role, level=0, **kw):
	p = {
		"role": role,
		"permlevel": level,
		"read": 1,
		"write": 1,
		"create": 1,
		"delete": 0,
		"submit": 0,
		"cancel": 0,
		"amend": 0,
		"report": 1,
		"export": 1,
		"share": 1,
		"print": 1,
		"email": 1,
	}
	p.update(kw)
	return p


def default_permissions():
	return [perm("System Manager", delete=1, submit=1, cancel=1, amend=1)]


def ensure_role(role_name, desk_access=1):
	if not frappe.db.exists("Role", role_name):
		frappe.get_doc(
			{"doctype": "Role", "role_name": role_name, "desk_access": desk_access}
		).insert(ignore_permissions=True)
	return role_name


def upsert(doctype, filters, values, *, submit=False):
	"""Create a doc if absent, otherwise leave it alone. Returns the name."""
	existing = frappe.db.exists(doctype, filters)
	if existing:
		return existing
	doc = frappe.get_doc({"doctype": doctype, **values})
	doc.flags.ignore_permissions = True
	doc.flags.ignore_mandatory = True
	doc.insert(ignore_permissions=True)
	if submit and doc.meta.is_submittable:
		doc.submit()
	return doc.name
