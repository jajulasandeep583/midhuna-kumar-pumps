import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import nowdate

from kumar_service.tests import fixtures

IGNORE_TEST_RECORD_DEPENDENCIES = fixtures.LINK_DEPENDENCIES


def _visit(request, submit=False, **overrides):
	values = {
		"doctype": "Service Visit",
		"service_request": request.name,
		"technician": fixtures.technician(),
		"visit_date": nowdate(),
		"visit_type": "On-Site",
		"findings": "Impeller choked with sand.",
		"action_taken": "Cleaned and refitted.",
	}
	values.update(overrides)
	doc = frappe.get_doc(values)
	doc.flags.ignore_permissions = True
	doc.insert(ignore_permissions=True)
	if submit:
		doc.submit()
	return doc


class TestServiceVisit(IntegrationTestCase):
	def test_create_pulls_the_serial_off_the_request(self):
		request = fixtures.service_request(submit=True)
		visit = _visit(request)

		self.assertEqual(visit.serial_no, request.serial_no)
		self.assertEqual(visit.technician, fixtures.TECHNICIAN)

	def test_validate_failure_without_a_technician(self):
		request = fixtures.service_request(submit=True)
		doc = frappe.get_doc(
			{
				"doctype": "Service Visit",
				"service_request": request.name,
				"visit_date": nowdate(),
			}
		)
		self.assertRaises(frappe.MandatoryError, doc.insert)

	def test_a_warranty_replacement_is_never_billed(self):
		"""The customer pays for the parts they consumed, not for our defect."""
		request = fixtures.service_request(submit=True)
		visit = _visit(
			request,
			is_chargeable=1,
			labour_charge=300,
			parts_used=[
				{"item_code": fixtures.spare_item(), "qty": 2, "rate": 100},
				{
					"item_code": fixtures.spare_item(),
					"qty": 1,
					"rate": 500,
					"is_warranty_replacement": 1,
				},
			],
		)

		self.assertEqual(visit.parts_used[0].amount, 200)
		self.assertEqual(visit.parts_used[1].amount, 500)
		self.assertEqual(visit.total_parts_value, 200)
		self.assertEqual(visit.grand_total, 500)  # 200 parts + 300 labour

	def test_a_non_chargeable_visit_totals_nothing(self):
		request = fixtures.service_request(submit=True)
		visit = _visit(
			request,
			is_chargeable=0,
			labour_charge=300,
			parts_used=[{"item_code": fixtures.spare_item(), "qty": 1, "rate": 100}],
		)
		self.assertEqual(visit.grand_total, 0)

	def test_part_rows_fill_in_their_own_name_and_uom(self):
		request = fixtures.service_request(submit=True)
		visit = _visit(
			request, parts_used=[{"item_code": fixtures.spare_item(), "qty": 1, "rate": 50}]
		)
		self.assertEqual(visit.parts_used[0].item_name, fixtures.SPARE_ITEM)
		self.assertEqual(visit.parts_used[0].uom, "Nos")

	def test_submit_moves_the_request_to_in_progress(self):
		request = fixtures.service_request(submit=True)
		visit = _visit(request, submit=True)

		self.assertEqual(visit.docstatus, 1)
		self.assertEqual(
			frappe.db.get_value("Service Request", request.name, "status"), "In Progress"
		)

	def test_cancel(self):
		request = fixtures.service_request(submit=True)
		visit = _visit(request, submit=True)
		visit.cancel()
		self.assertEqual(visit.docstatus, 2)

	def test_permission_denied_for_a_user_without_roles(self):
		outsider = fixtures.outsider()
		self.assertFalse(frappe.has_permission("Service Visit", "read", user=outsider))
		self.assertFalse(frappe.has_permission("Service Visit", "create", user=outsider))

	def test_a_dealer_may_read_visits_but_not_raise_them(self):
		"""Visits are the service organisation's record, not the dealer's."""
		_dealer, email = fixtures.dealer_login()
		self.assertTrue(frappe.has_permission("Service Visit", "read", user=email))
		self.assertFalse(frappe.has_permission("Service Visit", "create", user=email))
		self.assertFalse(frappe.has_permission("Service Visit", "submit", user=email))
