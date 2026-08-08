"""The KUMAR login page.

This is the first screen anyone sees, so it carries the company rather than a
bare form. It deliberately does NOT reimplement logging in: `get_context`
delegates to frappe's own controller first, so forgot-password, signup, the
email-link login, LDAP and any OAuth provider keep working exactly as they do
out of the box. Everything this module adds is brochure content around the form.

The template does the same thing - `login.html` extends `frappe/www/login.html`
and drops frappe's login sections into the right-hand column with `super()`.
"""

import frappe
from frappe import _

no_cache = True

#: From the 2025 brochure. Static because it is history, and NOT wrapped in _()
#: at module level - a module-level translation freezes whichever language
#: imported the module first. The template translates.
PILLARS = (
	(
		"quality",
		"No Problem performance",
		"Reputed since 1971 for pumps that simply run. Every unit is tested on the "
		"bench against the BIS specification before it leaves Tenali.",
	),
	(
		"trace",
		"Every pump has a history",
		"The melt its casing came from, the winding lot in its stator, the test "
		"reading before dispatch. One serial number answers all of it.",
	),
	(
		"service",
		"Answered, not just sold",
		"A dealer raises a complaint here and the response clock starts. No "
		"ringing round, no waiting to find out whether the visit is free.",
	),
)

#: What the login box should tell people before they get it wrong.
GUIDANCE = (
	("dealer", "Dealers and distributors", "Use the login your branch office set up for you. "
		"It shows only your own network's pumps and customers."),
	("staff", "KUMAR staff", "Use your kumarpumps.local email address."),
	("customer", "Just checking a warranty?", "You do not need to log in - use the warranty "
		"check and type the serial number from the nameplate."),
)

NOTICES = (
	("info", "This portal works in English and తెలుగు. Use the language switch on any page."),
	("info", "Register every pump on the day you sell it - the warranty starts from the "
		"registration, and the customer's certificate is generated from it."),
)


def get_context(context):
	# frappe's own login controller first: it owns the redirect-if-logged-in, the
	# provider list, LDAP, signup and the security headers. Anything below is
	# additive.
	from frappe.www.login import get_context as frappe_login_context

	frappe_login_context(context)

	context.no_cache = True
	context.title = _("KUMAR Pumps & Motors")

	context.kumar_pillars = PILLARS
	context.kumar_guidance = GUIDANCE
	context.kumar_notices = NOTICES
	context.kumar_years = frappe.utils.now_datetime().year - 1971

	# Live from the catalogue, not typed: the login page then cannot go stale, and
	# it is the same number the landing page and the dealer portal quote.
	context.kumar_models = frappe.db.count("Pump Model", {"is_active": 1})
	context.kumar_families = len(
		frappe.get_all("Pump Category", filters={"is_active": 1}, pluck="name")
	)
	context.kumar_states = 13

	context.kumar_range = frappe.db.sql(
		"""
		select   c.name as category, count(m.name) as models
		from     `tabPump Category` c
		join     `tabPump Model` m on m.pump_category = c.name and m.is_active = 1
		where    c.is_active = 1
		group by c.name
		order by count(m.name) desc
		limit    6
		""",
		as_dict=True,
	)
	return context
