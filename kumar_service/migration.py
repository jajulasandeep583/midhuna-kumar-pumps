"""Bootstrapping historical serials.

A plant that has been shipping pumps for years arrives with a spreadsheet, not
a database. This module turns that spreadsheet into Serial No records and, for
the rows that carry a sale, into submitted Pump Registrations with the warranty
already running - so a claim on a pump sold before go-live still has paperwork
behind it.

Three entry points, in the order you should use them:

    template()      download a CSV with the right columns, filled in with two
                    example rows taken from this site's own masters
    dry_run(...)    read the file back and report exactly what would happen,
                    row by row, writing nothing
    import_file()   do it - one Serial No per row, plus a registration for the
                    rows that have a sale date

Nothing here writes twice: a serial that already exists is skipped, and a
serial that already carries a submitted registration is never registered again,
so a half-finished import can simply be re-run.

Anything left over afterwards shows up in the "Stock vs Registration
Reconciliation" report as SHIPPED - NOT REGISTERED.
"""

import csv
import io

import frappe
from frappe import _
from frappe.utils import cint, cstr, getdate, nowdate

from kumar_service.utils import CH_DEALER, CH_DIRECT, qr_url_for, sale_channel_for

# One column per thing the office actually has on the old sheet. Order matters:
# the parser maps by position when a header row is missing.
COLUMNS = [
	"serial_no",
	"item_code",
	"pump_model",
	"manufacturing_date",
	"heat_no",
	"winding_batch",
	"qc_status",
	"dealer",
	"sale_date",
	"dealer_invoice_no",
	"dealer_invoice_date",
	"kumar_invoice",
	"end_customer_name",
	"end_customer_mobile",
	"application_type",
	"district",
	"state",
	"pincode",
]

REQUIRED = ("serial_no", "item_code")

# Above this, the import goes to the long queue rather than blocking a request.
QUEUE_THRESHOLD = 200

QC_VALUES = ("Pending", "Passed", "Failed", "Rework")


# --------------------------------------------------------------------- template


def _sample_masters():
	"""Fill the example rows from this site's own masters where we can, so the
	template reads as a worked example rather than as invented data."""
	model = frappe.db.get_value(
		"Pump Model", {"is_active": 1}, ["name", "item"], as_dict=True
	) or frappe._dict()
	item = model.item or frappe.db.get_value(
		"Item", {"custom_is_finished_pump": 1, "has_serial_no": 1}, "name"
	)
	dealer = frappe.db.get_value("Dealer", {"is_own_outlet": 0, "status": "Active"}, "name")
	branch = frappe.db.get_value("Dealer", {"is_own_outlet": 1, "status": "Active"}, "name")
	# A direct sale must point at a real Sales Invoice - the field is a Link.
	# Historical invoices that were never in ERPNext cannot be linked, which is
	# exactly why the example shows a live one.
	invoice = frappe.db.get_value("Sales Invoice", {"docstatus": 1}, "name")
	return frappe._dict(
		model=model.name or "KBP05SW/24",
		item=item or "KP-KBP05SW/24",
		dealer=dealer or "Your Dealer Name",
		branch=branch or dealer or "Your Branch Name",
		invoice=invoice or "SINV-0001",
	)


def template_rows():
	"""Header row plus two examples - one sold through a dealer, one sold over
	a KUMAR counter. The two need different invoice columns, which is the whole
	reason there are two of them."""
	m = _sample_masters()
	return [
		list(COLUMNS),
		[
			"KP-EXAMPLE-2024-00001", m.item, m.model, "2024-06-14", "HT-240612-003",
			"WD-240610-002", "Passed", m.dealer, "2024-07-02", "D/2024-25/118",
			"2024-07-02", "", "Ramesh Reddy", "9876543210", "Agriculture",
			"Krishna", "Andhra Pradesh", "521001",
		],
		[
			"KP-EXAMPLE-2024-00002", m.item, m.model, "2024-06-14", "HT-240612-003",
			"WD-240610-002", "Passed", m.branch, "2024-07-09", "", "",
			m.invoice, "Lakshmi Devi", "9812345678", "Domestic",
			"Guntur", "Andhra Pradesh", "522001",
		],
	]


def template_csv():
	buf = io.StringIO()
	writer = csv.writer(buf, lineterminator="\n")
	for row in template_rows():
		writer.writerow(row)
	return buf.getvalue()


@frappe.whitelist()
def template():
	"""Download the CSV template."""
	frappe.has_permission("Serial No", "create", throw=True)
	frappe.response["type"] = "csv"
	frappe.response["doctype"] = "kumar-historical-serials"
	frappe.response["result"] = template_csv()


# ----------------------------------------------------------------------- parse


def _read_file(file_url):
	doc = frappe.get_doc("File", {"file_url": file_url})
	content = doc.get_content()
	if isinstance(content, bytes):
		content = content.decode("utf-8-sig", errors="replace")
	return content


