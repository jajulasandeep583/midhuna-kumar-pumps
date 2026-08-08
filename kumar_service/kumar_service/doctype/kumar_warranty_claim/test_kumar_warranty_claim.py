import frappe
from frappe.model.workflow import apply_workflow
from frappe.tests import IntegrationTestCase
from frappe.utils import getdate, nowdate

from kumar_service.tests import fixtures

IGNORE_TEST_RECORD_DEPENDENCIES = fixtures.LINK_DEPENDENCIES


def _claim(serial=None, dealer=None, submit=False, **overrides):
	values = {
		"doctype": "Kumar Warranty Claim",
		"serial_no": serial or fixtures.serial_no(),
		"dealer": dealer or fixtures.dealer(),
		"claim_date": nowdate(),
		"claim_type": "Part Replacement",
		"root_cause": "Manufacturing Defect",
		"technician_report": "Winding failed inside the warranty period.",
	}
	values.update(overrides)
	doc = frappe.get_doc(values)
	doc.flags.ignore_permissions = True
	doc.insert(ignore_permissions=True)
	if submit:
		doc.submit()
	return doc


class TestKumarWarrantyClaim(IntegrationTestCase):
	def test_create_pulls_the_traceability_forward(self):
		"""Heat and winding batch ride along on the claim - without them batch
		defect analysis has nothing to group on."""
		serial = fixtures.serial_no()
		frappe.db.set_value(
			"Serial No",
			serial,
			{"custom_heat_no": None, "custom_winding_batch": None},
			update_modified=False,
		)
		claim = _claim(serial=serial)

		self.assertEqual(claim.pump_model, fixtures.MODEL)
		self.assertEqual(claim.dealer, fixtures.DEALER_INDEPENDENT)
		self.assertEqual(getdate(claim.claim_date), getdate(nowdate()))

	def test_the_dealer_defaults_from_the_serial(self):
		reg = fixtures.registration(submit=True)
		claim = _claim(serial=reg.serial_no, dealer=None)
		# dealer left out of the payload entirely, so the serial supplies it
		claim.dealer = None
		claim.save(ignore_permissions=True)
		self.assertEqual(claim.dealer, reg.dealer)

	def test_claim_amount_is_the_sum_of_the_parts(self):
		claim = _claim(
			defective_parts=[
				{"item_code": fixtures.spare_item(), "qty": 2, "rate": 150},
				{"item_code": fixtures.spare_item(), "qty": 1, "rate": 400},
			]
		)
		self.assertEqual(claim.defective_parts[0].amount, 300)
		self.assertEqual(claim.claim_amount, 700)

	def test_a_part_row_takes_its_rate_from_the_item(self):
		claim = _claim(defective_parts=[{"item_code": fixtures.spare_item(), "qty": 1}])
		self.assertEqual(claim.defective_parts[0].rate, 250)
		self.assertEqual(claim.defective_parts[0].item_name, fixtures.SPARE_ITEM)

	def test_validate_failure_without_a_serial_to_trace(self):
		"""Traceability is pulled off the serial before frappe's mandatory pass
		runs, so a claim with no serial fails there first."""
		doc = frappe.get_doc({"doctype": "Kumar Warranty Claim", "claim_date": nowdate()})
		self.assertRaises(frappe.ValidationError, doc.insert)

	def test_validate_failure_without_a_dealer(self):
		"""A serial that was never registered cannot supply a dealer, and a
		claim with no dealer has nobody to settle against."""
		doc = frappe.get_doc(
			{
				"doctype": "Kumar Warranty Claim",
				"serial_no": fixtures.serial_no(),
				"claim_date": nowdate(),
			}
		)
		self.assertRaises(frappe.MandatoryError, doc.insert)

	def test_submit_links_the_claim_back_to_its_service_request(self):
		request = fixtures.service_request(submit=True)
		claim = _claim(serial=request.serial_no, service_request=request.name, submit=True)

		self.assertEqual(claim.docstatus, 1)
		self.assertEqual(
			frappe.db.get_value("Service Request", request.name, "linked_claim"), claim.name
		)

	def test_cancel_unlinks_it_again(self):
		request = fixtures.service_request(submit=True)
		claim = _claim(serial=request.serial_no, service_request=request.name, submit=True)
		claim.cancel()

		self.assertEqual(claim.docstatus, 2)
		self.assertIsNone(
			frappe.db.get_value("Service Request", request.name, "linked_claim")
		)

	def test_the_workflow_runs_from_draft_to_settled(self):
		"""Every state change is an approval someone has to own."""
		claim = _claim(
			defective_parts=[{"item_code": fixtures.spare_item(), "qty": 1, "rate": 500}]
		)
		self.assertEqual(claim.workflow_state, "Draft")

		claim = apply_workflow(claim, "Submit for Review")
		self.assertEqual(claim.workflow_state, "Pending Review")
		self.assertEqual(claim.docstatus, 1)

		claim = apply_workflow(claim, "Review")
		self.assertEqual(claim.workflow_state, "Under Investigation")

		claim = apply_workflow(claim, "Approve")
		self.assertEqual(claim.workflow_state, "Approved")

		claim = apply_workflow(claim, "Settle")
		self.assertEqual(claim.workflow_state, "Settled")
		self.assertEqual(
			getdate(frappe.db.get_value("Kumar Warranty Claim", claim.name, "settled_on")),
			getdate(nowdate()),
		)

	def test_a_claim_can_be_rejected_without_ever_being_approved(self):
		claim = _claim()
		claim = apply_workflow(claim, "Submit for Review")
		claim = apply_workflow(claim, "Reject")
		self.assertEqual(claim.workflow_state, "Rejected")
		self.assertIsNone(frappe.db.get_value("Kumar Warranty Claim", claim.name, "settled_on"))

	def test_permission_denied_across_dealers(self):
		mine, my_email = fixtures.dealer_login()
		theirs, _ = fixtures.rival_login()

		my_claim = _claim(dealer=mine, submit=True)
		their_claim = _claim(dealer=theirs, submit=True)

		self.assertTrue(
			frappe.has_permission("Kumar Warranty Claim", doc=my_claim, user=my_email)
		)
		self.assertFalse(
			frappe.has_permission("Kumar Warranty Claim", doc=their_claim, user=my_email)
		)

		with self.set_user(my_email):
			visible = frappe.get_list("Kumar Warranty Claim", pluck="name", limit_page_length=0)
		self.assertIn(my_claim.name, visible)
		self.assertNotIn(their_claim.name, visible)

	def test_a_dealer_cannot_approve_its_own_claim(self):
		"""Raising a claim and settling it must never be the same person."""
		_dealer, email = fixtures.dealer_login()
		self.assertTrue(frappe.has_permission("Kumar Warranty Claim", "create", user=email))
		self.assertFalse(frappe.has_permission("Kumar Warranty Claim", "cancel", user=email))

		roles = {t.allowed for t in frappe.get_doc("Workflow", "Kumar Warranty Claim Approval").transitions}
		self.assertIn("Dealer", roles)
		approvals = {
			t.allowed
			for t in frappe.get_doc("Workflow", "Kumar Warranty Claim Approval").transitions
			if t.action in ("Approve", "Settle")
		}
		self.assertNotIn("Dealer", approvals)

	def test_permission_denied_for_a_user_without_roles(self):
		outsider = fixtures.outsider()
		self.assertFalse(frappe.has_permission("Kumar Warranty Claim", "read", user=outsider))
		self.assertFalse(frappe.has_permission("Kumar Warranty Claim", "create", user=outsider))
