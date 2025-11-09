// Copyright (c) 2024, Solede SA and contributors
// Client Script for Quotation

frappe.ui.form.on('Quotation', {
    refresh: function(frm) {
        // Disabilita il campo service_template se il documento è submitted
        if (frm.doc.docstatus === 1) {
            frm.set_df_property('service_template', 'read_only', 1);
        }

        // Button: Create Project (solo se Quotation è submitted e non ha già un progetto)
        if (frm.doc.docstatus === 1) {
            // Verifica se esiste già un progetto
            frappe.db.get_value('Project', {'quotation': frm.doc.name}, 'name', (r) => {
                if (!r || !r.name) {
                    frm.add_custom_button(__('Create Project'), () => {
                        frappe.call({
                            method: 'solede_project.api.quotation_api.create_project_from_quotation',
                            args: {
                                quotation_name: frm.doc.name
                            },
                            freeze: true,
                            freeze_message: __('Creating Project...'),
                            callback: function(r) {
                                if (r.message && r.message.success) {
                                    frappe.msgprint({
                                        title: __('Success'),
                                        message: r.message.message,
                                        indicator: 'green'
                                    });
                                    // Ricarica il form per mostrare lo status aggiornato
                                    frm.reload_doc();
                                    // Naviga al progetto creato
                                    setTimeout(() => {
                                        frappe.set_route('Form', 'Project', r.message.project);
                                    }, 1000);
                                }
                            }
                        });
                    }, __('Actions'));
                }
            });
        }
    },

    service_template: function(frm) {
        // Non caricare il template se il documento è submitted
        if (frm.doc.docstatus === 1) {
            frappe.msgprint(__('Cannot load template on submitted document'));
            frm.set_value('service_template', '');
            return;
        }

        // Quando viene selezionato un template, caricalo automaticamente
        if (frm.doc.service_template) {
            load_template_into_form(frm);
        }
    },

    load_template: function(frm) {
        // Non caricare il template se il documento è submitted
        if (frm.doc.docstatus === 1) {
            frappe.msgprint(__('Cannot load template on submitted document'));
            return;
        }

        // Bottone per ricaricare il template
        if (!frm.doc.service_template) {
            frappe.msgprint(__('Please select a Service Template first'));
            return;
        }
        load_template_into_form(frm);
    },

    // Calcola totali quando items cambiano
    items_on_form_rendered: function(frm) {
        calculate_quotation_totals(frm);
    }
});

// Quando cambiano i service groups, sincronizza i nomi negli items e ricalcola totali
frappe.ui.form.on('Quotation Service Group', {
    group_name: function(frm, cdt, cdn) {
        let group_row = locals[cdt][cdn];
        // Aggiorna il service_group_name in tutti gli items collegati a questo gruppo
        if (frm.doc.items) {
            frm.doc.items.forEach(item => {
                if (item.service_group === group_row.name) {
                    frappe.model.set_value(item.doctype, item.name, 'service_group_name', group_row.group_name);
                }
            });
        }
        frm.refresh_field('items');
        calculate_service_group_totals(frm);
    },
    discount_percentage: function(frm, cdt, cdn) {
        calculate_service_group_totals(frm);
    }
});

// Quando cambiano gli items, ricalcola i totali
frappe.ui.form.on('Quotation Item', {
    items_add: function(frm) {
        calculate_quotation_totals(frm);
    },
    items_remove: function(frm) {
        calculate_quotation_totals(frm);
    },
    qty: function(frm) {
        calculate_quotation_totals(frm);
    },
    rate: function(frm) {
        calculate_quotation_totals(frm);
    },
    amount: function(frm) {
        calculate_service_group_totals(frm);
    },
    uom: function(frm) {
        calculate_quotation_totals(frm);
    },
    service_group: function(frm) {
        calculate_service_group_totals(frm);
    }
});

function calculate_quotation_totals(frm) {
    let total_hours = 0;
    let total_days = 0;

    if (frm.doc.items) {
        frm.doc.items.forEach(item => {
            if (item.uom === 'Hour') {
                total_hours += item.qty || 0;
            } else if (item.uom === 'Day') {
                total_days += item.qty || 0;
            }
        });
    }

    frm.set_value('total_hours', total_hours);
    frm.set_value('total_days', total_days);

    // Ricalcola anche i totali dei service groups
    calculate_service_group_totals(frm);
}

