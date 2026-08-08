"""Public landing page - what the site opens on.

Deliberately reads live numbers out of the system rather than hardcoding them.
The point of the page is that the brochure and the ERP are the same thing: the
product range on screen IS the Pump Model table, and the branch list IS the
Dealer tree.
"""

import frappe
from frappe import _

no_cache = 1

# From the 2025 brochure's R&D timeline. Static because it is history.
# NOT wrapped in _() here: a module-level _() runs at import time and freezes
# whichever language happened to load the module first. The template translates.
MILESTONES = (
	(1971, "Sri Lakshmi Ganapathi Engineering Works founded at Tenali"),
	(1973, "Pumps and motors begin under the KUMAR brand"),
	(1993, "DISA moulding machines installed in the foundry"),
	(2008, "Inductotherm induction furnace and metallurgical lab"),
	(2011, "DISA computerised foundry from Denmark"),
	(2016, "KUKA and ABB robots on the machining lines"),
	(2020, "Doosan twin-spindle machines from Korea"),
	(2023, "5-star rated BLDC fans, junction boxes and steel furniture"),
	(2024, "Flat submersible cable"),
)

STATES = (
	"Andhra Pradesh", "Telangana", "Tamil Nadu", "Kerala", "Karnataka",
	"Madhya Pradesh", "Maharashtra", "Gujarat", "Uttar Pradesh", "Bihar",
	"Odisha", "West Bengal", "Assam",
)

# The icon names are symbol ids in the inline sprite at the top of home.html.
# They cannot come from the desk sprite: `app_include_icons` only injects that
# into the desk, so a `<use href="#icon-...">` on a website page renders nothing.
CAPABILITIES = (
	(
		"foundry",
		"Automated foundry",
		"DISA moulding on German technology, for accuracy and casting strength.",
	),
	(
		"furnace",
		"Induction furnace and metallurgical lab",
		"Iron melted to 1500&deg;C under control, and a spectrometer reading taken before the "
		"metal is ever poured.",
	),
	(
		"cnc",
		"CNC, VMC and HMC machining",
		"Every pump component machined on computerised machines, so parts are interchangeable "
		"across a production run.",
	),
	(
		"balance",
		"Dynamic balancing and CNC grinding",
		"Shafts and rotors ground to micron precision, then balanced - which is what keeps "
		"bearings alive.",
	),
)


def get_context(context):
	from kumar_service.i18n import apply_language

	context.no_cache = 1
	apply_language(context)
	context.title = _("KUMAR Pumps & Motors")

	context.milestones = MILESTONES
	context.states = STATES
	context.capabilities = CAPABILITIES
	context.years = frappe.utils.now_datetime().year - 1971

	# The range, straight out of the catalogue the plant actually builds against.
	context.product_range = frappe.db.sql(
		"""
		select   c.name as category,
		         count(m.name)      as models,
		         min(m.hp)          as hp_min,
		         max(m.hp)          as hp_max,
		         min(m.head_min_m)  as head_min,
		         max(m.head_max_m)  as head_max
		from     `tabPump Category` c
		join     `tabPump Model`    m on m.pump_category = c.name and m.is_active = 1
		where    c.is_active = 1
		group by c.name
		order by count(m.name) desc, c.name
		""",
		as_dict=True,
	)

	context.totals = {
		"models": frappe.db.count("Pump Model", {"is_active": 1}),
		"categories": len(context.product_range),
		"states": len(STATES),
		# Only pumps whose warranty we are actually carrying right now.
		"in_warranty": frappe.db.count(
			"Serial No", {"custom_warranty_status": ["in", ["In Warranty", "Expiring Soon"]]}
		),
	}

	# Own branches only. An independent distributor's address is their business,
	# not ours to publish, and the brochure lists them separately anyway.
	context.branches = frappe.get_all(
		"Dealer",
		filters={"is_own_outlet": 1, "status": "Active", "city": ["!=", ""]},
		fields=["dealer_name", "city", "state", "mobile_no", "landline", "address_line"],
		order_by="city",
	)
	context.distributors = frappe.get_all(
		"Dealer",
		filters={"is_own_outlet": 0, "dealer_type": "Authorised Distributor", "status": "Active"},
		fields=["dealer_name", "city", "state"],
		order_by="state",
	)
	return context
