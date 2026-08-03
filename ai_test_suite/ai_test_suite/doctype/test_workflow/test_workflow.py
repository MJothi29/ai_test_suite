import frappe
from frappe.model.document import Document


class TestWorkflow(Document):
	def validate(self):
		if self.workflow_type == "Module-wise" and not self.module:
			frappe.throw("Module is required for a Module-wise workflow")
		if not self.steps:
			frappe.throw("Add at least one Test Workflow Step")
