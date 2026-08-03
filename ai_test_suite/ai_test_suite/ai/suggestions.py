"""AI-generated root cause analysis and fix suggestions for failed test steps.

Uses whichever LLM provider is configured in AI Test Settings. If AI
suggestions are disabled or no API key is set, falls back to a small rule
table matching common Frappe exception types so the report is never empty.
"""

import json

import frappe
import requests

FALLBACK_RULES = [
	("PermissionError", "Check role permissions and User Permissions for the doctype involved."),
	("LinkValidationError", "Verify that linked records exist and are not disabled or cancelled."),
	("MandatoryError", "A required field was left blank; review the field list and default values."),
	("UniqueValidationError", "A duplicate value was submitted for a field marked unique."),
	("ValidationError", "A business rule validation failed; review custom validate() logic for this doctype."),
	("DoesNotExistError", "The referenced record was not found; check naming series/keys or seed data."),
	("Timeout", "The operation exceeded the expected time; check for long-running hooks or external API calls."),
	("KeyError", "Code referenced a field/key that does not exist; check for a recent field rename or removal."),
]


def generate_suggestion(message, error_log):
	settings = frappe.get_single("AI Test Settings")

	if settings.get("enable_ai_suggestions") and settings.get("api_key") and settings.get("ai_provider") != "None":
		try:
			return _call_llm(settings, message, error_log)
		except Exception:
			frappe.log_error(title="AI Test Suite: LLM suggestion call failed")

	return _fallback_suggestion(message, error_log)


def _fallback_suggestion(message, error_log):
	text = f"{message}\n{error_log}"
	for keyword, suggestion in FALLBACK_RULES:
		if keyword.lower() in text.lower():
			return keyword, suggestion
	return "Unclassified error", "Review the error log/stack trace manually; no matching known pattern was found."


def _call_llm(settings, message, error_log):
	provider = settings.get("ai_provider")
	api_key = settings.get_password("api_key")
	model = settings.get("model_name")

	prompt = (
		"You are assisting with debugging a failed automated test for a Frappe/ERPNext "
		"business process. Given the error message and stack trace below, respond with a "
		"strict JSON object: {\"root_cause\": \"<one sentence>\", \"suggestion\": \"<one or two "
		"sentences on how to fix it>\"}. Do not include any text outside the JSON.\n\n"
		f"Error message: {message}\n\nStack trace:\n{(error_log or '')[:4000]}"
	)

	if provider == "Anthropic":
		resp = requests.post(
			"https://api.anthropic.com/v1/messages",
			headers={
				"x-api-key": api_key,
				"anthropic-version": "2023-06-01",
				"content-type": "application/json",
			},
			json={
				"model": model or "claude-sonnet-5",
				"max_tokens": 300,
				"messages": [{"role": "user", "content": prompt}],
			},
			timeout=30,
		)
		resp.raise_for_status()
		text = resp.json()["content"][0]["text"]
	else:  # OpenAI-compatible default
		resp = requests.post(
			"https://api.openai.com/v1/chat/completions",
			headers={"Authorization": f"Bearer {api_key}"},
			json={
				"model": model or "gpt-4o-mini",
				"messages": [{"role": "user", "content": prompt}],
				"max_tokens": 300,
			},
			timeout=30,
		)
		resp.raise_for_status()
		text = resp.json()["choices"][0]["message"]["content"]

	try:
		parsed = json.loads(text)
		return parsed.get("root_cause", ""), parsed.get("suggestion", "")
	except (json.JSONDecodeError, TypeError):
		return "AI analysis", text.strip()
