// Copyright (c) 2026, Solede SA and contributors
// Client Script for Supplier Quotation - Project Phase Filter

frappe.ui.form.on('Supplier Quotation', {
    setup: function(frm) {
        // Filtro per project_phase negli items: mostra solo fasi del progetto selezionato
        frm.set_query('project_phase', 'items', function(doc, cdt, cdn) {
            let row = locals[cdt][cdn];
            if (!row.project) {
                return { filters: { name: '' } };
            }
            return {
                query: 'solede_project.api.project_phase_api.get_project_phases',
                filters: {
                    parent: row.project
                }
            };
        });
    }
});

frappe.ui.form.on('Supplier Quotation Item', {
    project: function(frm, cdt, cdn) {
        // Resetta project_phase quando cambia il progetto
        frappe.model.set_value(cdt, cdn, 'project_phase', '');
    }
});
