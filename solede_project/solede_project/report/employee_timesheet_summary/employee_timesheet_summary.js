// Copyright (c) 2024, Solede SA and contributors
// For license information, please see license.txt

frappe.query_reports["Employee Timesheet Summary"] = {
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
			"fieldname": "employee",
			"label": __("Employee"),
			"fieldtype": "MultiSelectList",
			"options": "Employee",
			"get_data": function(txt) {
				return frappe.db.get_link_options('Employee', txt);
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
			"fieldname": "customer",
			"label": __("Customer"),
			"fieldtype": "MultiSelectList",
			"options": "Customer",
			"get_data": function(txt) {
				return frappe.db.get_link_options('Customer', txt);
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
			"fieldname": "group_by",
			"label": __("Group By"),
			"fieldtype": "Select",
			"options": ["None", "Day", "Week", "Month", "Quarter"],
			"default": "None"
		},
		{
			"fieldname": "chart_type",
			"label": __("Chart Type"),
			"fieldtype": "Select",
			"options": ["Bar - Hours per Employee", "Pie - Billable vs Non-Billable", "Line - Trend over Time"],
			"default": "Bar - Hours per Employee"
		}
	]
};
