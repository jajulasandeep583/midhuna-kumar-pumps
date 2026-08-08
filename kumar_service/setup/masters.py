"""Seed masters from the company's own brochure and plant history.

Everything here is idempotent and safe to re-run on migrate.
"""

import frappe
from frappe.utils import cint, flt

from kumar_service.setup.common import upsert

COMPANY = "Sri Lakshmi Ganapathi Engineering Works"
ABBR = "SLGEW"

CATEGORIES = [
	("Piston Pumps", "PP", 12),
	("Electrical Motors", "MOT", 12),
	("Submersible Pumps", "SUB", 18),
	# The brochure lists openwell separately and for a real reason: an openwell
	# unit runs an ALUMINIUM rotor where a borewell unit runs copper. Same
	# warranty as borewell, so recategorising a model does not move its expiry.
	("Openwell Submersible Pumps", "OWS", 18),
	("Centrifugal Monobloc", "CMB", 12),
	("Agricultural Monobloc", "AMB", 12),
	("High Pressure Pumps", "HPP", 12),
	("3-Plunger Pumps", "3PL", 12),
	("Booster Pumps", "BP", 12),
	("Self-Priming Monobloc", "SPM", 12),
	("Jet Monobloc", "JM", 12),
	("Engine Driven Pumps", "EDP", 12),
	("Hand Pumps", "HP", 6),
]

