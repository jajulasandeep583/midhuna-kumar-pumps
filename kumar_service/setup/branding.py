"""Make the site read as KUMAR, not as Frappe/ERPNext.

Everything a demo audience actually looks at: the browser tab, the navbar logo,
the login page, the splash, the website footer and the company record. All of it
is stored in Singles, so all of it is idempotent - `build_all()` is safe on every
migrate and simply re-asserts the values.

Read together with `icons.py` (workspace glyphs) and `kumar.bundle.css` (desk
chrome). This module is about the frappe-owned chrome that CSS cannot reach.
"""

import frappe

BRAND = "KUMAR"
COMPANY = "Sri Lakshmi Ganapathi Engineering Works"
APP_NAME = "KUMAR Pumps"
BLUE = "#0b5394"

ASSET = "/assets/kumar_service/images"
#: Square tile, 64x64. `hooks.add_to_apps_screen` points at kumar-logo.svg and
#: the /apps screen draws it in a square slot, so that file must stay square -
#: a wide wordmark there renders squashed.
MARK = f"{ASSET}/kumar-mark.svg"
TILE = f"{ASSET}/kumar-logo.svg"
#: Wide lockup, 260x64: mark plus "KUMAR / PUMPS & MOTORS". For the login
#: banner and the company letterhead, never for a square slot.
LOGO = f"{ASSET}/kumar-wordmark.svg"
SPLASH = f"{ASSET}/kumar-splash.svg"

# From the 2025 brochure. Kept here rather than typed into the UI so a rebuilt
# site says exactly the same thing.
ESTABLISHED = "1971-01-01"
BRAND_SINCE = 1973
PHONE = "08644 - 226471"
WEBSITE = "https://www.kumarpumps.co.in"
ADDRESS_LINES = (
	"Kumar Building, Wahab Road",
	"Tenali - 522 201, Guntur Dist.",
	"Andhra Pradesh, India",
)
TAGLINE = "No Problem performance since 1971"

COMPANY_DESCRIPTION = (
	"Sri Lakshmi Ganapathi Engineering Works, founded in 1971 at Tenali, has manufactured "
	"pumpsets and electric motors under the KUMAR brand since 1973. An automated DISA foundry, "
	"an induction furnace with its own metallurgical lab, and CNC/VMC/HMC machining lines feed a "
	"product range that reaches 13 states. Recognised with the MSME National Award 2010 for "
	"Outstanding Entrepreneurship and the MSME National Quality Award 2010 for submersible pumps."
)


def _apply(fn, label):
	"""One failing Single must not stop the rest of the branding.

	Deliberately does NOT roll back, unlike the demo builders' `_try`: these are
	independent Singles, and rolling back would throw away the ones that already
	succeeded in this transaction.
	"""
	try:
		fn()
		return True
	except Exception as exc:  # noqa: BLE001 - keep branding the rest
		frappe.clear_last_message()
		print(f"! branding: {label} skipped: {str(exc)[:160]}")
		return False


def build_all():
	_apply(website_settings, "website settings")
	_apply(navbar, "navbar logo")
	_apply(system_settings, "system settings")
	_apply(theme, "website theme")
	_apply(company, "company record")
	frappe.db.commit()


def website_settings():
	"""The browser tab, the login screen and the website chrome."""
	ws = frappe.get_single("Website Settings")
	ws.update(
		{
			"app_name": APP_NAME,
			"app_logo": MARK,
			"splash_image": SPLASH,
			"favicon": MARK,
			"banner_image": LOGO,
			"brand_html": (
				f'<img src="{MARK}" alt="{BRAND}" style="height:26px;margin-right:8px">'
				f'<span style="font-weight:800;letter-spacing:1px;color:{BLUE}">{BRAND}</span>'
			),
			"copyright": COMPANY,
			# The tab reads "KUMAR Pumps | <page>" instead of a bare page name.
			"title_prefix": APP_NAME,
			"footer_powered": (
				f'<span style="color:#8a9099">{COMPANY} &middot; Tenali &middot; '
				f"{TAGLINE}</span>"
			),
			"address": "<br>".join(ADDRESS_LINES),
			"home_page": "home",
			# frappe's own picker, for the website pages that are not ours
			"show_language_picker": 1,
			"disable_signup": 1,
			"hide_footer_signup": 1,
		}
	)
	ws.flags.ignore_permissions = True
	ws.save(ignore_permissions=True)


def navbar():
	"""The desk's top-left logo. A separate Single from Website Settings."""
	nb = frappe.get_single("Navbar Settings")
	nb.app_logo = MARK
	nb.flags.ignore_permissions = True
	nb.save(ignore_permissions=True)


def system_settings():
	"""`app_name` here is what the desk window title and the About box show."""
	frappe.db.set_single_value("System Settings", "app_name", APP_NAME)


#: `primary_color` and friends on Website Theme are Link fields to the Color
#: DocType, which ships EMPTY on this site - setting them raises
#: "Could not find Primary Color: #0b5394". The palette therefore lives in
#: custom_scss, which is a Code field and is appended after the base theme.
THEME_SCSS = """
:root {
  --kumar-blue: #0b5394;
  --kumar-blue-dark: #08406f;
  --primary: #0b5394;
  --primary-color: #0b5394;
}
.navbar-brand img, .navbar .app-logo { height: 26px; width: auto; }
.navbar-brand { font-weight: 700; letter-spacing: .4px; }
a { color: #0b5394; }
.btn-primary, .btn-primary:focus {
  background-color: #0b5394; border-color: #0b5394; color: #fff;
}
.btn-primary:hover { background-color: #08406f; border-color: #08406f; }
.page-header, h1, h2, h3 { color: #1a2733; }
.web-footer, .footer-logo-extension { border-top-color: #dde5ee; }
"""


def theme():
	"""A KUMAR-blue website theme, applied to the public pages."""
	name = "KUMAR"
	exists = frappe.db.exists("Website Theme", name)
	doc = frappe.get_doc("Website Theme", name) if exists else frappe.new_doc("Website Theme")
	doc.update(
		{
			"theme": name,
			"module": "Kumar Service",
			"custom": 1,
			"button_rounded_corners": 1,
			"button_gradients": 0,
			"button_shadows": 0,
			"custom_scss": THEME_SCSS,
		}
	)
	doc.flags.ignore_permissions = True
	if exists:
		doc.save(ignore_permissions=True)
	else:
		doc.insert(ignore_permissions=True)
	frappe.db.set_single_value("Website Settings", "website_theme", name)


def company():
	"""Fill the company record from the brochure.

	Only blank fields are written, so a real deployment that has already entered
	its own GSTIN or phone number is never overwritten.
	"""
	if not frappe.db.exists("Company", COMPANY):
		return
	doc = frappe.get_doc("Company", COMPANY)
	wanted = {
		"company_description": COMPANY_DESCRIPTION,
		"phone_no": PHONE,
		"website": WEBSITE,
		"date_of_establishment": ESTABLISHED,
		"company_logo": LOGO,
		"domain": "Manufacturing",
	}
	changed = False
	for field, value in wanted.items():
		if doc.meta.has_field(field) and not doc.get(field):
			doc.set(field, value)
			changed = True
	if changed:
		doc.flags.ignore_permissions = True
		doc.save(ignore_permissions=True)
