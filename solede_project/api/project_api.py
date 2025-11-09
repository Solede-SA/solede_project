# Copyright (c) 2024, Solede SA and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate


@frappe.whitelist()
def create_sales_invoice_from_timesheet(project_name, from_date, to_date):
    """
    API Method
    Crea Sales Invoice da Timesheet per billing Time-based
    """
    project = frappe.get_doc("Project", project_name)

    # Valida billing mode
    if project.billing_mode != "Time-based":
        frappe.throw(_("Project billing mode must be Time-based"))

    # Query Timesheet nel periodo
    timesheets = frappe.db.sql("""
        SELECT
            td.parent,
            td.task,
            td.activity_type,
            td.hours,
            td.billing_rate,
            td.billing_amount
        FROM `tabTimesheet Detail` td
        INNER JOIN `tabTimesheet` t ON t.name = td.parent
        WHERE td.project = %s
        AND t.docstatus = 1
        AND td.from_time BETWEEN %s AND %s
    """, (project_name, from_date, to_date), as_dict=True)

    if not timesheets:
        frappe.throw(_("No billable timesheets found in period"))

    # Crea Sales Invoice
    invoice = frappe.new_doc("Sales Invoice")
    invoice.customer = project.customer
    invoice.project = project.name
    invoice.posting_date = getdate()

    # Raggruppa per Task
    task_hours = {}
    for ts in timesheets:
        task_name = ts.task or "No Task"
        if task_name not in task_hours:
            task_hours[task_name] = {
                "hours": 0,
                "amount": 0
            }
        task_hours[task_name]["hours"] += ts.hours or 0
        task_hours[task_name]["amount"] += ts.billing_amount or 0

    # Crea Invoice Items
    for task_name, data in task_hours.items():
        if task_name != "No Task":
            task = frappe.get_doc("Task", task_name)
            description = f"{task.subject} - {data['hours']} hours"
        else:
            description = f"Time tracking - {data['hours']} hours"

        invoice.append("items", {
            "item_code": "TIMESHEET-HOURS",
            "description": description,
            "qty": data["hours"],
            "uom": "Hour",
            "rate": data["amount"] / data["hours"] if data["hours"] > 0 else 0,
            "amount": data["amount"]
        })

    invoice.insert()

    return {
        "success": True,
        "invoice": invoice.name,
        "message": _("Sales Invoice {0} created successfully").format(invoice.name)
    }


@frappe.whitelist()
def create_milestone_invoice(project_name, milestone_name, percentage):
    """
    API Method
    Crea Sales Invoice per milestone (Forfait progressivo)
    """
    project = frappe.get_doc("Project", project_name)

    # Valida billing mode
    if project.billing_mode != "Forfait Progressivo":
        frappe.throw(_("Project billing mode must be Forfait Progressivo"))

    # Calcola importo
    amount = flt(project.total_quoted_amount) * flt(percentage) / 100

    # Crea Sales Invoice
    invoice = frappe.new_doc("Sales Invoice")
    invoice.customer = project.customer
    invoice.project = project.name
    invoice.posting_date = getdate()

    invoice.append("items", {
        "item_code": "MILESTONE-PAYMENT",
        "description": f"{milestone_name} - {percentage}%",
        "qty": 1,
        "rate": amount,
        "amount": amount
    })

    invoice.insert()

    return {
        "success": True,
        "invoice": invoice.name,
        "message": _("Sales Invoice {0} created successfully").format(invoice.name)
    }
