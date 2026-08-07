"""Workspace header icons - the tiles on the /apps desk screen.

Frappe's sidebar_header.set_header_icon() assigns the Workspace Sidebar's
header_icon and then immediately overwrites it with a generated letter tile, so
that field never reaches the screen. The only path that renders a real image is
a Desktop Icon whose label matches the sidebar title, backed by a file at
  <app>/public/icons/desktop_icons/{solid,subtle}/<scrub(label)>.svg
which frappe indexes into boot.desktop_icon_urls.

So each workspace gets a proper 54x54 tile, generated from the same glyph
geometry as the sprite so the desk and the tile always agree.
"""

import os
import re

import frappe

from kumar_service.setup.icons import WORKSPACE_ICONS

# Only the tile colour lives here. The SYMBOL is read from WORKSPACE_ICONS, so
# the tile on the apps screen and the glyph in the sidebar cannot disagree -
# they did once, when Production was moved to the factory glyph in one file and
# left as a pump in this one.
TILE_COLOURS = {
	"Management": "#0B5394",
	"Dealer Desk": "#EA580C",
	"Service Desk": "#0284C7",
	"Warranty": "#16A34A",
	"Traceability": "#0D9488",
	"Production": "#1D4ED8",
	"Masters": "#475569",
}

# workspace -> (sprite symbol, tile colour)
TILES = {
	label: (WORKSPACE_ICONS[label], colour)
	for label, colour in TILE_COLOURS.items()
	if label in WORKSPACE_ICONS
}

# the rounded square erpnext uses, so our tiles sit in the same grid
SQUIRCLE = (
	"M38.5714 0H15.4286C6.90761 0 0 6.90761 0 15.4286V38.5714C0 47.0924 6.90761 54 "
	"15.4286 54H38.5714C47.0924 54 54 47.0924 54 38.5714V15.4286C54 6.90761 47.0924 0 "
	"38.5714 0Z"
)

SCALE = 1.45  # 24 -> 34.8 within a 54 canvas
OFFSET = (54 - 24 * SCALE) / 2


def glyphs():
	"""Pull each symbol's inner geometry straight out of the sprite."""
	path = frappe.get_app_path("kumar_service", "public", "icons", "kumar-icons.svg")
	with open(path, encoding="utf-8") as fh:
		src = fh.read()
	out = {}
	for m in re.finditer(
		r'<symbol[^>]*id="icon-(kumar-[a-z0-9-]+)"[^>]*>(.*?)</symbol>', src, re.S
	):
		out[m.group(1)] = m.group(2).strip()
	return out


def tile(inner, colour, solid):
	bg = (
		'<path d="%s" fill="%s"/>' % (SQUIRCLE, colour)
		if solid
		else '<path d="%s" fill="%s" fill-opacity="0.12"/>' % (SQUIRCLE, colour)
	)
	stroke = "#FFFFFF" if solid else colour
	return (
		'<svg width="54" height="54" viewBox="0 0 54 54" fill="none" '
		'xmlns="http://www.w3.org/2000/svg">\n'
		"%s\n"
		'<g transform="translate(%.2f %.2f) scale(%s)" fill="none" '
		'stroke="%s" stroke-width="1.9" stroke-linecap="round" '
		'stroke-linejoin="round">\n%s\n</g>\n</svg>\n'
		% (bg, OFFSET, OFFSET, SCALE, stroke, inner)
	)


