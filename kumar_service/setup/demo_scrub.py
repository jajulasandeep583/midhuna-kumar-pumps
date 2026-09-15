"""Take the test driving out of the demo data.

Clicking around a demo site leaves real records behind: a dozen "Customer rang:
pump trips on start" requests on one pump, each with a visit booked, and the
dealer's Upcoming visits reads as though KUMAR is sending the same man to the
same pump seven times. The seeded story is fine - it is everything raised AFTER
it that has to go.

So this removes work created after a cutoff (default: everything newer than the
seeded month) and, with it, the visits, tickets, comments and communications
hanging off it. It never touches the seed.

	bench --site kumarpumps.localhost execute kumar_service.setup.demo_scrub.run
	# or, to preview:
	bench --site kumarpumps.localhost execute kumar_service.setup.demo_scrub.preview

Run it before a demo, after any session of clicking about. See also
setup.demo_story.build_all, which re-dates the seeded story onto today.
"""

import frappe

#: Anything raised on or after this is test driving, not the seeded story. The
#: seed builds a month ending 2026-08-07 and demo_story re-dates it; nothing the
#: seed owns is created after that run.
DEFAULT_CUTOFF = "2026-09-08"


def _residue(cutoff):
	requests = frappe.get_all(
		"Service Request", filters={"creation": [">=", cutoff]}, pluck="name"
	)
	claims = frappe.get_all(
		"Kumar Warranty Claim", filters={"creation": [">=", cutoff]}, pluck="name"
	)
	return requests, claims


def preview(cutoff=None):
	cutoff = cutoff or DEFAULT_CUTOFF
	requests, claims = _residue(cutoff)
	visits = frappe.get_all(
		"Service Visit", filters={"service_request": ["in", requests or [""]]}, pluck="name"
	)
	print(f"residue created on/after {cutoff}:")
	print(f"  service requests : {len(requests)}")
	print(f"  warranty claims  : {len(claims)}")
	print(f"  service visits   : {len(visits)}")
	return {"requests": requests, "claims": claims, "visits": visits}


def _drop(doctype, name):
	"""Delete one document and the thread hanging off it."""
	if not frappe.db.exists(doctype, name):
		return
	for dt in ("Comment", "Communication"):
		for row in frappe.get_all(
			dt, filters={"reference_doctype": doctype, "reference_name": name}, pluck="name"
		):
			frappe.delete_doc(dt, row, force=True, ignore_permissions=True)
	if frappe.db.get_value(doctype, name, "docstatus") == 1:
		frappe.db.set_value(doctype, name, "docstatus", 2, update_modified=False)
	frappe.delete_doc(
		doctype, name, force=True, ignore_permissions=True, ignore_on_trash=True
	)


def run(cutoff=None):
	cutoff = cutoff or DEFAULT_CUTOFF
	requests, claims = _residue(cutoff)
	counts = {"tickets": 0, "visits": 0, "claims": 0, "requests": 0}

	# tickets first: they point at the documents below them
	for field, names in (("custom_service_request", requests), ("custom_warranty_claim", claims)):
		if not names or not frappe.db.exists("DocType", "HD Ticket"):
			continue
		for tk in frappe.get_all("HD Ticket", filters={field: ["in", names]}, pluck="name"):
			_drop("HD Ticket", tk)
			counts["tickets"] += 1

	for v in frappe.get_all(
		"Service Visit", filters={"service_request": ["in", requests or [""]]}, pluck="name"
	):
		_drop("Service Visit", v)
		counts["visits"] += 1

	for c in claims:
		# a claim stamps linked_claim on its request; clear it before the request goes
		sr = frappe.db.get_value("Kumar Warranty Claim", c, "service_request")
		if sr and frappe.db.exists("Service Request", sr):
			frappe.db.set_value("Service Request", sr, "linked_claim", None, update_modified=False)
		_drop("Kumar Warranty Claim", c)
		counts["claims"] += 1

	for r in requests:
		_drop("Service Request", r)
		counts["requests"] += 1

	frappe.db.commit()
	print(
		"  + scrubbed: %(requests)d requests, %(claims)d claims, %(visits)d visits, "
		"%(tickets)d tickets" % counts
	)
	return counts
