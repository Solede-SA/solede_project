# Copyright (c) 2024, Solede SA and contributors
# For license information, please see license.txt

import frappe
from frappe import _


@frappe.whitelist()
def load_service_template(quotation_name, template_name):
    """
    API Method
    Carica Service Template in Quotation
    """
    quotation = frappe.get_doc("Quotation", quotation_name)
    template = frappe.get_doc("Service Template", template_name)

    # Valida permessi
    quotation.check_permission("write")

    # Pulisci service groups esistenti
    quotation.service_groups = []

    # Carica Service Groups dal template
    for template_group in template.service_groups:
        # Recupera il Service Group master
        service_group = frappe.get_doc("Service Group", template_group.service_group)

        # Aggiungi Service Group alla quotation
        group_row = quotation.append("service_groups", {
            "group_name": service_group.group_name,
            "description": template_group.description or service_group.description,
            "sequence": template_group.sequence
        })

        # Carica Items dal Service Group
        for group_item in service_group.items:
            quotation.append("items", {
                "item_code": group_item.item_code,
                "qty": group_item.qty,
                "uom": group_item.uom,
                "service_group": group_row.name,
                "description": group_item.description
            })

    quotation.save()

    return {
        "success": True,
        "message": _("Template loaded successfully")
    }


@frappe.whitelist()
def create_project_from_quotation(quotation_name):
    """
    API Method
    Crea Project da Quotation con Tasks
    """
    quotation = frappe.get_doc("Quotation", quotation_name)

    # Validazioni
    if quotation.docstatus != 1:
        frappe.throw(_("Quotation must be submitted"))

    # Se la quotation non è ancora Accepted, cambia lo status
    if quotation.status not in ["Accepted", "Ordered"]:
        quotation.db_set("status", "Accepted", update_modified=False)

    # Verifica se esiste già un progetto
    existing_project = frappe.db.exists("Project", {"quotation": quotation.name})
    if existing_project:
        frappe.throw(_("A project already exists for this quotation: {0}").format(existing_project))

    # Crea Project
    project = frappe.new_doc("Project")
    project.project_name = f"{quotation.party_name} - {quotation.name}"
    project.customer = quotation.party_name
    project.quotation = quotation.name
    project.expected_start_date = quotation.transaction_date

    # Imposta il Project Manager (utente corrente che crea il progetto)
    project.project_manager = frappe.session.user

    # Imposta billing mode
    if quotation.billing_type == "Forfait":
        project.billing_mode = "Forfait Progressivo"
    else:
        project.billing_mode = "Time-based"

    project.total_quoted_amount = quotation.grand_total
    project.expected_total_hours = quotation.total_hours or 0
    project.price_list = quotation.selling_price_list

    project.insert()

    # Crea Tasks da Service Groups usando la gerarchia nativa parent_task
    if quotation.service_groups:
        for group in quotation.service_groups:
            # Crea Parent Task per il gruppo
            parent_task = frappe.new_doc("Task")
            parent_task.subject = group.group_name
            parent_task.description = group.description
            parent_task.project = project.name
            parent_task.is_group = 1
            parent_task.insert()

            # Crea Child Tasks da Items del gruppo
            group_items = [item for item in quotation.items if item.service_group == group.name]
            for item in group_items:
                child_task = frappe.new_doc("Task")
                child_task.subject = item.item_name
                child_task.description = item.description
                child_task.project = project.name
                child_task.parent_task = parent_task.name
                child_task.quotation_item = item.name
                child_task.activity_type = item.activity_type

                # Converti giorni in ore (1 giorno = 8 ore)
                if item.uom == "Day":
                    child_task.expected_hours = (item.qty or 0) * 8
                else:
                    child_task.expected_hours = item.qty or 0

                child_task.insert()
    else:
        # Se non ci sono service groups, crea tasks direttamente dagli items
        for item in quotation.items:
            task = frappe.new_doc("Task")
            task.subject = item.item_name
            task.description = item.description
            task.project = project.name
            task.quotation_item = item.name
            task.activity_type = item.activity_type

            # Converti giorni in ore (1 giorno = 8 ore)
            if item.uom == "Day":
                task.expected_hours = (item.qty or 0) * 8
            else:
                task.expected_hours = item.qty or 0

            task.insert()

    frappe.db.commit()

    return {
        "success": True,
        "project": project.name,
        "message": _("Project {0} created successfully").format(project.name)
    }
