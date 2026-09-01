"""The Knowledge Base a dealer actually reaches for.

Written from the counter's side rather than the plant's. A dealer with a
customer on the phone wants to know whether the visit is free, why a pump is not
priming, and what to say about a warranty that has run out - not a specification
sheet. Every article answers one question a dealer has actually been asked.

Seeded from code so it ships with the app, survives a reinstall, and can be
reviewed in a pull request like everything else. Articles are created as
Published; editing them afterwards in the desk is expected and this will not
overwrite an edit - it only creates what is missing.
"""

import frappe

CATEGORIES = [
	("Before you call KUMAR", "What a dealer can check in five minutes at the customer's site."),
	("Warranty", "What is covered, what is not, and how long is left."),
	("Installation", "Getting a set running so it does not come back."),
	("Using this desk", "Registering a sale, raising a request, following it."),
]

# (category, title, body)
ARTICLES = [
	# ------------------------------------------------- before you call KUMAR
	(
		"Before you call KUMAR",
		"Motor runs but no water comes up",
		"""<p>The most common call, and most of it is not the pump.</p>
<ol>
<li><b>Is the foot valve holding?</b> Prime the pump and watch. If the water drains back
within a minute the foot valve is leaking - it is a five rupee part and not a warranty
failure.</li>
<li><b>Has the water level dropped below the suction?</b> Ask what the level was when the
set was installed. In summer a borewell that ran at 40 feet can be at 90.</li>
<li><b>Is the delivery valve open?</b> Obvious, and it is the answer often enough to check
it before ringing.</li>
<li><b>Air lock.</b> Loosen the priming plug, let the air out, tighten it and start again.</li>
</ol>
<p>If all four are ruled out and the motor still runs dry, raise a Complaint from
<b>What I Sold</b> so the serial and the warranty position come with it. Send a photo of
the nameplate and a short video of the pump running - it saves a visit more often than
you would think.</p>""",
	),
	(
		"Before you call KUMAR",
		"Motor trips as soon as it starts",
		"""<p>A trip on start is usually electrical, not mechanical.</p>
<ul>
<li><b>Check the incoming voltage.</b> A three phase set on two phases will trip every time.
Below 380 V a 3-phase motor is being asked to work on supply it was not built for, and the
overload is doing its job.</li>
<li><b>Check the capacitor</b> on a single phase set. A dead capacitor gives exactly this
symptom: a hum, a trip, no rotation.</li>
<li><b>Turn the shaft by hand</b> with the power off. If it will not turn freely the pump is
jammed - that is a KUMAR job, and worth photographing before anything is dismantled.</li>
</ul>
<p>Note the voltage you measured in the complaint. A burnt winding on a set that was fed
340 V is a different conversation from one that was fed 415 V, and the reading is the
whole difference.</p>""",
	),
	(
		"Before you call KUMAR",
		"Noise, vibration or a hot motor body",
		"""<p>Take these seriously: a set that is left running like this usually comes back as a
burnt winding a fortnight later.</p>
<ul>
<li><b>Grinding or rumbling</b> - bearing. Stop the set. Running it further damages the
shaft, and a bearing job becomes a rewinding job.</li>
<li><b>Rattling that changes with the delivery valve</b> - cavitation. The pump is being
starved. Usually suction height or a partly blocked foot valve, not the pump.</li>
<li><b>Body too hot to touch</b> - check the ampere draw against the nameplate. Over the
rated current means it is working against something.</li>
</ul>
<p>A ten second video with the sound on tells us more than a paragraph. Attach one to the
complaint.</p>""",
	),
	# --------------------------------------------------------------- warranty
	(
		"Warranty",
		"What the KUMAR warranty covers",
		"""<p>The warranty covers <b>manufacturing defects</b>: winding failures that are not
caused by supply, casting defects, bearing failures inside the warranty period, and
impeller failures that are not from abrasion.</p>
<p>It does not cover:</p>
<ul>
<li>Damage from voltage outside the nameplate range, or from single phasing</li>
<li>Dry running</li>
<li>Sand and abrasion wear - a pump run in sandy water is a consumable</li>
<li>Any set opened by somebody other than a KUMAR service centre</li>
</ul>
<p><b>The warranty starts from the registration, not from the invoice.</b> Register on the
day you sell, or the customer loses the days between.</p>
<p>Check any serial under <b>Pump Lookup</b> or in <b>What I Sold</b>: it shows the state and
the days left, so you can answer on the phone.</p>""",
	),
	(
		"Warranty",
		"Telling a customer their warranty has run out",
		"""<p>Have the facts in front of you before you make the call. Look the serial up and you
will have the sale date, the expiry, and how long ago it lapsed.</p>
<p>What helps:</p>
<ul>
<li>Say when it expired, not just that it has. "It ran out in March" lands better than
"it is out of warranty".</li>
<li>Give the likely cost before they ask.</li>
<li>Raise it as a <b>Paid Service</b> request, not a Complaint. It goes to the same desk,
but everybody involved knows it is chargeable from the start and nobody argues about it
on the doorstep.</li>
</ul>
<p>A set whose warranty is about to run out is worth a call before it does. <b>What I
Sold</b> has an "Expiring in 45 days" filter for exactly that.</p>""",
	),
	(
		"Warranty",
		"Raising a claim that gets settled quickly",
		"""<p>A claim with evidence is settled faster than one without. What the approver is
looking for:</p>
<ol>
<li><b>What failed</b>, named as a part - "impeller", not "the pump".</li>
<li><b>What the technician found on dismantling.</b> One or two honest sentences.</li>
<li><b>Photographs of the failed part.</b> This is the whole argument. A picture of a burnt
winding or a scored impeller decides the claim.</li>
<li><b>The root cause</b>, if you know it. If you do not, say so rather than guessing -
a wrong cause slows the claim down more than an unknown one.</li>
</ol>
<p>Claims are reviewed, investigated by quality, approved, and then settled. You will see
each step on the claim itself, and you can ask a question on it at any point.</p>""",
	),
	# ----------------------------------------------------------- installation
	(
		"Installation",
		"Installing a submersible set so it does not come back",
		"""<ul>
<li><b>Never run it dry, not even for a second</b> to check rotation. Check rotation with
the set in water.</li>
<li><b>Keep it off the bottom</b> - at least three metres above the borewell floor, or it
sits in the silt and the pump becomes a sand pump.</li>
<li><b>Cable joints below water must be properly sealed.</b> Most "motor burnt within a
month" calls are a joint, not a motor.</li>
<li><b>Fit the control panel the customer paid for.</b> A set without dry-run protection
will eventually run dry, and that is not a warranty failure.</li>
</ul>
<p>Register the sale the same day and hand over the printed certificate. Print it from the
row in <b>What I Sold</b>.</p>""",
	),
	(
		"Installation",
		"Suction limits on a monobloc",
		"""<p>A monobloc lifts by suction, and physics puts a ceiling on it regardless of what the
motor can do.</p>
<ul>
<li>Practical suction lift is about <b>7 metres</b>, less in summer heat and at altitude.</li>
<li>Every bend and every metre of horizontal pipe costs you more lift.</li>
<li>Suction pipe should be at least the size of the suction port. Never smaller.</li>
<li>A foot valve is not optional.</li>
</ul>
<p>If the water is deeper than that, the customer needs a submersible or a jet set - not a
bigger monobloc. Selling a larger monobloc into a deep well produces a complaint within
the week and it is not a warranty failure.</p>""",
	),
	# ---------------------------------------------------------- using the desk
	(
		"Using this desk",
		"Registering a sale",
		"""<p><b>Register a Sale</b> in the sidebar. Scan the nameplate barcode with the Scan
button, or type the serial.</p>
<p>You need: your invoice number, the sale date, the customer's name and mobile, and where
the set is installed. The address matters - it is where a technician gets sent, and a
request carries no address of its own.</p>
<p>Registering produces the warranty certificate the customer keeps. Print it there, or
later from any row in <b>What I Sold</b>.</p>
<p><b>The warranty starts from the registration.</b> A set registered a month after it was
sold has a month less cover.</p>""",
	),
	(
		"Using this desk",
		"Raising a request, and which type to pick",
		"""<p>One form, and the first question is what you need:</p>
<ul>
<li><b>Complaint</b> - a set that is not working. Asks you which fault.</li>
<li><b>Installation</b> - a new set to be fitted.</li>
<li><b>Paid Service</b> - a visit on a set that is out of warranty.</li>
<li><b>Spare Part</b> - a part you need sent.</li>
<li><b>Enquiry</b> - anything else.</li>
</ul>
<p>Pick the pump first and the warranty position appears before you write anything, so you
can tell the customer on the phone whether the visit is free.</p>
<p>Attach photographs. Up to 8 MB each, and a video is fine. It is the fastest way to get
a technician sent with the right part in his bag.</p>
<p>Everything you raise appears under <b>My Tickets</b>, with KUMAR's replies on it. If you
reply to something already marked resolved, it reopens - you are never writing into a
thread nobody reads.</p>""",
	),
]


def build_all():
	"""Create the categories and articles that are missing. Never overwrites."""
	if not frappe.db.exists("DocType", "HD Article"):
		return {"skipped": "helpdesk is not installed"}

	made_categories, made_articles = [], []

	cat_ids = {}
	for name, description in CATEGORIES:
		existing = frappe.db.get_value("HD Article Category", {"category_name": name})
		if existing:
			cat_ids[name] = existing
			continue
		doc = frappe.get_doc(
			{
				"doctype": "HD Article Category",
				"category_name": name,
				"description": description,
			}
		)
		doc.flags.ignore_permissions = True
		doc.insert(ignore_permissions=True)
		cat_ids[name] = doc.name
		made_categories.append(name)

	for category, title, content in ARTICLES:
		if frappe.db.exists("HD Article", {"title": title}):
			continue
		doc = frappe.get_doc(
			{
				"doctype": "HD Article",
				"title": title,
				"category": cat_ids.get(category),
				"content": content,
				"status": "Published",
				"author": frappe.session.user,
			}
		)
		doc.flags.ignore_permissions = True
		doc.insert(ignore_permissions=True)
		made_articles.append(title)

	frappe.db.commit()
	return {"categories": made_categories, "articles": made_articles}