# model_code, category, family, hp, phase, rpm, suction, delivery, head_min, head_max,
# disch_min, disch_max, uom, impeller, bis
MODELS = [
	("KPP075", "Piston Pumps", "PP", 0.5, "Single Phase", 1440, "1", "1", 39, 39, 1980, 1980, "LPH", "Cast Iron", "IS 8034"),
	("KPP100", "Piston Pumps", "PP", 1.0, "Single Phase", 1440, "1", "1", 39, 39, 3120, 3120, "LPH", "Cast Iron", "IS 8034"),
	("KPP125", "Piston Pumps", "PP", 1.5, "Single Phase", 1440, "1", "1", 39, 39, 4300, 4300, "LPH", "Cast Iron", "IS 8034"),
	("KPPS075", "High Pressure Pumps", "PPS", 1.0, "Single Phase", 250, "1", "1", 0, 0, 0, 0, "LPM", "Gunmetal", ""),
	("KPPS100", "High Pressure Pumps", "PPS", 2.0, "Three Phase", 250, "1", "1", 0, 0, 0, 0, "LPM", "Gunmetal", ""),
	("KPPS3PLG", "3-Plunger Pumps", "PPS3PLG", 2.0, "Three Phase", 700, "1", "1", 0, 0, 0, 0, "LPM", "Stainless Steel", ""),
	("KBP05SW/24", "Booster Pumps", "BP", 0.5, "Single Phase", 2880, "1", "1", 0, 0, 1500, 1500, "LPH", "Thermoplastic", ""),
	("KBP05SW/35", "Booster Pumps", "BP", 0.5, "Single Phase", 2880, "1", "1", 0, 0, 2000, 2000, "LPH", "Thermoplastic", ""),
	("KJM05GISB", "Jet Monobloc", "JM", 0.5, "Single Phase", 2880, "1.25", "1", 9, 21, 900, 1368, "LPH", "Gunmetal", "IS 9079"),
	("KJM05CISB", "Jet Monobloc", "JM", 0.5, "Single Phase", 2880, "1.25", "1", 9, 21, 900, 1368, "LPH", "Cast Iron", "IS 9079"),
	("KJM10GISB", "Jet Monobloc", "JM", 1.0, "Single Phase", 2880, "1.25", "1", 9, 39, 468, 1368, "LPH", "Gunmetal", "IS 9079"),
	("KJM15GISB", "Jet Monobloc", "JM", 1.5, "Single Phase", 2880, "1.25", "1", 10, 50, 468, 1368, "LPH", "Gunmetal", "IS 9079"),
	("KJM10DGI", "Jet Monobloc", "JM", 1.0, "Single Phase", 2880, "1.25", "1", 30, 50, 420, 900, "LPH", "Gunmetal", "IS 9079"),
	("KJM15DCI", "Jet Monobloc", "JM", 1.5, "Single Phase", 2880, "1.25", "1", 30, 60, 450, 1100, "LPH", "Cast Iron", "IS 9079"),
	("KJM20DGI", "Jet Monobloc", "JM", 2.0, "Single Phase", 2880, "1.25", "1", 30, 70, 450, 1100, "LPH", "Gunmetal", "IS 9079"),
	("KSMB05", "Self-Priming Monobloc", "SMB", 0.5, "Single Phase", 1440, "1", "1", 6, 18, 31, 52, "LPM", "Gunmetal", "IS 8472"),
	("KSMB05N", "Self-Priming Monobloc", "SMB", 0.5, "Single Phase", 1440, "1", "1", 6, 18, 31, 52, "LPM", "Cast Iron", "IS 8472"),
	("KSMB10", "Self-Priming Monobloc", "SMB", 1.0, "Single Phase", 1440, "1", "1", 6, 36, 30, 59, "LPM", "Gunmetal", "IS 8472"),
	("KSMB10N", "Self-Priming Monobloc", "SMB", 1.0, "Single Phase", 1440, "1", "1", 6, 36, 30, 59, "LPM", "Cast Iron", "IS 8472"),
	("KHMB05HF", "Centrifugal Monobloc", "HMB", 0.5, "Single Phase", 2880, "1", "1", 30, 50, 1440, 2520, "LPH", "Gunmetal", "IS 9079"),
	("KHMB05SW", "Centrifugal Monobloc", "HMB", 0.5, "Single Phase", 2880, "1", "1", 16, 28, 1800, 3600, "LPH", "Gunmetal", "IS 9079"),
	("KHMB05CP", "Centrifugal Monobloc", "HMB", 0.5, "Single Phase", 2880, "1", "1", 18, 29, 1800, 2520, "LPH", "Cast Iron", "IS 9079"),
	("KHMB05MMB", "Centrifugal Monobloc", "HMB", 0.5, "Single Phase", 2880, "1", "1", 3, 30, 750, 3700, "LPH", "Thermoplastic", "IS 9079"),
	("KHMB05(1x1)", "Centrifugal Monobloc", "HMB", 0.5, "Single Phase", 2880, "1", "1", 6, 22, 35, 90, "LPM", "Gunmetal", "IS 9079"),
	("KHMB05(1.5x1.5)", "Centrifugal Monobloc", "HMB", 0.5, "Single Phase", 2880, "1.5", "1.5", 6, 9, 180, 220, "LPM", "Gunmetal", "IS 9079"),
	("KHMB05(2x2)", "Centrifugal Monobloc", "HMB", 0.5, "Single Phase", 2880, "2", "2", 6, 9, 120, 275, "LPM", "Gunmetal", "IS 9079"),
	("KHMB10(1x1)", "Centrifugal Monobloc", "HMB", 1.0, "Single Phase", 2880, "1", "1", 20, 33, 40, 100, "LPM", "Gunmetal", "IS 9079"),
	("KHMB10(1.5x1.5)", "Centrifugal Monobloc", "HMB", 1.0, "Single Phase", 2880, "1.5", "1.5", 6, 15, 136, 329, "LPM", "Gunmetal", "IS 9079"),
	("KHMB10(2x2)", "Centrifugal Monobloc", "HMB", 1.0, "Single Phase", 2880, "2", "2", 6, 12, 125, 422, "LPM", "Gunmetal", "IS 9079"),
	("KHMB15DGI(1.25x1)", "Centrifugal Monobloc", "HMB", 1.5, "Single Phase", 2880, "1.25", "1", 38, 42, 32, 72, "LPM", "Gunmetal", "IS 9079"),
	("KHMB15(2x2)", "Centrifugal Monobloc", "HMB", 1.5, "Single Phase", 2880, "2", "2", 6, 14, 250, 470, "LPM", "Gunmetal", "IS 9079"),
	("KHMB15(2.5x2)", "Centrifugal Monobloc", "HMB", 1.5, "Single Phase", 2880, "2.5", "2", 6, 13, 200, 560, "LPM", "Gunmetal", "IS 9079"),
	("KHMB20DGI(1.5x1.25)", "Centrifugal Monobloc", "HMB", 2.0, "Single Phase", 2880, "1.5", "1.25", 49, 52, 50, 85, "LPM", "Gunmetal", "IS 9079"),
	("KHMB20(2x2)", "Centrifugal Monobloc", "HMB", 2.0, "Single Phase", 2880, "2", "2", 6, 18, 260, 490, "LPM", "Gunmetal", "IS 9079"),
	("KHMB20(2.5x2)", "Centrifugal Monobloc", "HMB", 2.0, "Single Phase", 2880, "2.5", "2", 6, 15, 330, 654, "LPM", "Gunmetal", "IS 9079"),
	("KHMB20(3x2.5)", "Centrifugal Monobloc", "HMB", 2.0, "Single Phase", 2880, "3", "2.5", 6, 12, 500, 900, "LPM", "Gunmetal", "IS 9079"),
	("KSMB20P3(3x3)", "Agricultural Monobloc", "SMB", 2.0, "Three Phase", 1440, "3", "3", 6, 11, 7.2, 18.5, "LPS", "Gunmetal", "IS 9079"),
	("KSMB20P3(4x4)", "Agricultural Monobloc", "SMB", 2.0, "Three Phase", 1440, "4", "4", 6, 8, 16.2, 24, "LPS", "Gunmetal", "IS 9079"),
	("KSMB30P3(3x2.5)", "Agricultural Monobloc", "SMB", 3.0, "Three Phase", 1440, "3", "2.5", 6, 13, 11, 18, "LPS", "Gunmetal", "IS 9079"),
	("KSMB30P3(4x3)", "Agricultural Monobloc", "SMB", 3.0, "Three Phase", 1440, "4", "3", 6, 12, 12.5, 25, "LPS", "Gunmetal", "IS 9079"),
	("KSMB30P3(4x4)", "Agricultural Monobloc", "SMB", 3.0, "Three Phase", 1440, "4", "4", 6, 10, 17, 30, "LPS", "Gunmetal", "IS 9079"),
	("KSMB50P3(3x3)", "Agricultural Monobloc", "SMB", 5.0, "Three Phase", 1440, "3", "3", 6, 15, 16, 28, "LPS", "Gunmetal", "IS 9079"),
	("KSMB50P3(4x3)", "Agricultural Monobloc", "SMB", 5.0, "Three Phase", 1440, "4", "3", 6, 15, 16, 30, "LPS", "Gunmetal", "IS 9079"),
	("KSMB50P3(4x4)", "Agricultural Monobloc", "SMB", 5.0, "Three Phase", 1440, "4", "4", 6, 14, 14, 33, "LPS", "Gunmetal", "IS 9079"),
	("KSMB50P3(6x6)", "Agricultural Monobloc", "SMB", 5.0, "Three Phase", 1440, "6", "6", 6, 6, 43.4, 43.4, "LPS", "Gunmetal", "IS 9079"),
	("KSMB75P3(4x3)", "Agricultural Monobloc", "SMB", 7.5, "Three Phase", 1440, "4", "3", 10, 20, 15.5, 36, "LPS", "Gunmetal", "IS 9079"),
	("KSMB75P3(6x6)", "Agricultural Monobloc", "SMB", 7.5, "Three Phase", 1440, "6", "6", 6, 11, 30, 60, "LPS", "Gunmetal", "IS 9079"),
	("KHMB30P3(2.5x2)", "Agricultural Monobloc", "HMB", 3.0, "Three Phase", 2880, "2.5", "2", 13, 23, 4.0, 12, "LPS", "Gunmetal", "IS 9079"),
	("KHMB50P3(3x2.5)", "Agricultural Monobloc", "HMB", 5.0, "Three Phase", 2880, "3", "2.5", 12, 16, 13.1, 15.6, "LPS", "Gunmetal", "IS 9079"),
	("KHMB50HHP3(2.5x2)", "Agricultural Monobloc", "HMB", 5.0, "Three Phase", 2880, "2.5", "2", 26, 35, 8.5, 12.1, "LPS", "Gunmetal", "IS 9079"),
	("KHMB75P3(4x3)", "Agricultural Monobloc", "HMB", 7.5, "Three Phase", 2880, "4", "3", 10, 21, 18, 31.5, "LPS", "Gunmetal", "IS 9079"),
	("KHMB100P3(4x3)", "Agricultural Monobloc", "HMB", 10.0, "Three Phase", 2880, "4", "3", 19, 35, 19, 28, "LPS", "Gunmetal", "IS 9079"),
	("KV4-1P-100-1.25", "Submersible Pumps", "V4", 1.0, "Single Phase", 2880, "", "1.25", 22, 90, 12, 108, "LPM", "Stainless Steel", "IS 8034"),
	("KV4-1P-150-1.25", "Submersible Pumps", "V4", 1.5, "Single Phase", 2880, "", "1.25", 30, 130, 12, 90, "LPM", "Stainless Steel", "IS 8034"),
	("KV4-3P-300-1.5", "Submersible Pumps", "V4", 3.0, "Three Phase", 2880, "", "1.5", 31, 100, 42, 150, "LPM", "Stainless Steel", "IS 8034"),
	("KV4-3P-500-2", "Submersible Pumps", "V4", 5.0, "Three Phase", 2880, "", "2", 15, 48, 180, 252, "LPM", "Stainless Steel", "IS 8034"),
	("KV6-3P-750-3", "Submersible Pumps", "V6", 7.5, "Three Phase", 2880, "", "3", 15, 140, 168, 1080, "LPM", "Stainless Steel", "IS 8034"),
	("KV6-3P-1250-4", "Submersible Pumps", "V6", 12.5, "Three Phase", 2880, "", "4", 17, 42, 300, 1200, "LPM", "Stainless Steel", "IS 8034"),
	("KOW-1P-100-1", "Submersible Pumps", "V4", 1.0, "Single Phase", 2880, "", "1", 12, 22, 60, 174, "LPM", "Cast Iron", "IS 8034"),
	("KOW-3P-500-2.5", "Submersible Pumps", "V4", 5.0, "Three Phase", 2880, "", "2.5", 8, 27, 300, 1890, "LPM", "Cast Iron", "IS 8034"),
	("KHAND-2", "Hand Pumps", "HAND", 0.0, "", 0, "", "2", 0, 0, 0, 0, "LPM", "Cast Iron", "IS 9301"),
	("KHAND-4", "Hand Pumps", "HAND", 0.0, "", 0, "", "4", 0, 0, 0, 0, "LPM", "Cast Iron", "IS 9301"),
	("KHAND-6", "Hand Pumps", "HAND", 0.0, "", 0, "", "6", 0, 0, 0, 0, "LPM", "Cast Iron", "IS 9301"),
	("KMOT-1P-100", "Electrical Motors", "MOTOR", 1.0, "Single Phase", 1440, "", "", 0, 0, 0, 0, "LPM", "", "IS 7538"),
	("KMOT-3P-300", "Electrical Motors", "MOTOR", 3.0, "Three Phase", 1440, "", "", 0, 0, 0, 0, "LPM", "", "IS 7538"),
	("KMOT-3P-500", "Electrical Motors", "MOTOR", 5.0, "Three Phase", 2880, "", "", 0, 0, 0, 0, "LPM", "", "IS 7538"),
	("KEDP-50-3x2.5", "Engine Driven Pumps", "ENGINE", 5.0, "", 1500, "3", "2.5", 6, 12, 900, 1320, "LPM", "Gunmetal", ""),
	("KEDP-75-6x6", "Engine Driven Pumps", "ENGINE", 7.5, "", 1500, "6", "6", 6, 11, 1800, 3600, "LPM", "Gunmetal", ""),

	# ------------------------------------------------------------------ 2026-08-08
	# Everything below is read off the performance tables in the 2025 brochure,
	# which gives ranges per bore size / delivery size / phase rather than model
	# codes. The codes follow the scheme already in use above -
	# K<family>-<phase>-<HP x 100>-<delivery> - and each row's head and discharge
	# sit inside the band the brochure prints for that row.
	#
	# Borewell submersibles, V3 = 75 mm bore, copper rotor, 1" delivery
	("KV3-1P-100-1", "Submersible Pumps", "V3", 1.0, "Single Phase", 2880, "", "1", 30, 43, 18, 36, "LPM", "Stainless Steel", "IS 8034"),
	# V4 = 100 mm bore, single phase: 1¼" 0.5-3.0 HP, 1½" 1.5-3.0, 2" 2.0-3.0
	("KV4-1P-050-1.25", "Submersible Pumps", "V4", 0.5, "Single Phase", 2880, "", "1.25", 22, 45, 30, 108, "LPM", "Stainless Steel", "IS 8034"),
	("KV4-1P-200-1.25", "Submersible Pumps", "V4", 2.0, "Single Phase", 2880, "", "1.25", 40, 170, 12, 100, "LPM", "Stainless Steel", "IS 8034"),
	("KV4-1P-300-1.25", "Submersible Pumps", "V4", 3.0, "Single Phase", 2880, "", "1.25", 50, 220, 12, 95, "LPM", "Stainless Steel", "IS 8034"),
	("KV4-1P-150-1.5", "Submersible Pumps", "V4", 1.5, "Single Phase", 2880, "", "1.5", 31, 70, 60, 150, "LPM", "Stainless Steel", "IS 8034"),
	("KV4-1P-300-1.5", "Submersible Pumps", "V4", 3.0, "Single Phase", 2880, "", "1.5", 60, 100, 42, 120, "LPM", "Stainless Steel", "IS 8034"),
	("KV4-1P-200-2", "Submersible Pumps", "V4", 2.0, "Single Phase", 2880, "", "2", 15, 25, 200, 252, "LPM", "Stainless Steel", "IS 8034"),
	("KV4-1P-300-2", "Submersible Pumps", "V4", 3.0, "Single Phase", 2880, "", "2", 20, 33, 180, 252, "LPM", "Stainless Steel", "IS 8034"),
	# V4 three phase: 1¼" 1.0-5.0 HP head up to 308 m, 1½" 2.0-5.0, 2" 2.0-5.0, 2½" 3.0
	("KV4-3P-100-1.25", "Submersible Pumps", "V4", 1.0, "Three Phase", 2880, "", "1.25", 27, 90, 12, 100, "LPM", "Stainless Steel", "IS 8034"),
	("KV4-3P-300-1.25", "Submersible Pumps", "V4", 3.0, "Three Phase", 2880, "", "1.25", 60, 200, 12, 100, "LPM", "Stainless Steel", "IS 8034"),
	("KV4-3P-500-1.25", "Submersible Pumps", "V4", 5.0, "Three Phase", 2880, "", "1.25", 100, 308, 12, 80, "LPM", "Stainless Steel", "IS 8034"),
	("KV4-3P-500-1.5", "Submersible Pumps", "V4", 5.0, "Three Phase", 2880, "", "1.5", 40, 100, 42, 150, "LPM", "Stainless Steel", "IS 8034"),
	("KV4-3P-300-2.5", "Submersible Pumps", "V4", 3.0, "Three Phase", 2880, "", "2.5", 23, 33, 180, 252, "LPM", "Stainless Steel", "IS 8034"),
	# V6 = 150 mm bore, RADIAL flow, 2" delivery
	("KV6R-3P-300-2", "Submersible Pumps", "V6", 3.0, "Three Phase", 2880, "", "2", 30, 70, 48, 396, "LPM", "Stainless Steel", "IS 8034"),
	("KV6R-3P-750-2", "Submersible Pumps", "V6", 7.5, "Three Phase", 2880, "", "2", 60, 120, 48, 330, "LPM", "Stainless Steel", "IS 8034"),
	("KV6R-3P-1500-2", "Submersible Pumps", "V6", 15.0, "Three Phase", 2880, "", "2", 100, 184, 48, 300, "LPM", "Stainless Steel", "IS 8034"),
	("KV6R-1P-300-2", "Submersible Pumps", "V6", 3.0, "Single Phase", 2880, "", "2", 30, 60, 42, 312, "LPM", "Stainless Steel", "IS 8034"),
	("KV6R-1P-500-2", "Submersible Pumps", "V6", 5.0, "Single Phase", 2880, "", "2", 45, 87, 42, 280, "LPM", "Stainless Steel", "IS 8034"),
	# V6 MIXED flow: 2½" 3.0-17.5 HP, 3" 5.0-20.0, 4" 6.0-7.5
	("KV6M-3P-300-2.5", "Submersible Pumps", "V6", 3.0, "Three Phase", 2880, "", "2.5", 14, 40, 180, 780, "LPM", "Stainless Steel", "IS 8034"),
	("KV6M-3P-1750-2.5", "Submersible Pumps", "V6", 17.5, "Three Phase", 2880, "", "2.5", 60, 125, 180, 600, "LPM", "Stainless Steel", "IS 8034"),
	("KV6M-3P-500-3", "Submersible Pumps", "V6", 5.0, "Three Phase", 2880, "", "3", 15, 45, 168, 1080, "LPM", "Stainless Steel", "IS 8034"),
	("KV6M-3P-2000-3", "Submersible Pumps", "V6", 20.0, "Three Phase", 2880, "", "3", 70, 140, 168, 700, "LPM", "Stainless Steel", "IS 8034"),
	("KV6M-3P-600-4", "Submersible Pumps", "V6", 6.0, "Three Phase", 2880, "", "4", 15, 30, 330, 1080, "LPM", "Stainless Steel", "IS 8034"),
	("KV6M-1P-500-2.5", "Submersible Pumps", "V6", 5.0, "Single Phase", 2880, "", "2.5", 23, 33, 180, 570, "LPM", "Stainless Steel", "IS 8034"),
	("KV6M-1P-750-3", "Submersible Pumps", "V6", 7.5, "Single Phase", 2880, "", "3", 30, 48, 276, 750, "LPM", "Stainless Steel", "IS 8034"),
	# V8 = 200 mm bore, mixed flow, 4" delivery, 7.5-12.5 HP
	("KV8-3P-750-4", "Submersible Pumps", "V8", 7.5, "Three Phase", 2880, "", "4", 17, 30, 300, 1200, "LPM", "Stainless Steel", "IS 8034"),
	("KV8-3P-1250-4", "Submersible Pumps", "V8", 12.5, "Three Phase", 2880, "", "4", 28, 42, 300, 1000, "LPM", "Stainless Steel", "IS 8034"),
	# Openwell submersibles - ALUMINIUM rotor, hence the separate family
	("KOW-1P-050-1", "Openwell Submersible Pumps", "OW", 0.5, "Single Phase", 2880, "", "1", 12, 18, 90, 174, "LPM", "Cast Iron", "IS 8034"),
	("KOW-3P-300-2", "Openwell Submersible Pumps", "OW", 3.0, "Three Phase", 2880, "", "2", 8, 20, 300, 1890, "LPM", "Cast Iron", "IS 8034"),
	("KOW-3P-750-3", "Openwell Submersible Pumps", "OW", 7.5, "Three Phase", 2880, "", "3", 10, 27, 300, 1500, "LPM", "Cast Iron", "IS 8034"),

	# Agriculture monobloc rows the brochure lists that were not seeded before
	("KSMB30P3(3x3)", "Agricultural Monobloc", "SMB", 3.0, "Three Phase", 1440, "3", "3", 6, 12.4, 11, 18, "LPS", "Gunmetal", "IS 9079"),
	("KSMB50P3(3x2.5)", "Agricultural Monobloc", "SMB", 5.0, "Three Phase", 1440, "3", "2.5", 6, 14, 15, 22, "LPS", "Gunmetal", "IS 9079"),
	("KSMB50P3(5x5)", "Agricultural Monobloc", "SMB", 5.0, "Three Phase", 1440, "5", "5", 6, 8, 34, 40, "LPS", "Gunmetal", "IS 9079"),
	("KSMB75P3(4x4)", "Agricultural Monobloc", "SMB", 7.5, "Three Phase", 1440, "4", "4", 6, 15, 22, 32, "LPS", "Gunmetal", "IS 9079"),
	("KSMB20(3x3)", "Agricultural Monobloc", "SMB", 2.0, "Single Phase", 1440, "3", "3", 6, 11, 7.2, 18.5, "LPS", "Gunmetal", "IS 9079"),
	("KSMB20(4x4)", "Agricultural Monobloc", "SMB", 2.0, "Single Phase", 1440, "4", "4", 6, 8, 16.2, 24, "LPS", "Gunmetal", "IS 9079"),
	("KHMB30P3(3x2.5)", "Agricultural Monobloc", "HMB", 3.0, "Three Phase", 2880, "3", "2.5", 9, 18.5, 8.0, 17, "LPS", "Gunmetal", "IS 9079"),
	("KHMB50P3(2.5x2)", "Agricultural Monobloc", "HMB", 5.0, "Three Phase", 2880, "2.5", "2", 16, 21, 8.7, 9.8, "LPS", "Gunmetal", "IS 9079"),
	("KHMB50P3(4x3)", "Agricultural Monobloc", "HMB", 5.0, "Three Phase", 2880, "4", "3", 8, 12, 16.5, 18.5, "LPS", "Gunmetal", "IS 9079"),
	("KHMB75P3(3x2.5)", "Agricultural Monobloc", "HMB", 7.5, "Three Phase", 2880, "3", "2.5", 25, 35, 11.0, 19.4, "LPS", "Gunmetal", "IS 9079"),
	("KHMB75HHP3(4x3)", "Agricultural Monobloc", "HMB", 7.5, "Three Phase", 2880, "4", "3", 16, 32, 19, 28, "LPS", "Gunmetal", "IS 9079"),
	("KHMB20(1.5x1.5)", "Centrifugal Monobloc", "HMB", 2.0, "Single Phase", 2880, "1.5", "1.5", 14, 24, 100, 265, "LPM", "Gunmetal", "IS 9079"),
	# Mini monobloc, cast-iron variants
	("KHMB05CMMB", "Centrifugal Monobloc", "HMB", 0.5, "Single Phase", 2880, "1", "1", 3, 30, 750, 3700, "LPH", "Cast Iron", "IS 9079"),
	("KHMB10CMMB", "Centrifugal Monobloc", "HMB", 1.0, "Single Phase", 2880, "1", "1", 21, 53, 750, 3700, "LPH", "Cast Iron", "IS 9079"),
	# Jet monobloc: the brochure ships every rating in gunmetal AND cast iron, in
	# square base, round base and double-stage round base.
	("KJM10CISB", "Jet Monobloc", "JM", 1.0, "Single Phase", 2880, "1.25", "1", 9, 39, 468, 1368, "LPH", "Cast Iron", "IS 9079"),
	("KJM15CISB", "Jet Monobloc", "JM", 1.5, "Single Phase", 2880, "1.25", "1", 10, 50, 468, 1368, "LPH", "Cast Iron", "IS 9079"),
	("KJM05GIRB", "Jet Monobloc", "JM", 0.5, "Single Phase", 2880, "1.25", "1", 9, 21, 900, 1368, "LPH", "Gunmetal", "IS 9079"),
	("KJM05CIRB", "Jet Monobloc", "JM", 0.5, "Single Phase", 2880, "1.25", "1", 9, 21, 900, 1368, "LPH", "Cast Iron", "IS 9079"),
	("KJM10GIRB", "Jet Monobloc", "JM", 1.0, "Single Phase", 2880, "1.25", "1", 9, 39, 468, 1368, "LPH", "Gunmetal", "IS 9079"),
	("KJM10CIRB", "Jet Monobloc", "JM", 1.0, "Single Phase", 2880, "1.25", "1", 9, 39, 468, 1368, "LPH", "Cast Iron", "IS 9079"),
	("KJM15GIRB", "Jet Monobloc", "JM", 1.5, "Single Phase", 2880, "1.25", "1", 10, 50, 468, 1368, "LPH", "Gunmetal", "IS 9079"),
	("KJM15CIRB", "Jet Monobloc", "JM", 1.5, "Single Phase", 2880, "1.25", "1", 10, 50, 468, 1368, "LPH", "Cast Iron", "IS 9079"),
	("KJM10DCI", "Jet Monobloc", "JM", 1.0, "Single Phase", 2880, "1.25", "1", 30, 50, 420, 900, "LPH", "Cast Iron", "IS 9079"),
	("KJM15DGI", "Jet Monobloc", "JM", 1.5, "Single Phase", 2880, "1.25", "1", 30, 60, 450, 1100, "LPH", "Gunmetal", "IS 9079"),
	("KJM20DCI", "Jet Monobloc", "JM", 2.0, "Single Phase", 2880, "1.25", "1", 30, 70, 450, 1100, "LPH", "Cast Iron", "IS 9079"),
]

