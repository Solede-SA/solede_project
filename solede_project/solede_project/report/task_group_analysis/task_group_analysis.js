// Copyright (c) 2024, Solede SA and contributors
// For license information, please see license.txt

frappe.query_reports["Task Group Analysis"] = {
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
			"fieldname": "parent_task",
			"label": __("Task Group"),
			"fieldtype": "MultiSelectList",
			"options": "Task",
			"get_data": function(txt) {
				return frappe.db.get_link_options('Task', txt, {
					'is_group': 1
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
			"options": ["Bar - Hours per Group", "Pie - Group Distribution", "Bar - Group Progress"],
			"default": "Bar - Hours per Group"
		}
	]
};
