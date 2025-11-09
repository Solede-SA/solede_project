# Copyright (c) 2024, Solede SA and contributors
# For license information, please see license.txt

import frappe


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
