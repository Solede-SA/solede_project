# Copyright (c) 2024, Solede SA and contributors
# For license information, please see license.txt

import frappe


def calculate_actual_hours_from_timesheet(doc, method=None):
    """
    Hook: on_update
    Calcola ore effettive da Timesheet collegati al Task
    """
    if not doc.name:
        return

    # Query somma ore da Timesheet
    result = frappe.db.sql("""
        SELECT SUM(hours) as total
        FROM `tabTimesheet Detail`
        WHERE task = %s
        AND docstatus = 1
    """, doc.name, as_dict=True)

    actual_hours = result[0].total if result and result[0].total else 0

    # Calcola variance
    expected = doc.expected_hours or 0
    variance = actual_hours - expected

    # Aggiorna senza triggare on_update ricorsivo
    doc.db_set({
        "actual_hours": actual_hours,
        "hours_variance": variance
    }, update_modified=False)
