# Copyright (c) 2024, Solede SA and contributors
# For license information, please see license.txt

import frappe


def create_default_phases(doc, method=None):
    """
    Hook: after_insert
    Crea le fasi di default "Offerta" e "Esecuzione" per un nuovo progetto
    """
    if not doc.name:
        return

    # Verifica se il progetto ha già delle fasi (es. creato da template)
    if doc.get("project_phases") and len(doc.project_phases) > 0:
        return

    # Crea le fasi di default
    default_phases = [
        {"phase_name": "Offerta", "sequence": 1, "status": "Open"},
        {"phase_name": "Esecuzione", "sequence": 2, "status": "Open"}
    ]

    for phase_data in default_phases:
        doc.append("project_phases", phase_data)

    doc.save(ignore_permissions=True)


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
