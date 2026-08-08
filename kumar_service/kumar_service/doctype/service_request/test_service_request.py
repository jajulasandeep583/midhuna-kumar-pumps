import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_to_date, get_datetime, now_datetime

from kumar_service.tests import fixtures

IGNORE_TEST_RECORD_DEPENDENCIES = fixtures.LINK_DEPENDENCIES


class TestServiceRequest(IntegrationTestCase):
	def test_create_pulls_the_whole_pump_off_the_serial(self):
		"""One serial in, and the technician has the pump's identity without
		typing anything - that is the point of the form."""
		reg = fixtures.registration(submit=True)
		request = fixtures.service_request(serial=reg.serial_no)

		self.assertEqual(request.pump_model, fixtures.MODEL)
		self.assertEqual(request.hp, 5.0)
		self.assertEqual(request.phase, "Three Phase")
		self.assertEqual(request.dealer, reg.dealer)
		self.assertEqual(request.end_customer_name, "_KT Customer")
		self.assertEqual(request.end_customer_mobile, "9812345678")
		self.assertEqual(
			get_datetime(request.warranty_expiry_date), get_datetime(reg.warranty_expiry_date)
		)
		self.assertTrue(request.is_under_warranty)

	def test_an_unregistered_pump_is_not_under_warranty(self):
		request = fixtures.service_request()
		self.assertFalse(request.is_under_warranty)

	def test_validate_failure_without_a_complaint(self):
		doc = frappe.get_doc(
			{
				"doctype": "Service Request",
				"serial_no": fixtures.serial_no(),
				"complaint_category": "Leakage",
			}
		)
		self.assertRaises(frappe.MandatoryError, doc.insert)

	def test_validate_failure_on_an_unknown_serial(self):
		doc = frappe.get_doc(
			{
				"doctype": "Service Request",
				"serial_no": "_KT-SN-DOES-NOT-EXIST",
				"complaint_category": "Leakage",
				"complaint_description": "x",
			}
		)
		self.assertRaises(
			(frappe.LinkValidationError, frappe.ValidationError), doc.insert
		)

	def test_sla_clocks_come_from_settings(self):
		with self.change_settings(
			"Kumar Service Settings", sla_response_hours=4, sla_resolution_hours=12
		):
			request = fixtures.service_request()

		self.assertEqual(
			get_datetime(request.response_due_on),
			get_datetime(add_to_date(get_datetime(request.reported_on), hours=4)),
		)
		self.assertEqual(
			get_datetime(request.resolution_due_on),
			get_datetime(add_to_date(get_datetime(request.reported_on), hours=12)),
		)
		self.assertEqual(request.sla_status, "Ongoing")

	def test_resolving_inside_the_window_fulfils_the_sla(self):
		request = fixtures.service_request()
		request.status = "Resolved"
		request.resolved_on = now_datetime()
		request.save(ignore_permissions=True)
		self.assertEqual(request.sla_status, "Fulfilled")

	def test_resolving_late_fails_the_sla(self):
		request = fixtures.service_request(reported_on=add_to_date(now_datetime(), days=-10))
		request.status = "Resolved"
		request.resolved_on = now_datetime()
		request.save(ignore_permissions=True)
		self.assertEqual(request.sla_status, "Failed")

	def test_a_second_complaint_on_the_same_pump_is_flagged_as_a_repeat(self):
		"""A repeat failure inside the window is the signal that a batch, not a
		unit, has gone wrong."""
		serial = fixtures.serial_no()
		first = fixtures.service_request(serial=serial)
		second = fixtures.service_request(serial=serial)

		self.assertFalse(first.is_repeat_failure)
		self.assertTrue(second.is_repeat_failure)

	def test_assigning_a_technician_moves_it_out_of_open(self):
		request = fixtures.service_request(assigned_technician=fixtures.technician())
		self.assertEqual(request.status, "Assigned")
		self.assertEqual(request.service_centre, fixtures.DEALER_INDEPENDENT)

	def test_submit_and_cancel(self):
		request = fixtures.service_request(submit=True)
		self.assertEqual(request.docstatus, 1)
		request.cancel()
		self.assertEqual(request.docstatus, 2)

	def test_submitting_notifies_the_assigned_technician(self):
		email = fixtures.user("_kt.tech@kumartest.local", roles=["Service Technician"])
		technician = frappe.get_doc("Service Technician", fixtures.technician())
		technician.user = email
		technician.save(ignore_permissions=True)

		request = fixtures.service_request(assigned_technician=technician.name, submit=True)

		self.assertTrue(
			frappe.db.exists(
				"Notification Log",
				{"document_type": "Service Request", "document_name": request.name, "for_user": email},
			)
		)

	def test_permission_denied_across_dealers(self):
		mine, my_email = fixtures.dealer_login()
		theirs, _ = fixtures.rival_login()

		my_reg = fixtures.registration(dealer_name=mine, submit=True)
		their_reg = fixtures.registration(dealer_name=theirs, submit=True)
		my_request = fixtures.service_request(serial=my_reg.serial_no, submit=True)
		their_request = fixtures.service_request(serial=their_reg.serial_no, submit=True)

		self.assertTrue(frappe.has_permission("Service Request", doc=my_request, user=my_email))
		self.assertFalse(frappe.has_permission("Service Request", doc=their_request, user=my_email))

		with self.set_user(my_email):
			visible = frappe.get_list("Service Request", pluck="name", limit_page_length=0)
		self.assertIn(my_request.name, visible)
		self.assertNotIn(their_request.name, visible)

	def test_permission_denied_for_a_user_without_roles(self):
		outsider = fixtures.outsider()
		self.assertFalse(frappe.has_permission("Service Request", "read", user=outsider))
		self.assertFalse(frappe.has_permission("Service Request", "create", user=outsider))