def write_tile_files():
	"""Regenerate the tile SVGs from the sprite.

	The generated files are COMMITTED, so a deployed site never needs this to
	run. Failures are swallowed on purpose: they must never abort the rest of
	setup, or the Desktop Icon records go missing and the desk falls back to
	letter tiles.
	"""
	written = 0
	try:
		g = glyphs()
		base = frappe.get_app_path("kumar_service", "public", "icons", "desktop_icons")
		for variant in ("solid", "subtle"):
			os.makedirs(os.path.join(base, variant), exist_ok=True)
		for label, (symbol, colour) in TILES.items():
			inner = g.get(symbol)
			if not inner:
				print("  ! no glyph for %s" % symbol)
				continue
			fname = frappe.scrub(label) + ".svg"
			for variant, solid in (("solid", True), ("subtle", False)):
				target = os.path.join(base, variant, fname)
				content = tile(inner, colour, solid)
				if os.path.exists(target):
					with open(target, encoding="utf-8") as fh:
						if fh.read() == content:
							continue
				with open(target, "w", encoding="utf-8") as fh:
					fh.write(content)
				written += 1
	except OSError as e:
		print("  ! app tree not writable (%s) - keeping the committed tile files" % e)
		return
	print("  + desktop icon files refreshed: %d" % written)


def install():
	# Records first, files last: the records are what make the tiles render,
	# and the file write may legitimately fail on a read-only app tree.
	made = 0
	for label, (symbol, _colour) in TILES.items():
		if not frappe.db.exists("Workspace", label):
			continue
		name = frappe.db.get_value("Desktop Icon", {"label": label})
		doc = frappe.get_doc("Desktop Icon", name) if name else frappe.new_doc("Desktop Icon")
		if not name:
			doc.label = label
		doc.app = "kumar_service"
		doc.icon = symbol
		doc.icon_type = "Link"
		doc.standard = 1
		doc.hidden = 0
		# Each workspace stands on its own on the desk. Nested under the app
		# tile they do not appear there at all.
		doc.parent_icon = None
		# Link through the Workspace Sidebar, never as "External": v16 prefixes
		# an External icon's link with the origin, opens it in a NEW TAB, and
		# drops it from the app-switcher menu.
		doc.link = None
		if frappe.db.exists("Workspace Sidebar", label):
			doc.link_type = "Workspace Sidebar"
			doc.link_to = label
			doc.sidebar = label
		doc.flags.ignore_permissions = True
		doc.save()
		made += 1

	# Frappe generates an "App"-type icon for every installed app from the
	# add_to_apps_screen hook. Ours carries the generic cube and a label long
	# enough to overlap the tile next to it, and it only duplicates the six
	# workspace tiles above - so hide it.
	for label in ("Kumar Service and Traceability", "KUMAR Pumps", "kumar_service"):
		name = frappe.db.get_value("Desktop Icon", {"label": label, "icon_type": "App"})
		if name:
			frappe.db.set_value("Desktop Icon", name, "hidden", 1, update_modified=False)
			print("  + hid duplicate app tile: %s" % label)

	prune_stale_tiles()

	frappe.db.commit()
	frappe.clear_cache()
	print("  + desktop icon records: %d" % made)

	write_tile_files()


def prune_stale_tiles():
	"""Drop tiles for workspaces that were renamed away.

	Renaming a workspace leaves its old Desktop Icon behind, and nothing ever
	cleaned those up - so the apps screen carried "KUMAR Masters" beside
	"Masters", "Warranty & Claims" beside "Warranty", and so on. Worse, the
	strays point at tile files that no longer exist, so they draw as a broken
	image rather than an icon.

	Identified by the KUMAR glyph they carry: an old tile of ours always has a
	`kumar-*` icon, and never the app+standard stamp that install() writes.
	Nothing belonging to frappe or erpnext can match.
	"""
	removed = []
	for row in frappe.get_all(
		"Desktop Icon", filters={"icon": ["like", "kumar-%"]}, fields=["name", "label", "app"]
	):
		if row.label in TILES and row.app == "kumar_service":
			continue
		frappe.delete_doc(
			"Desktop Icon", row.name, force=True, ignore_permissions=True, delete_permanently=True
		)
		removed.append(row.label)
	if removed:
		print("  + removed %d stale desktop tile(s): %s" % (len(removed), ", ".join(removed)))
	return removed


run = install