# Rotor material is a real product distinction the brochure keeps making, and it
# does not follow from the category name alone: borewell submersibles run a
# COPPER rotor, openwell submersibles an aluminium one. Everything else on the
# monobloc side is aluminium pressure die cast.
COPPER_ROTOR_FAMILIES = {"V3", "V4", "V6", "V8"}

# name, type, parent, city, state, pincode, contact, mobile, address
DEALERS = [
	("KUMAR Network", "Branch Office", None, "Tenali", "Andhra Pradesh", "522202", "", "", "Head Office - Industrial Estate, Sultanabad, Tenali", 1),
	("Aruna Jyothi Distributors - Secunderabad", "Branch Office", "KUMAR Network", "Secunderabad", "Telangana", "500003", "Branch Manager", "9490759500", "5-2-396-81/A, Shop 4 & 5, Hyderbasti, R.P. Road, behind SBI", 0),
	("Aruna Jyothi Distributors - Visakhapatnam", "Branch Office", "KUMAR Network", "Visakhapatnam", "Andhra Pradesh", "530020", "Branch Manager", "9490759511", "30-12-25, Ranga Street, Daba Gardens", 0),
	("Aruna Jyothi Distributors - Vijayawada", "Branch Office", "KUMAR Network", "Vijayawada", "Andhra Pradesh", "520001", "Branch Manager", "9966355111", "12-10-25, 1st Floor, TSR Complex, Convent Street", 0),
	("Aruna Jyothi Distributors - Chennai", "Branch Office", "KUMAR Network", "Chennai", "Tamil Nadu", "600001", "Branch Manager", "9381299777", "336/3 (Old 166/3), Thambuchetty Street", 0),
	("Aruna Jyothi Distributors - Tenali", "Branch Office", "KUMAR Network", "Tenali", "Andhra Pradesh", "522201", "Branch Manager", "9490759522", "Kumar Building, Wahab Road", 0),
	("Aruna Jyothi Distributors - Nellore", "Branch Office", "KUMAR Network", "Nellore", "Andhra Pradesh", "524002", "Branch Manager", "9490759544", "15/305, Shop 4, Ramireddy Complex, New Talkies Centre", 0),
	("Aruna Jyothi Distributors - Tirupati", "Branch Office", "KUMAR Network", "Tirupati", "Andhra Pradesh", "517501", "Branch Manager", "9490759519", "23-8-69/14, Plot 18, Mitta Enclave, Rayala Cheruvu Road", 0),
	("Kappens Sani Wares", "Authorised Distributor", "KUMAR Network", "Palai", "Kerala", "686575", "Proprietor", "9447805704", "Market Road, Palai", 0),
	("SP Machinary Stores", "Authorised Distributor", "KUMAR Network", "Maunath Bhanjan", "Uttar Pradesh", "275101", "Proprietor", "9451004745", "Mirzahadipura Chowk", 0),
	("Jain Enterprises", "Authorised Distributor", "KUMAR Network", "Muzaffarpur", "Bihar", "842001", "Proprietor", "9430013384", "Jawaharlal Road", 0),
	("Sudhakar Stores", "Authorised Distributor", "KUMAR Network", "Berhampur", "Odisha", "760002", "Proprietor", "9437008813", "Aska Road", 0),
]

