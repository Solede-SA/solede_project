# Copyright (c) 2024, Solede SA and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
	columns = get_columns(filters)
	data = get_data(filters)
	chart = get_chart_data(data, filters)

	return columns, data, None, chart


def get_columns(filters):
	"""Define report columns"""
	columns = [
		{
			"label": _("Project"),
			"fieldname": "project",
			"fieldtype": "Link",
			"options": "Project",
			"width": 180
		},
		{
			"label": _("Customer"),
			"fieldname": "customer",
			"fieldtype": "Link",
			"options": "Customer",
			"width": 150
		},
		{
			"label": _("Status"),
			"fieldname": "status",
			"fieldtype": "Data",
			"width": 100
		},
		{
			"label": _("Planned Hours"),
			"fieldname": "planned_hours",
			"fieldtype": "Float",
			"width": 120,
			"precision": 2
		},
		{
			"label": _("Actual Hours"),
			"fieldname": "actual_hours",
			"fieldtype": "Float",
			"width": 120,
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
			"label": _("Billable Hours"),
			"fieldname": "billable_hours",
			"fieldtype": "Float",
			"width": 120,
			"precision": 2
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
			"width": 80
		}
	]

	return columns


def get_data(filters):
	"""Fetch project and task data based on filters"""
	if not filters.get("from_date") or not filters.get("to_date"):
		frappe.throw(_("From Date and To Date are mandatory"))

	show_task_breakdown = filters.get("show_task_breakdown", 1)

	# Get project summary data
	project_data = get_project_summary(filters)

	# If breakdown is enabled, add task details
	if show_task_breakdown:
		data = []
		for project in project_data:
			# Add project row
			data.append(project)

			# Get tasks for this project
			tasks = get_task_breakdown(project["project"], filters)
			for task in tasks:
				# Mark as task row with indent
				task["indent"] = 1
				data.append(task)

		return data
	else:
		return project_data


def get_project_summary(filters):
	"""Get aggregated data per project"""
	conditions = get_conditions(filters)

	query = f"""
		SELECT
			p.name as project,
			p.customer,
			p.status,
			COALESCE(p.expected_time, 0) as planned_hours,
			COALESCE(SUM(tsd.hours), 0) as actual_hours,
			COALESCE(SUM(CASE WHEN tsd.is_billable = 1 THEN tsd.hours ELSE 0 END), 0) as billable_hours,
			COUNT(DISTINCT ts.employee) as employee_count,
			COUNT(DISTINCT tsd.task) as task_count
		FROM `tabProject` p
		LEFT JOIN `tabTimesheet Detail` tsd ON tsd.project = p.name
			AND tsd.from_time >= %(from_date)s
			AND tsd.from_time <= %(to_date)s
		LEFT JOIN `tabTimesheet` ts ON tsd.parent = ts.name
			AND ts.docstatus IN (0, 1)
		WHERE 1=1
			{conditions}
		GROUP BY p.name
		HAVING actual_hours > 0 OR planned_hours > 0
		ORDER BY p.name
	"""

	data = frappe.db.sql(query, filters, as_dict=1)

	# Calculate variance and percentage
	for row in data:
		row.variance = row.actual_hours - row.planned_hours
		if row.planned_hours > 0:
			row.percent_complete = (row.actual_hours / row.planned_hours) * 100
		else:
			row.percent_complete = 0 if row.actual_hours == 0 else 100

	return data


def get_task_breakdown(project, filters):
	"""Get task-level breakdown for a project"""
	conditions = get_task_conditions(filters)

	query = f"""
		SELECT
			t.name as project,
			t.subject as customer,
			t.status as status,
			COALESCE(t.expected_hours, 0) as planned_hours,
			COALESCE(SUM(tsd.hours), 0) as actual_hours,
			COALESCE(SUM(CASE WHEN tsd.is_billable = 1 THEN tsd.hours ELSE 0 END), 0) as billable_hours,
			COUNT(DISTINCT ts.employee) as employee_count,
			t.parent_task
		FROM `tabTask` t
		LEFT JOIN `tabTimesheet Detail` tsd ON tsd.task = t.name
			AND tsd.from_time >= %(from_date)s
			AND tsd.from_time <= %(to_date)s
		LEFT JOIN `tabTimesheet` ts ON tsd.parent = ts.name
			AND ts.docstatus IN (0, 1)
		WHERE t.project = %(project)s
			{conditions}
		GROUP BY t.name
		HAVING actual_hours > 0 OR planned_hours > 0
		ORDER BY t.parent_task, t.name
	"""

	task_filters = filters.copy()
	task_filters["project"] = project

	data = frappe.db.sql(query, task_filters, as_dict=1)

	# Calculate variance and percentage for tasks
	for row in data:
		row.variance = row.actual_hours - row.planned_hours
		if row.planned_hours > 0:
			row.percent_complete = (row.actual_hours / row.planned_hours) * 100
		else:
			row.percent_complete = 0 if row.actual_hours == 0 else 100

		# Show parent task in customer column for visual grouping
		if row.parent_task:
			row.customer = f"[{row.parent_task}] {row.customer}"

		# Task count is always 1 for task rows
		row.task_count = 1

	return data


def get_conditions(filters):
	"""Build WHERE conditions for project query"""
	conditions = []

	if filters.get("project"):
		projects = filters.get("project")
		if isinstance(projects, str):
			projects = [projects]
		project_conditions = "', '".join(projects)
		conditions.append(f"p.name IN ('{project_conditions}')")

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

	if filters.get("activity_type"):
		activity_types = filters.get("activity_type")
		if isinstance(activity_types, str):
			activity_types = [activity_types]
		activity_conditions = "', '".join(activity_types)
		conditions.append(f"tsd.activity_type IN ('{activity_conditions}')")

	return " AND " + " AND ".join(conditions) if conditions else ""


def get_task_conditions(filters):
	"""Build WHERE conditions for task query"""
	conditions = []

	if filters.get("task_status"):
		statuses = filters.get("task_status")
		if isinstance(statuses, str):
			statuses = [statuses]
		status_conditions = "', '".join(statuses)
		conditions.append(f"t.status IN ('{status_conditions}')")

	if filters.get("employee"):
		employees = filters.get("employee")
		if isinstance(employees, str):
			employees = [employees]
		employee_conditions = "', '".join(employees)
		conditions.append(f"ts.employee IN ('{employee_conditions}')")

	if filters.get("activity_type"):
		activity_types = filters.get("activity_type")
		if isinstance(activity_types, str):
			activity_types = [activity_types]
		activity_conditions = "', '".join(activity_types)
		conditions.append(f"tsd.activity_type IN ('{activity_conditions}')")

	return " AND " + " AND ".join(conditions) if conditions else ""


def get_chart_data(data, filters):
	"""Generate chart data showing % completion per project"""
	if not data:
		return None

	# Filter only project-level rows (no indent)
	project_rows = [row for row in data if not row.get("indent")]

	if not project_rows:
		return None

	# Limit to top 10 projects for readability
	if len(project_rows) > 10:
		project_rows = sorted(project_rows, key=lambda x: x.get("actual_hours", 0), reverse=True)[:10]

	labels = [row.get("project") for row in project_rows]
	percent_values = [row.get("percent_complete", 0) for row in project_rows]

	chart = {
		"data": {
			"labels": labels,
			"datasets": [
				{
					"name": _("% Complete"),
					"values": percent_values
				}
			]
		},
		"type": "bar",
		"colors": ["#2196F3"],
		"axisOptions": {
			"xIsSeries": 1
		},
		"barOptions": {
			"stacked": 0
		}
	}

	return chart
