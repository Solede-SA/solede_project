# Copyright (c) 2026, Solede SA and contributors
# For license information, please see license.txt

import frappe


def update_phase_totals_from_po(doc, method=None):
    """
    Hook: on_update, on_submit, on_cancel
    Aggiorna i totali delle fasi quando un Purchase Order viene salvato/sottomesso/cancellato
    """
    update_phase_totals_from_purchase_doc(doc, method)


def update_phase_totals_from_purchase_doc(doc, method=None):
    """
    Hook: on_update, on_submit, on_cancel
    Aggiorna i totali delle fasi quando un documento di acquisto (PO/PI) viene salvato/sottomesso/cancellato
    """
    # Raccoglie tutte le fasi uniche presenti negli item
    phases_to_update = set()

    for item in doc.items:
        if item.project_phase:
            phases_to_update.add(item.project_phase)

    if not phases_to_update:
        return

    from solede_project.api.project_phase_api import update_phase_actuals

    for phase_name in phases_to_update:
        update_phase_actuals(phase_name)