SUB_DEALERS = [
	("Sri Venkateswara Pump Center", "Dealer", "Aruna Jyothi Distributors - Vijayawada", "Guntur", "Andhra Pradesh", "522001", "9848012345"),
	("Balaji Agro Machinery", "Dealer", "Aruna Jyothi Distributors - Vijayawada", "Eluru", "Andhra Pradesh", "534001", "9848112233"),
	("Krishna Borewells", "Sub-Dealer", "Sri Venkateswara Pump Center", "Mangalagiri", "Andhra Pradesh", "522503", "9848223344"),
	("Deccan Pumps & Motors", "Dealer", "Aruna Jyothi Distributors - Secunderabad", "Hyderabad", "Telangana", "500018", "9848334455"),
	("Coastal Irrigation Systems", "Service Centre", "Aruna Jyothi Distributors - Visakhapatnam", "Visakhapatnam", "Andhra Pradesh", "530016", "9848445566"),
]

WAREHOUSES = [
	"Foundry WIP",
	"Machine Shop WIP",
	"Winding WIP",
	"Assembly WIP",
	"Test Bay",
	"FG Store",
	"Dealer Stock",
]

WORKSTATIONS = [
	("Induction Furnace", 1200),
	("Cupola Furnace", 900),
	("DISA Moulding Line", 1500),
	("Shot Blasting", 400),
	("CNC Lathe", 800),
	("VMC Machining Centre", 1100),
	("CNC Grinding", 900),
	("Dynamic Balancing", 600),
	("Coil Winding Machine", 700),
	("Varnish Oven", 500),
	("Assembly Line", 650),
	("Test Bench", 550),
	("Paint Conveyor", 450),
]

