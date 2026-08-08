"""Bootstrapping historical serials.

The import writes submitted registrations, so the interesting cases are the
ones where it must refuse: a sale before the pump was built, a mobile number
that is not one, the wrong invoice for the channel. Each of those is a warranty
date somebody would otherwise have to unpick by hand later.
"""

import csv
import io

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, getdate, nowdate

from kumar_service import migration
from kumar_service.tests import fixtures
from kumar_service.utils import CH_DEALER


def _csv(rows, header=True):
	buf = io.StringIO()
	writer = csv.writer(buf, lineterminator="\n")
	if header:
		writer.writerow(migration.COLUMNS)
	for row in rows:
		writer.writerow(row)
	return buf.getvalue()


def _upload(content):
	"""Put a CSV where the importer expects to find one."""
	doc = frappe.get_doc(
		{
			"doctype": "File",
			"file_name": f"_kt-historical-{frappe.generate_hash(length=6)}.csv",
			"content": content,
			"is_private": 1,
		}
	)
	doc.flags.ignore_permissions = True
	doc.insert(ignore_permissions=True)
	return doc.file_url


def _row(**overrides):
	values = {
		"serial_no": f"_KT-HIST-{frappe.generate_hash(length=6).upper()}",
		"item_code": fixtures.pump_item(),
		"pump_model": fixtures.pump_model(),
		"manufacturing_date": add_days(nowdate(), -400),
		"qc_status": "Passed",
		"dealer": fixtures.dealer(),
		"sale_date": add_days(nowdate(), -300),
		"dealer_invoice_no": "D/2023-24/091",
		"dealer_invoice_date": add_days(nowdate(), -300),
		"end_customer_name": "_KT Historical Customer",
		"end_customer_mobile": "9812345678",
		"application_type": "Agriculture",
		"district": "Krishna",
		"state": "Andhra Pradesh",
		"pincode": "521001",
	}
	values.update(overrides)
	return [str(values.get(c, "") or "") for c in migration.COLUMNS]


