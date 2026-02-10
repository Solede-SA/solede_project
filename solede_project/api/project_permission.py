# Copyright (c) 2024, Solede SA and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def sync_project_user_permission(doc, method=None):
    """
    Hook: on_update, after_insert
    Crea/aggiorna User Permission per il Project Manager.
    Il PM potrà vedere solo i progetti di cui è responsabile.
    """
    if not doc.project_manager:
        return

    # Verifica se l'utente ha il ruolo Projects Manager (non Supervisor)
    user_roles = frappe.get_roles(doc.project_manager)

    # Se l'utente è Supervisor, non serve User Permission (vede tutto)
    if "Projects Supervisor" in user_roles:
        return

    # Se non ha il ruolo Projects Manager, non fare nulla
    if "Projects Manager" not in user_roles:
        return

    # Verifica se esiste già una User Permission per questo progetto e utente
    existing = frappe.db.exists("User Permission", {
        "user": doc.project_manager,
        "allow": "Project",
        "for_value": doc.name
    })

    if not existing:
        # Crea nuova User Permission
        frappe.get_doc({
            "doctype": "User Permission",
            "user": doc.project_manager,
            "allow": "Project",
            "for_value": doc.name,
            "apply_to_all_doctypes": 1,
            "is_default": 0
        }).insert(ignore_permissions=True)

        frappe.msgprint(
            _("User Permission created for Project Manager {0}").format(doc.project_manager),
            indicator="green",
            alert=True
        )


def cleanup_old_project_manager_permission(doc, method=None):
    """
    Hook: validate
    Rimuove User Permission del vecchio Project Manager se cambiato.
    """
    if not doc.name or doc.is_new():
        return

    # Recupera il vecchio project_manager
    old_pm = frappe.db.get_value("Project", doc.name, "project_manager")

    if old_pm and old_pm != doc.project_manager:
        # Rimuovi la vecchia User Permission
        old_permission = frappe.db.get_value("User Permission", {
            "user": old_pm,
            "allow": "Project",
            "for_value": doc.name
        })

        if old_permission:
            frappe.delete_doc("User Permission", old_permission, ignore_permissions=True)
            frappe.msgprint(
                _("User Permission removed for previous Project Manager {0}").format(old_pm),
                indicator="orange",
                alert=True
            )


def get_permission_query_conditions(user):
    """
    Filtra i progetti visibili in base al ruolo dell'utente.
    - Projects Supervisor: vede tutti i progetti
    - Projects Manager: vede solo i progetti dove è project_manager
    - Projects User: non vede progetti (accede solo ai task assegnati)
    """
    if not user:
        user = frappe.session.user

    # Administrator e System Manager vedono tutto
    if user == "Administrator":
        return ""

    user_roles = frappe.get_roles(user)

    # Projects Supervisor vede tutto
    if "Projects Supervisor" in user_roles:
        return ""

    # Projects Manager vede solo i suoi progetti
    if "Projects Manager" in user_roles:
        return f"(`tabProject`.project_manager = {frappe.db.escape(user)})"

    # Projects User vede solo progetti dove ha task assegnati
    if "Projects User" in user_roles:
        return f"""
            `tabProject`.name IN (
                SELECT DISTINCT project FROM `tabTask`
                WHERE _assign LIKE {frappe.db.escape('%' + user + '%')}
                AND project IS NOT NULL
            )
        """

    # Altri utenti: usa il sistema standard di User Permission
    return ""


def has_permission(doc, ptype, user):
    """
    Verifica se l'utente ha permesso su un specifico progetto.
    """
    if not user:
        user = frappe.session.user

    # Administrator può tutto
    if user == "Administrator":
        return True

    user_roles = frappe.get_roles(user)

    # Projects Supervisor può tutto
    if "Projects Supervisor" in user_roles:
        return True

    # Projects Manager può accedere solo ai propri progetti
    if "Projects Manager" in user_roles:
        if doc.project_manager == user:
            return True
        return False

    # Projects User: lascia gestire al sistema standard con query conditions
    if "Projects User" in user_roles:
        return None

    # Per altri utenti, usa il sistema standard
    return None


# --- Task Permission ---

def get_task_permission_query_conditions(user):
    """
    Filtra i Task visibili in base al ruolo dell'utente.
    - Projects Supervisor: vede tutti i task
    - Projects Manager: vede task dei propri progetti
    - Projects User: vede solo task assegnati a lui
    """
    if not user:
        user = frappe.session.user

    if user == "Administrator":
        return ""

    user_roles = frappe.get_roles(user)

    # Projects Supervisor vede tutti i task
    if "Projects Supervisor" in user_roles:
        return ""

    # Projects Manager vede solo task dei propri progetti
    if "Projects Manager" in user_roles:
        return f"""
            (`tabTask`.project IS NULL OR `tabTask`.project IN (
                SELECT name FROM `tabProject` WHERE project_manager = {frappe.db.escape(user)}
            ))
        """

    # Projects User vede solo task assegnati a lui
    if "Projects User" in user_roles:
        return f"(`tabTask`._assign LIKE {frappe.db.escape('%' + user + '%')})"

    return ""


