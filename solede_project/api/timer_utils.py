# Copyright (c) 2024, Solede SA and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import now_datetime, time_diff_in_hours


@frappe.whitelist()
def force_close_all_timers():
    """
    Utility di emergenza: Chiude TUTTI i timer attivi
    - Trova tutti i time_logs con completed=0 o to_time=NULL
    - Chiude i timer calcolando le ore
    - Resetta i flag timer_running nei Task
    """
    frappe.only_for("System Manager")  # Solo admin

    result = {
        "timesheets_updated": 0,
        "time_logs_closed": 0,
        "tasks_updated": 0,
        "errors": []
    }

    # 1. Trova tutti i time_logs con timer attivo
    active_logs = frappe.db.sql("""
        SELECT
            tsd.name as log_name,
            tsd.parent as timesheet,
            tsd.from_time,
            tsd.to_time,
            tsd.completed,
            tsd.task,
            ts.docstatus
        FROM `tabTimesheet Detail` tsd
        INNER JOIN `tabTimesheet` ts ON ts.name = tsd.parent
        WHERE (tsd.completed = 0 OR tsd.to_time IS NULL)
        AND ts.docstatus = 0
    """, as_dict=True)

    frappe.msgprint(_("Found {0} active timers to close").format(len(active_logs)))

    # 2. Raggruppa per timesheet
    timesheets = {}
    for log in active_logs:
        if log.timesheet not in timesheets:
            timesheets[log.timesheet] = []
        timesheets[log.timesheet].append(log)

    # 3. Chiudi i timer per ogni timesheet
    for timesheet_name, logs in timesheets.items():
        try:
            timesheet = frappe.get_doc("Timesheet", timesheet_name)

            for log_data in logs:
                # Trova la riga corrispondente
                for log in timesheet.time_logs:
                    if log.name == log_data.log_name:
                        # Chiudi il timer
                        if not log.to_time:
                            log.to_time = now_datetime()

                        if not log.hours or log.hours == 0:
                            log.hours = time_diff_in_hours(log.to_time, log.from_time)

                        log.completed = 1
                        result["time_logs_closed"] += 1
                        break

            timesheet.save()
            result["timesheets_updated"] += 1

        except Exception as e:
            result["errors"].append(f"Timesheet {timesheet_name}: {str(e)}")

    # 4. Reset tutti i task con timer_running=1
    tasks_with_timer = frappe.get_all("Task",
        filters={"timer_running": 1},
        pluck="name"
    )

    for task_name in tasks_with_timer:
        try:
            frappe.db.set_value("Task", task_name, {
                "timer_running": 0,
                "timer_started_at": None
            }, update_modified=False)
            result["tasks_updated"] += 1
        except Exception as e:
            result["errors"].append(f"Task {task_name}: {str(e)}")

    frappe.db.commit()

    # Messaggio di successo
    msg = _("""
        <h4>Timer chiusi con successo!</h4>
        <ul>
            <li>Timesheet aggiornati: {0}</li>
            <li>Time logs chiusi: {1}</li>
            <li>Task aggiornati: {2}</li>
        </ul>
    """).format(
        result["timesheets_updated"],
        result["time_logs_closed"],
        result["tasks_updated"]
    )

    if result["errors"]:
        msg += "<h5>Errori:</h5><ul>"
        for error in result["errors"]:
            msg += f"<li>{error}</li>"
        msg += "</ul>"

    frappe.msgprint(msg, title=_("Force Close Timers"), indicator="green")

    return result


@frappe.whitelist()
def get_active_timers_count():
    """
    Restituisce il conteggio dei timer attivi
    """
    count = frappe.db.sql("""
        SELECT COUNT(*) as count
        FROM `tabTimesheet Detail` tsd
        INNER JOIN `tabTimesheet` ts ON ts.name = tsd.parent
        WHERE (tsd.completed = 0 OR tsd.to_time IS NULL)
        AND ts.docstatus = 0
    """, as_dict=True)

    return count[0].count if count else 0