OPERATIONS = [
	"Melting & Pouring",
	"Moulding",
	"Fettling & Shot Blast",
	"Machining",
	"Grinding",
	"Winding",
	"Varnishing & Curing",
	"Rotor Die Casting",
	"Assembly",
	"Performance Testing",
	"Painting & Packing",
]

# component items that carry a batch
COMPONENTS = [
	("KC-CASING", "Pump Casing (FG 200)", "Casing", 1, 420),
	("KC-STATOR", "Wound Stator", "Stator", 1, 1150),
	("KC-ROTOR", "Rotor Assembly", "Rotor", 1, 780),
	("KC-IMPELLER", "Impeller (Gunmetal)", "Impeller", 1, 560),
	("KC-SHAFT", "SS Shaft", "Shaft", 1, 340),
	("KC-BEARING", "SKF Ball Bearing", "Bought-out", 1, 190),
	("KC-SEAL", "Mechanical Seal", "Bought-out", 1, 145),
	("KC-CAPACITOR", "Capacitor", "Bought-out", 1, 95),
	("KC-CABLE", "Submersible Cable (m)", "Bought-out", 0, 60),
	("KC-TOP", "Terminal Box", "Bought-out", 0, 110),
]

ITEM_GROUP_PUMPS = "Finished Pumps"
ITEM_GROUP_COMPONENTS = "Pump Components"


