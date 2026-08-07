import frappe
from frappe.utils.nestedset import NestedSet


class Dealer(NestedSet):
	nsm_parent_field = "parent_dealer"

	def validate(self):
		if self.portal_user:
			other = frappe.db.get_value(
				"Dealer", {"portal_user": self.portal_user, "name": ["!=", self.name]}, "name"
			)
			if other:
				frappe.throw(
					frappe._("{0} is already the portal user for dealer {1}").format(
						self.portal_user, other
					)
				)

	def on_update(self):
		super().on_update()
		self.update_nsm_model()
