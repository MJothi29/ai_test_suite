"""UI level: verifies forms, buttons, fields, navigation and interactions.

Desk/browser automation cannot run inside a Frappe background worker, so this
module delegates to an external browser-automation service (Playwright,
Selenium, Cypress, etc.) configured via AI Test Settings. Point
`ui_test_runner_url` at a small HTTP service that accepts
{doctype, action, expected_result} and returns {passed, message}.
"""

import frappe
import requests


def run(step):
	settings = frappe.get_single("AI Test Settings")
	runner_url = settings.get("ui_test_runner_url")

	if not runner_url:
		return "Skipped", (
			"No UI test runner configured. Set 'UI Test Runner Webhook URL' in "
			"AI Test Settings to point at a Playwright/Selenium/Cypress service."
		)

	payload = {
		"doctype": step.reference_doctype,
		"action": step.action,
		"expected_result": step.expected_result,
	}

	try:
		resp = requests.post(runner_url, json=payload, timeout=60)
		resp.raise_for_status()
		data = resp.json()
		status = "Pass" if data.get("passed") else "Fail"
		return status, data.get("message", "")
	except requests.RequestException as e:
		return "Fail", f"UI test runner call failed: {e}"
