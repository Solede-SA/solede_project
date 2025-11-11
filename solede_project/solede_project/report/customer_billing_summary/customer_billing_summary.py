# Copyright (c) 2024, Solede SA and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import add_days, today


def execute(filters=None):
	if not filters:
		filters = {}

	if not filters.get("from_date"):
		filters["from_date"] = add_days(today(), -30)

	if not filters.get("to_date"):
		filters["to_date"] = today()

	columns = get_columns(filters)
	data = get_data(filters)
	chart = get_chart_data(data, filters)

	return columns, data, None, chart


def get_columns(filters):
	"""Define report columns"""
	columns = [
		{
			"label": _("Customer"),
			"fieldname": "customer",
			"fieldtype": "Link",
			"options": "Customer",
			"width": 180
		},
		{
			"label": _("Total Hours"),
			"fieldname": "total_hours",
			"fieldtype": "Float",
			"width": 120,
			"precision": 2
		},
		{
			"label": _("Billable Hours"),
			"fieldname": "billable_hours",
			"fieldtype": "Float",
			"width": 120,
			"precision": 2
		},
		{
			"label": _("Non-Billable Hours"),
			"fieldname": "non_billable_hours",
			"fieldtype": "Float",
			"width": 150,
			"precision": 2
		},
		{
			"label": _("Projects"),
			"fieldname": "project_count",
			"fieldtype": "Int",
			"width": 100
		},
		{
			"label": _("Tasks"),
			"fieldname": "task_count",
			"fieldtype": "Int",
			"width": 100
		}
	]

	return columns


def get_data(filters):
	"""Fetch customer billing data"""
	show_breakdown = filters.get("show_breakdown", 1)

	# Get customer summary
	customer_data = get_customer_summary(filters)

	if show_breakdown:
		data = []
		for customer in customer_data:
			# Add customer row
			data.append(customer)

			# Get project breakdown
			projects = get_project_breakdown(customer["customer"], filters)
			for project in projects:
				project["indent"] = 1
				data.append(project)

		return data
	else:
		return customer_data


def get_customer_summary(filters):
	"""Get aggregated data per customer"""
	conditions = get_conditions(filters)

	query = f"""
		SELECT
			p.customer,
			SUM(tsd.hours) as total_hours,
			SUM(CASE WHEN tsd.is_billable = 1 THEN tsd.hours ELSE 0 END) as billable_hours,
			SUM(CASE WHEN tsd.is_billable = 0 THEN tsd.hours ELSE 0 END) as non_billable_hours,
			COUNT(DISTINCT tsd.project) as project_count,
			COUNT(DISTINCT tsd.task) as task_count
		FROM `tabTimesheet Detail` tsd
		INNER JOIN `tabTimesheet` ts ON tsd.parent = ts.name
		INNER JOIN `tabProject` p ON tsd.project = p.name
		WHERE
			ts.docstatus IN (0, 1)
			AND tsd.from_time >= %(from_date)s
			AND tsd.from_time <= %(to_date)s
			AND p.customer IS NOT NULL
			{conditions}
		GROUP BY p.customer
		ORDER BY total_hours DESC
	"""

	data = frappe.db.sql(query, filters, as_dict=1)
	return data


def get_project_breakdown(customer, filters):
	"""Get project breakdown for a customer"""
	conditions = get_conditions(filters)

	query = f"""
		SELECT
			p.name as customer,
			SUM(tsd.hours) as total_hours,
			SUM(CASE WHEN tsd.is_billable = 1 THEN tsd.hours ELSE 0 END) as billable_hours,
			SUM(CASE WHEN tsd.is_billable = 0 THEN tsd.hours ELSE 0 END) as non_billable_hours,
			COUNT(DISTINCT tsd.task) as task_count
		FROM `tabTimesheet Detail` tsd
		INNER JOIN `tabTimesheet` ts ON tsd.parent = ts.name
		INNER JOIN `tabProject` p ON tsd.project = p.name
		WHERE
			ts.docstatus IN (0, 1)
			AND tsd.from_time >= %(from_date)s
			AND tsd.from_time <= %(to_date)s
			AND p.customer = %(customer)s
			{conditions}
		GROUP BY p.name
		ORDER BY total_hours DESC
	"""

	project_filters = filters.copy()
	project_filters["customer"] = customer

	data = frappe.db.sql(query, project_filters, as_dict=1)

	# Set project_count to empty for breakdown rows
	for row in data:
		row.project_count = None

	return data


def get_conditions(filters):
	"""Build WHERE conditions"""
	conditions = []

	if filters.get("customer"):
		customers = filters.get("customer")
		if isinstance(customers, str):
			customers = [customers]
		customer_conditions = "', '".join(customers)
		conditions.append(f"p.customer IN ('{customer_conditions}')")

	if filters.get("project"):
		projects = filters.get("project")
		if isinstance(projects, str):
			projects = [projects]
		project_conditions = "', '".join(projects)
		conditions.append(f"tsd.project IN ('{project_conditions}')")

	return " AND " + " AND ".join(conditions) if conditions else ""


def get_chart_data(data, filters):
	"""Generate chart based on selected type"""
	if not data:
		return None

	# Filter only customer-level rows (no indent)
	customer_rows = [row for row in data if not row.get("indent")]

	if not customer_rows:
		return None

	chart_type = filters.get("chart_type", "Bar - Hours per Customer")

	if chart_type == "Pie - Customer Distribution":
		return get_pie_chart(customer_rows)
	elif chart_type == "Bar - Billable Hours":
		return get_billable_chart(customer_rows)
	else:  # Default: Bar - Hours per Customer
		return get_bar_chart(customer_rows)


def get_bar_chart(customer_rows):
	"""Bar chart: Total Hours per Customer"""
	# Limit to top 10
	if len(customer_rows) > 10:
		customer_rows = customer_rows[:10]

	labels = [row.customer for row in customer_rows]
	values = [row.total_hours for row in customer_rows]

	return {
		"data": {
			"labels": labels,
			"datasets": [
				{
					"name": _("Total Hours"),
					"values": values
				}
			]
		},
		"type": "bar",
		"colors": ["#4CAF50"]
	}


def get_pie_chart(customer_rows):
	"""Pie chart: Customer Distribution"""
	# Limit to top 10
	if len(customer_rows) > 10:
		customer_rows = customer_rows[:10]

	labels = [row.customer for row in customer_rows]
	values = [row.total_hours for row in customer_rows]

	return {
		"data": {
			"labels": labels,
			"datasets": [
				{
					"values": values
				}
			]
		},
		"type": "pie",
		"colors": ["#2196F3", "#4CAF50", "#FF9800", "#9C27B0", "#F44336", "#00BCD4", "#FFEB3B", "#795548", "#607D8B", "#E91E63"]
	}


def get_billable_chart(customer_rows):
	"""Bar chart: Billable vs Non-Billable Hours"""
	# Limit to top 10
	if len(customer_rows) > 10:
		customer_rows = customer_rows[:10]

	labels = [row.customer for row in customer_rows]
	billable_values = [row.billable_hours for row in customer_rows]
	non_billable_values = [row.non_billable_hours for row in customer_rows]

	return {
		"data": {
			"labels": labels,
			"datasets": [
				{
					"name": _("Billable Hours"),
					"values": billable_values
				},
				{
					"name": _("Non-Billable Hours"),
					"values": non_billable_values
				}
			]
		},
		"type": "bar",
		"colors": ["#2196F3", "#FF9800"]
	}
