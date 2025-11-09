# Copyright (c) 2024, Solede SA and contributors
# Script per creare dati di test

import frappe


def create_item_group():
    """Crea Item Group per i servizi Solede"""
    if not frappe.db.exists("Item Group", "Solede Services"):
        item_group = frappe.new_doc("Item Group")
        item_group.item_group_name = "Solede Services"
        item_group.parent_item_group = "All Item Groups"
        item_group.is_group = 0
        item_group.insert(ignore_permissions=True)
        print("✓ Item Group 'Solede Services' creato")


def create_items():
    """Crea Items standard per servizi Solede"""
    items = [
        {
            "item_code": "CONS-ERPNEXT",
            "item_name": "Consulenza ERPNext",
            "stock_uom": "Hour",
        },
        {
            "item_code": "ANALISI-PROCESSI",
            "item_name": "Analisi Processi Aziendali",
            "stock_uom": "Day",
        },
        {
            "item_code": "MAPPATURA-ERPNEXT",
            "item_name": "Mappatura Processi con ERPNext",
            "stock_uom": "Day",
        },
        {
            "item_code": "CONFIG-ERPNEXT",
            "item_name": "Configurazione Sistema ERPNext",
            "stock_uom": "Hour",
        },
        {
            "item_code": "DEV-CUSTOM",
            "item_name": "Sviluppo App Custom",
            "stock_uom": "Hour",
        },
        {
            "item_code": "TRAINING-UTENTI",
            "item_name": "Training Utenti",
            "stock_uom": "Hour",
        },
        {
            "item_code": "SUPPORTO-GOLIVE",
            "item_name": "Supporto Post Go-Live",
            "stock_uom": "Day",
        },
        {
            "item_code": "MIGRATION-DATI",
            "item_name": "Migration Dati",
            "stock_uom": "Day",
        },
        {
            "item_code": "TIMESHEET-HOURS",
            "item_name": "Timesheet Hours",
            "stock_uom": "Hour",
        },
        {
            "item_code": "MILESTONE-PAYMENT",
            "item_name": "Milestone Payment",
            "stock_uom": "Nos",
        },
    ]

    for item_data in items:
        if not frappe.db.exists("Item", item_data["item_code"]):
            item = frappe.new_doc("Item")
            item.item_code = item_data["item_code"]
            item.item_name = item_data["item_name"]
            item.item_group = "Solede Services"
            item.stock_uom = item_data["stock_uom"]
            item.is_stock_item = 0
            item.is_sales_item = 1
            item.insert(ignore_permissions=True)
            print(f"✓ Item '{item_data['item_code']}' creato")
        else:
            print(f"  Item '{item_data['item_code']}' già esistente")


def create_price_lists():
    """Crea Price Lists per servizi Solede"""
    price_lists = [
        {
            "name": "Consulenza Senior",
            "currency": "CHF",
        },
        {
            "name": "Consulenza Junior",
            "currency": "CHF",
        },
        {
            "name": "Sviluppo Custom",
            "currency": "CHF",
        },
        {
            "name": "Training Standard",
            "currency": "CHF",
        },
    ]

    for pl_data in price_lists:
        if not frappe.db.exists("Price List", pl_data["name"]):
            price_list = frappe.new_doc("Price List")
            price_list.price_list_name = pl_data["name"]
            price_list.currency = pl_data["currency"]
            price_list.enabled = 1
            price_list.buying = 0
            price_list.selling = 1
            price_list.insert(ignore_permissions=True)
            print(f"✓ Price List '{pl_data['name']}' creata")
        else:
            print(f"  Price List '{pl_data['name']}' già esistente")


def create_item_prices():
    """Crea Item Prices di esempio"""
    item_prices = [
        # Consulenza Senior
        {"item_code": "CONS-ERPNEXT", "price_list": "Consulenza Senior", "rate": 150.00},
        {"item_code": "CONFIG-ERPNEXT", "price_list": "Consulenza Senior", "rate": 150.00},
        {"item_code": "TRAINING-UTENTI", "price_list": "Consulenza Senior", "rate": 150.00},
        {"item_code": "ANALISI-PROCESSI", "price_list": "Consulenza Senior", "rate": 1200.00},
        {"item_code": "MAPPATURA-ERPNEXT", "price_list": "Consulenza Senior", "rate": 1200.00},
        {"item_code": "SUPPORTO-GOLIVE", "price_list": "Consulenza Senior", "rate": 1200.00},
        {"item_code": "MIGRATION-DATI", "price_list": "Consulenza Senior", "rate": 1200.00},

        # Consulenza Junior
        {"item_code": "CONS-ERPNEXT", "price_list": "Consulenza Junior", "rate": 100.00},
        {"item_code": "CONFIG-ERPNEXT", "price_list": "Consulenza Junior", "rate": 100.00},
        {"item_code": "TRAINING-UTENTI", "price_list": "Consulenza Junior", "rate": 100.00},
        {"item_code": "ANALISI-PROCESSI", "price_list": "Consulenza Junior", "rate": 800.00},
        {"item_code": "MAPPATURA-ERPNEXT", "price_list": "Consulenza Junior", "rate": 800.00},
        {"item_code": "SUPPORTO-GOLIVE", "price_list": "Consulenza Junior", "rate": 800.00},
        {"item_code": "MIGRATION-DATI", "price_list": "Consulenza Junior", "rate": 800.00},

        # Sviluppo Custom
        {"item_code": "DEV-CUSTOM", "price_list": "Sviluppo Custom", "rate": 120.00},
        {"item_code": "CONFIG-ERPNEXT", "price_list": "Sviluppo Custom", "rate": 120.00},

        # Training Standard
        {"item_code": "TRAINING-UTENTI", "price_list": "Training Standard", "rate": 130.00},
    ]

    for ip_data in item_prices:
        # Verifica se esiste già
        existing = frappe.db.exists("Item Price", {
            "item_code": ip_data["item_code"],
            "price_list": ip_data["price_list"]
        })

        if not existing:
            item_price = frappe.new_doc("Item Price")
            item_price.item_code = ip_data["item_code"]
            item_price.price_list = ip_data["price_list"]
            item_price.price_list_rate = ip_data["rate"]
            item_price.insert(ignore_permissions=True)
            print(f"✓ Item Price '{ip_data['item_code']}' @ '{ip_data['price_list']}' creato")
        else:
            print(f"  Item Price '{ip_data['item_code']}' @ '{ip_data['price_list']}' già esistente")


def execute():
    """Esegue setup completo dati di test"""
    print("\n=== Setup Dati di Test Solede Project ===\n")

    print("1. Creazione Item Group...")
    create_item_group()

    print("\n2. Creazione Items...")
    create_items()

    print("\n3. Creazione Price Lists...")
    create_price_lists()

    print("\n4. Creazione Item Prices...")
    create_item_prices()

    frappe.db.commit()
    print("\n✅ Setup completato!\n")


if __name__ == "__main__":
    execute()
