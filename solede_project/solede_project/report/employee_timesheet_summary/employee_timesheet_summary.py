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

	columns = get_columns(filters)
	data = get_data(filters)
	chart = get_chart_data(data, filters)

	return columns, data, None, chart


def get_columns(filters):
	"""Define report columns based on filters"""
	columns = []

	# Add period column if grouping is selected
	if filters.get("group_by") and filters.get("group_by") != "None":
		columns.append({
			"label": _("Period"),
			"fieldname": "period",
			"fieldtype": "Data",
			"width": 120
		})

	columns.extend([
		{
			"label": _("Employee"),
			"fieldname": "employee",
			"fieldtype": "Link",
			"options": "Employee",
			"width": 150
		},
		{
			"label": _("Employee Name"),
			"fieldname": "employee_name",
			"fieldtype": "Data",
			"width": 180
		},
		{
			"label": _("Department"),
			"fieldname": "department",
			"fieldtype": "Link",
			"options": "Department",
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
			"label": _("Number of Tasks"),
			"fieldname": "task_count",
			"fieldtype": "Int",
			"width": 130
		},
		{
			"label": _("Number of Projects"),
			"fieldname": "project_count",
			"fieldtype": "Int",
			"width": 150
		},
		{
			"label": _("Avg Hours per Day"),
			"fieldname": "avg_hours_per_day",
			"fieldtype": "Float",
			"width": 150,
			"precision": 2
		}
	])

	return columns


def get_data(filters):
	"""Fetch timesheet data based on filters"""
	if not filters.get("from_date") or not filters.get("to_date"):
		frappe.throw(_("From Date and To Date are mandatory"))

	conditions = get_conditions(filters)
	group_by_clause = get_group_by_clause(filters)

	query = f"""
		SELECT
			{get_select_clause(filters)}
			ts.employee,
			e.employee_name,
			e.department,
			SUM(tsd.hours) as total_hours,
			SUM(CASE WHEN tsd.is_billable = 1 THEN tsd.hours ELSE 0 END) as billable_hours,
			SUM(CASE WHEN tsd.is_billable = 0 THEN tsd.hours ELSE 0 END) as non_billable_hours,
			COUNT(DISTINCT tsd.task) as task_count,
			COUNT(DISTINCT tsd.project) as project_count,
			COUNT(DISTINCT DATE(tsd.from_time)) as working_days
		FROM `tabTimesheet Detail` tsd
		INNER JOIN `tabTimesheet` ts ON tsd.parent = ts.name
		INNER JOIN `tabEmployee` e ON ts.employee = e.name
		LEFT JOIN `tabTask` t ON tsd.task = t.name
		LEFT JOIN `tabProject` p ON tsd.project = p.name
		WHERE
			ts.docstatus IN (0, 1)
			AND tsd.from_time >= %(from_date)s
			AND tsd.from_time <= %(to_date)s
			{conditions}
		{group_by_clause}
		ORDER BY {get_order_by_clause(filters)}
	"""

	data = frappe.db.sql(query, filters, as_dict=1)

	# Calculate average hours per day
	for row in data:
		if row.working_days > 0:
			row.avg_hours_per_day = row.total_hours / row.working_days
		else:
			row.avg_hours_per_day = 0

	return data


def get_select_clause(filters):
	"""Build SELECT clause based on group_by filter"""
	group_by = filters.get("group_by")

	if not group_by or group_by == "None":
		return ""
	elif group_by == "Day":
		return "DATE(tsd.from_time) as period,"
	elif group_by == "Week":
		return "DATE_FORMAT(tsd.from_time, '%%Y-W%%u') as period,"
	elif group_by == "Month":
		return "DATE_FORMAT(tsd.from_time, '%%Y-%%m') as period,"
	elif group_by == "Quarter":
		return "CONCAT(YEAR(tsd.from_time), '-Q', QUARTER(tsd.from_time)) as period,"

	return ""


