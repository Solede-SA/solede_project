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

	columns = get_columns()
	data = get_data(filters)
	chart = get_chart_data(data, filters)

	return columns, data, None, chart


def get_columns():
	"""Define report columns"""
	return [
		{
			"label": _("Activity Type"),
			"fieldname": "activity_type",
			"fieldtype": "Link",
			"options": "Activity Type",
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
			"label": _("Projects"),
			"fieldname": "project_count",
			"fieldtype": "Int",
			"width": 100
		},
		{
			"label": _("Employees"),
			"fieldname": "employee_count",
			"fieldtype": "Int",
			"width": 100
		},
		{
			"label": _("Tasks"),
			"fieldname": "task_count",
			"fieldtype": "Int",
			"width": 100
		},
		{
			"label": _("Avg Hours per Task"),
			"fieldname": "avg_hours_per_task",
			"fieldtype": "Float",
			"width": 150,
			"precision": 2
		}
	]


def get_data(filters):
	"""Fetch activity type analysis data"""
	conditions = get_conditions(filters)

	query = f"""
		SELECT
			tsd.activity_type,
			SUM(tsd.hours) as total_hours,
			SUM(CASE WHEN tsd.is_billable = 1 THEN tsd.hours ELSE 0 END) as billable_hours,
			COUNT(DISTINCT tsd.project) as project_count,
			COUNT(DISTINCT ts.employee) as employee_count,
			COUNT(DISTINCT tsd.task) as task_count
		FROM `tabTimesheet Detail` tsd
		INNER JOIN `tabTimesheet` ts ON tsd.parent = ts.name
		LEFT JOIN `tabProject` p ON tsd.project = p.name
		WHERE
			ts.docstatus IN (0, 1)
			AND tsd.from_time >= %(from_date)s
			AND tsd.from_time <= %(to_date)s
			{conditions}
		GROUP BY tsd.activity_type
		ORDER BY total_hours DESC
	"""

	data = frappe.db.sql(query, filters, as_dict=1)

	# Calculate average
	for row in data:
		if row.task_count > 0:
			row.avg_hours_per_task = row.total_hours / row.task_count
		else:
			row.avg_hours_per_task = 0

	return data


def get_conditions(filters):
	"""Build WHERE conditions"""
	conditions = []

	if filters.get("activity_type"):
		activity_types = filters.get("activity_type")
		if isinstance(activity_types, str):
			activity_types = [activity_types]
		activity_conditions = "', '".join(activity_types)
		conditions.append(f"tsd.activity_type IN ('{activity_conditions}')")

	if filters.get("project"):
		projects = filters.get("project")
		if isinstance(projects, str):
			projects = [projects]
		project_conditions = "', '".join(projects)
		conditions.append(f"tsd.project IN ('{project_conditions}')")

	if filters.get("customer"):
		customers = filters.get("customer")
		if isinstance(customers, str):
			customers = [customers]
		customer_conditions = "', '".join(customers)
		conditions.append(f"p.customer IN ('{customer_conditions}')")

	if filters.get("employee"):
		employees = filters.get("employee")
		if isinstance(employees, str):
			employees = [employees]
		employee_conditions = "', '".join(employees)
		conditions.append(f"ts.employee IN ('{employee_conditions}')")

	return " AND " + " AND ".join(conditions) if conditions else ""


def get_chart_data(data, filters):
	"""Generate chart based on selected type"""
	if not data:
		return None

	chart_type = filters.get("chart_type", "Bar - Hours per Activity")

	if chart_type == "Pie - Activity Distribution":
		return get_pie_chart(data)
	elif chart_type == "Bar - Activity by Project":
		return get_activity_by_project_chart(filters)
	else:  # Default: Bar - Hours per Activity
		return get_bar_chart(data)


def get_bar_chart(data):
	"""Bar chart: Hours per Activity Type"""
	labels = [row.activity_type for row in data[:10]]
	values = [row.total_hours for row in data[:10]]

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


def get_pie_chart(data):
	"""Pie chart: Activity Distribution"""
	labels = [row.activity_type for row in data[:10]]
	values = [row.total_hours for row in data[:10]]

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


def get_activity_by_project_chart(filters):
	"""Bar chart: Activity Type breakdown by Project"""
	conditions = get_conditions(filters)

	query = f"""
		SELECT
			p.name as project,
			tsd.activity_type,
			SUM(tsd.hours) as hours
		FROM `tabTimesheet Detail` tsd
		INNER JOIN `tabTimesheet` ts ON tsd.parent = ts.name
		INNER JOIN `tabProject` p ON tsd.project = p.name
		WHERE
			ts.docstatus IN (0, 1)
			AND tsd.from_time >= %(from_date)s
			AND tsd.from_time <= %(to_date)s
			{conditions}
		GROUP BY p.name, tsd.activity_type
		ORDER BY p.name, hours DESC
		LIMIT 50
	"""

	data = frappe.db.sql(query, filters, as_dict=1)

	if not data:
		return None

	# Group by project
	projects = {}
	for row in data:
		if row.project not in projects:
			projects[row.project] = {}
		projects[row.project][row.activity_type] = row.hours

	# Get unique activity types
	all_activities = set()
	for proj_activities in projects.values():
		all_activities.update(proj_activities.keys())

	# Build datasets
	datasets = []
	colors = ["#2196F3", "#4CAF50", "#FF9800", "#9C27B0", "#F44336"]
	for i, activity in enumerate(list(all_activities)[:5]):
		dataset_values = []
		for project in projects.keys():
			dataset_values.append(projects[project].get(activity, 0))

		datasets.append({
			"name": activity,
			"values": dataset_values
		})

	return {
		"data": {
			"labels": list(projects.keys())[:10],
			"datasets": datasets
		},
		"type": "bar",
		"colors": colors
	}
