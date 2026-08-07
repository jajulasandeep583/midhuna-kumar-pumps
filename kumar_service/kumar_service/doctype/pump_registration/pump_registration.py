import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, cint, getdate, nowdate

from kumar_service.utils import CH_DIRECT, sale_channel_for, setting, validate_mobile
from kumar_service.warranty import apply_registration, compute_for_registration


class PumpRegistration(Document):
	def validate(self):
		self.validate_not_already_registered()
		self.set_sale_channel()
		compute_for_registration(self)
		validate_mobile(self.end_customer_mobile, _("Customer Mobile"))
		self.validate_dates()
		self.validate_sale_paperwork()

	def set_sale_channel(self):
		"""Ownership of the outlet decides the channel, so derive it rather than
		trusting whoever is typing. Anyone may still override it afterwards -
		an own branch does occasionally sell to a trade customer."""
		if not self.sale_channel:
			self.sale_channel = sale_channel_for(self.dealer)

	def validate_sale_paperwork(self):
		"""Each channel has exactly one invoice that proves the sale to the end
		customer. Insisting on it here is what makes a warranty claim
		defensible months later."""
		if self.sale_channel == CH_DIRECT:
			if not self.sales_invoice:
				frappe.throw(
					_("{0} sold this directly, so the customer holds a KUMAR invoice. Link it.").format(
						self.dealer
					),
					title=_("KUMAR Invoice Required"),
				)
			# a dealer invoice cannot exist on a sale we made ourselves
			self.invoice_no = None
			self.dealer_invoice_date = None
			return

		if not self.invoice_no:
			frappe.throw(
				_("{0} is an independent dealer, so the customer holds the DEALER's invoice, "
					"not ours. Enter its number.").format(self.dealer),
				title=_("Dealer's Invoice Required"),
			)

		if self.dealer_invoice_date and getdate(self.dealer_invoice_date) > getdate(self.sale_date):
			frappe.throw(
				_("The dealer's invoice ({0}) is dated after the sale ({1}).").format(
					frappe.format(self.dealer_invoice_date, "Date"),
					frappe.format(self.sale_date, "Date"),
				)
			)

	def validate_not_already_registered(self):
		existing = frappe.db.get_value(
			"Pump Registration",
			{"serial_no": self.serial_no, "docstatus": 1, "name": ["!=", self.name]},
			"name",
		)
		if existing:
			frappe.throw(
				_("Serial {0} is already registered under {1}. Amend that registration instead.").format(
					self.serial_no, frappe.utils.get_link_to_form("Pump Registration", existing)
				),
				title=_("Already Registered"),
			)

	def validate_dates(self):
		if not self.sale_date:
			return

		if getdate(self.sale_date) > getdate(nowdate()):
			frappe.throw(_("Sale date cannot be in the future"))

		if self.manufacturing_date and getdate(self.sale_date) < getdate(self.manufacturing_date):
			frappe.throw(
				_("Sale date {0} is before the pump was manufactured ({1})").format(
					frappe.format(self.sale_date, "Date"), frappe.format(self.manufacturing_date, "Date")
				)
			)

		# a dealer may only backdate so far, otherwise warranty can be gamed
		limit = cint(setting("allow_dealer_backdated_registration_days", 30))
		if limit and self.registration_source == "Dealer Portal":
			earliest = add_days(nowdate(), -limit)
			if getdate(self.sale_date) < getdate(earliest):
				frappe.throw(
					_("Dealers can only register sales up to {0} days old. Contact the branch office.").format(limit)
				)

	def on_submit(self):
		apply_registration(self)

	def on_cancel(self):
		apply_registration(self, revert=True)

	def on_trash(self):
		if self.docstatus == 1:
			apply_registration(self, revert=True)
