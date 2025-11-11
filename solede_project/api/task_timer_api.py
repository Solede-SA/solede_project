# Copyright (c) 2024, Solede SA and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import now_datetime, time_diff_in_hours, get_datetime


def get_or_create_timesheet(task, employee):
    """
    Helper function: Recupera timesheet esistente o ne crea uno nuovo
    Cambia automaticamente lo status del Task a "Working" al primo inserimento
    Returns: (timesheet, is_new)
    """
    if task.linked_timesheet:
        timesheet = frappe.get_doc("Timesheet", task.linked_timesheet)
        if timesheet.docstatus != 0:
            frappe.throw(_("Cannot add time to a submitted timesheet. Timesheet {0} is already submitted.").format(timesheet.name))
        return timesheet, False
    else:
        # Crea nuovo Timesheet
        timesheet = frappe.new_doc("Timesheet")
        timesheet.employee = employee
        timesheet.task = task.name

        # Popola parent_project e customer dal task
        if task.project:
            project = frappe.get_doc("Project", task.project)
            timesheet.parent_project = task.project
            if project.customer:
                timesheet.customer = project.customer

        # Cambia status Task a "Working" (DRY: logica centralizzata)
        task.db_set("status", "Working", update_modified=False)

        return timesheet, True


@frappe.whitelist()
def start_timer(task_name, description=None):
    """
    Avvia il timer per un task
    """
    task = frappe.get_doc("Task", task_name)
    task.check_permission("write")

    if task.timer_running:
        frappe.throw(_("Timer is already running for this task"))

    if not task.activity_type:
        frappe.throw(_("Activity Type is required to start timer. Please set Activity Type first."))

    # Verifica che l'utente abbia un Employee associato
    employee = frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "name")
    if not employee:
        frappe.throw(_("No Employee record found for user {0}. Please create an Employee record first.").format(frappe.session.user))

    # Verifica che l'employee non abbia già altri timer attivi
    active_timers = frappe.db.sql("""
        SELECT t.name, t.subject
        FROM `tabTask` t
        INNER JOIN `tabTimesheet` ts ON t.linked_timesheet = ts.name
        WHERE
            t.timer_running = 1
            AND ts.employee = %(employee)s
            AND ts.docstatus = 0
            AND t.name != %(task_name)s
    """, {"employee": employee, "task_name": task_name}, as_dict=True)

    if active_timers:
        # Crea lista HTML con link cliccabili
        timer_links = []
        for t in active_timers:
            timer_links.append(f'<a href="/app/task/{t.name}" target="_blank"><b>{t.name}</b></a> ({t.subject})')

        timer_list_html = ", ".join(timer_links)

        frappe.throw(
            msg=_("You already have an active timer running on: {0}. Please stop it before starting a new one.").format(timer_list_html),
            title=_("Active Timer Found"),
            as_list=False
        )

    # Verifica o crea Timesheet
    timesheet, is_new_timesheet = get_or_create_timesheet(task, employee)

    # Aggiungi riga time_log
    # IMPORTANTE: completed=0 indica timer attivo, ERPNext lo riconoscerà
    from_time = now_datetime()
    time_log = timesheet.append("time_logs", {
        "activity_type": task.activity_type,
        "task": task.name,
        "project": task.project,
        "from_time": from_time,
        "to_time": None,  # Timer in corso
        "hours": 0,
        "completed": 0,  # Timer attivo (ERPNext lo riconoscerà)
        "is_billable": 1,
        "description": description or ""
    })

    if is_new_timesheet:
        timesheet.insert()
        task.db_set("linked_timesheet", timesheet.name, update_modified=False)
    else:
        timesheet.save()

    # Imposta flag timer running
    task.db_set({
        "timer_running": 1,
        "timer_started_at": now_datetime()
    }, update_modified=False)

    return {
        "success": True,
        "message": _("Timer started"),
        "timesheet": timesheet.name,
        "time_log": time_log.name,
        "started_at": now_datetime()
    }


