# Copyright (c) 2024, Solede SA and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import now_datetime, time_diff_in_hours, get_datetime


def check_long_running_timers():
    """
    Scheduled task: Controlla timer che stanno girando da troppo tempo
    Invia email di alert agli utenti
    """
    # Recupera tutte le configurazioni attive
    all_settings = frappe.get_all(
        "Project Settings",
        filters={"enable_long_timer_alert": 1},
        fields=["name", "company", "max_timer_hours", "alert_frequency", "email_template"]
    )

    if not all_settings:
        frappe.logger().info("No active Project Settings found with timer alerts enabled")
        return

    total_timers = 0
    total_users = 0

    # Per ogni company con alert attivo
    for settings in all_settings:
        max_hours = settings.max_timer_hours or 8.0
        company = settings.company

        # Trova tutti i timer attivi per questa company
        active_timers = frappe.db.sql("""
            SELECT
                t.name as task_name,
                t.subject as task_subject,
                t.timer_started_at,
                t.project,
                t.linked_timesheet,
                ts.employee,
                ts.name as timesheet_name,
                e.user_id,
                e.employee_name,
                p.project_name,
                p.customer,
                c.name as company
            FROM `tabTask` t
            INNER JOIN `tabTimesheet` ts ON t.linked_timesheet = ts.name
            INNER JOIN `tabEmployee` e ON ts.employee = e.name
            LEFT JOIN `tabProject` p ON t.project = p.name
            LEFT JOIN `tabCompany` c ON p.company = c.name
            WHERE
                t.timer_running = 1
                AND t.timer_started_at IS NOT NULL
                AND ts.docstatus = 0
                AND c.name = %(company)s
        """, {"company": company}, as_dict=True)

        if not active_timers:
            continue

        # Filtra timer che superano le ore massime (in Python per gestire timezone)
        long_timers = []
        for timer in active_timers:
            started = get_datetime(timer.timer_started_at)
            elapsed_hours = time_diff_in_hours(now_datetime(), started)
            if elapsed_hours >= max_hours:
                timer.elapsed_hours = elapsed_hours
                long_timers.append(timer)

        if not long_timers:
            continue

        # Raggruppa per utente
        timers_by_user = {}
        for timer in long_timers:
            user_id = timer.user_id
            if user_id not in timers_by_user:
                timers_by_user[user_id] = []
            timers_by_user[user_id].append(timer)

        # Invia email a ciascun utente
        for user_id, timers in timers_by_user.items():
            frappe.log_error(f"Checking alert for user {user_id}, {len(timers)} timers, frequency={settings.alert_frequency}", "Timer Alert Debug")
            # Controlla se abbiamo già inviato un alert recentemente
            should_send = should_send_alert(user_id, timers, settings.alert_frequency)
            frappe.log_error(f"should_send_alert returned {should_send}", "Timer Alert Debug")
            if should_send:
                frappe.log_error(f"Calling send_timer_alert_email for {user_id}", "Timer Alert Debug")
                send_timer_alert_email(user_id, timers, settings)

        total_timers += len(long_timers)
        total_users += len(timers_by_user)

        frappe.logger().info(f"Company {company}: Processed {len(long_timers)} long running timers for {len(timers_by_user)} users")

    frappe.logger().info(f"Total: Processed {total_timers} long running timers for {total_users} users across {len(all_settings)} companies")


def should_send_alert(user_id, timers, frequency):
    """
    Determina se dobbiamo inviare l'alert in base alla frequenza configurata
    """
    if frequency == "Once":
        # Controlla se abbiamo già inviato un alert per questi timer
        for timer in timers:
            key = f"timer_alert_{timer.task_name}"
            if not frappe.cache().get(key):
                return True
        return False

    elif frequency == "Every Hour":
        # Controlla se è passata almeno un'ora dall'ultimo alert
        key = f"timer_alert_last_{user_id}"
        last_alert = frappe.cache().get(key)
        if not last_alert:
            return True

        last_alert_time = get_datetime(last_alert)
        hours_since_last = time_diff_in_hours(now_datetime(), last_alert_time)
        return hours_since_last >= 1.0

    elif frequency == "Every 2 Hours":
        key = f"timer_alert_last_{user_id}"
        last_alert = frappe.cache().get(key)
        if not last_alert:
            return True

        last_alert_time = get_datetime(last_alert)
        hours_since_last = time_diff_in_hours(now_datetime(), last_alert_time)
        return hours_since_last >= 2.0

    return True


def send_timer_alert_email(user_id, timers, settings):
    """
    Invia email di alert all'utente
    """
    try:
        # Prepara i dati per il template
        context = {
            "user": frappe.get_doc("User", user_id),
            "timers": timers,
            "company": timers[0].company if timers else None
        }

        # Se c'è un template configurato, usalo
        if settings.email_template:
            frappe.sendmail(
                recipients=[user_id],
                template=settings.email_template,
                args=context,
                subject=_("Long Running Timer Alert")
            )
        else:
            # Usa template di default
            subject = _("Timer Alert: You have {0} timer(s) running for a long time").format(len(timers))

            message = "<h3>Long Running Timer Alert</h3>"
            message += "<p>The following timer(s) have been running for a long time:</p>"
            message += "<ul>"

            for timer in timers:
                message += f"<li>"
                message += f"<strong>{timer.task_name}</strong>: {timer.task_subject}<br>"
                message += f"Project: {timer.project_name or timer.project}<br>"
                if timer.customer:
                    message += f"Customer: {timer.customer}<br>"
                message += f"Running for: <strong>{timer.elapsed_hours:.1f} hours</strong><br>"
                message += f'<a href="{frappe.utils.get_url()}/app/task/{timer.task_name}">Stop Timer</a>'
                message += f"</li><br>"

            message += "</ul>"
            message += "<p>Please stop the timer(s) if you've finished working on these tasks.</p>"

            frappe.sendmail(
                recipients=[user_id],
                subject=subject,
                message=message
            )

        # Salva timestamp dell'alert
        if settings.alert_frequency == "Once":
            for timer in timers:
                key = f"timer_alert_{timer.task_name}"
                frappe.cache().set(key, "1", expires_in_sec=86400)  # 24 ore
        else:
            key = f"timer_alert_last_{user_id}"
            frappe.cache().set(key, str(now_datetime()), expires_in_sec=86400)

        frappe.logger().info(f"Sent timer alert email to {user_id} for {len(timers)} timer(s)")

    except Exception as e:
        frappe.logger().error(f"Failed to send timer alert email to {user_id}: {str(e)}")


@frappe.whitelist()
def test_timer_alert(user_id=None, company=None):
    """
    API di test per verificare l'invio degli alert
    """
    if not user_id:
        user_id = frappe.session.user

    if not company:
        frappe.throw(_("Please specify a company"))

    # Recupera le impostazioni per la company specificata
    settings = frappe.get_all(
        "Project Settings",
        filters={"company": company},
        fields=["name", "company", "max_timer_hours", "alert_frequency", "email_template"]
    )

    if not settings:
        frappe.throw(_("No Project Settings found for company {0}").format(company))

    settings = frappe._dict(settings[0])

    # Simula un timer lungo
    test_timer = frappe._dict({
        "task_name": "TEST-001",
        "task_subject": "Test Task",
        "project": "Test Project",
        "project_name": "Test Project Name",
        "customer": "Test Customer",
        "elapsed_hours": 10.5,
        "company": company
    })

    send_timer_alert_email(user_id, [test_timer], settings)

    return {
        "success": True,
        "message": _("Test alert email sent to {0}").format(user_id)
    }