def has_task_permission(doc, ptype, user):
    """
    Verifica se l'utente ha permesso su un specifico task.
    """
    if not user:
        user = frappe.session.user

    if user == "Administrator":
        return True

    user_roles = frappe.get_roles(user)

    # Projects Supervisor può tutto
    if "Projects Supervisor" in user_roles:
        return True

    # Projects Manager può accedere solo ai task dei propri progetti
    if "Projects Manager" in user_roles:
        if not doc.project:
            return True  # Task senza progetto

        project_manager = frappe.db.get_value("Project", doc.project, "project_manager")
        if project_manager == user:
            return True
        return False

    # Projects User: lascia gestire al sistema standard con query conditions
    if "Projects User" in user_roles:
        return None

    return None


# --- Timesheet Permission ---

def get_timesheet_permission_query_conditions(user):
    """
    Filtra i Timesheet visibili in base al ruolo dell'utente.
    - Projects Supervisor: vede tutti i timesheet
    - Projects Manager: vede timesheet dei propri progetti
    - Projects User: vede solo i propri timesheet
    """
    if not user:
        user = frappe.session.user

    if user == "Administrator":
        return ""

    user_roles = frappe.get_roles(user)

    # Projects Supervisor vede tutti i timesheet
    if "Projects Supervisor" in user_roles:
        return ""

    # Projects Manager vede solo timesheet dei propri progetti
    if "Projects Manager" in user_roles:
        return f"""
            (`tabTimesheet`.parent_project IS NULL OR `tabTimesheet`.parent_project IN (
                SELECT name FROM `tabProject` WHERE project_manager = {frappe.db.escape(user)}
            ))
        """

    # Projects User vede solo i propri timesheet
    if "Projects User" in user_roles:
        return f"(`tabTimesheet`.owner = {frappe.db.escape(user)})"

    return ""


def has_timesheet_permission(doc, ptype, user):
    """
    Verifica se l'utente ha permesso su un specifico timesheet.
    """
    if not user:
        user = frappe.session.user

    if user == "Administrator":
        return True

    user_roles = frappe.get_roles(user)

    # Projects Supervisor può tutto
    if "Projects Supervisor" in user_roles:
        return True

    # Projects Manager può accedere solo ai timesheet dei propri progetti
    if "Projects Manager" in user_roles:
        if not doc.parent_project:
            return True  # Timesheet senza progetto

        project_manager = frappe.db.get_value("Project", doc.parent_project, "project_manager")
        if project_manager == user:
            return True
        return False

    # Projects User: lascia gestire al sistema standard con query conditions
    if "Projects User" in user_roles:
        return None

    return None


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_project_manager_users(doctype, txt, searchfield, start, page_len, filters):
    """
    API: Restituisce utenti con ruolo Projects Manager o Projects Supervisor.
    Usato come filtro per il campo project_manager nel form Project.
    """
    return frappe.db.sql("""
        SELECT DISTINCT u.name, u.full_name
        FROM `tabUser` u
        INNER JOIN `tabHas Role` hr ON hr.parent = u.name
        WHERE hr.role IN ('Projects Manager', 'Projects Supervisor')
            AND u.enabled = 1
            AND u.name NOT IN ('Guest', 'Administrator')
            AND (u.name LIKE %(txt)s OR u.full_name LIKE %(txt)s)
        ORDER BY u.full_name
        LIMIT %(start)s, %(page_len)s
    """, {
        'txt': f'%{txt}%',
        'start': start,
        'page_len': page_len
    })


@frappe.whitelist()
def get_project_manager_projects(user=None):
    """
    API: Restituisce la lista dei progetti gestiti dall'utente.
    """
    if not user:
        user = frappe.session.user

    return frappe.get_all(
        "Project",
        filters={"project_manager": user},
        fields=["name", "project_name", "status", "customer", "percent_complete"]
    )


@frappe.whitelist()
def assign_project_manager(project, user):
    """
    API: Assegna un Project Manager a un progetto.
    Solo Projects Supervisor può usare questa API.
    """
    if not frappe.has_permission("Project", "write"):
        frappe.throw(_("You don't have permission to modify this project"))

    user_roles = frappe.get_roles()
    if "Projects Supervisor" not in user_roles and "System Manager" not in user_roles:
        frappe.throw(_("Only Projects Supervisor can assign Project Managers"))

    # Verifica che l'utente target abbia il ruolo Projects Manager
    target_roles = frappe.get_roles(user)
    if "Projects Manager" not in target_roles and "Projects Supervisor" not in target_roles:
        frappe.throw(_("User {0} doesn't have the Projects Manager role").format(user))

    doc = frappe.get_doc("Project", project)
    doc.project_manager = user
    doc.save()

    return {"success": True, "message": _("Project Manager assigned successfully")}
