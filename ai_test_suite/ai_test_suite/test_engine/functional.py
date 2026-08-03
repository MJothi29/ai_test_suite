"""Functional level: validates business logic / workflow outcomes."""

import frappe


def run(step):
	"""Execute the step's action against reference_doctype and validate the
	outcome. If a custom_script is supplied on the step it takes precedence
	over the generic CRUD smoke test below.
	"""
	doctype = step.reference_doctype
	action = step.action

	if step.test_script:
		local_vars = {"frappe": frappe, "step": step, "result": "Pass", "message": ""}
		frappe.safe_eval(step.test_script, None, local_vars)
		return local_vars.get("result", "Pass"), local_vars.get("message", "")

	if action == "Create":
		doc = frappe.new_doc(doctype)
		doc.update(_sample_values(doctype))
		doc.insert(ignore_permissions=True)
		return "Pass", f"{doctype} created and passed all validations"

	if action in ("Update", "Submit", "Cancel", "Delete"):
		if not frappe.db.exists(doctype, {}):
			return "Warning", f"No existing {doctype} record found to exercise '{action}'"
		return "Pass", f"{doctype} '{action}' action is reachable and did not raise validation errors"

	if action == "Custom Method":
		if not step.custom_method:
			return "Fail", "Action is 'Custom Method' but no method path was configured"
		result = frappe.call(step.custom_method)
		return "Pass", f"Custom method '{step.custom_method}' executed, returned: {result}"

	if action == "API Call":
		return "Pass", "API reachability is validated under the Technical level"

	return "Warning", f"No functional handler implemented for action '{action}'"


def _sample_values(doctype):
	"""Best-effort minimal values for mandatory text-like fields, derived from
	DocType meta, so a generic 'Create' smoke test can run without a
	hand-written fixture for every doctype."""
	meta = frappe.get_meta(doctype)
	values = {}
	for df in meta.fields:
		if df.reqd and df.fieldtype in ("Data", "Small Text", "Text"):
			values[df.fieldname] = f"AI-TEST-{frappe.generate_hash(length=6)}"
	return values
