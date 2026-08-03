AI TEST SUITE - Frappe/ERPNext Custom App (starter codebase)
==============================================================

WHAT THIS IS
------------
A starter Frappe custom app that lets an Administrator run Module-wise or
DocType-to-DocType workflow tests (e.g. Lead -> Opportunity -> Quotation ->
Sales Order) at three levels - Functional, UI, and Technical - from a single
Desk page, with live progress, AI-assisted root cause analysis on failures,
PDF/Excel report export, and execution history.

FOLDER STRUCTURE
-----------------
ai_test_suite/                     <- app root (this is the git repo / bench app)
  setup.py, requirements.txt, MANIFEST.in, license.txt
  ai_test_suite/                   <- python package (app_name)
    hooks.py
    modules.txt                    <- declares module "AI Test Suite"
    ai_test_suite/                 <- module folder (doctype/page/logic live here)
      doctype/
        ai_test_settings/          <- Single: API keys, provider, UI runner URL
        test_workflow/             <- defines a workflow (module-wise or chain)
        test_workflow_step/        <- child table: one step per doctype/action
        test_execution/            <- one record per test run, holds results + reports
        test_execution_result/     <- child table: per-step, per-level outcome
      page/ai_test_runner/         <- the Administrator-facing Desk page
        ai_test_runner.js          <- module/workflow picker, Run button, live log,
                                       summary cards, export buttons, history table
      test_engine/
        runner.py                  <- orchestrator: queues + executes a run,
                                       streams progress via frappe.publish_realtime
        functional.py              <- business-logic / workflow outcome checks
        ui.py                      <- delegates to an external Playwright/
                                       Selenium/Cypress runner (configurable URL)
        technical.py                <- API/method resolvability, DB table checks,
                                       permissions, recent Error Log entries
      ai/
        suggestions.py             <- calls OpenAI or Anthropic for root cause +
                                       fix suggestions on failures; falls back to
                                       a rule table if no API key is configured
      reports_export/
        export.py                  <- generates PDF (via frappe get_pdf) and
                                       Excel (via make_xlsx) reports, attaches
                                       them to the Test Execution record
        templates/report.html      <- Jinja template used for the PDF report
      api.py                       <- read-only helpers: list workflows, list
                                       execution history

HOW IT WORKS END TO END
-------------------------
1. Administrator creates one or more "Test Workflow" records, each with a
   list of "Test Workflow Step" rows (DocType + Action + optional custom
   Python assertion script + which levels the step applies to).
2. On the "AI Test Runner" Desk page, pick a Module and/or Workflow, tick
   Functional / UI / Technical, click Run.
3. This calls start_test_execution(), which creates a "Test Execution"
   record and queues execute_workflow() as a background job (frappe.enqueue)
   so the browser is never blocked.
4. execute_workflow() walks every step at every requested level and calls
   functional.run() / ui.run() / technical.run() as appropriate, catching
   exceptions and rolling back any DB writes made by the test itself.
5. Each result is appended to the execution record and pushed to the
   browser instantly via frappe.publish_realtime (event "ai_test_progress"),
   so the log and pass/fail counters update in real time.
6. On failure, ai/suggestions.py sends the error + stack trace to the
   configured LLM (or a fallback rule table) to produce a root cause and
   fix suggestion, stored alongside the result.
7. When done, the Administrator can export the full report as PDF or Excel
   (reports_export/export.py) and browse past runs in the History table on
   the same page (backed by Test Execution list + api.get_execution_history).

INSTALLATION (on an existing bench)
--------------------------------------
1. Copy this "ai_test_suite" folder into your bench's apps/ directory, or
   turn it into a git repo and use: bench get-app <repo-url>
2. bench --site <your-site> install-app ai_test_suite
3. bench --site <your-site> migrate
4. Open the Desk, search for "AI Test Runner" to open the page.
5. Configure AI Test Settings (single doctype) with your OpenAI/Anthropic
   API key if you want AI-generated root cause suggestions, and optionally
   a UI Test Runner Webhook URL if you have a Playwright/Selenium/Cypress
   service for browser-level checks.

WHAT'S INTENTIONALLY LEFT FOR YOU TO WIRE UP
-----------------------------------------------
- UI-level testing needs a real browser; this scaffold calls out to an
  external automation service rather than embedding Selenium/Playwright in
  the Frappe worker process. You'll need to stand up (or point to) that
  service and have it return {"passed": true/false, "message": "..."}.
- The generic "Create" functional test only fills mandatory Data/Text
  fields with placeholder values. For real business-process validation,
  fill in each step's "Custom Test Script" field with a short Python
  snippet that sets local variables `result` ("Pass"/"Fail"/"Warning") and
  `message`, using the `frappe` and `step` objects made available to it.
- Doctype JSON files here are hand-written to match Frappe's schema; run
  `bench migrate` and review in the DocType list UI to confirm formatting
  before relying on them in production.
- No fixtures/sample Test Workflow records are included - create a couple
  for your own modules (e.g. CRM: Lead -> Opportunity -> Quotation) to see
  the flow end to end.
