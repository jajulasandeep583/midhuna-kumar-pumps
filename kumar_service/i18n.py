"""Language switching for the two public pages.

The desk has frappe's own language selector, and the print view has its own. The
website pages have neither, and they are the ones a farmer and a village dealer
actually open - so they get an explicit EN / తెలుగు switch.

Frappe resolves the request language in this order (frappe/translate.py,
``get_language``): ``?_lang=`` first, then the ``preferred_language`` cookie for
guests, then the User record. So:

* ``?_lang=te`` alone lasts exactly one request - submit the search form and the
  page is English again. Hence the cookie, and hence ``lang_qs``, which every
  link and form on those pages carries.
* For a logged-in dealer the cookie is skipped entirely, which is why the
  in-page links matter more than the cookie. A dealer who wants Telugu for good
  should set Language on their own User record.
"""

import frappe

SUPPORTED = ("en", "te")
LABELS = {"en": "English", "te": "తెలుగు"}
COOKIE = "preferred_language"


def current():
	"""The active language, narrowed to one this app actually ships."""
	lang = (frappe.local.lang or "en").split("-")[0]
	return lang if lang in SUPPORTED else "en"


def apply_language(context):
	"""Add the toggle to a website page context.

	Sets ``lang_code``, ``lang_qs`` (``""`` or ``"&_lang=te"``) and
	``lang_options`` - one ``(code, label, query string, is_active)`` per
	language, ready to render as links.
	"""
	lang = current()
	requested = frappe.form_dict.get("_lang")

	if requested and requested.split("-")[0] in SUPPORTED:
		# Remember it, so the next click does not fall back to English.
		cookie_manager = getattr(frappe.local, "cookie_manager", None)
		if cookie_manager:
			cookie_manager.set_cookie(COOKIE, lang)

	context.lang_code = lang
	# two forms, because a link either already has a query string or does not
	context.lang_qs = "" if lang == "en" else f"&_lang={lang}"
	context.lang_q = "" if lang == "en" else f"?_lang={lang}"
	context.lang_options = [
		(code, LABELS[code], _switch_url(code), code == lang) for code in SUPPORTED
	]
	return context


def _switch_url(code):
	"""This page, same query string, different language.

	Rebuilt rather than hardcoded so that switching language on a result page
	keeps the serial number the visitor already typed.
	"""
	from urllib.parse import urlencode

	request = getattr(frappe.local, "request", None)
	path = request.path if request else "/"
	params = {k: v for k, v in frappe.form_dict.items() if not k.startswith("_") and v}
	params["_lang"] = code
	return f"{path}?{urlencode(params)}"