def build_all():
	company = frappe.db.get_value("Company", {"company_name": COMPANY}) or frappe.db.get_value(
		"Company", {}, "name"
	)
	if not company:
		frappe.msgprint("No Company yet - skipping KUMAR masters")
		return

	abbr = frappe.db.get_value("Company", company, "abbr")
	categories()
	models()
	item_groups()
	warehouses(company, abbr)
	workstations()
	operations()
	component_items()
	pump_items()
	dealer_tree()
	technicians()
	stock_settings()
	settings_defaults()
	frappe.db.commit()


def stock_settings():
	"""Serial/batch bundles are the whole point of this app - turn them on."""
	ss = frappe.get_single("Stock Settings")
	ss.enable_serial_and_batch_no_for_item = 1
	ss.auto_create_serial_and_batch_bundle_for_outward = 1
	ss.do_not_update_serial_batch_on_creation_of_auto_bundle = 0
	ss.allow_negative_stock = 0
	ss.flags.ignore_permissions = True
	ss.save(ignore_permissions=True)


def categories():
	for name, abbr, months in CATEGORIES:
		upsert(
			"Pump Category",
			{"category_name": name},
			{
				"category_name": name,
				"abbr": abbr,
				"default_warranty_months": months,
				"is_active": 1,
				"description": f"{name} manufactured by KUMAR Pumps & Motors, Tenali.",
			},
		)


def models():
	for row in MODELS:
		(code, category, family, hp, phase, rpm, suction, delivery, hmin, hmax,
			dmin, dmax, uom, impeller, bis) = row
		if frappe.db.exists("Pump Model", code):
			continue
		doc = frappe.get_doc(
			{
				"doctype": "Pump Model",
				"model_code": code,
				"pump_category": category,
				"family_code": family,
				"hp": hp,
				"kw": flt(hp * 0.7457, 2),
				"phase": phase or None,
				"voltage_range": "180-250V" if phase == "Single Phase" else ("360-415V" if phase else ""),
				"rpm": rpm,
				"suction_size_inch": suction,
				"delivery_size_inch": delivery,
				"impeller_material": impeller or None,
				# by family, not by category: "Openwell Submersible Pumps" also
				# contains "Submersible" but runs an aluminium rotor
				"rotor_type": (
					"Copper" if family in COPPER_ROTOR_FAMILIES else "Aluminium Die Cast"
				),
				"head_min_m": hmin,
				"head_max_m": hmax,
				"discharge_min": dmin,
				"discharge_max": dmax,
				"discharge_uom": uom,
				"bis_standard": bis,
				"is_active": 1,
			}
		)
		# a small performance curve so the model page is not empty
		if hmax and dmax:
			steps = [(hmin, dmax), ((hmin + hmax) / 2, (dmin + dmax) / 2), (hmax, dmin)]
			for head, disch in steps:
				doc.append(
					"performance_curve",
					{
						"head_m": flt(head, 2),
						"discharge": flt(disch, 2),
						"efficiency_pct": flt(45 + (hp * 2), 1),
						"input_kw": flt(hp * 0.7457 * 1.15, 2),
						"current_amp": flt(hp * (7.5 if phase == "Single Phase" else 1.9), 2),
					},
				)
		doc.flags.ignore_permissions = True
		doc.insert(ignore_permissions=True)

	repair_openwell_family()


