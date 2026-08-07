import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, add_to_date, cint, get_datetime, now_datetime

from kumar_service.utils import setting


class ServiceRequest(Document):
	def validate(self):
		self.pull_pump_snapshot()
		self.set_sla()
		self.set_repeat_failure()
		self.set_defaults()

	def pull_pump_snapshot(self):
		sn = frappe.db.get_value(
			"Serial No",
			self.serial_no,
			[
				"custom_pump_model", "custom_manufacturing_date", "custom_dealer",
				"custom_sale_date", "custom_warranty_expiry_date", "custom_warranty_status",
				"custom_end_customer_name", "custom_end_customer_mobile", "custom_registration",
			],
			as_dict=True,
		)
		if not sn:
			frappe.throw(_("Serial number {0} does not exist").format(self.serial_no))

		self.pump_model = sn.custom_pump_model
		self.manufacturing_date = sn.custom_manufacturing_date
		self.dealer = sn.custom_dealer
		self.sale_date = sn.custom_sale_date
		self.warranty_expiry_date = sn.custom_warranty_expiry_date
		self.end_customer_name = sn.custom_end_customer_name
		self.end_customer_mobile = sn.custom_end_customer_mobile

		if self.pump_model:
			model = frappe.db.get_value("Pump Model", self.pump_model, ["hp", "phase"], as_dict=True)
			if model:
				self.hp = model.hp
				self.phase = model.phase

		self.is_under_warranty = 1 if sn.custom_warranty_status in ("In Warranty", "Expiring Soon") else 0

	def set_sla(self):
		if not self.reported_on:
			self.reported_on = now_datetime()

		response_hours = cint(setting("sla_response_hours", 24))
		resolution_hours = cint(setting("sla_resolution_hours", 72))

		self.response_due_on = add_to_date(get_datetime(self.reported_on), hours=response_hours)
		self.resolution_due_on = add_to_date(get_datetime(self.reported_on), hours=resolution_hours)

		if self.status in ("Resolved", "Closed"):
			if not self.resolved_on:
				self.resolved_on = now_datetime()
			met = get_datetime(self.resolved_on) <= get_datetime(self.resolution_due_on)
			self.sla_status = "Fulfilled" if met else "Failed"
		elif self.first_response_on:
			on_time = get_datetime(self.first_response_on) <= get_datetime(self.response_due_on)
			self.sla_status = "Responded" if on_time else "Failed"
		elif get_datetime(self.resolution_due_on) < now_datetime():
			self.sla_status = "Failed"
		else:
			self.sla_status = "Ongoing"

	def set_repeat_failure(self):
		window = cint(setting("repeat_failure_window_days", 90))
		count = frappe.db.count(
			"Service Request",
			{
				"serial_no": self.serial_no,
				"docstatus": ["<", 2],
				"name": ["!=", self.name or ""],
				"reported_on": [">=", add_days(now_datetime(), -window)],
			},
		)
		self.is_repeat_failure = 1 if count else 0

	def set_defaults(self):
		if not self.service_centre:
			self.service_centre = (
				frappe.db.get_value("Service Technician", self.assigned_technician, "dealer")
				if self.assigned_technician
				else setting("default_service_centre")
			)
		if self.assigned_technician and self.status == "Open":
			self.status = "Assigned"

	def on_submit(self):
		self.notify_technician()

	def notify_technician(self):
		if not self.assigned_technician:
			return
		user = frappe.db.get_value("Service Technician", self.assigned_technician, "user")
		if not user:
			return
		frappe.get_doc(
			{
				"doctype": "Notification Log",
				"subject": _("Service request assigned: {0}").format(self.name),
				"email_content": _("{0} - {1} at {2}").format(
					self.serial_no, self.complaint_category, self.end_customer_name or ""
				),
				"for_user": user,
				"type": "Assignment",
				"document_type": self.doctype,
				"document_name": self.name,
			}
		).insert(ignore_permissions=True)
