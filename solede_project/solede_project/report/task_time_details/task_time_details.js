// Copyright (c) 2024, Solede SA and contributors
// For license information, please see license.txt

frappe.query_reports["Task Time Details"] = {
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
			"fieldname": "task",
			"label": __("Task"),
			"fieldtype": "MultiSelectList",
			"options": "Task",
			"get_data": function(txt) {
				return frappe.db.get_link_options('Task', txt);
			}
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
			"fieldname": "employee",
			"label": __("Employee"),
			"fieldtype": "MultiSelectList",
			"options": "Employee",
			"get_data": function(txt) {
				return frappe.db.get_link_options('Employee', txt);
			}
		},
		{
			"fieldname": "status",
			"label": __("Task Status"),
			"fieldtype": "Select",
			"options": "\nOpen\nWorking\nPending Review\nCompleted\nCancelled\nOverdue"
		},
		{
			"fieldname": "chart_type",
			"label": __("Chart Type"),
			"fieldtype": "Select",
			"options": ["Bar - Hours per Task", "Line - Timeline Progression", "Pie - Employee Distribution"],
			"default": "Bar - Hours per Task"
		}
	]
};
