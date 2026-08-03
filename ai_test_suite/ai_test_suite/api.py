"""Shared read-only helper endpoints used by the AI Test Runner Desk page."""

import frappe


@frappe.whitelist()
def get_workflows(module=None):
	filters = {"disabled": 0}
	if module:
		filters["module"] = module
	return frappe.get_all(
		"Test Workflow",
		filters=filters,
		fields=["name", "workflow_name", "workflow_type", "module"],
		order_by="workflow_name",
	)


@frappe.whitelist()
def get_execution_history(workflow=None, limit=20):
	filters = {}
	if workflow:
		filters["workflow"] = workflow
	return frappe.get_all(
		"Test Execution",
		filters=filters,
		fields=[
			"name", "workflow", "status", "total_tests",
			"passed", "failed", "warnings", "start_time", "end_time",
		],
		order_by="creation desc",
		limit_page_length=limit,
	)
