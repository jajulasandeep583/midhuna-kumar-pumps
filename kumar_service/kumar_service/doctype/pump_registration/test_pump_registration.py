import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, add_months, getdate, nowdate

from kumar_service.tests import fixtures
from kumar_service.utils import CH_DEALER, CH_DIRECT

IGNORE_TEST_RECORD_DEPENDENCIES = fixtures.LINK_DEPENDENCIES


class TestPumpRegistration(IntegrationTestCase):
	def test_create_through_the_dealer_channel(self):
		reg = fixtures.registration()

		self.assertEqual(reg.sale_channel, CH_DEALER)
		self.assertEqual(reg.pump_model, fixtures.MODEL)
		self.assertEqual(reg.item_code, fixtures.PUMP_ITEM)
		self.assertEqual(reg.hp, 5.0)
		# no months on the model, so the category's 18 is what applies
		self.assertEqual(reg.warranty_months, 18)
		self.assertEqual(getdate(reg.warranty_start_date), getdate(reg.sale_date))
		self.assertEqual(
			getdate(reg.warranty_expiry_date), getdate(add_months(reg.sale_date, 18))
		)
		self.assertEqual(reg.warranty_card_no, f"KWC-{reg.serial_no}")
		self.assertIn(reg.serial_no, reg.qr_url)

	def test_an_own_branch_is_a_direct_sale_and_needs_a_kumar_invoice(self):
		"""Ownership decides the channel, and a direct sale has exactly one
		invoice - ours. Without it there is no proof of purchase at all."""
		branch = fixtures.dealer(fixtures.DEALER_OWN, is_own_outlet=1)
		doc = frappe.get_doc(
			{
				"doctype": "Pump Registration",
				"serial_no": fixtures.serial_no(),
				"dealer": branch,
				"sale_date": add_days(nowdate(), -3),
				"end_customer_name": "_KT Customer",
				"end_customer_mobile": "9812345678",
			}
		)
		with self.assertRaises(frappe.ValidationError) as caught:
			doc.insert(ignore_permissions=True)

		self.assertEqual(doc.sale_channel, CH_DIRECT)
		self.assertIn("KUMAR invoice", str(caught.exception))

	def test_an_independent_dealer_must_give_its_own_invoice_number(self):
		"""The customer walks away holding the DEALER's invoice, not ours."""
		doc = frappe.get_doc(
			{
				"doctype": "Pump Registration",
				"serial_no": fixtures.serial_no(),
				"dealer": fixtures.dealer(),
				"sale_date": add_days(nowdate(), -3),
				"end_customer_name": "_KT Customer",
				"end_customer_mobile": "9812345678",
			}
		)
		self.assertRaises(frappe.ValidationError, doc.insert)

	def test_an_own_branch_may_still_sell_on_trade_terms(self):
		"""Ownership only sets the default. A branch does occasionally sell to
		a trade customer on the dealer's own paperwork, so an explicit channel
		is honoured - and then the dealer's invoice number is what is demanded."""
		branch = fixtures.dealer(fixtures.DEALER_OWN, is_own_outlet=1)
		reg = frappe.get_doc(
			{
				"doctype": "Pump Registration",
				"serial_no": fixtures.serial_no(),
				"dealer": branch,
				"sale_date": add_days(nowdate(), -3),
				"sale_channel": CH_DEALER,
				"invoice_no": "D/2026/9999",
				"end_customer_name": "_KT Customer",
				"end_customer_mobile": "9812345678",
			}
		).insert(ignore_permissions=True)

		self.assertEqual(reg.sale_channel, CH_DEALER)
		self.assertEqual(reg.invoice_no, "D/2026/9999")

	def test_validate_failure_on_a_bad_mobile_number(self):
		doc = frappe.get_doc(
			{
				"doctype": "Pump Registration",
				"serial_no": fixtures.serial_no(),
				"dealer": fixtures.dealer(),
				"sale_date": add_days(nowdate(), -3),
				"invoice_no": "D/2026/0002",
				"end_customer_name": "_KT Customer",
				"end_customer_mobile": "12345",
			}
		)
		with self.assertRaises(frappe.ValidationError) as caught:
			doc.insert(ignore_permissions=True)
		self.assertIn("10 digits", str(caught.exception))

	def test_validate_failure_on_a_future_sale_date(self):
		doc = frappe.get_doc(
			{
				"doctype": "Pump Registration",
				"serial_no": fixtures.serial_no(),
				"dealer": fixtures.dealer(),
				"sale_date": add_days(nowdate(), 3),
				"invoice_no": "D/2026/0003",
				"end_customer_name": "_KT Customer",
				"end_customer_mobile": "9812345678",
			}
		)
		with self.assertRaises(frappe.ValidationError) as caught:
			doc.insert(ignore_permissions=True)
		self.assertIn("future", str(caught.exception))

	def test_validate_failure_when_sold_before_it_was_built(self):
		serial = fixtures.serial_no(manufactured_days_ago=10)
		doc = frappe.get_doc(
			{
				"doctype": "Pump Registration",
				"serial_no": serial,
				"dealer": fixtures.dealer(),
				"sale_date": add_days(nowdate(), -30),
				"invoice_no": "D/2026/0004",
				"end_customer_name": "_KT Customer",
				"end_customer_mobile": "9812345678",
			}
		)
		with self.assertRaises(frappe.ValidationError) as caught:
			doc.insert(ignore_permissions=True)
		self.assertIn("manufactured", str(caught.exception))

	def test_validate_failure_when_the_dealer_backdates_too_far(self):
		"""A portal registration may only reach back as far as Settings allows,
		otherwise a dealer could start a warranty whenever it suited them."""
		serial = fixtures.serial_no(manufactured_days_ago=400)
		doc = frappe.get_doc(
			{
				"doctype": "Pump Registration",
				"serial_no": serial,
				"dealer": fixtures.dealer(),
				"sale_date": add_days(nowdate(), -200),
				"invoice_no": "D/2026/0005",
				"dealer_invoice_date": add_days(nowdate(), -200),
				"registration_source": "Dealer Portal",
				"end_customer_name": "_KT Customer",
				"end_customer_mobile": "9812345678",
			}
		)
		with self.assertRaises(frappe.ValidationError) as caught:
			doc.insert(ignore_permissions=True)
		self.assertIn("days old", str(caught.exception))

	def test_validate_failure_on_a_dealer_invoice_dated_after_the_sale(self):
		doc = frappe.get_doc(
			{
				"doctype": "Pump Registration",
				"serial_no": fixtures.serial_no(),
				"dealer": fixtures.dealer(),
				"sale_date": add_days(nowdate(), -10),
				"invoice_no": "D/2026/0006",
				"dealer_invoice_date": add_days(nowdate(), -2),
				"end_customer_name": "_KT Customer",
				"end_customer_mobile": "9812345678",
			}
		)
		with self.assertRaises(frappe.ValidationError) as caught:
			doc.insert(ignore_permissions=True)
		self.assertIn("dated after", str(caught.exception))

	def test_a_serial_cannot_be_registered_twice(self):
		first = fixtures.registration(submit=True)
		second = frappe.get_doc(
			{
				"doctype": "Pump Registration",
				"serial_no": first.serial_no,
				"dealer": fixtures.dealer(),
				"sale_date": add_days(nowdate(), -1),
				"invoice_no": "D/2026/0007",
				"end_customer_name": "_KT Second Customer",
				"end_customer_mobile": "9812345679",
			}
		)
		with self.assertRaises(frappe.ValidationError) as caught:
			second.insert(ignore_permissions=True)
		self.assertIn("already registered", str(caught.exception).lower())

	def test_submit_starts_the_warranty_on_the_serial(self):
		reg = fixtures.registration(submit=True)
		serial = frappe.db.get_value(
			"Serial No",
			reg.serial_no,
			[
				"custom_registration",
				"custom_dealer",
				"custom_warranty_status",
				"custom_warranty_expiry_date",
				"custom_end_customer_name",
				"custom_qr_url",
			],
			as_dict=True,
		)

		self.assertEqual(reg.docstatus, 1)
		self.assertEqual(serial.custom_registration, reg.name)
		self.assertEqual(serial.custom_dealer, reg.dealer)
		self.assertEqual(serial.custom_warranty_status, "In Warranty")
		self.assertEqual(getdate(serial.custom_warranty_expiry_date), getdate(reg.warranty_expiry_date))
		self.assertEqual(serial.custom_end_customer_name, "_KT Customer")
		self.assertIn(reg.serial_no, serial.custom_qr_url or "")

	def test_cancel_takes_the_warranty_back_off_the_serial(self):
		reg = fixtures.registration(submit=True)
		reg.cancel()

		serial = frappe.db.get_value(
			"Serial No",
			reg.serial_no,
			["custom_registration", "custom_dealer", "custom_warranty_status",
			 "custom_warranty_expiry_date"],
			as_dict=True,
		)
		self.assertEqual(reg.docstatus, 2)
		self.assertIsNone(serial.custom_registration)
		self.assertIsNone(serial.custom_dealer)
		self.assertIsNone(serial.custom_warranty_expiry_date)
		self.assertEqual(serial.custom_warranty_status, "Not Registered")

	def test_a_cancelled_registration_frees_the_serial_again(self):
		first = fixtures.registration(submit=True)
		first.cancel()
		second = fixtures.registration(serial=first.serial_no, submit=True)
		self.assertEqual(second.docstatus, 1)

	def test_warranty_can_be_taken_from_the_manufacturing_date_instead(self):
		"""Nothing about the warranty clock is hardcoded - Settings moves it."""
		serial = fixtures.serial_no(manufactured_days_ago=60)
		with self.change_settings("Kumar Service Settings", warranty_from="Manufacturing Date"):
			reg = fixtures.registration(serial=serial)
		self.assertEqual(
			getdate(reg.warranty_start_date), getdate(add_days(nowdate(), -60))
		)

	def test_permission_denied_across_dealers(self):
		mine, my_email = fixtures.dealer_login()
		theirs, _ = fixtures.rival_login()

		my_reg = fixtures.registration(dealer_name=mine, submit=True)
		their_reg = fixtures.registration(dealer_name=theirs, submit=True)

		self.assertTrue(frappe.has_permission("Pump Registration", doc=my_reg, user=my_email))
		self.assertFalse(frappe.has_permission("Pump Registration", doc=their_reg, user=my_email))

		# get_list, not get_all - get_all deliberately ignores permissions
		with self.set_user(my_email):
			visible = frappe.get_list("Pump Registration", pluck="name", limit_page_length=0)
		self.assertIn(my_reg.name, visible)
		self.assertNotIn(their_reg.name, visible)

	def test_permission_denied_for_a_user_without_roles(self):
		outsider = fixtures.outsider()
		self.assertFalse(frappe.has_permission("Pump Registration", "read", user=outsider))
		self.assertFalse(frappe.has_permission("Pump Registration", "create", user=outsider))
