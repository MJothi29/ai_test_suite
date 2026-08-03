app_name = "ai_test_suite"
app_title = "AI Test Suite"
app_publisher = "Nalam Hospital"
app_description = "AI-powered testing application for validating Frappe/ERPNext business processes at Functional, UI and Technical levels."
app_email = "md.office@nalamhospital.in"
app_license = "MIT"

# Include the custom Desk page in the app's menu / desk
# (Frappe auto-discovers pages under <module>/page/<page_name>/)

# Whitelisted methods used by the front-end are defined directly in:
#   ai_test_suite.ai_test_suite.test_engine.runner
#   ai_test_suite.ai_test_suite.reports_export.export
#   ai_test_suite.ai_test_suite.api
# No additional hook wiring is required for them.

# Realtime event used to stream execution progress to the browser:
#   event name: "ai_test_progress"