def repair_openwell_family():
	"""Move the two openwell models built before the category existed.

	`models()` skips a model that already exists, so an earlier seed left
	KOW-1P-100-1 and KOW-3P-500-2.5 filed as borewell V4 units with a copper
	rotor. Both are wrong on the shop floor and on the test certificate. Safe to
	move because openwell and borewell carry the same 18-month warranty, so no
	registration's expiry shifts.
	"""
	if not frappe.db.exists("Pump Category", "Openwell Submersible Pumps"):
		return
	for code in frappe.get_all(
		"Pump Model", filters={"model_code": ["like", "KOW-%"]}, pluck="name"
	):
		current = frappe.db.get_value("Pump Model", code, ["pump_category", "family_code"])
		if current == ("Openwell Submersible Pumps", "OW"):
			continue
		frappe.db.set_value(
			"Pump Model",
			code,
			{
				"pump_category": "Openwell Submersible Pumps",
				"family_code": "OW",
				"rotor_type": "Aluminium Die Cast",
			},
			update_modified=False,
		)


def item_groups():
	for group in (ITEM_GROUP_PUMPS, ITEM_GROUP_COMPONENTS):
		upsert(
			"Item Group",
			{"item_group_name": group},
			{"item_group_name": group, "parent_item_group": "All Item Groups", "is_group": 0},
		)


def warehouses(company, abbr):
	root = frappe.db.get_value("Warehouse", {"company": company, "is_group": 1, "parent_warehouse": ""})
	for wh in WAREHOUSES:
		name = f"{wh} - {abbr}"
		if frappe.db.exists("Warehouse", name):
			continue
		frappe.get_doc(
			{
				"doctype": "Warehouse",
				"warehouse_name": wh,
				"company": company,
				"parent_warehouse": root,
				"is_group": 0,
			}
		).insert(ignore_permissions=True)


def workstations():
	for name, rate in WORKSTATIONS:
		upsert(
			"Workstation",
			{"workstation_name": name},
			{"workstation_name": name, "hour_rate_electricity": rate / 100.0, "hour_rate": rate / 100.0},
		)


def operations():
	for name in OPERATIONS:
		upsert("Operation", {"name": name}, {"__newname": name, "operation_name": name})


def component_items():
	for code, name, group, batched, rate in COMPONENTS:
		if frappe.db.exists("Item", code):
			continue
		frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": code,
				"item_name": name,
				"item_group": ITEM_GROUP_COMPONENTS,
				"stock_uom": "Nos",
				"is_stock_item": 1,
				"has_batch_no": batched,
				"create_new_batch": batched,
				"batch_number_series": {
					"Casing": "HT-.YY..MM..DD.-.###",
					"Stator": "WD-.YY..MM.-.####",
					"Rotor": "RT-.YY..MM.-.####",
				}.get(group, f"{code[-3:]}-.YY..MM.-.####") if batched else None,
				"custom_trace_group": group,
				"valuation_rate": rate,
				"is_purchase_item": 1 if group == "Bought-out" else 0,
			}
		).insert(ignore_permissions=True)


def pump_items():
	"""One serialised Item per Pump Model - the stock side of the catalogue."""
	for row in MODELS:
		code, category, family, hp = row[0], row[1], row[2], row[3]
		item_code = f"KP-{code}"
		if frappe.db.exists("Item", item_code):
			continue
		safe = code.replace("(", "").replace(")", "").replace("/", "-").replace(".", "")
		rate = 3200 + (hp * 2600)
		frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": item_code,
				"item_name": f"KUMAR {code}",
				"description": f"KUMAR {category} model {code}, {hp} HP",
				"item_group": ITEM_GROUP_PUMPS,
				"stock_uom": "Nos",
				"is_stock_item": 1,
				"has_serial_no": 1,
				"serial_no_series": f"KP-{safe}-.YY..MM.-.#####",
				"custom_pump_model": code,
				"custom_is_finished_pump": 1,
				"custom_trace_group": "NA",
				"valuation_rate": rate,
				"standard_rate": flt(rate * 1.35, 0),
				"is_sales_item": 1,
			}
		).insert(ignore_permissions=True)
		frappe.db.set_value("Pump Model", code, "item", item_code, update_modified=False)


def dealer_tree():
	for name, dtype, parent, city, state, pincode, contact, mobile, address, is_group in DEALERS:
		if frappe.db.exists("Dealer", name):
			continue
		frappe.get_doc(
			{
				"doctype": "Dealer",
				"dealer_name": name,
				"dealer_code": _code(name),
				"dealer_type": dtype,
				"parent_dealer": parent,
				"is_group": is_group or (1 if parent is None else 0),
				"city": city,
				"state": state,
				"pincode": pincode,
				"contact_person": contact,
				"mobile_no": mobile,
				"address_line": address,
				"status": "Active",
				"onboarding_date": "2020-04-01",
			}
		).insert(ignore_permissions=True)

	# A branch or distributor that actually has dealers under it has to be a
	# group so they can hang off it. One that does not must stay a leaf - a
	# distributor sells pumps itself, and a dealer flagged as a group can never
	# be put on a registration or an invoice.
	for name, _dtype, parent, *_rest in DEALERS:
		if not parent:
			continue
		has_children = bool(frappe.db.exists("Dealer", {"parent_dealer": name}))
		if bool(frappe.db.get_value("Dealer", name, "is_group")) != has_children:
			frappe.db.set_value(
				"Dealer", name, "is_group", 1 if has_children else 0, update_modified=False
			)

	for name, dtype, parent, city, state, pincode, mobile in SUB_DEALERS:
		if frappe.db.exists("Dealer", name):
			continue
		# the parent must be a group before a child can be attached to it
		if parent and not frappe.db.get_value("Dealer", parent, "is_group"):
			frappe.db.set_value("Dealer", parent, "is_group", 1, update_modified=False)
		frappe.get_doc(
			{
				"doctype": "Dealer",
				"dealer_name": name,
				"dealer_code": _code(name),
				"dealer_type": dtype,
				"parent_dealer": parent,
				# only a dealer that will itself have sub-dealers is a group
				"is_group": 1 if name == "Sri Venkateswara Pump Center" else 0,
				"city": city,
				"state": state,
				"pincode": pincode,
				"mobile_no": mobile,
				"status": "Active",
				"service_centre_flag": 1 if dtype == "Service Centre" else 0,
				"onboarding_date": "2023-06-01",
			}
		).insert(ignore_permissions=True)

	# and once the children exist, settle the group flags again
	for name in frappe.get_all("Dealer", pluck="name"):
		if not frappe.db.get_value("Dealer", name, "parent_dealer"):
			continue
		has_children = bool(frappe.db.exists("Dealer", {"parent_dealer": name}))
		if bool(frappe.db.get_value("Dealer", name, "is_group")) != has_children:
			frappe.db.set_value(
				"Dealer", name, "is_group", 1 if has_children else 0, update_modified=False
			)

	stamp_outlet_ownership()
	dealer_gstins()
	dealer_trade_accounts()


