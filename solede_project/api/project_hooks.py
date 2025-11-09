# Copyright (c) 2024, Solede SA and contributors
# For license information, please see license.txt

import frappe


def sync_tasks_hours(doc, method=None):
    """
    Hook: on_update
    Sincronizza ore previste totali con somma tasks
    """
    if not doc.name:
        return

    # Query somma expected_hours da tutti i tasks del project
    result = frappe.db.sql("""
        SELECT SUM(expected_hours) as total
        FROM `tabTask`
        WHERE project = %s AND docstatus < 2
    """, doc.name, as_dict=True)

    if result and result[0].total:
        doc.db_set("expected_total_hours", result[0].total, update_modified=False)
