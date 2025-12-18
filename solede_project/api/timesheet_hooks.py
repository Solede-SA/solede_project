# Copyright (c) 2024, Solede SA and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def validate_task_relationship(doc, method=None):
    """
    Hook: validate
    Valida relazione 1:1 con Task
    """
    if doc.task:
        # Verifica che non esista già un altro Timesheet per questo Task
        existing = frappe.db.get_value("Timesheet", {
            "task": doc.task,
            "name": ["!=", doc.name],
            "docstatus": ["<", 2]  # Escludi cancellati
        }, "name")

        if existing:
            frappe.throw(_("A Timesheet already exists for Task {0}: {1}").format(doc.task, existing))


def sync_task_link(doc, method=None):
    """
    Hook: after_insert / on_update
    Sincronizza campo linked_timesheet nel Task
    """
    if doc.task and doc.docstatus == 0:
        task = frappe.get_doc("Task", doc.task)
        if task.linked_timesheet != doc.name:
            task.db_set("linked_timesheet", doc.name, update_modified=False)


def update_task_actual_hours(doc, method=None):
    """
    Hook: on_submit / on_cancel
    Aggiorna Task actual_hours quando Timesheet viene submitted/cancelled
    """
    # Aggiorna tutti i Tasks referenziati nel Timesheet
    tasks = set()
    for detail in doc.time_logs:
        if detail.task:
            tasks.add(detail.task)

    # Trigger ricalcolo per ogni task
    for task_name in tasks:
        task = frappe.get_doc("Task", task_name)
        # Il ricalcolo avviene tramite hook task.on_update
        task.save()


def sync_timer_with_task(doc, method=None):
    """
    Hook: on_update
    Sincronizza lo stato del timer tra Timesheet e Task
    Se l'utente ferma/avvia il timer dal Timesheet, aggiorna il Task
    """
    if not doc.task:
        return

    # Cerca time_log attivo (completed=0) per questo task
    active_timer = None
    for log in doc.time_logs:
        if log.task == doc.task and log.completed == 0:
            active_timer = log
            break

    task = frappe.get_doc("Task", doc.task)

    if active_timer:
        # Timer attivo nel Timesheet -> assicurati che Task sia sincronizzato
        task.db_set({
            "timer_running": 1,
            "timer_started_at": active_timer.from_time
        }, update_modified=False)
    else:
        # Nessun timer attivo nel Timesheet -> assicurati che Task sia fermato
        if task.timer_running:
            task.db_set({
                "timer_running": 0,
                "timer_started_at": None
            }, update_modified=False)


def update_task_totals(doc, method=None):
    """
    Hook: on_update
    Aggiorna actual_hours dei Task quando si modificano le ore nel Timesheet
    """
    if doc.docstatus > 1:  # Ignora cancellati
        return

    # Trova tutti i task referenziati nei time_logs
    tasks = set()
    for detail in doc.time_logs:
        if detail.task:
            tasks.add(detail.task)

    # Aggiorna ogni task
    for task_name in tasks:
        # Calcola somma ore per questo task
        result = frappe.db.sql("""
            SELECT SUM(hours) as total
            FROM `tabTimesheet Detail`
            WHERE task = %s
            AND docstatus IN (0, 1)
        """, task_name, as_dict=True)

        actual_hours = result[0].total if result and result[0].total else 0

        # Recupera expected_hours per calcolare variance e progress
        task = frappe.get_doc("Task", task_name)
        expected = task.expected_hours or 0
        variance = actual_hours - expected
        progress = 0
        if expected > 0:
            progress = round(min((actual_hours / expected) * 100, 100), 2)

        # Aggiorna senza triggare eventi
        frappe.db.set_value("Task", task_name, {
            "actual_hours": actual_hours,
            "hours_variance": variance,
            "progress": progress
        }, update_modified=False)


def update_project_costing(doc, method=None):
    """
    Hook: on_update / after_insert
    Aggiorna Project total_costing_amount e total_billable_amount
    Include timesheet draft per avere visibilità real-time dei costi
    """
    if not doc.parent_project:
        return

    # Calcola totali da TUTTI i timesheet del progetto (draft + submitted)
    result = frappe.db.sql("""
        SELECT
            SUM(tsd.costing_amount) as total_costing,
            SUM(CASE WHEN tsd.is_billable = 1 THEN tsd.billing_amount ELSE 0 END) as total_billable
        FROM `tabTimesheet Detail` tsd
        INNER JOIN `tabTimesheet` ts ON ts.name = tsd.parent
        WHERE ts.parent_project = %s
        AND ts.docstatus IN (0, 1)
    """, doc.parent_project, as_dict=True)

    total_costing = result[0].total_costing if result and result[0].total_costing else 0
    total_billable = result[0].total_billable if result and result[0].total_billable else 0

    # Aggiorna Project senza triggare eventi
    frappe.db.set_value("Project", doc.parent_project, {
        "total_costing_amount": total_costing,
        "total_billable_amount": total_billable
    }, update_modified=False)
