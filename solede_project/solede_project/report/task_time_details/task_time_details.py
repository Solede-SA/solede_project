# Copyright (c) 2024, Solede SA and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import add_days, today


def execute(filters=None):
	# Set default date range if not provided
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
			"label": _("Task"),
			"fieldname": "task",
			"fieldtype": "Link",
			"options": "Task",
			"width": 150
		},
		{
			"label": _("Subject"),
			"fieldname": "subject",
			"fieldtype": "Data",
			"width": 200
		},
		{
			"label": _("Project"),
			"fieldname": "project",
			"fieldtype": "Link",
			"options": "Project",
			"width": 150
		},
		{
			"label": _("Status"),
			"fieldname": "status",
			"fieldtype": "Data",
			"width": 100
		},
		{
			"label": _("Employee"),
			"fieldname": "employee_name",
			"fieldtype": "Data",
			"width": 150
		},
		{
			"label": _("Activity Type"),
			"fieldname": "activity_type",
			"fieldtype": "Link",
			"options": "Activity Type",
			"width": 130
		},
		{
			"label": _("Date"),
			"fieldname": "log_date",
			"fieldtype": "Date",
			"width": 100
		},
		{
			"label": _("Hours"),
			"fieldname": "hours",
			"fieldtype": "Float",
			"width": 80,
			"precision": 2
		},
		{
			"label": _("Billable"),
			"fieldname": "is_billable",
			"fieldtype": "Check",
			"width": 80
		},
		{
			"label": _("Description"),
			"fieldname": "description",
			"fieldtype": "Text",
			"width": 200
		}
	]


def get_data(filters):
	"""Fetch task time details"""
	conditions = get_conditions(filters)

	query = f"""
		SELECT
			t.name as task,
			t.subject,
			t.project,
			t.status,
			e.employee_name,
			tsd.activity_type,
			DATE(tsd.from_time) as log_date,
			tsd.hours,
			tsd.is_billable,
			tsd.description
		FROM `tabTimesheet Detail` tsd
		INNER JOIN `tabTimesheet` ts ON tsd.parent = ts.name
		INNER JOIN `tabTask` t ON tsd.task = t.name
		INNER JOIN `tabEmployee` e ON ts.employee = e.name
		WHERE
			ts.docstatus IN (0, 1)
			AND tsd.from_time >= %(from_date)s
			AND tsd.from_time <= %(to_date)s
			{conditions}
		ORDER BY tsd.from_time DESC, t.name
	"""

	data = frappe.db.sql(query, filters, as_dict=1)
	return data


def get_conditions(filters):
	"""Build WHERE conditions"""
	conditions = []

	if filters.get("task"):
		tasks = filters.get("task")
		if isinstance(tasks, str):
			tasks = [tasks]
		task_conditions = "', '".join(tasks)
		conditions.append(f"t.name IN ('{task_conditions}')")

	if filters.get("project"):
		projects = filters.get("project")
		if isinstance(projects, str):
			projects = [projects]
		project_conditions = "', '".join(projects)
		conditions.append(f"t.project IN ('{project_conditions}')")

	if filters.get("employee"):
		employees = filters.get("employee")
		if isinstance(employees, str):
			employees = [employees]
		employee_conditions = "', '".join(employees)
		conditions.append(f"ts.employee IN ('{employee_conditions}')")

	if filters.get("status"):
		conditions.append(f"t.status = '{filters.get('status')}'")

	return " AND " + " AND ".join(conditions) if conditions else ""


def get_chart_data(data, filters):
	"""Generate chart based on selected type"""
	if not data:
		return None

	chart_type = filters.get("chart_type", "Bar - Hours per Task")

	if chart_type == "Line - Timeline Progression":
		return get_timeline_chart(data)
	elif chart_type == "Pie - Employee Distribution":
		return get_employee_pie_chart(data)
	else:  # Default: Bar - Hours per Task
		return get_task_bar_chart(data)


def get_task_bar_chart(data):
	"""Bar chart: Hours per Task"""
	task_hours = {}
	for row in data:
		task = row.task
		if task not in task_hours:
			task_hours[task] = 0
		task_hours[task] += row.hours

	# Sort and limit to top 10
	sorted_tasks = sorted(task_hours.items(), key=lambda x: x[1], reverse=True)[:10]
	labels = [x[0] for x in sorted_tasks]
	values = [x[1] for x in sorted_tasks]

	return {
		"data": {
			"labels": labels,
			"datasets": [
				{
					"name": _("Hours"),
					"values": values
				}
			]
		},
		"type": "bar",
		"colors": ["#4CAF50"]
	}


def get_timeline_chart(data):
	"""Line chart: Timeline Progression"""
	date_hours = {}
	for row in data:
		date = str(row.log_date)
		if date not in date_hours:
			date_hours[date] = 0
		date_hours[date] += row.hours

	sorted_dates = sorted(date_hours.keys())
	labels = sorted_dates
	values = [date_hours[d] for d in sorted_dates]

	return {
		"data": {
			"labels": labels,
			"datasets": [
				{
					"name": _("Hours"),
					"values": values
				}
			]
		},
		"type": "line",
		"colors": ["#2196F3"]
	}


def get_employee_pie_chart(data):
	"""Pie chart: Employee Distribution"""
	employee_hours = {}
	for row in data:
		emp = row.employee_name
		if emp not in employee_hours:
			employee_hours[emp] = 0
		employee_hours[emp] += row.hours

	# Limit to top 10
	sorted_employees = sorted(employee_hours.items(), key=lambda x: x[1], reverse=True)[:10]
	labels = [x[0] for x in sorted_employees]
	values = [x[1] for x in sorted_employees]

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
