# Copyright (c) 2024, Solede SA and contributors
# Script per creare Service Template di esempio

import frappe


def create_sample_template():
    """Crea un Service Template di esempio: Implementazione ERPNext Completa"""

    # Verifica se esiste già
    if frappe.db.exists("Service Template", "Implementazione ERPNext Completa"):
        print("Service Template 'Implementazione ERPNext Completa' già esistente")
        return

    template = frappe.new_doc("Service Template")
    template.template_name = "Implementazione ERPNext Completa"
    template.description = "<p>Template completo per implementazione ERPNext con analisi, configurazione, sviluppo custom e training</p>"
    template.is_active = 1

    # Service Groups
    template.append("service_groups", {
        "group_name": "Fase 1 - Analisi",
        "description": "<p>Analisi processi aziendali e mappatura requisiti con ERPNext</p>",
        "sequence": 1
    })

    template.append("service_groups", {
        "group_name": "Fase 2 - Implementazione",
        "description": "<p>Configurazione sistema e sviluppo personalizzazioni</p>",
        "sequence": 2
    })

    template.append("service_groups", {
        "group_name": "Fase 3 - Go Live e Training",
        "description": "<p>Training utenti e supporto post go-live</p>",
        "sequence": 3
    })

    # Items - Fase 1
    template.append("items", {
        "service_group": "Fase 1 - Analisi",
        "item_code": "ANALISI-PROCESSI",
        "qty": 5,
        "uom": "Day",
        "rate": 1200.00,
        "description": "Analisi approfondita dei processi aziendali attuali"
    })

    template.append("items", {
        "service_group": "Fase 1 - Analisi",
        "item_code": "MAPPATURA-ERPNEXT",
        "qty": 3,
        "uom": "Day",
        "rate": 1200.00,
        "description": "Mappatura requisiti e configurazione ERPNext"
    })

    # Items - Fase 2
    template.append("items", {
        "service_group": "Fase 2 - Implementazione",
        "item_code": "CONFIG-ERPNEXT",
        "qty": 80,
        "uom": "Hour",
        "rate": 150.00,
        "description": "Configurazione sistema ERPNext"
    })

    template.append("items", {
        "service_group": "Fase 2 - Implementazione",
        "item_code": "DEV-CUSTOM",
        "qty": 120,
        "uom": "Hour",
        "rate": 120.00,
        "description": "Sviluppo personalizzazioni custom"
    })

    template.append("items", {
        "service_group": "Fase 2 - Implementazione",
        "item_code": "MIGRATION-DATI",
        "qty": 5,
        "uom": "Day",
        "rate": 1200.00,
        "description": "Migrazione dati da sistema precedente"
    })

    # Items - Fase 3
    template.append("items", {
        "service_group": "Fase 3 - Go Live e Training",
        "item_code": "TRAINING-UTENTI",
        "qty": 40,
        "uom": "Hour",
        "rate": 150.00,
        "description": "Training utenti finali"
    })

    template.append("items", {
        "service_group": "Fase 3 - Go Live e Training",
        "item_code": "SUPPORTO-GOLIVE",
        "qty": 10,
        "uom": "Day",
        "rate": 1200.00,
        "description": "Supporto post go-live"
    })

    template.insert(ignore_permissions=True)
    frappe.db.commit()

    print(f"✅ Service Template '{template.template_name}' creato con successo!")
    print(f"   - 3 Service Groups")
    print(f"   - 8 Items totali")
    print(f"   - Totale ore: 240")
    print(f"   - Totale giorni: 23")


def execute():
    """Esegue creazione template di esempio"""
    print("\n=== Creazione Service Template di Esempio ===\n")
    create_sample_template()
    print("\n")


if __name__ == "__main__":
    execute()
