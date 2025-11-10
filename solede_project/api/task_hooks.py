# Copyright (c) 2024, Solede SA and contributors
# For license information, please see license.txt

import frappe


def calculate_actual_hours_from_timesheet(doc, method=None):
    """
    Hook: on_update
    Calcola ore effettive da Timesheet collegati al Task
    Include timesheet in bozza (docstatus = 0) e submitted (docstatus = 1)
    Calcola automaticamente il progress in base alle ore
    """
    if not doc.name:
        return

    # Query somma ore da Timesheet (include draft e submitted)
    result = frappe.db.sql("""
        SELECT SUM(hours) as total
        FROM `tabTimesheet Detail`
        WHERE task = %s
        AND docstatus IN (0, 1)
    """, doc.name, as_dict=True)

    actual_hours = result[0].total if result and result[0].total else 0

    # Calcola variance
    expected = doc.expected_hours or 0
    variance = actual_hours - expected

    # Calcola progress in percentuale (arrotondato a 2 decimali)
    progress = 0
    if expected > 0:
        progress = round(min((actual_hours / expected) * 100, 100), 2)  # Max 100%

    # Aggiorna senza triggare on_update ricorsivo
    doc.db_set({
        "actual_hours": actual_hours,
        "hours_variance": variance,
        "progress": progress
    }, update_modified=False)


def handle_task_completion(doc, method=None):
    """
    Hook: on_update
    Quando un task viene completato, sottometti il timesheet collegato
    """
    if doc.status == "Completed" and doc.linked_timesheet:
        timesheet = frappe.get_doc("Timesheet", doc.linked_timesheet)
        if timesheet.docstatus == 0:
            timesheet.submit()
            frappe.msgprint(f"Timesheet {timesheet.name} submitted automatically")
