"""
Core orchestration engine for the AI Test Suite.

Flow:
  1. start_test_execution() - called from the Desk page. Creates a
     "Test Execution" record and enqueues the actual run as a background job
     so the UI is never blocked.
  2. execute_workflow() - the background job. Walks every step of the
     selected "Test Workflow", runs it at each requested level
     (Functional / UI / Technical), records a "Test Execution Result" row
     per (step, level), and streams progress to the browser over
     frappe.publish_realtime.
"""

import time
import traceback

import frappe
from frappe.utils import now_datetime

from ai_test_suite.ai_test_suite.test_engine import functional, technical, ui
from ai_test_suite.ai_test_suite.ai.suggestions import generate_suggestion

REALTIME_EVENT = "ai_test_progress"


@frappe.whitelist()
def start_test_execution(workflow, levels):
	"""Create a Test Execution record and queue it for background run.

	Args:
	    workflow (str): name of a Test Workflow document
	    levels (str | list): "Functional,UI,Technical" or a list of the same

	Returns:
	    str: name of the created Test Execution document
	"""
	if isinstance(levels, str):
		levels = [l.strip() for l in levels.split(",") if l.strip()]

	if not frappe.db.exists("Test Workflow", workflow):
		frappe.throw(f"Test Workflow '{workflow}' not found")

	execution = frappe.get_doc({
		"doctype": "Test Execution",
		"workflow": workflow,
		"levels_tested": ", ".join(levels),
		"status": "Queued",
		"executed_by": frappe.session.user,
	}).insert(ignore_permissions=True)
	frappe.db.commit()

	frappe.enqueue(
		"ai_test_suite.ai_test_suite.test_engine.runner.execute_workflow",
		queue="long",
		timeout=1800,
		execution=execution.name,
		levels=levels,
	)

	return execution.name


def execute_workflow(execution, levels):
	"""Background job: runs every step of the workflow at every requested level."""

	exec_doc = frappe.get_doc("Test Execution", execution)
	exec_doc.status = "Running"
	exec_doc.start_time = now_datetime()
	exec_doc.save(ignore_permissions=True)
	frappe.db.commit()
	_publish(execution, "started", {})

	workflow = frappe.get_doc("Test Workflow", exec_doc.workflow)

	passed = failed = warnings = 0

	for step in workflow.steps:
		step_levels = [l.strip() for l in (step.applicable_levels or "").split(",") if l.strip()]
		run_levels = [l for l in levels if not step_levels or l in step_levels]

		for level in run_levels:
			start = time.time()
			status, message, error_log = "Pass", "", ""

			try:
				if level == "Functional":
					status, message = functional.run(step)
				elif level == "UI":
					status, message = ui.run(step)
				elif level == "Technical":
					status, message = technical.run(step)
				else:
					status, message = "Skipped", f"Unknown test level: {level}"
			except Exception:
				status = "Fail"
				error_log = traceback.format_exc()
				last_line = error_log.strip().splitlines()[-1] if error_log.strip() else "Unhandled error"
				message = last_line
			finally:
				frappe.db.rollback()  # never let a test step's DB changes persist

			root_cause, suggestion = "", ""
			if status == "Fail":
				root_cause, suggestion = generate_suggestion(message, error_log)
				failed += 1
			elif status == "Warning":
				warnings += 1
			elif status == "Pass":
				passed += 1

			result_row = {
				"step_name": step.step_name,
				"reference_doctype": step.reference_doctype,
				"test_level": level,
				"status": status,
				"message": message,
				"error_log": error_log,
				"root_cause": root_cause,
				"ai_suggestion": suggestion,
				"execution_time": round(time.time() - start, 3),
			}
			exec_doc.append("results", result_row)
			_publish(execution, "progress", result_row)

	total = passed + failed + warnings
	exec_doc.total_tests = total
	exec_doc.passed = passed
	exec_doc.failed = failed
	exec_doc.warnings = warnings
	exec_doc.status = "Failed" if failed else "Completed"
	exec_doc.end_time = now_datetime()
	exec_doc.summary = f"Total: {total} | Passed: {passed} | Failed: {failed} | Warnings: {warnings}"
	exec_doc.save(ignore_permissions=True)
	frappe.db.commit()

	_publish(execution, "completed", {
		"total": total, "passed": passed, "failed": failed, "warnings": warnings,
	})

	return exec_doc.name


def _publish(execution, event, data):
	frappe.publish_realtime(
		event=REALTIME_EVENT,
		message={"execution": execution, "event": event, "data": data},
		user=frappe.session.user,
	)