def get_group_by_clause(filters):
	"""Build GROUP BY clause based on group_by filter"""
	group_by = filters.get("group_by")

	base_group = "GROUP BY ts.employee"

	if not group_by or group_by == "None":
		return base_group
	elif group_by == "Day":
		return f"GROUP BY DATE(tsd.from_time), ts.employee"
	elif group_by == "Week":
		return f"GROUP BY YEARWEEK(tsd.from_time), ts.employee"
	elif group_by == "Month":
		return f"GROUP BY YEAR(tsd.from_time), MONTH(tsd.from_time), ts.employee"
	elif group_by == "Quarter":
		return f"GROUP BY YEAR(tsd.from_time), QUARTER(tsd.from_time), ts.employee"

	return base_group


def get_order_by_clause(filters):
	"""Build ORDER BY clause based on group_by filter"""
	group_by = filters.get("group_by")

	if not group_by or group_by == "None":
		return "total_hours DESC"
	else:
		return "period DESC, total_hours DESC"


def get_conditions(filters):
	"""Build additional WHERE conditions from filters"""
	conditions = []

	if filters.get("employee"):
		employees = filters.get("employee")
		if isinstance(employees, str):
			employees = [employees]
		employee_conditions = "', '".join(employees)
		conditions.append(f"ts.employee IN ('{employee_conditions}')")

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

	if filters.get("activity_type"):
		activity_types = filters.get("activity_type")
		if isinstance(activity_types, str):
			activity_types = [activity_types]
		activity_conditions = "', '".join(activity_types)
		conditions.append(f"tsd.activity_type IN ('{activity_conditions}')")

	return " AND " + " AND ".join(conditions) if conditions else ""


def get_chart_data(data, filters):
	"""Generate chart data for visualization"""
	if not data:
		return None

	chart_type = filters.get("chart_type", "Bar - Hours per Employee")

	if chart_type == "Pie - Billable vs Non-Billable":
		return get_pie_chart(data)
	elif chart_type == "Line - Trend over Time":
		return get_line_chart(data, filters)
	else:  # Default: Bar - Hours per Employee
		return get_bar_chart(data, filters)


def get_bar_chart(data, filters):
	"""Bar chart: Hours per Employee"""
	# For grouped data, aggregate by employee
	if filters.get("group_by") and filters.get("group_by") != "None":
		# Aggregate by employee across all periods
		employee_totals = {}
		for row in data:
			emp = row.employee_name
			if emp not in employee_totals:
				employee_totals[emp] = 0
			employee_totals[emp] += row.total_hours

		labels = list(employee_totals.keys())
		values = list(employee_totals.values())
	else:
		labels = [row.employee_name for row in data]
		values = [row.total_hours for row in data]

	# Limit to top 10 employees for readability
	if len(labels) > 10:
		# Sort by values and take top 10
		sorted_data = sorted(zip(labels, values), key=lambda x: x[1], reverse=True)[:10]
		labels = [x[0] for x in sorted_data]
		values = [x[1] for x in sorted_data]

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
	"""Pie chart: Billable vs Non-Billable Hours"""
	total_billable = sum(row.billable_hours for row in data)
	total_non_billable = sum(row.non_billable_hours for row in data)

	if total_billable == 0 and total_non_billable == 0:
		return None

	return {
		"data": {
			"labels": [_("Billable Hours"), _("Non-Billable Hours")],
			"datasets": [
				{
					"values": [total_billable, total_non_billable]
				}
			]
		},
		"type": "pie",
		"colors": ["#2196F3", "#FF9800"]
	}


def get_line_chart(data, filters):
	"""Line chart: Trend over Time"""
	group_by = filters.get("group_by")

	if not group_by or group_by == "None":
		# If no grouping, can't show trend - fallback to bar chart
		return get_bar_chart(data, filters)

	# Aggregate by period
	period_totals = {}
	for row in data:
		period = row.get("period")
		if period:
			if period not in period_totals:
				period_totals[period] = 0
			period_totals[period] += row.total_hours

	# Sort periods
	sorted_periods = sorted(period_totals.keys())
	labels = sorted_periods
	values = [period_totals[p] for p in sorted_periods]

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
		"type": "line",
		"colors": ["#9C27B0"]
	}
