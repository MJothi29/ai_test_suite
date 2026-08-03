"""Technical level: APIs, server-side methods, DB operations, permissions, logs."""

import frappe
from frappe.utils import add_to_date, now_datetime


def run(step):
	doctype = step.reference_doctype
	notes = []

	if not frappe.db.exists("DocType", doctype):
		return "Fail", f"DocType '{doctype}' does not exist"

	if not frappe.has_permission(doctype, "read"):
		return "Fail", f"Current user lacks read permission on '{doctype}'"
	notes.append("permission check passed")

	if not frappe.db.table_exists(doctype):
		return "Fail", f"Database table for '{doctype}' is missing"
	notes.append("database table verified")

	if step.action == "Custom Method":
		if not step.custom_method:
			return "Fail", "Action is 'Custom Method' but no method path was configured"
		try:
			frappe.get_attr(step.custom_method)
			notes.append(f"method '{step.custom_method}' is resolvable")
		except Exception as e:
			return "Fail", f"Custom method '{step.custom_method}' not resolvable: {e}"

	if step.action == "API Call":
		try:
			frappe.get_attr(step.custom_method) if step.custom_method else None
			notes.append("API endpoint reference resolved")
		except Exception as e:
			return "Fail", f"API endpoint not resolvable: {e}"

	recent_errors = frappe.get_all(
		"Error Log",
		filters={"creation": [">", add_to_date(now_datetime(), minutes=-5)]},
		limit=1,
	)
	if recent_errors:
		notes.append("warning: recent entries found in Error Log")
		return "Warning", "; ".join(notes)

	return "Pass", "; ".join(notes)
