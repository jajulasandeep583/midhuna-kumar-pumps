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
		# NestedSet.on_update already rebuilds the lft/rgt bounds. There is no
		# second "update the model" step to call - reaching for one raised
		# AttributeError on every dealer save.
		super().on_update()
