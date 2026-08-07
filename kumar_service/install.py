"""Install / migrate entry points.

DocTypes ship as JSON and are synced by Frappe itself. Everything here is the
*data* an empty site needs to be usable: roles, custom fields, masters,
settings, workflow, workspaces.
"""

import frappe

ROLES = (
	"Dealer",
	"Dealer Manager",
	"Service Technician",
	"Service Manager",
	"Quality Engineer",
	"Warranty Approver",
	"Production Manager",
	"Foundry Operator",
)


def before_install():
	create_roles()


def after_install():
	create_roles()
	run_data_setup()


def after_migrate():
	create_roles()
	run_data_setup()


def create_roles():
	from kumar_service.setup.common import ensure_role

	for role in ROLES:
		ensure_role(role)
	frappe.db.commit()


def run_data_setup():
	"""Idempotent. Safe on every migrate."""
	from kumar_service.setup import (
		custom_fields,
		desktop_icons,
		icons,
		masters,
		print_formats,
		reports,
		workflows,
		workspaces,
	)

	if not frappe.db.exists("DocType", "Pump Model"):
		# first bootstrap: DocTypes are not synced yet, nothing to seed into
		print("KUMAR DocTypes not present yet - skipping data setup")
		return

	custom_fields.build_all()
	masters.build_all()
	workflows.build_all()
	reports.build_all()
	print_formats.build_all()
	# workspaces before icons: icons stamp the rows the workspaces just created
	workspaces.build_all()

	# Frappe builds the desk sidebar (and its icon rows) only at app-install
	# time. Our workspaces are created after that, so the sidebar never learns
	# about them and the icons have nothing to attach to - build it here.
	from frappe.utils.install import auto_generate_icons_and_sidebar

	auto_generate_icons_and_sidebar()

	icons.install()
	desktop_icons.install()
	frappe.db.commit()


def build_from_code():
	"""Dev-time only: (re)generate the DocType JSON from setup/doctypes.py.

	Requires developer_mode. Normal installs never call this - they read the
	JSON that this produced.
	"""
	if not frappe.conf.get("developer_mode"):
		frappe.throw("developer_mode must be on to regenerate DocTypes from code")

	from kumar_service.setup import doctypes

	create_roles()
	doctypes.build_all()
	run_data_setup()
	frappe.db.commit()
	print("DocTypes and data rebuilt from code")