function calculate_service_group_totals(frm) {
    console.log('calculate_service_group_totals called');

    if (!frm.doc.service_groups || !frm.doc.items) {
        console.log('No service_groups or items found');
        return;
    }

    console.log('Service groups:', frm.doc.service_groups.length);
    console.log('Items:', frm.doc.items.length);

    frm.doc.service_groups.forEach(group => {
        let group_hours = 0;
        let group_days = 0;
        let group_total = 0;

        console.log('Processing group:', group.group_name, 'row name:', group.name);

        frm.doc.items.forEach(item => {
            console.log('Item service_group:', item.service_group, 'group.name:', group.name, 'match:', item.service_group === group.name);

            if (item.service_group === group.name) {
                console.log('Match found! Item:', item.item_name, 'amount:', item.amount, 'qty:', item.qty, 'uom:', item.uom);
                group_total += item.amount || 0;
                if (item.uom === 'Hour') {
                    group_hours += item.qty || 0;
                } else if (item.uom === 'Day') {
                    group_days += item.qty || 0;
                }
            }
        });

        console.log('Group totals - hours:', group_hours, 'days:', group_days, 'amount:', group_total);

        // Applica sconto gruppo se presente
        let discount_pct = parseFloat(group.discount_percentage) || 0;
        if (discount_pct) {
            group_total = group_total * (1 - discount_pct / 100);
        }

        // Aggiorna i campi del gruppo direttamente
        console.log('Before update - group totals:', group.total_hours, group.total_days, group.total_amount);
        group.total_hours = group_hours;
        group.total_days = group_days;
        group.total_amount = group_total;
        console.log('After update - group totals:', group.total_hours, group.total_days, group.total_amount);
        console.log('Updated group:', group.group_name, 'with totals:', group.total_hours, group.total_days, group.total_amount);
    });

    frm.refresh_field('service_groups');
}

async function load_template_into_form(frm) {
    if (!frm.doc.service_template) {
        return;
    }

    frappe.dom.freeze(__('Loading Template...'));

    try {
        // Recupera il template
        const template_response = await frappe.call({
            method: 'frappe.client.get',
            args: {
                doctype: 'Service Template',
                name: frm.doc.service_template
            }
        });

        if (!template_response.message) {
            frappe.dom.unfreeze();
            return;
        }

        let template = template_response.message;

        // Pulisci service groups e items esistenti
        frm.clear_table('service_groups');
        frm.clear_table('items');

        // Carica i Service Groups dal template
        if (template.service_groups) {
            for (const template_group of template.service_groups) {
                // Recupera il Service Group master
                const sg_response = await frappe.call({
                    method: 'frappe.client.get',
                    args: {
                        doctype: 'Service Group',
                        name: template_group.service_group
                    }
                });

                if (sg_response.message) {
                    let service_group = sg_response.message;

                    // Aggiungi Service Group alla quotation
                    let group_row = frm.add_child('service_groups');
                    group_row.group_name = service_group.group_name;
                    group_row.description = template_group.description || service_group.description;
                    group_row.sequence = template_group.sequence;

                    // Refresh per assegnare il nome alla riga
                    frm.refresh_field('service_groups');

                    // Aggiungi gli Items del Service Group
                    if (service_group.items) {
                        for (const group_item of service_group.items) {
                            // Aggiungi la riga item
                            let item_row = frm.add_child('items');

                            // Imposta i campi base prima di item_code
                            item_row.qty = group_item.qty;
                            item_row.uom = group_item.uom;
                            item_row.service_group = group_row.name;
                            item_row.service_group_name = service_group.group_name;

                            // Usa set_value per item_code per triggerare il calcolo automatico dei prezzi
                            await frappe.model.set_value(item_row.doctype, item_row.name, 'item_code', group_item.item_code);

                            // Sovrascrivi description se specificata nel gruppo
                            if (group_item.description) {
                                await frappe.model.set_value(item_row.doctype, item_row.name, 'description', group_item.description);
                            }
                        }
                    }
                }
            }
        }

        // Refresh delle tabelle
        frm.refresh_field('service_groups');
        frm.refresh_field('items');

        // Calcola i totali dopo aver caricato tutti gli items
        calculate_quotation_totals(frm);

        frappe.show_alert({
            message: __('Template loaded successfully'),
            indicator: 'green'
        }, 5);

    } catch (error) {
        frappe.msgprint({
            title: __('Error'),
            message: __('Failed to load template: ') + error.message,
            indicator: 'red'
        });
    } finally {
        frappe.dom.unfreeze();
    }
}
