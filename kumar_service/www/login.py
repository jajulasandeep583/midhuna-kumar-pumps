"""The KUMAR login page.

This is the first screen anyone sees, so it says what the product is and who
signs in, around frappe's own form. It deliberately does NOT reimplement logging
in: `get_context` delegates to frappe's own controller first, so forgot-password,
signup, the email-link login, LDAP and any OAuth provider keep working exactly
as they do out of the box. Everything this module adds is the frame.

The template does the same thing - `login.html` extends `frappe/www/login.html`
and drops frappe's login sections into the right-hand column with `super()`.
"""

import frappe
from frappe import _

no_cache = True

#: Who signs in, in the order a stranger to the system needs them. NOT wrapped
#: in _() at module level - a module-level translation freezes whichever
#: language imported the module first. The template translates.
GUIDANCE = (
	("dealer", "Dealers and distributors",
		"Use the login your branch office set up. You see your own network's pumps, "
		"requests and claims, and nothing from another outlet.", ""),
	("staff", "KUMAR staff",
		"Your kumarpumps.local address. You land on the Command Centre.", ""),
	("guest", "Only checking a warranty?",
		"No login needed - type the serial from the nameplate.", "/warranty_check"),
)


def get_context(context):
	# frappe's own login controller first: it owns the redirect-if-logged-in, the
	# provider list, LDAP, signup and the security headers. Anything below is
	# additive.
	from frappe.www.login import get_context as frappe_login_context

	frappe_login_context(context)

	context.no_cache = True
	context.title = _("KUMAR Pumps Desk")

	context.kumar_guidance = GUIDANCE
	return context
