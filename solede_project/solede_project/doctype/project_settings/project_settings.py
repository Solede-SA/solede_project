# Copyright (c) 2024, Solede SA and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class ProjectSettings(Document):
	def validate(self):
		if self.enable_long_timer_alert and self.max_timer_hours <= 0:
			frappe.throw(_("Alert After Hours must be greater than 0"))