@frappe.whitelist()
def stop_timer(task_name):
    """
    Ferma il timer per un task
    """
    task = frappe.get_doc("Task", task_name)
    task.check_permission("write")

    if not task.timer_running:
        frappe.throw(_("No timer is running for this task"))

    if not task.linked_timesheet:
        frappe.throw(_("No timesheet found for this task"))

    timesheet = frappe.get_doc("Timesheet", task.linked_timesheet)

    # Trova l'ultimo time_log per questo task (quello con completed=0)
    time_log = None
    for log in reversed(timesheet.time_logs):
        if log.task == task.name and log.completed == 0:
            time_log = log
            break

    if not time_log:
        frappe.throw(_("No active timer found in timesheet"))

    # Aggiorna time_log
    to_time = now_datetime()
    hours = time_diff_in_hours(to_time, time_log.from_time)

    time_log.to_time = to_time
    time_log.hours = hours
    time_log.completed = 1  # Marca come completato

    timesheet.save()

    # Reset flag timer
    task.db_set({
        "timer_running": 0,
        "timer_started_at": None
    }, update_modified=False)

    # Trigger ricalcolo ore
    task.reload()
    from solede_project.api.task_hooks import calculate_actual_hours_from_timesheet
    calculate_actual_hours_from_timesheet(task)

    return {
        "success": True,
        "message": _("Timer stopped"),
        "hours": hours,
        "timesheet": timesheet.name
    }


@frappe.whitelist()
def add_manual_time(task_name, from_time, to_time, hours=None, description=None):
    """
    Aggiunge tempo manualmente
    """
    task = frappe.get_doc("Task", task_name)
    task.check_permission("write")

    if not task.activity_type:
        frappe.throw(_("Activity Type is required. Please set Activity Type first."))

    # Verifica che l'utente abbia un Employee associato
    employee = frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "name")
    if not employee:
        frappe.throw(_("No Employee record found for user {0}").format(frappe.session.user))

    # Converti stringhe in datetime
    from_time = get_datetime(from_time)
    to_time = get_datetime(to_time)

    # Valida date
    if from_time >= to_time:
        frappe.throw(_("From Time must be before To Time"))

    # Calcola ore se non fornite
    if not hours:
        hours = time_diff_in_hours(to_time, from_time)

    # Verifica o crea Timesheet
    timesheet, is_new_timesheet = get_or_create_timesheet(task, employee)

    # Aggiungi riga time_log
    time_log = timesheet.append("time_logs", {
        "activity_type": task.activity_type,
        "task": task.name,
        "project": task.project,
        "from_time": from_time,
        "to_time": to_time,
        "hours": hours,
        "completed": 1,  # Tempo manuale è sempre completato
        "is_billable": 1,
        "description": description or ""
    })

    if is_new_timesheet:
        timesheet.insert()
        task.db_set("linked_timesheet", timesheet.name, update_modified=False)
    else:
        timesheet.save()

    # Trigger ricalcolo ore
    task.reload()
    from solede_project.api.task_hooks import calculate_actual_hours_from_timesheet
    calculate_actual_hours_from_timesheet(task)

    return {
        "success": True,
        "message": _("Time added successfully"),
        "hours": hours,
        "timesheet": timesheet.name,
        "time_log": time_log.name
    }


@frappe.whitelist()
def get_timer_status(task_name):
    """
    Restituisce lo stato del timer per un task
    """
    task = frappe.get_doc("Task", task_name)

    return {
        "timer_running": task.timer_running,
        "timer_started_at": task.timer_started_at,
        "linked_timesheet": task.linked_timesheet,
        "activity_type": task.activity_type,
        "actual_hours": task.actual_hours or 0,
        "expected_hours": task.expected_hours or 0
    }


@frappe.whitelist()
def get_active_timers(employee=None):
    """
    Recupera tutti i timer attivi
    Se employee è specificato, filtra per quell'employee
    Altrimenti mostra i timer dell'utente corrente
    """
    # Se non è specificato employee, usa quello dell'utente corrente
    if not employee:
        employee = frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "name")
        if not employee:
            return []

    # Recupera tutti i task con timer running per questo employee
    # Verifica che il timesheet collegato appartenga all'employee
    active_timers = frappe.db.sql("""
        SELECT
            t.name as task_name,
            t.subject as task_subject,
            t.timer_started_at,
            t.project,
            t.activity_type,
            t.linked_timesheet,
            ts.employee,
            p.project_name,
            p.customer
        FROM `tabTask` t
        LEFT JOIN `tabTimesheet` ts ON t.linked_timesheet = ts.name
        LEFT JOIN `tabProject` p ON t.project = p.name
        WHERE
            t.timer_running = 1
            AND ts.employee = %(employee)s
            AND ts.docstatus = 0
        ORDER BY t.timer_started_at DESC
    """, {"employee": employee}, as_dict=True)

    # Calcola elapsed time per ogni timer
    for timer in active_timers:
        if timer.timer_started_at:
            started = get_datetime(timer.timer_started_at)
            now = now_datetime()
            elapsed_seconds = (now - started).total_seconds()
            timer.elapsed_hours = elapsed_seconds / 3600
            timer.elapsed_formatted = format_elapsed_time(elapsed_seconds)

    return active_timers


def format_elapsed_time(seconds):
    """
    Formatta secondi in HH:MM:SS
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"
