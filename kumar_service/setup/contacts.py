"""Who a dealer rings at KUMAR.

The portal's Contact KUMAR screen is built from the dealer tree - a dealer sees
their own branch office, the head office, and their nearest service centre - so
it is only as good as the contact fields on those Dealer records. The seed left
the head office with an empty contact_person and mobile, which rendered a card
with a name and nothing to ring.

This fills the KUMAR-owned rungs of the tree (head office, branches, service
centres) with a named person and a reachable number. It never touches an
independent dealer's own details: those belong to the shop, not to us.

	bench --site kumarpumps.localhost execute kumar_service.setup.contacts.build_all
"""

import frappe

#: dealer name -> (contact person, mobile, landline, email)
#: Landlines carry real STD codes for the town they sit in, so the card reads
#: like a KUMAR letterhead rather than filler.
KUMAR_CONTACTS = {
	"KUMAR Network": (
		"Service Head - Head Office", "9490759000", "0864-2233100",
		"service@kumarpumps.co.in",
	),
	"Aruna Jyothi Distributors - Secunderabad": (
		"P. Ramesh Babu - Branch Manager", "9490759500", "040-27812345",
		"secunderabad@kumarpumps.co.in",
	),
	"Aruna Jyothi Distributors - Visakhapatnam": (
		"K. Satyanarayana - Branch Manager", "9490759511", "0891-2564321",
		"visakhapatnam@kumarpumps.co.in",
	),
	"Aruna Jyothi Distributors - Vijayawada": (
		"M. Srinivas Rao - Branch Manager", "9490759522", "0866-2471234",
		"vijayawada@kumarpumps.co.in",
	),
	"Aruna Jyothi Distributors - Tenali": (
		"B. Venkateswarlu - Branch Manager", "9490759533", "0864-2251234",
		"tenali@kumarpumps.co.in",
	),
	"Aruna Jyothi Distributors - Tirupati": (
		"G. Prasad - Branch Manager", "9490759544", "0877-2287654",
		"tirupati@kumarpumps.co.in",
	),
	"Coastal Irrigation Systems": (
		"A. Mahesh - Service Centre In-charge", "9848445566", "0891-2701188",
		"service.vizag@kumarpumps.co.in",
	),
}


def build_all():
	"""Fill in the KUMAR-side contact details. Safe to run again."""
	filled = []
	for dealer, (person, mobile, landline, email) in KUMAR_CONTACTS.items():
		if not frappe.db.exists("Dealer", dealer):
			continue
		values = {
			"contact_person": person,
			"mobile_no": mobile,
			"landline": landline,
			"email_id": email,
		}
		# only write what is actually missing or different, so a real deployment
		# that has edited these keeps its own numbers
		current = frappe.db.get_value("Dealer", dealer, list(values), as_dict=True) or {}
		changed = {k: v for k, v in values.items() if not (current.get(k) or "").strip()}
		if changed:
			frappe.db.set_value("Dealer", dealer, changed, update_modified=False)
			filled.append(f"{dealer} ({', '.join(changed)})")
	frappe.db.commit()
	print("  + contact details filled on %d outlet(s)" % len(filled))
	for f in filled:
		print("    -", f)
	return filled


run = build_all
