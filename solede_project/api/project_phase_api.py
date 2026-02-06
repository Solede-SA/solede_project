# Copyright (c) 2026, Solede SA and contributors
# For license information, please see license.txt

import frappe
from frappe import _


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_project_phases(doctype, txt, searchfield, start, page_len, filters):
    """
    Query personalizzata per il campo Link project_phase.
    Mostra phase_name invece del name auto-generato.
    """
    project = filters.get("parent")
    if not project:
        return []

    return frappe.db.sql("""
        SELECT name, phase_name
        FROM `tabProject Phase`
        WHERE parent = %(project)s
          AND parenttype = 'Project'
          AND (phase_name LIKE %(txt)s OR name LIKE %(txt)s)
        ORDER BY sequence
        LIMIT %(start)s, %(page_len)s
    """, {
        "project": project,
        "txt": f"%{txt}%",
        "start": start,
        "page_len": page_len
    })


@frappe.whitelist()
def get_phase_summary(project_name):
    """
    Ritorna un riepilogo delle fasi di un progetto con ore e costi aggregati
    """
    project = frappe.get_doc("Project", project_name)

    phases_summary = []

    for phase in project.project_phases:
        # Calcola ore effettive dai Task
        task_hours = frappe.db.sql("""
            SELECT COALESCE(SUM(actual_hours), 0) as total_hours
            FROM `tabTask`
            WHERE project = %s AND project_phase = %s AND docstatus < 2
        """, (project_name, phase.name), as_dict=True)[0].total_hours

        # Calcola ore dai Timesheet Detail
        timesheet_hours = frappe.db.sql("""
            SELECT COALESCE(SUM(hours), 0) as total_hours
            FROM `tabTimesheet Detail`
            WHERE project = %s AND project_phase = %s AND docstatus = 1
        """, (project_name, phase.name), as_dict=True)[0].total_hours

        # Calcola costi effettivi dai Purchase Order Item
        po_cost = frappe.db.sql("""
            SELECT COALESCE(SUM(poi.amount), 0) as total_cost
            FROM `tabPurchase Order Item` poi
            INNER JOIN `tabPurchase Order` po ON poi.parent = po.name
            WHERE poi.project = %s AND poi.project_phase = %s AND po.docstatus = 1
        """, (project_name, phase.name), as_dict=True)[0].total_cost

        # Calcola costi effettivi dalle Purchase Invoice Item
        pi_cost = frappe.db.sql("""
            SELECT COALESCE(SUM(pii.amount), 0) as total_cost
            FROM `tabPurchase Invoice Item` pii
            INNER JOIN `tabPurchase Invoice` pi ON pii.parent = pi.name
            WHERE pii.project = %s AND pii.project_phase = %s AND pi.docstatus = 1
        """, (project_name, phase.name), as_dict=True)[0].total_cost

        phases_summary.append({
            "name": phase.name,
            "phase_name": phase.phase_name,
            "sequence": phase.sequence,
            "status": phase.status,
            "expected_start_date": phase.expected_start_date,
            "expected_end_date": phase.expected_end_date,
            "actual_start_date": phase.actual_start_date,
            "actual_end_date": phase.actual_end_date,
            "expected_hours": phase.expected_hours or 0,
            "actual_hours": max(task_hours, timesheet_hours),
            "expected_cost": phase.expected_cost or 0,
            "ordered_cost": po_cost,
            "invoiced_cost": pi_cost,
            "hours_progress": _calculate_progress(phase.expected_hours or 0, max(task_hours, timesheet_hours)),
            "cost_progress": _calculate_progress(phase.expected_cost or 0, pi_cost or po_cost)
        })

    return phases_summary


def _calculate_progress(expected, actual):
    """Calcola la percentuale di avanzamento"""
    if expected <= 0:
        return 0
    return min(round((actual / expected) * 100, 1), 100)


