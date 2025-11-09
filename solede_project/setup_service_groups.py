# Copyright (c) 2024, Solede SA and contributors
# Script per creare Service Groups e Template

import frappe


def create_service_groups():
    """Crea Service Groups riutilizzabili"""

    groups_data = [
        {
            "group_name": "Analisi e Requisiti",
            "description": "<p>Analisi processi aziendali e mappatura requisiti con ERPNext</p>",
            "items": [
                {
                    "item_code": "ANALISI-PROCESSI",
                    "qty": 5,
                    "uom": "Day",
                    "description": "Analisi approfondita dei processi aziendali attuali"
                },
                {
                    "item_code": "MAPPATURA-ERPNEXT",
                    "qty": 3,
                    "uom": "Day",
                    "description": "Mappatura requisiti e configurazione ERPNext"
                }
            ]
        },
        {
            "group_name": "Implementazione e Sviluppo",
            "description": "<p>Configurazione sistema ERPNext e sviluppo personalizzazioni</p>",
            "items": [
                {
                    "item_code": "CONFIG-ERPNEXT",
                    "qty": 80,
                    "uom": "Hour",
                    "description": "Configurazione sistema ERPNext"
                },
                {
                    "item_code": "DEV-CUSTOM",
                    "qty": 120,
                    "uom": "Hour",
                    "description": "Sviluppo personalizzazioni custom"
                },
                {
                    "item_code": "MIGRATION-DATI",
                    "qty": 5,
                    "uom": "Day",
                    "description": "Migrazione dati da sistema precedente"
                }
            ]
        },
        {
            "group_name": "Training e Go Live",
            "description": "<p>Formazione utenti e supporto post go-live</p>",
            "items": [
                {
                    "item_code": "TRAINING-UTENTI",
                    "qty": 40,
                    "uom": "Hour",
                    "description": "Training utenti finali"
                },
                {
                    "item_code": "SUPPORTO-GOLIVE",
                    "qty": 10,
                    "uom": "Day",
                    "description": "Supporto post go-live"
                }
            ]
        }
    ]

    for group_data in groups_data:
        if not frappe.db.exists("Service Group", group_data["group_name"]):
            group = frappe.new_doc("Service Group")
            group.group_name = group_data["group_name"]
            group.description = group_data["description"]
            group.is_active = 1

            for item_data in group_data["items"]:
                group.append("items", item_data)

            group.insert(ignore_permissions=True)
            print(f"✓ Service Group '{group_data['group_name']}' creato con {len(group_data['items'])} items")
        else:
            print(f"  Service Group '{group_data['group_name']}' già esistente")


def create_service_template():
    """Crea Service Template usando i Service Groups"""

    # Elimina template esistente se presente
    if frappe.db.exists("Service Template", "Implementazione ERPNext Completa"):
        frappe.delete_doc("Service Template", "Implementazione ERPNext Completa", force=1)
        print("  Template esistente eliminato")

    template = frappe.new_doc("Service Template")
    template.template_name = "Implementazione ERPNext Completa"
    template.description = "<p>Template completo per implementazione ERPNext con analisi, configurazione, sviluppo custom e training</p>"
    template.is_active = 1

    # Aggiungi Service Groups al template
    template.append("service_groups", {
        "service_group": "Analisi e Requisiti",
        "sequence": 1,
        "description": "<p>Analisi processi aziendali e mappatura requisiti con ERPNext</p>"
    })

    template.append("service_groups", {
        "service_group": "Implementazione e Sviluppo",
        "sequence": 2,
        "description": "<p>Configurazione sistema e sviluppo personalizzazioni</p>"
    })

    template.append("service_groups", {
        "service_group": "Training e Go Live",
        "sequence": 3,
        "description": "<p>Training utenti e supporto post go-live</p>"
    })

    template.insert(ignore_permissions=True)
    print(f"✓ Service Template '{template.template_name}' creato con 3 Service Groups")


def execute():
    """Esegue setup completo"""
    print("\n=== Setup Service Groups e Template ===\n")

    print("1. Creazione Service Groups...")
    create_service_groups()

    print("\n2. Creazione Service Template...")
    create_service_template()

    frappe.db.commit()
    print("\n✅ Setup completato!\n")


if __name__ == "__main__":
    execute()
