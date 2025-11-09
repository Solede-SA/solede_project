# Copyright (c) 2024, Solede SA and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def calculate_service_totals(doc, method=None):
    """
    Hook: validate
    Calcola totali ore/giorni da Quotation Items e sincronizza nomi service groups
    """
    # Prima sincronizza i nomi e i riferimenti dei service groups negli items
    sync_service_group_references(doc)
    sync_service_group_names(doc)

    if not doc.get("items"):
        return

    total_hours = 0
    total_days = 0

    for item in doc.items:
        if item.uom == "Hour":
            total_hours += item.qty or 0
        elif item.uom == "Day":
            total_days += item.qty or 0

    doc.total_hours = total_hours
    doc.total_days = total_days

    # Calcola anche i totali dei service groups
    update_service_groups(doc, method)


def sync_service_group_references(doc):
    """
    Sincronizza i riferimenti service_group negli items quando i row names cambiano.
    Questo succede quando un documento viene salvato e i nomi temporanei tipo
    'new-quotation-service-group-xxx' vengono sostituiti con nomi definitivi.
    """
    if not doc.get("service_groups") or not doc.get("items"):
        return

    # Crea una mappa: service_group_name -> row name
    name_to_row = {}
    for group in doc.service_groups:
        name_to_row[group.group_name] = group.name

    # Aggiorna i riferimenti negli items usando service_group_name come chiave
    for item in doc.items:
        if item.service_group_name and item.service_group_name in name_to_row:
            # Aggiorna il riferimento se il row name è cambiato
            item.service_group = name_to_row[item.service_group_name]


def sync_service_group_names(doc):
    """
    Sincronizza i nomi dei service groups negli items.
    Gestisce anche il caso in cui i row names cambiano dopo il salvataggio.
    """
    if not doc.get("service_groups") or not doc.get("items"):
        return

    # Crea una mappa: vecchio_name -> nuovo_name e group_name
    group_map = {}
    for group in doc.service_groups:
        group_map[group.name] = {
            "name": group.name,
            "group_name": group.group_name
        }

    # Aggiorna gli items con i nomi corretti
    for item in doc.items:
        # Cerca il gruppo corrispondente
        if item.service_group:
            # Prima prova con match diretto
            if item.service_group in group_map:
                item.service_group_name = group_map[item.service_group]["group_name"]
            else:
                # Se non trova match diretto, cerca per group_name
                # (questo gestisce il caso di items aggiunti manualmente)
                for group in doc.service_groups:
                    if item.service_group_name == group.group_name:
                        item.service_group = group.name
                        break


def update_service_groups(doc, method=None):
    """
    Hook: on_update
    Aggiorna totali Service Groups
    """
    if not doc.get("service_groups"):
        return

    for group in doc.service_groups:
        # Calcola totali items del gruppo
        group_hours = 0
        group_days = 0
        group_total = 0

        for item in doc.items:
            # Controlla se l'item è collegato a questo gruppo (tramite link al row name)
            if item.service_group == group.name:
                group_total += item.amount or 0
                if item.uom == "Hour":
                    group_hours += item.qty or 0
                elif item.uom == "Day":
                    group_days += item.qty or 0

        # Applica sconto gruppo se presente
        discount_pct = frappe.utils.flt(group.discount_percentage)
        if discount_pct:
            group_total = group_total * (1 - discount_pct / 100)

        group.total_amount = group_total
        group.total_hours = group_hours
        group.total_days = group_days