class TestHistoricalImport(IntegrationTestCase):
	@classmethod
	def tearDownClass(cls):
		# the importer commits by design, so the class rollback cannot undo it
		fixtures.purge()
		super().tearDownClass()

	def test_the_template_has_a_column_for_everything_the_parser_reads(self):
		rows = migration.template_rows()
		self.assertEqual(rows[0], migration.COLUMNS)
		self.assertGreater(len(rows), 1)

	def test_the_template_is_valid_csv_and_parses_back_to_itself(self):
		parsed = migration.parse(content=migration.template_csv())
		self.assertEqual(len(parsed), len(migration.template_rows()) - 1)
		self.assertEqual(
			parsed[0]["serial_no"], migration.template_rows()[1][0]
		)

	def test_a_file_without_a_header_falls_back_to_the_template_order(self):
		row = _row()
		parsed = migration.parse(content=_csv([row], header=False))
		self.assertEqual(len(parsed), 1)
		self.assertEqual(parsed[0]["serial_no"], row[0])
		self.assertEqual(parsed[0]["end_customer_mobile"], "9812345678")

	def test_dry_run_writes_nothing(self):
		row = _row()
		report = migration.dry_run(content=_csv([row]))

		self.assertEqual(report["rows"], 1)
		self.assertEqual(report["errors"], 0)
		self.assertEqual(report["serials"], 1)
		self.assertEqual(report["registrations"], 1)
		self.assertFalse(frappe.db.exists("Serial No", row[0]))

	def test_import_creates_the_serial_and_starts_the_warranty(self):
		row = _row()
		result = migration.run_import(migration.parse(content=_csv([row])))

		self.assertEqual(result["serials"], 1)
		self.assertEqual(result["registrations"], 1)
		self.assertEqual(result["failed"], 0)

		serial = frappe.db.get_value(
			"Serial No",
			row[0],
			["custom_pump_model", "custom_registration", "custom_warranty_status",
			 "custom_warranty_expiry_date", "custom_dealer"],
			as_dict=True,
		)
		self.assertEqual(serial.custom_pump_model, fixtures.MODEL)
		self.assertEqual(serial.custom_dealer, fixtures.DEALER_INDEPENDENT)
		self.assertTrue(serial.custom_registration)
		# sold 300 days ago with 18 months of cover, so it is still live
		self.assertEqual(serial.custom_warranty_status, "In Warranty")

		reg = frappe.get_doc("Pump Registration", serial.custom_registration)
		self.assertEqual(reg.docstatus, 1)
		self.assertEqual(reg.registration_source, "Bulk Import")
		self.assertEqual(reg.sale_channel, CH_DEALER)
		self.assertEqual(
			getdate(reg.warranty_start_date), getdate(add_days(nowdate(), -300))
		)

	def test_a_row_with_no_sale_date_is_stock_only(self):
		row = _row(sale_date="", dealer_invoice_no="", dealer_invoice_date="",
			end_customer_name="", end_customer_mobile="")
		result = migration.run_import(migration.parse(content=_csv([row])))

		self.assertEqual(result["serials"], 1)
		self.assertEqual(result["registrations"], 0)
		self.assertIsNone(frappe.db.get_value("Serial No", row[0], "custom_registration"))

	def test_running_the_same_file_twice_changes_nothing(self):
		"""A half-finished import has to be safe to re-run."""
		row = _row()
		first = migration.run_import(migration.parse(content=_csv([row])))
		second = migration.run_import(migration.parse(content=_csv([row])))

		self.assertEqual(first["serials"], 1)
		self.assertEqual(second["serials"], 0)
		self.assertEqual(second["skipped"], 1)
		self.assertEqual(second["registrations"], 0)
		self.assertEqual(
			frappe.db.count("Pump Registration", {"serial_no": row[0], "docstatus": 1}), 1
		)

	def test_a_sale_before_the_pump_was_built_is_refused(self):
		row = _row(
			manufacturing_date=add_days(nowdate(), -100),
			sale_date=add_days(nowdate(), -300),
		)
		report = migration.dry_run(content=_csv([row]))
		self.assertEqual(report["errors"], 1)
		self.assertIn("before it was built", str(report["problems"]))

	def test_a_bad_mobile_number_is_refused(self):
		report = migration.dry_run(content=_csv([_row(end_customer_mobile="12345")]))
		self.assertEqual(report["errors"], 1)
		self.assertIn("10 digits", str(report["problems"]))

	def test_an_independent_dealer_needs_its_own_invoice_number(self):
		report = migration.dry_run(content=_csv([_row(dealer_invoice_no="")]))
		self.assertEqual(report["errors"], 1)
		self.assertIn("independent", str(report["problems"]))

	def test_a_kumar_branch_needs_a_real_kumar_invoice(self):
		branch = fixtures.dealer(fixtures.DEALER_OWN, is_own_outlet=1)
		report = migration.dry_run(
			content=_csv([_row(dealer=branch, dealer_invoice_no="", kumar_invoice="")])
		)
		self.assertEqual(report["errors"], 1)
		self.assertIn("KUMAR invoice number is required", str(report["problems"]))

		report = migration.dry_run(
			content=_csv([_row(dealer=branch, dealer_invoice_no="",
				kumar_invoice="_KT-SINV-NOT-IN-ERPNEXT")])
		)
		self.assertEqual(report["errors"], 1)
		self.assertIn("not in ERPNext", str(report["problems"]))

	def test_unknown_masters_are_refused(self):
		report = migration.dry_run(content=_csv([_row(item_code="_KT-NO-SUCH-ITEM")]))
		self.assertEqual(report["errors"], 1)
		self.assertIn("does not exist", str(report["problems"]))

		report = migration.dry_run(content=_csv([_row(dealer="_KT No Such Dealer")]))
		self.assertEqual(report["errors"], 1)

	def test_the_same_serial_twice_in_one_file_is_caught(self):
		row = _row()
		report = migration.dry_run(content=_csv([row, list(row)]))
		self.assertEqual(report["errors"], 1)
		self.assertIn("appears twice", str(report["problems"]))

	def test_one_bad_row_does_not_take_the_good_ones_down_with_it(self):
		good_a, bad, good_b = _row(), _row(end_customer_mobile="nope"), _row()
		result = migration.run_import(migration.parse(content=_csv([good_a, bad, good_b])))

		self.assertEqual(result["serials"], 2)
		self.assertEqual(result["failed"], 1)
		self.assertTrue(frappe.db.exists("Serial No", good_a[0]))
		self.assertTrue(frappe.db.exists("Serial No", good_b[0]))
		self.assertFalse(frappe.db.exists("Serial No", bad[0]))

	def test_a_small_file_is_imported_in_the_request(self):
		rows = [_row(), _row()]
		result = migration.import_file(_upload(_csv(rows)), dry=0)

		self.assertNotIn("queued", result)
		self.assertEqual(result["serials"], 2)

	def test_a_big_file_goes_to_the_queue_rather_than_blocking(self):
		"""A five-thousand-row sheet must not be written inside a web request."""
		original = migration.QUEUE_THRESHOLD
		rows = [_row(), _row()]
		file_url = _upload(_csv(rows))
		try:
			migration.QUEUE_THRESHOLD = 1
			result = migration.import_file(file_url, dry=0)
		finally:
			migration.QUEUE_THRESHOLD = original

		self.assertTrue(result["queued"])
		self.assertEqual(result["rows"], 2)

		# and the job the queue was handed does the work when it runs
		done = migration._import_from_file(file_url)
		self.assertEqual(done["serials"], 2)
		self.assertTrue(frappe.db.exists("Serial No", rows[0][0]))

	def test_a_dry_run_through_the_endpoint_still_writes_nothing(self):
		rows = [_row()]
		result = migration.import_file(_upload(_csv(rows)), dry=1)

		self.assertEqual(result["errors"], 0)
		self.assertEqual(result["serials"], 1)
		self.assertFalse(frappe.db.exists("Serial No", rows[0][0]))

	def test_imported_stock_shows_up_in_the_reconciliation_report(self):
		"""Whatever the import could not place has to be visible afterwards."""
		row = _row(sale_date="", dealer_invoice_no="", dealer_invoice_date="",
			end_customer_name="", end_customer_mobile="")
		migration.run_import(migration.parse(content=_csv([row])))

		from frappe.desk.query_report import run

		result = run(
			"Stock vs Registration Reconciliation",
			filters={"verdict": "No stock record at all"},
			ignore_prepared_report=True,
		)
		serials = [r["serial_no"] for r in result["result"]]
		self.assertIn(row[0], serials)

	def test_the_import_endpoints_check_permissions(self):
		outsider = fixtures.outsider()
		with self.set_user(outsider):
			self.assertRaises(
				frappe.PermissionError, migration.import_file, file_url="/files/nope.csv"
			)
			self.assertRaises(frappe.PermissionError, migration.unregistered_after_import)

	def test_the_summary_counts_both_kinds_of_loose_end(self):
		summary = migration.unregistered_after_import()
		self.assertIn("shipped_not_registered", summary)
		self.assertIn("in_stock_not_sold", summary)
		self.assertIn("Reconciliation", summary["report"])
