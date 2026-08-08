import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import now_datetime

from kumar_service.tests import fixtures

IGNORE_TEST_RECORD_DEPENDENCIES = fixtures.LINK_DEPENDENCIES


def _certificate(serial=None, submit=False, **overrides):
	values = {
		"doctype": "Pump Test Certificate",
		"serial_no": serial or fixtures.serial_no(qc_status="Pending"),
		"test_date": now_datetime(),
		"supply_voltage_v": 415,
		"frequency_hz": 50,
		"no_load_current_a": 3.1,
		"full_load_current_a": 7.4,
		"insulation_resistance_mohm": 200,
		"hipot_voltage_kv": 1.8,
		"hipot_result": "Pass",
		"hydrostatic_result": "Pass",
		"overall_result": "Pass",
		"duty_points": [
			{"head_m": 20, "discharge_lpm": 1100, "efficiency_pct": 48, "is_duty_point": 0},
			{"head_m": 30, "discharge_lpm": 900, "efficiency_pct": 52, "is_duty_point": 1},
		],
	}
	values.update(overrides)
	doc = frappe.get_doc(values)
	doc.flags.ignore_permissions = True
	doc.insert(ignore_permissions=True)
	if submit:
		doc.submit()
	return doc


class TestPumpTestCertificate(IntegrationTestCase):
	def test_create_pulls_the_model_and_its_standard(self):
		cert = _certificate()
		self.assertEqual(cert.pump_model, fixtures.MODEL)
		self.assertEqual(cert.bis_standard_ref, "IS 8034")
		self.assertEqual(len(cert.duty_points), 2)

	def test_validate_failure_passing_a_unit_that_failed_a_sub_test(self):
		"""A pump that failed HiPot cannot leave with a pass certificate."""
		with self.assertRaises(frappe.ValidationError) as caught:
			_certificate(hipot_result="Fail", overall_result="Pass")
		self.assertIn("HiPot", str(caught.exception))

	def test_validate_failure_on_a_failed_hydrostatic_test(self):
		with self.assertRaises(frappe.ValidationError) as caught:
			_certificate(hydrostatic_result="Fail", overall_result="Pass")
		self.assertIn("Hydrostatic", str(caught.exception))

	def test_a_failed_sub_test_is_fine_on_a_failed_certificate(self):
		cert = _certificate(hipot_result="Fail", overall_result="Fail")
		self.assertEqual(cert.overall_result, "Fail")

	def test_validate_failure_without_a_serial(self):
		"""The controller reaches for the serial before frappe's own mandatory
		pass runs, so this comes back as a plain ValidationError."""
		doc = frappe.get_doc(
			{"doctype": "Pump Test Certificate", "test_date": now_datetime(), "overall_result": "Pass"}
		)
		self.assertRaises(frappe.ValidationError, doc.insert)

	def test_submit_stamps_qc_onto_the_serial(self):
		serial = fixtures.serial_no(qc_status="Pending")
		cert = _certificate(serial=serial, submit=True)

		stamped = frappe.db.get_value(
			"Serial No", serial, ["custom_test_certificate", "custom_qc_status"], as_dict=True
		)
		self.assertEqual(cert.docstatus, 1)
		self.assertEqual(stamped.custom_test_certificate, cert.name)
		self.assertEqual(stamped.custom_qc_status, "Passed")

	def test_a_failed_test_leaves_the_serial_marked_failed(self):
		serial = fixtures.serial_no(qc_status="Pending")
		_certificate(serial=serial, hipot_result="Fail", overall_result="Fail", submit=True)
		self.assertEqual(
			frappe.db.get_value("Serial No", serial, "custom_qc_status"), "Failed"
		)

	def test_a_rework_result_holds_the_serial_in_rework(self):
		serial = fixtures.serial_no(qc_status="Pending")
		_certificate(serial=serial, overall_result="Rework", submit=True)
		self.assertEqual(
			frappe.db.get_value("Serial No", serial, "custom_qc_status"), "Rework"
		)

	def test_cancel_takes_the_qc_stamp_back_off(self):
		serial = fixtures.serial_no(qc_status="Pending")
		cert = _certificate(serial=serial, submit=True)
		cert.cancel()

		stamped = frappe.db.get_value(
			"Serial No", serial, ["custom_test_certificate", "custom_qc_status"], as_dict=True
		)
		self.assertEqual(cert.docstatus, 2)
		self.assertIsNone(stamped.custom_test_certificate)
		self.assertEqual(stamped.custom_qc_status, "Pending")

	def test_permission_denied_for_a_user_without_roles(self):
		outsider = fixtures.outsider()
		self.assertFalse(frappe.has_permission("Pump Test Certificate", "read", user=outsider))
		self.assertFalse(frappe.has_permission("Pump Test Certificate", "create", user=outsider))

	def test_a_dealer_may_show_a_certificate_but_never_issue_one(self):
		_dealer, email = fixtures.dealer_login()
		self.assertTrue(frappe.has_permission("Pump Test Certificate", "read", user=email))
		self.assertFalse(frappe.has_permission("Pump Test Certificate", "create", user=email))
		self.assertFalse(frappe.has_permission("Pump Test Certificate", "submit", user=email))
