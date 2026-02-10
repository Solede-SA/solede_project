# Copyright (c) 2024, Solede SA and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def after_install():
    """Setup after app installation."""
    create_projects_supervisor_role()
    setup_custom_docperms()


def after_migrate():
    """Setup after migration."""
    create_projects_supervisor_role()
    setup_custom_docperms()


def create_projects_supervisor_role():
    """Create the Projects Supervisor role if it doesn't exist."""
    if not frappe.db.exists("Role", "Projects Supervisor"):
        role = frappe.get_doc({
            "doctype": "Role",
            "role_name": "Projects Supervisor",
            "desk_access": 1,
            "is_custom": 1
        })
        role.insert(ignore_permissions=True)
        frappe.db.commit()
        print("Created role: Projects Supervisor")


def setup_custom_docperms():
    """Setup Custom DocPerms for Projects Supervisor and Projects Manager."""

    # DocPerm definitions
    docperms = [
        # Projects Supervisor - Full access
        {
            "parent": "Project",
            "role": "Projects Supervisor",
            "permlevel": 0,
            "read": 1, "write": 1, "create": 1, "delete": 1,
            "report": 1, "export": 1, "import": 1, "share": 1,
            "print": 1, "email": 1, "select": 1
        },
        {
            "parent": "Task",
            "role": "Projects Supervisor",
            "permlevel": 0,
            "read": 1, "write": 1, "create": 1, "delete": 1,
            "report": 1, "export": 1, "import": 1, "share": 1,
            "print": 1, "email": 1, "select": 1
        },
        {
            "parent": "Timesheet",
            "role": "Projects Supervisor",
            "permlevel": 0,
            "read": 1, "write": 1, "create": 1, "delete": 1,
            "submit": 1, "cancel": 1, "amend": 1,
            "report": 1, "export": 1, "import": 1, "share": 1,
            "print": 1, "email": 1, "select": 1
        },
        # Projects Manager - Limited access (filtered by permission_query_conditions)
        {
            "parent": "Project",
            "role": "Projects Manager",
            "permlevel": 0,
            "read": 1, "write": 1, "create": 1, "delete": 0,
            "report": 1, "export": 1, "share": 1,
            "print": 1, "email": 1, "select": 1
        },
        {
            "parent": "Task",
            "role": "Projects Manager",
            "permlevel": 0,
            "read": 1, "write": 1, "create": 1, "delete": 1,
            "report": 1, "export": 1, "share": 1,
            "print": 1, "email": 1, "select": 1
        },
        {
            "parent": "Timesheet",
            "role": "Projects Manager",
            "permlevel": 0,
            "read": 1, "write": 1, "create": 1, "delete": 0,
            "submit": 1, "cancel": 1,
            "report": 1, "export": 1, "share": 1,
            "print": 1, "email": 1, "select": 1
        },
        # Projects User - Read-only access to projects, work on assigned tasks
        {
            "parent": "Project",
            "role": "Projects User",
            "permlevel": 0,
            "read": 1, "write": 0, "create": 0, "delete": 0,
            "report": 1, "print": 1, "select": 1
        },
        {
            "parent": "Task",
            "role": "Projects User",
            "permlevel": 0,
            "read": 1, "write": 1, "create": 0, "delete": 0,
            "report": 1, "print": 1, "select": 1
        },
        {
            "parent": "Timesheet",
            "role": "Projects User",
            "permlevel": 0,
            "read": 1, "write": 1, "create": 1, "delete": 0,
            "submit": 1,
            "report": 1, "print": 1, "select": 1
        },
    ]

    for perm in docperms:
        # Check if permission already exists
        existing = frappe.db.exists("Custom DocPerm", {
            "parent": perm["parent"],
            "role": perm["role"],
            "permlevel": perm.get("permlevel", 0)
        })

        if not existing:
            doc = frappe.get_doc({
                "doctype": "Custom DocPerm",
                **perm
            })
            doc.insert(ignore_permissions=True)
            print(f"Created Custom DocPerm: {perm['role']} on {perm['parent']}")

    frappe.db.commit()


def sync_existing_project_permissions():
    """
    Utility function to create User Permissions for existing projects.
    Run this manually if needed: bench execute solede_project.setup.sync_existing_project_permissions
    """
    projects = frappe.get_all(
        "Project",
        filters={"project_manager": ["is", "set"]},
        fields=["name", "project_manager"]
    )

    for project in projects:
        user = project.project_manager
        user_roles = frappe.get_roles(user)

        # Skip if user is Supervisor (they see everything)
        if "Projects Supervisor" in user_roles:
            continue

        # Skip if user doesn't have Projects Manager role
        if "Projects Manager" not in user_roles:
            continue

        # Check if User Permission already exists
        existing = frappe.db.exists("User Permission", {
            "user": user,
            "allow": "Project",
            "for_value": project.name
        })

        if not existing:
            frappe.get_doc({
                "doctype": "User Permission",
                "user": user,
                "allow": "Project",
                "for_value": project.name,
                "apply_to_all_doctypes": 1
            }).insert(ignore_permissions=True)
            print(f"Created User Permission for {user} on {project.name}")

    frappe.db.commit()
    print("Sync completed.")