def parse(file_url=None, content=None):
	"""CSV text (or an uploaded File) to a list of dicts keyed by COLUMNS."""
	if content is None:
		content = _read_file(file_url)

	reader = csv.reader(io.StringIO(content))
	raw = [r for r in reader if any(cstr(c).strip() for c in r)]
	if not raw:
		return []

	header = [cstr(c).strip().lower().replace(" ", "_") for c in raw[0]]
	if set(header) & set(COLUMNS):
		index = {name: i for i, name in enumerate(header) if name in COLUMNS}
		body = raw[1:]
	else:
		# no header - fall back to the template's column order
		index = {name: i for i, name in enumerate(COLUMNS)}
		body = raw

	rows = []
	for line in body:
		rows.append(
			{name: cstr(line[i]).strip() if i < len(line) else "" for name, i in index.items()}
		)
	return rows


def _as_dict(row):
	"""Accept either a dict or a positional list, as the template emits."""
	if isinstance(row, dict):
		return {k: cstr(row.get(k, "")).strip() for k in COLUMNS}
	return {name: cstr(row[i]).strip() if i < len(row) else "" for i, name in enumerate(COLUMNS)}


# -------------------------------------------------------------------- validate


def _check(row):
	"""Everything wrong with one row, in the order the office would fix it."""
	problems = []

	for field in REQUIRED:
		if not row.get(field):
			problems.append(_("{0} is required").format(field))
	if problems:
		return problems

	if row["item_code"] and not frappe.db.exists("Item", row["item_code"]):
		problems.append(_("Item {0} does not exist").format(row["item_code"]))
	elif not frappe.db.get_value("Item", row["item_code"], "has_serial_no"):
		problems.append(_("Item {0} is not serialised").format(row["item_code"]))

	if row["pump_model"] and not frappe.db.exists("Pump Model", row["pump_model"]):
		problems.append(_("Pump Model {0} does not exist").format(row["pump_model"]))

	if row["dealer"] and not frappe.db.exists("Dealer", row["dealer"]):
		problems.append(_("Dealer {0} does not exist").format(row["dealer"]))

	if row["qc_status"] and row["qc_status"] not in QC_VALUES:
		problems.append(
			_("QC Status must be one of {0}").format(", ".join(QC_VALUES))
		)

	built = None
	if row["manufacturing_date"]:
		try:
			built = getdate(row["manufacturing_date"])
		except Exception:
			problems.append(_("Manufacturing date {0} is not a date").format(row["manufacturing_date"]))

	if not row["sale_date"]:
		# stock only - no registration, nothing more to check
		return problems

	try:
		sold = getdate(row["sale_date"])
	except Exception:
		problems.append(_("Sale date {0} is not a date").format(row["sale_date"]))
		return problems

	if not row["dealer"]:
		problems.append(_("A sale date needs a dealer - who sold it?"))
	if sold > getdate(nowdate()):
		problems.append(_("Sale date is in the future"))
	if built and sold < built:
		problems.append(_("Sold on {0}, before it was built on {1}").format(sold, built))

	if not row["end_customer_name"]:
		problems.append(_("Customer name is required on a sold pump"))
	mobile = row["end_customer_mobile"]
	if not mobile:
		problems.append(_("Customer mobile is required on a sold pump"))
	elif not (len(mobile) == 10 and mobile.isdigit() and mobile[0] in "6789"):
		problems.append(_("Mobile {0} must be 10 digits starting 6-9").format(mobile))

	channel = sale_channel_for(row["dealer"]) if row["dealer"] else CH_DEALER
	if channel == CH_DIRECT and not row["kumar_invoice"]:
		problems.append(_("{0} is a KUMAR outlet, so the KUMAR invoice number is required")
			.format(row["dealer"]))
	if channel == CH_DEALER and not row["dealer_invoice_no"]:
		problems.append(_("{0} is independent, so the dealer's own invoice number is required")
			.format(row["dealer"]))
	if row["kumar_invoice"] and not frappe.db.exists("Sales Invoice", row["kumar_invoice"]):
		problems.append(
			_("Sales Invoice {0} is not in ERPNext. A direct sale links to a real invoice - "
				"import the old invoices first, or route this row through the dealer channel.")
			.format(row["kumar_invoice"])
		)

	return problems


def dry_run(file_url=None, rows=None, content=None):
	"""Report what an import would do. Writes nothing."""
	if rows is None:
		rows = parse(file_url=file_url, content=content)
	rows = [_as_dict(r) for r in rows]

	report = {"rows": len(rows), "ok": 0, "errors": 0, "serials": 0,
		"registrations": 0, "skipped": 0, "problems": []}

	seen = set()
	for i, row in enumerate(rows, start=1):
		problems = _check(row)
		if row["serial_no"] in seen:
			problems.append(_("Serial {0} appears twice in this file").format(row["serial_no"]))
		seen.add(row["serial_no"])

		if problems:
			report["errors"] = report["errors"] + 1
			report["problems"].append({"row": i, "serial_no": row["serial_no"],
				"problems": problems})
			continue

		report["ok"] = report["ok"] + 1
		if frappe.db.exists("Serial No", row["serial_no"]):
			report["skipped"] = report["skipped"] + 1
		else:
			report["serials"] = report["serials"] + 1
		if row["sale_date"] and not frappe.db.exists(
			"Pump Registration", {"serial_no": row["serial_no"], "docstatus": 1}
		):
			report["registrations"] = report["registrations"] + 1

	return report


