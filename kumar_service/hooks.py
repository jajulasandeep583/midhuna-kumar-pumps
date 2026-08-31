app_name = "kumar_service"
app_title = "Kumar Service and Traceability"
app_publisher = "MIDHUNATECH"
app_description = "Serial and batch traceability, warranty and dealer service management for KUMAR Pumps"
app_email = "aimidhunatech@gmail.com"
app_license = "mit"

required_apps = ["erpnext"]

# ------------------------------------------------------------------ includes

# Bundled, not raw /assets paths. The bundler stamps a content hash into the
# built filename, so a rebuild changes the URL and browsers pick the new file
# up immediately. Raw paths were served with a 12-hour max-age and no hash,
# which left the management screens running stale CSS after every deploy.
app_include_css = "kumar.bundle.css"
app_include_js = "kumar.bundle.js"  # pulls in kumar_common.js + kumar_dashboard.js

# Purpose-drawn icon set, so every doctype, workspace and shortcut reads as a
# pump plant rather than sharing one generic glyph.
app_include_icons = ["/assets/kumar_service/icons/kumar-icons.svg"]

add_to_apps_screen = [
	{
		"name": app_name,
		# a real standalone image - the icon sprite is display:none and renders blank
		"logo": "/assets/kumar_service/images/kumar-logo.svg",
		"title": "KUMAR Pumps",
		"route": "/app/dealer-desk",
	}
]

doctype_js = {
	"Serial No": "public/js/serial_no.js",
	"Stock Entry": "public/js/stock_entry.js",
	"Service Request": "public/js/service_request.js",
	"Pump Registration": "public/js/pump_registration.js",
	"Pump Test Certificate": "public/js/pump_test_certificate.js",
	"Heat Record": "public/js/heat_record.js",
	"Kumar Warranty Claim": "public/js/warranty_claim.js",
	"Sales Invoice": "public/js/sales_invoice.js",
}

# ------------------------------------------------------------------- jinja

# frappe exposes these under their own function names - it has no alias syntax
jinja = {
	"methods": [
		"kumar_service.utils.qr_base64",
		"kumar_service.utils.qr_url_for",
	]
}

# ------------------------------------------------------------------- events

doc_events = {
	"Stock Entry": {
		"validate": "kumar_service.traceability.validate_qc_before_dispatch",
		"on_submit": "kumar_service.traceability.capture_genealogy",
		"on_cancel": "kumar_service.traceability.clear_genealogy",
	},
	"Delivery Note": {
		"validate": "kumar_service.traceability.validate_qc_before_dispatch",
		"on_submit": "kumar_service.traceability.mark_dispatched",
	},
	"Sales Invoice": {
		"on_submit": "kumar_service.warranty.auto_register_from_invoice",
	},
	# KUMAR Pumps Desk mirrors every request as an HD Ticket. The bridge is a
	# no-op when helpdesk is not installed, and never blocks a save.
	"Service Request": {
		"after_insert": "kumar_service.desk_bridge.mirror",
		"on_update": "kumar_service.desk_bridge.mirror",
		"on_submit": "kumar_service.desk_bridge.mirror",
	},
	"HD Ticket": {
		"on_update": "kumar_service.desk_bridge.set_status",
	},
}

# -------------------------------------------------------------- permissions

permission_query_conditions = {
	"Service Request": "kumar_service.permissions.service_request_query",
	"Pump Registration": "kumar_service.permissions.pump_registration_query",
	"Kumar Warranty Claim": "kumar_service.permissions.warranty_claim_query",
	"Serial No": "kumar_service.permissions.serial_no_query",
	"Dealer": "kumar_service.permissions.dealer_query",
	# Service Visit has no dealer field of its own; scoped via its ticket
	"Service Visit": "kumar_service.permissions.service_visit_query",
	"Pump Test Certificate": "kumar_service.permissions.test_certificate_query",
}

has_permission = {
	"Service Request": "kumar_service.permissions.service_request_has_permission",
	"Pump Registration": "kumar_service.permissions.pump_registration_has_permission",
	"Kumar Warranty Claim": "kumar_service.permissions.warranty_claim_has_permission",
	# the Dealer list was scoped by permission_query_conditions, but a direct
	# read of one Dealer document was not - see dealer_has_permission
	"Dealer": "kumar_service.permissions.dealer_has_permission",
	"Service Visit": "kumar_service.permissions.service_visit_has_permission",
	"Pump Test Certificate": "kumar_service.permissions.test_certificate_has_permission",
}

# --------------------------------------------------------------- scheduler

scheduler_events = {
	"daily": [
		"kumar_service.tasks.update_warranty_status",
		"kumar_service.tasks.send_expiry_reminders",
		"kumar_service.tasks.flag_sla_breaches",
	],
	"weekly": [
		"kumar_service.tasks.batch_failure_scan",
	],
}

# ---------------------------------------------------------------- website

# the page controllers live in files named with underscores - a hyphen in the
# filename cannot be imported, and the controller is silently skipped
website_route_rules = [
	{"from_route": "/warranty-check", "to_route": "warranty_check"},
	{"from_route": "/dealer-portal", "to_route": "dealer_portal"},
]

# ---------------------------------------------------------------- fixtures

fixtures = [
	{"dt": "Custom Field", "filters": [["module", "=", "Kumar Service"]]},
	{"dt": "Property Setter", "filters": [["module", "=", "Kumar Service"]]},
	{
		"dt": "Role",
		"filters": [
			[
				"name",
				"in",
				[
					"Dealer",
					"Dealer Manager",
					"Service Technician",
					"Service Manager",
					"Quality Engineer",
					"Warranty Approver",
					"Production Manager",
					"Foundry Operator",
				],
			]
		],
	},
	{"dt": "Workflow", "filters": [["name", "like", "Kumar%"]]},
	{"dt": "Print Format", "filters": [["module", "=", "Kumar Service"]]},
	{"dt": "Number Card", "filters": [["module", "=", "Kumar Service"]]},
	{"dt": "Dashboard Chart", "filters": [["module", "=", "Kumar Service"]]},
	{"dt": "Pump Category"},
]

after_install = "kumar_service.install.after_install"
after_migrate = "kumar_service.install.after_migrate"
