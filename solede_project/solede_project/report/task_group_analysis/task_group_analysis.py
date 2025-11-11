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
			"label": _("Task Group"),
			"fieldname": "task_group",
			"fieldtype": "Link",
			"options": "Task",
			"width": 180
		},
		{
			"label": _("Project"),
			"fieldname": "project",
			"fieldtype": "Link",
			"options": "Project",
			"width": 150
		},
		{
			"label": _("Total Hours"),
			"fieldname": "total_hours",
			"fieldtype": "Float",
			"width": 120,
			"precision": 2
		},
		{
			"label": _("Expected Hours"),
			"fieldname": "expected_hours",
			"fieldtype": "Float",
			"width": 130,
			"precision": 2
		},
		{
			"label": _("Variance"),
			"fieldname": "variance",
			"fieldtype": "Float",
			"width": 100,
			"precision": 2
		},
		{
			"label": _("% Complete"),
			"fieldname": "percent_complete",
			"fieldtype": "Percent",
			"width": 110
		},
		{
			"label": _("Child Tasks"),
			"fieldname": "task_count",
			"fieldtype": "Int",
			"width": 110
		},
		{
			"label": _("Employees"),
			"fieldname": "employee_count",
			"fieldtype": "Int",
			"width": 100
		}
	]


def get_data(filters):
	"""Fetch task group analysis data"""
	show_breakdown = filters.get("show_task_breakdown", 1)

	# Get group summary
	group_data = get_group_summary(filters)

	if show_breakdown:
		data = []
		for group in group_data:
			# Add group row
			data.append(group)

			# Get child tasks
			tasks = get_task_breakdown(group["task_group"], filters)
			for task in tasks:
				task["indent"] = 1
				data.append(task)

		return data
	else:
		return group_data


def get_group_summary(filters):
	"""Get aggregated data per task group (parent_task)"""
	conditions = get_conditions(filters)

	query = f"""
		SELECT
			COALESCE(t.parent_task, 'Ungrouped') as task_group,
			t.project,
			SUM(tsd.hours) as total_hours,
			SUM(t.expected_hours) as expected_hours,
			COUNT(DISTINCT t.name) as task_count,
			COUNT(DISTINCT ts.employee) as employee_count
		FROM `tabTask` t
		INNER JOIN `tabTimesheet Detail` tsd ON tsd.task = t.name
		INNER JOIN `tabTimesheet` ts ON tsd.parent = ts.name
		WHERE
			ts.docstatus IN (0, 1)
			AND tsd.from_time >= %(from_date)s
			AND tsd.from_time <= %(to_date)s
			{conditions}
		GROUP BY COALESCE(t.parent_task, 'Ungrouped'), t.project
		ORDER BY total_hours DESC
	"""

	data = frappe.db.sql(query, filters, as_dict=1)

	# Calculate variance and percentage
	for row in data:
		row.variance = row.total_hours - (row.expected_hours or 0)
		if row.expected_hours and row.expected_hours > 0:
			row.percent_complete = (row.total_hours / row.expected_hours) * 100
		else:
			row.percent_complete = 0 if row.total_hours == 0 else 100

	return data


def get_task_breakdown(parent_task, filters):
	"""Get child tasks for a parent_task"""
	conditions = get_conditions(filters)

	# Handle ungrouped tasks
	if parent_task == "Ungrouped":
		parent_condition = "t.parent_task IS NULL"
	else:
		parent_condition = f"t.parent_task = '{parent_task}'"

	query = f"""
		SELECT
			t.name as task_group,
			t.subject as project,
			SUM(tsd.hours) as total_hours,
			t.expected_hours,
			COUNT(DISTINCT ts.employee) as employee_count
		FROM `tabTask` t
		INNER JOIN `tabTimesheet Detail` tsd ON tsd.task = t.name
		INNER JOIN `tabTimesheet` ts ON tsd.parent = ts.name
		WHERE
			ts.docstatus IN (0, 1)
			AND tsd.from_time >= %(from_date)s
			AND tsd.from_time <= %(to_date)s
			AND {parent_condition}
			{conditions}
		GROUP BY t.name
		ORDER BY total_hours DESC
	"""

	data = frappe.db.sql(query, filters, as_dict=1)

	# Calculate variance and percentage
	for row in data:
		row.variance = row.total_hours - (row.expected_hours or 0)
		if row.expected_hours and row.expected_hours > 0:
			row.percent_complete = (row.total_hours / row.expected_hours) * 100
		else:
			row.percent_complete = 0 if row.total_hours == 0 else 100

		# Set task_count to None for breakdown rows
		row.task_count = None

	return data


def get_conditions(filters):
	"""Build WHERE conditions"""
	conditions = []

	if filters.get("project"):
		projects = filters.get("project")
		if isinstance(projects, str):
			projects = [projects]
		project_conditions = "', '".join(projects)
		conditions.append(f"t.project IN ('{project_conditions}')")

	if filters.get("parent_task"):
		parent_tasks = filters.get("parent_task")
		if isinstance(parent_tasks, str):
			parent_tasks = [parent_tasks]
		parent_conditions = "', '".join(parent_tasks)
		conditions.append(f"t.parent_task IN ('{parent_conditions}')")

	return " AND " + " AND ".join(conditions) if conditions else ""


def get_chart_data(data, filters):
	"""Generate chart based on selected type"""
	if not data:
		return None

	# Filter only group-level rows (no indent)
	group_rows = [row for row in data if not row.get("indent")]

	if not group_rows:
		return None

	chart_type = filters.get("chart_type", "Bar - Hours per Group")

	if chart_type == "Pie - Group Distribution":
		return get_pie_chart(group_rows)
	elif chart_type == "Bar - Group Progress":
		return get_progress_chart(group_rows)
	else:  # Default: Bar - Hours per Group
		return get_bar_chart(group_rows)


def get_bar_chart(group_rows):
	"""Bar chart: Hours per Task Group"""
	# Limit to top 10
	if len(group_rows) > 10:
		group_rows = group_rows[:10]

	labels = [row.task_group for row in group_rows]
	values = [row.total_hours for row in group_rows]

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


def get_pie_chart(group_rows):
	"""Pie chart: Task Group Distribution"""
	# Limit to top 10
	if len(group_rows) > 10:
		group_rows = group_rows[:10]

	labels = [row.task_group for row in group_rows]
	values = [row.total_hours for row in group_rows]

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


def get_progress_chart(group_rows):
	"""Bar chart: % Complete per Task Group"""
	# Limit to top 10
	if len(group_rows) > 10:
		group_rows = group_rows[:10]

	labels = [row.task_group for row in group_rows]
	values = [row.percent_complete for row in group_rows]

	return {
		"data": {
			"labels": labels,
			"datasets": [
				{
					"name": _("% Complete"),
					"values": values
				}
			]
		},
		"type": "bar",
		"colors": ["#2196F3"]
	}