def update_phase_actuals(phase_name):
    """
    Aggiorna i campi calcolati (actual_hours, ordered_cost, invoiced_cost) di una fase
    """
    phase = frappe.get_doc("Project Phase", phase_name)
    project_name = phase.parent

    # Calcola ore effettive dai Task
    task_hours = frappe.db.sql("""
        SELECT COALESCE(SUM(actual_hours), 0) as total_hours
        FROM `tabTask`
        WHERE project = %s AND project_phase = %s AND docstatus < 2
    """, (project_name, phase_name), as_dict=True)[0].total_hours

    # Calcola ore dai Timesheet Detail
    timesheet_hours = frappe.db.sql("""
        SELECT COALESCE(SUM(hours), 0) as total_hours
        FROM `tabTimesheet Detail`
        WHERE project = %s AND project_phase = %s AND docstatus = 1
    """, (project_name, phase_name), as_dict=True)[0].total_hours

    # Calcola costi ordinati dai Purchase Order Item
    po_cost = frappe.db.sql("""
        SELECT COALESCE(SUM(poi.amount), 0) as total_cost
        FROM `tabPurchase Order Item` poi
        INNER JOIN `tabPurchase Order` po ON poi.parent = po.name
        WHERE poi.project = %s AND poi.project_phase = %s AND po.docstatus = 1
    """, (project_name, phase_name), as_dict=True)[0].total_cost

    # Calcola costi fatturati dalle Purchase Invoice Item
    pi_cost = frappe.db.sql("""
        SELECT COALESCE(SUM(pii.amount), 0) as total_cost
        FROM `tabPurchase Invoice Item` pii
        INNER JOIN `tabPurchase Invoice` pi ON pii.parent = pi.name
        WHERE pii.project = %s AND pii.project_phase = %s AND pi.docstatus = 1
    """, (project_name, phase_name), as_dict=True)[0].total_cost

    # Aggiorna i campi
    frappe.db.set_value("Project Phase", phase_name, {
        "actual_hours": max(task_hours, timesheet_hours),
        "ordered_cost": po_cost,
        "invoiced_cost": pi_cost
    }, update_modified=False)

    # Calcola date effettive
    _update_actual_dates(phase_name, project_name)


def _update_actual_dates(phase_name, project_name):
    """
    Aggiorna le date effettive di inizio e fine fase basandosi sui task
    """
    # Data inizio: prima data di inizio effettivo tra i task della fase
    start_date = frappe.db.sql("""
        SELECT MIN(act_start_date) as start_date
        FROM `tabTask`
        WHERE project = %s AND project_phase = %s AND act_start_date IS NOT NULL AND docstatus < 2
    """, (project_name, phase_name), as_dict=True)[0].start_date

    # Data fine: ultima data di completamento tra i task della fase (solo se tutti completati)
    all_tasks_completed = frappe.db.sql("""
        SELECT COUNT(*) as total, SUM(CASE WHEN status = 'Completed' THEN 1 ELSE 0 END) as completed
        FROM `tabTask`
        WHERE project = %s AND project_phase = %s AND docstatus < 2
    """, (project_name, phase_name), as_dict=True)[0]

    end_date = None
    if all_tasks_completed.total > 0 and all_tasks_completed.total == all_tasks_completed.completed:
        end_date = frappe.db.sql("""
            SELECT MAX(completed_on) as end_date
            FROM `tabTask`
            WHERE project = %s AND project_phase = %s AND docstatus < 2
        """, (project_name, phase_name), as_dict=True)[0].end_date

    frappe.db.set_value("Project Phase", phase_name, {
        "actual_start_date": start_date,
        "actual_end_date": end_date
    }, update_modified=False)


def update_all_phases_for_project(project_name):
    """
    Aggiorna tutte le fasi di un progetto
    """
    phases = frappe.db.get_all("Project Phase",
        filters={"parent": project_name, "parenttype": "Project"},
        pluck="name"
    )

    for phase_name in phases:
        update_phase_actuals(phase_name)