# An independent dealer bills the end customer on their OWN GSTIN, and that
# number is what a warranty claim is checked against - so it belongs on the
# dealer master, not on ours. State code leads the number, so it has to agree
# with where the dealer actually is.
STATE_GST_CODE = {
	"Andhra Pradesh": "37",
	"Telangana": "36",
	"Tamil Nadu": "33",
	"Kerala": "32",
	"Karnataka": "29",
	"Uttar Pradesh": "09",
	"Bihar": "10",
	"Odisha": "21",
	"Maharashtra": "27",
}


def dealer_gstins():
	"""Give every independent dealer a well-formed GSTIN for its own state."""
	import hashlib

	for d in frappe.get_all(
		"Dealer",
		filters={"is_own_outlet": 0, "gstin": ["is", "not set"]},
		fields=["name", "state"],
	):
		code = STATE_GST_CODE.get(d.state)
		if not code:
			continue
		# deterministic, so a rebuild does not reissue every dealer a new number
		digest = hashlib.sha1(d.name.encode()).hexdigest().upper()
		pan = f"{digest[0:5].translate(str.maketrans('0123456789', 'ABCDEFGHIJ'))}" \
			f"{int(digest[5:9], 16) % 10000:04d}" \
			f"{digest[9].translate(str.maketrans('0123456789', 'ABCDEFGHIJ'))}"
		frappe.db.set_value("Dealer", d.name, "gstin", f"{code}{pan}1Z{digest[10]}",
			update_modified=False)


def stamp_outlet_ownership():
	"""Who owns each outlet - the fact that decides whose invoice the end
	customer gets.

	The head office and its branch offices are KUMAR. Everything else -
	distributors, dealers, sub-dealers, service centres - is somebody else's
	company that happens to sell our pumps.
	"""
	for name, dealer_type in frappe.get_all(
		"Dealer", fields=["name", "dealer_type"], as_list=True
	):
		own = 1 if dealer_type == "Branch Office" else 0
		if cint(frappe.db.get_value("Dealer", name, "is_own_outlet")) != own:
			frappe.db.set_value("Dealer", name, "is_own_outlet", own, update_modified=False)


def dealer_trade_accounts():
	"""Every independent dealer is a customer of ours - that is the whole
	first half of the transaction.

	Without a Customer there is nothing to raise the KUMAR -> Dealer invoice
	against, and dealer revenue can only ever be a guess. Our own branches get
	no trade account: we do not invoice ourselves.
	"""
	group = _trade_customer_group()
	territory = frappe.db.get_value("Territory", {"is_group": 0}, "name") or "All Territories"

	for d in frappe.get_all(
		"Dealer",
		filters={"is_own_outlet": 0, "is_group": 0},
		fields=["name", "dealer_name", "customer", "gstin", "mobile_no", "city", "state", "pincode"],
	):
		if d.customer and frappe.db.exists("Customer", d.customer):
			continue

		# the dealer's trade account is named for the dealer, so the two are
		# obviously the same firm on any report
		cust_name = f"{d.dealer_name} (Trade)"
		if not frappe.db.exists("Customer", cust_name):
			doc = frappe.get_doc(
				{
					"doctype": "Customer",
					"customer_name": cust_name,
					"customer_group": group,
					"territory": territory,
					"customer_type": "Company",
					"mobile_no": d.mobile_no,
					"custom_dealer": d.name,
				}
			)
			doc.flags.ignore_permissions = True
			doc.flags.ignore_mandatory = True
			doc.insert(ignore_permissions=True)
			cust_name = doc.name

		frappe.db.set_value("Dealer", d.name, "customer", cust_name, update_modified=False)
		frappe.db.set_value("Customer", cust_name, "custom_dealer", d.name, update_modified=False)


def _trade_customer_group():
	"""A dealer is not a retail buyer, so keep the trade accounts in their own
	group - it is what makes 'sales to the network' separable from 'sales to
	the public' on every standard ERPNext report."""
	name = "Dealer / Trade"
	if not frappe.db.exists("Customer Group", name):
		parent = frappe.db.get_value("Customer Group", {"is_group": 1}, "name") or "All Customer Groups"
		frappe.get_doc(
			{
				"doctype": "Customer Group",
				"customer_group_name": name,
				"parent_customer_group": parent,
				"is_group": 0,
			}
		).insert(ignore_permissions=True)
	return name


def _code(name):
	"""Initials plus the tail of the last word - 'Vijayawada' and 'Visakhapatnam'
	share their initials, so initials alone collide."""
	words = [w for w in name.replace("-", " ").split() if w and w[0].isalnum()]
	initials = "".join(w[0] for w in words).upper()[:4]
	tail = (words[-1][:3] if words else "").upper()
	return f"D-{initials}{tail}"


def technicians():
	people = [
		("Ravi Kumar", "Aruna Jyothi Distributors - Vijayawada", "9848501001"),
		("Srinivas Rao", "Aruna Jyothi Distributors - Secunderabad", "9848501002"),
		("Mahesh Babu", "Coastal Irrigation Systems", "9848501003"),
		("Naveen Reddy", "Aruna Jyothi Distributors - Tenali", "9848501004"),
		("Prasad Gupta", "Aruna Jyothi Distributors - Tirupati", "9848501005"),
	]
	for name, dealer, mobile in people:
		upsert(
			"Service Technician",
			{"technician_name": name},
			{
				"technician_name": name,
				"dealer": dealer,
				"mobile_no": mobile,
				"is_active": 1,
			},
		)


def settings_defaults():
	doc = frappe.get_single("Kumar Service Settings")
	if not doc.default_warranty_months:
		doc.default_warranty_months = 12
	if not doc.warranty_from:
		doc.warranty_from = "Sale Date"
	if not doc.sla_response_hours:
		doc.sla_response_hours = 24
	if not doc.sla_resolution_hours:
		doc.sla_resolution_hours = 72
	if not doc.certificate_issuer:
		doc.certificate_issuer = "KUMAR Pumps & Motors"
	if not doc.qr_base_url:
		doc.qr_base_url = "https://kumarpumps.co.in/warranty-check"
	if not doc.default_service_centre and frappe.db.exists("Dealer", "Coastal Irrigation Systems"):
		doc.default_service_centre = "Coastal Irrigation Systems"
	doc.enable_heat_traceability = 1
	doc.enable_test_certificate = 1
	doc.enforce_qc_before_dispatch = 1
	doc.flags.ignore_permissions = True
	doc.save(ignore_permissions=True)
