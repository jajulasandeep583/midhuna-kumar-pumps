"""Database indexes for the columns this app actually filters on.

Every one of these is a column that a screen, a report or the nightly scheduler
scans across the whole table:

  Serial No.custom_warranty_expiry_date  - "Warranty Expiring Soon", the daily
                                           status sweep and the reminder job
  Serial No.custom_dealer                - dealer row-level isolation, which is
                                           applied to *every* dealer query
  Serial No.custom_heat_no               - forward trace from a heat
  Serial No.custom_winding_batch         - forward trace from a winding batch
  Service Request.serial_no              - backward trace and repeat-failure
  Service Request.reported_on            - every dated report and SLA sweep
  Service Request.status                 - the service queue itself

`frappe.db.add_index` is idempotent and also writes a Property Setter, so a
later `bench migrate` will not quietly drop what it did not create.
"""

import frappe

INDEXES = (
	("Serial No", ["custom_warranty_expiry_date"]),
	("Serial No", ["custom_dealer"]),
	("Serial No", ["custom_heat_no"]),
	("Serial No", ["custom_winding_batch"]),
	("Service Request", ["serial_no"]),
	("Service Request", ["reported_on"]),
	("Service Request", ["status"]),
)


def index_name(fields):
	return frappe.db.get_index_name(fields)


def exists(doctype, fields):
	from frappe.utils import get_table_name

	return bool(frappe.db.has_index(get_table_name(doctype), index_name(fields)))


def missing():
	"""The indexes that are not on the table yet."""
	return [(dt, fields) for dt, fields in INDEXES if not exists(dt, fields)]


def build_all(verbose=False):
	made = []
	for doctype, fields in INDEXES:
		if not frappe.db.exists("DocType", doctype):
			continue
		if exists(doctype, fields):
			continue
		try:
			frappe.db.add_index(doctype, fields)
			made.append(f"{doctype}.{'+'.join(fields)}")
		except Exception as e:
			# an index is an optimisation, never a reason to abort a migrate
			print(f"! could not index {doctype}.{fields}: {e}")

	if verbose or made:
		print(f"indexes created: {made or 'none needed'}")
	return made
