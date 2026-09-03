"""KUMAR staff raising things for a pump, on behalf of whoever rang.

A dealer has the portal. Everyone else reaches KUMAR by phone or mail, and a
member of staff must be able to find the pump and raise the request, the claim
or the visit from one place - and it must land where a dealer's would.
"""

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, nowdate

from kumar_service.desk_bridge import desk_installed


class TestStaffRaise(IntegrationTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		reg = frappe.get_all(
			"Pump Registration",
			filters={"docstatus": 1, "end_customer_mobile": ["!=", ""], "dealer": ["!=", ""],
				"serial_no": ["not like", "\\_%"]},
			fields=["serial_no", "end_customer_mobile", "end_customer_name", "dealer"],
			limit=1,
		)
		if not reg:
			self.skipTest("no registered pump with a dealer on this site")
		self.reg = reg[0]
		tech = frappe.get_all("Service Technician", pluck="name", limit=1)
		if not tech:
			self.skipTest("no technician on this site")
		self.tech = tech[0]
		self.made = []

	def tearDown(self):
		frappe.set_user("Administrator")
		for doctype, name in reversed(self.made):
			if not frappe.db.exists(doctype, name):
				continue
			# submitted records must be cancelled before they can go
			if frappe.db.get_value(doctype, name, "docstatus") == 1:
				frappe.db.set_value(doctype, name, "docstatus", 2, update_modified=False)
			frappe.delete_doc(doctype, name, force=True, ignore_permissions=True, ignore_on_trash=True)

	def _track_ticket(self, ticket):
		if ticket:
			self.made.append(("HD Ticket", ticket))

	# ------------------------------------------------------------- finding

	def test_the_pump_is_found_by_the_callers_phone_and_name(self):
		from kumar_service.staff_api import find_pumps

		by_phone = [r["serial_no"] for r in find_pumps(self.reg.end_customer_mobile[-6:])]
		self.assertIn(self.reg.serial_no, by_phone)
		by_name = [r["serial_no"] for r in find_pumps(self.reg.end_customer_name.split()[0])]
		self.assertIn(self.reg.serial_no, by_name)
		self.assertEqual(find_pumps("K"), [], "one character is not a search")

	def test_the_options_cover_all_three_forms(self):
		from kumar_service.staff_api import raise_options

		o = raise_options()
		for key in ("request_types", "complaint_categories", "priorities", "claim_types", "visit_types"):
			self.assertTrue(o[key], f"{key} is empty")
		self.assertTrue(o["technicians"])

	# ------------------------------------------------------------- raising

	def test_a_claim_lodged_by_staff_is_the_dealers_claim_with_a_ticket(self):
		from kumar_service.staff_api import raise_claim_for_pump

		out = raise_claim_for_pump(self.reg.serial_no, "Part Replacement", 1800, "Impeller cracked at the hub")
		self.made.append(("Kumar Warranty Claim", out["name"]))
		self._track_ticket(out.get("ticket"))
		self.assertEqual(out["dealer"], self.reg.dealer, "the claim belongs to the pump's dealer")
		self.assertEqual(frappe.db.get_value("Kumar Warranty Claim", out["name"], "claim_amount"), 1800)
		if desk_installed():
			self.assertTrue(out["ticket"], "a staff-lodged claim must have a ticket like any other")
			self.assertEqual(frappe.db.get_value("HD Ticket", out["ticket"], "ticket_type"), "Warranty Claim")
		# the dealer is told, on the claim's thread
		note = frappe.get_all(
			"Comment",
			filters={"reference_doctype": "Kumar Warranty Claim", "reference_name": out["name"],
				"comment_type": "Comment"},
			pluck="content",
		)
		self.assertTrue(any("on your behalf" in n for n in note), "the dealer was not told")

	def test_a_claim_cannot_hang_off_another_pumps_request(self):
		from kumar_service.staff_api import raise_claim_for_pump

		other = frappe.get_all(
			"Service Request", filters={"serial_no": ["!=", self.reg.serial_no], "docstatus": 1},
			pluck="name", limit=1,
		)
		if not other:
			self.skipTest("no request on another pump")
		with self.assertRaises(frappe.ValidationError):
			raise_claim_for_pump(self.reg.serial_no, "Part Replacement", 1, "x", service_request=other[0])

	def test_a_visit_with_no_request_opens_one_typed_as_a_visit(self):
		from kumar_service.staff_api import schedule_visit_for_pump

		out = schedule_visit_for_pump(
			self.reg.serial_no, self.tech, add_days(nowdate(), 3), "On-Site",
			note="Call before", reason="Customer rang: pump trips on start",
		)
		sr = out["service_request"]
		self.made.append(("Service Request", sr))
		self._track_ticket(out.get("ticket"))
		visits = frappe.get_all("Service Visit", filters={"service_request": sr}, pluck="name")
		for v in visits:
			self.made.append(("Service Visit", v))
		self.assertEqual(len(visits), 1, "one visit, booked")
		self.assertEqual(frappe.db.get_value("Service Request", sr, "serial_no"), self.reg.serial_no)
		self.assertEqual(frappe.db.get_value("Service Request", sr, "docstatus"), 1, "submitted, so the SLA runs")
		if desk_installed():
			self.assertTrue(out["ticket"])

	def test_a_visit_without_a_reason_or_a_request_is_refused(self):
		from kumar_service.staff_api import schedule_visit_for_pump

		with self.assertRaises(frappe.ValidationError):
			schedule_visit_for_pump(self.reg.serial_no, self.tech, add_days(nowdate(), 3), "On-Site")

	def test_a_request_with_attachments_carries_them_on_the_thread(self):
		from kumar_service.staff_api import raise_request_for_pump

		out = raise_request_for_pump(
			self.reg.serial_no, "Complaint", "Other", "with a photo", "High",
			# a 1x1 PNG: the thread accepts photos and PDFs, not arbitrary files
			attachments=[{"filename": "nameplate.png",
				"content": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="}],
		)
		self.made.append(("Service Request", out["name"]))
		self._track_ticket(out.get("ticket"))
		self.assertEqual(out["attached"], 1)
		files = frappe.get_all(
			"File", filters={"attached_to_doctype": "Service Request", "attached_to_name": out["name"]},
			pluck="name",
		)
		for f in files:
			self.made.append(("File", f))
		self.assertEqual(len(files), 1)

	def test_a_dealer_cannot_use_the_staff_raise(self):
		from kumar_service.staff_api import find_pumps

		dealer_user = frappe.db.get_value("Dealer", {"portal_user": ["!=", ""]}, "portal_user")
		if not dealer_user or not frappe.db.exists("User", dealer_user):
			self.skipTest("no dealer login on this site")
		frappe.set_user(dealer_user)
		try:
			with self.assertRaises(frappe.PermissionError):
				find_pumps("KP-")
		finally:
			frappe.set_user("Administrator")
