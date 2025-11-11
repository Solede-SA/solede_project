// Copyright (c) 2024, Solede SA and contributors
// For license information, please see license.txt

frappe.query_reports["Project Time Analysis"] = {
	"filters": [
		{
			"fieldname": "from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.add_days(frappe.datetime.get_today(), -30),
			"reqd": 1
		},
		{
			"fieldname": "to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.get_today(),
			"reqd": 1
		},
		{
			"fieldname": "project",
			"label": __("Project"),
			"fieldtype": "MultiSelectList",
			"options": "Project",
			"get_data": function(txt) {
				return frappe.db.get_link_options('Project', txt);
			}
		},
		{
			"fieldname": "customer",
			"label": __("Customer"),
			"fieldtype": "MultiSelectList",
			"options": "Customer",
			"get_data": function(txt) {
				return frappe.db.get_link_options('Customer', txt);
			}
		},
		{
			"fieldname": "employee",
			"label": __("Employee"),
			"fieldtype": "MultiSelectList",
			"options": "Employee",
			"get_data": function(txt) {
				return frappe.db.get_link_options('Employee', txt);
			}
		},
		{
			"fieldname": "activity_type",
			"label": __("Activity Type"),
			"fieldtype": "MultiSelectList",
			"options": "Activity Type",
			"get_data": function(txt) {
				return frappe.db.get_link_options('Activity Type', txt);
			}
		},
		{
			"fieldname": "task_status",
			"label": __("Task Status"),
			"fieldtype": "MultiSelectList",
			"options": "Task",
			"get_data": function(txt) {
				return frappe.db.get_link_options('Task', txt, {
					'doctype': 'Task',
					'fieldname': 'status'
				});
			}
		},
		{
			"fieldname": "show_task_breakdown",
			"label": __("Show Task Breakdown"),
			"fieldtype": "Check",
			"default": 1
		},
		{
			"fieldname": "chart_type",
			"label": __("Chart Type"),
			"fieldtype": "Select",
			"options": ["Bar - % Completion", "Bar - Planned vs Actual", "Pie - Hours Distribution"],
			"default": "Bar - % Completion"
		}
	]
};
