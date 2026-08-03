"""Export a Test Execution's results as a PDF or Excel report and attach it
to the record."""

import frappe
from frappe.utils.pdf import get_pdf
from frappe.utils.xlsxutils import make_xlsx


@frappe.whitelist()
def export_report(execution, format="PDF"):
	exec_doc = frappe.get_doc("Test Execution", execution)

	if format.upper() == "PDF":
		return _export_pdf(exec_doc)
	elif format.upper() == "EXCEL":
		return _export_excel(exec_doc)

	frappe.throw(f"Unsupported export format: {format}")


def _export_pdf(exec_doc):
	html = frappe.render_template(
		"ai_test_suite/ai_test_suite/reports_export/templates/report.html",
		{"doc": exec_doc},
	)
	pdf_content = get_pdf(html)

	file_doc = frappe.get_doc({
		"doctype": "File",
		"file_name": f"{exec_doc.name}-report.pdf",
		"attached_to_doctype": "Test Execution",
		"attached_to_name": exec_doc.name,
		"content": pdf_content,
		"is_private": 1,
	}).insert(ignore_permissions=True)

	exec_doc.db_set("report_pdf", file_doc.file_url)
	return file_doc.file_url


def _export_excel(exec_doc):
	rows = [["Step", "DocType", "Level", "Status", "Message", "Root Cause", "AI Suggestion", "Time (s)"]]
	for r in exec_doc.results:
		rows.append([
			r.step_name, r.reference_doctype, r.test_level, r.status,
			r.message, r.root_cause, r.ai_suggestion, r.execution_time,
		])

	xlsx_data = make_xlsx(rows, "Test Results")

	file_doc = frappe.get_doc({
		"doctype": "File",
		"file_name": f"{exec_doc.name}-report.xlsx",
		"attached_to_doctype": "Test Execution",
		"attached_to_name": exec_doc.name,
		"content": xlsx_data.getvalue(),
		"is_private": 1,
	}).insert(ignore_permissions=True)

	exec_doc.db_set("report_excel", file_doc.file_url)
	return file_doc.file_url
