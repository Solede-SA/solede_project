// Copyright (c) 2024, Solede SA and contributors
// For license information, please see license.txt

frappe.query_reports["Customer Billing Summary"] = {
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
			"fieldname": "customer",
			"label": __("Customer"),
			"fieldtype": "MultiSelectList",
			"options": "Customer",
			"get_data": function(txt) {
				return frappe.db.get_link_options('Customer', txt);
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
			"fieldname": "show_breakdown",
			"label": __("Show Project Breakdown"),
			"fieldtype": "Check",
			"default": 1
		},
		{
			"fieldname": "chart_type",
			"label": __("Chart Type"),
			"fieldtype": "Select",
			"options": ["Bar - Hours per Customer", "Pie - Customer Distribution", "Bar - Billable Hours"],
			"default": "Bar - Hours per Customer"
		}
	]
};