# ---------------------------------------------------------------------- import


def _make_serial(row):
	if frappe.db.exists("Serial No", row["serial_no"]):
		return False

	doc = frappe.get_doc(
		{
			"doctype": "Serial No",
			"serial_no": row["serial_no"],
			"item_code": row["item_code"],
			"company": frappe.defaults.get_defaults().get("company"),
			"custom_pump_model": row["pump_model"] or None,
			"custom_manufacturing_date": getdate(row["manufacturing_date"])
				if row["manufacturing_date"] else None,
			"custom_heat_no": row["heat_no"] or None,
			"custom_winding_batch": row["winding_batch"] or None,
			"custom_qc_status": row["qc_status"] or "Passed",
			"custom_qr_url": qr_url_for(row["serial_no"]),
			"custom_warranty_status": "Not Registered",
		}
	)
	doc.flags.ignore_permissions = True
	doc.insert(ignore_permissions=True)
	return True


def _make_registration(row):
	if not row["sale_date"]:
		return False
	if frappe.db.exists("Pump Registration", {"serial_no": row["serial_no"], "docstatus": 1}):
		return False

	channel = sale_channel_for(row["dealer"])
	doc = frappe.get_doc(
		{
			"doctype": "Pump Registration",
			"serial_no": row["serial_no"],
			"dealer": row["dealer"],
			"sale_channel": channel,
			"sale_date": getdate(row["sale_date"]),
			"invoice_no": row["dealer_invoice_no"] or None,
			"dealer_invoice_date": getdate(row["dealer_invoice_date"])
				if row["dealer_invoice_date"] else None,
			"sales_invoice": row["kumar_invoice"] or None,
			# a historical row is not a dealer typing into the portal, so the
			# backdating limit must not apply to it
			"registration_source": "Bulk Import",
			"end_customer_name": row["end_customer_name"],
			"end_customer_mobile": row["end_customer_mobile"],
			"application_type": row["application_type"] or "Agriculture",
			"district": row["district"] or None,
			"state": row["state"] or None,
			"pincode": row["pincode"] or None,
		}
	)
	doc.flags.ignore_permissions = True
	doc.insert(ignore_permissions=True)
	doc.submit()
	return True


def run_import(rows, log_name=None):
	"""The worker. Each row is its own transaction-ish unit: one bad row is
	recorded and skipped rather than taking the other 4,999 down with it."""
	rows = [_as_dict(r) for r in rows]
	result = {"rows": len(rows), "serials": 0, "registrations": 0,
		"skipped": 0, "failed": 0, "problems": []}

	for i, row in enumerate(rows, start=1):
		problems = _check(row)
		if problems:
			result["failed"] = result["failed"] + 1
			result["problems"].append({"row": i, "serial_no": row["serial_no"],
				"problems": problems})
			continue

		savepoint = f"kt_import_{i}"
		frappe.db.savepoint(savepoint)
		try:
			made = _make_serial(row)
			result["serials"] = result["serials"] + (1 if made else 0)
			result["skipped"] = result["skipped"] + (0 if made else 1)
			if _make_registration(row):
				result["registrations"] = result["registrations"] + 1
		except Exception as e:  # noqa: BLE001
			frappe.db.rollback(save_point=savepoint)
			result["failed"] = result["failed"] + 1
			result["problems"].append({"row": i, "serial_no": row["serial_no"],
				"problems": [cstr(e)[:200]]})

	frappe.db.commit()

	if log_name:
		frappe.publish_realtime(
			"kumar_historical_import_done", result, user=frappe.session.user
		)
	return result


def _import_from_file(file_url):
	return run_import(parse(file_url=file_url), log_name=file_url)


@frappe.whitelist()
def import_file(file_url, dry=1):
	"""Entry point for the desk. `dry=1` reports, `dry=0` writes."""
	frappe.has_permission("Serial No", "create", throw=True)
	frappe.has_permission("Pump Registration", "create", throw=True)

	rows = parse(file_url=file_url)
	if cint(dry):
		return dry_run(rows=rows)

	if len(rows) > QUEUE_THRESHOLD:
		frappe.enqueue(
			"kumar_service.migration._import_from_file",
			queue="long",
			timeout=3600,
			file_url=file_url,
		)
		return {"queued": True, "rows": len(rows)}

	return run_import(rows)


@frappe.whitelist()
def unregistered_after_import():
	"""The short version of the reconciliation report, for a quick check
	straight after an import."""
	frappe.has_permission("Serial No", "read", throw=True)
	shipped = frappe.db.count(
		"Serial No", {"custom_registration": ["is", "not set"], "warehouse": ["is", "not set"]}
	)
	in_stock = frappe.db.count(
		"Serial No", {"custom_registration": ["is", "not set"], "warehouse": ["is", "set"]}
	)
	return {
		"shipped_not_registered": shipped,
		"in_stock_not_sold": in_stock,
		"report": "/app/query-report/Stock vs Registration Reconciliation",
	}
