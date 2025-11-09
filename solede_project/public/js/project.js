// Copyright (c) 2024, Solede SA and contributors
// Client Script for Project

frappe.ui.form.on('Project', {
    refresh: function(frm) {
        // Mostra i tasks raggruppati per Service Group
        if (frm.doc.name) {
            show_grouped_tasks(frm);
        }

        // Button: Create Invoice from Timesheet (solo per Time-based)
        if (frm.doc.billing_mode === 'Time-based') {
            frm.add_custom_button(__('Create Invoice from Timesheet'), () => {
                let d = new frappe.ui.Dialog({
                    title: __('Create Invoice from Timesheet'),
                    fields: [
                        {
                            fieldname: 'from_date',
                            fieldtype: 'Date',
                            label: __('From Date'),
                            reqd: 1,
                            default: frappe.datetime.month_start()
                        },
                        {
                            fieldname: 'to_date',
                            fieldtype: 'Date',
                            label: __('To Date'),
                            reqd: 1,
                            default: frappe.datetime.month_end()
                        }
                    ],
                    primary_action_label: __('Create Invoice'),
                    primary_action: function(values) {
                        frappe.call({
                            method: 'solede_project.api.project_api.create_sales_invoice_from_timesheet',
                            args: {
                                project_name: frm.doc.name,
                                from_date: values.from_date,
                                to_date: values.to_date
                            },
                            freeze: true,
                            freeze_message: __('Creating Invoice...'),
                            callback: function(r) {
                                if (r.message && r.message.success) {
                                    frappe.msgprint({
                                        title: __('Success'),
                                        message: r.message.message,
                                        indicator: 'green'
                                    });
                                    d.hide();
                                    frappe.set_route('Form', 'Sales Invoice', r.message.invoice);
                                }
                            }
                        });
                    }
                });
                d.show();
            }, __('Create'));
        }

        // Button: Create Milestone Invoice (solo per Forfait Progressivo)
        if (frm.doc.billing_mode === 'Forfait Progressivo') {
            frm.add_custom_button(__('Create Milestone Invoice'), () => {
                let d = new frappe.ui.Dialog({
                    title: __('Create Milestone Invoice'),
                    fields: [
                        {
                            fieldname: 'milestone_name',
                            fieldtype: 'Data',
                            label: __('Milestone Name'),
                            reqd: 1
                        },
                        {
                            fieldname: 'percentage',
                            fieldtype: 'Percent',
                            label: __('Percentage'),
                            reqd: 1
                        }
                    ],
                    primary_action_label: __('Create Invoice'),
                    primary_action: function(values) {
                        frappe.call({
                            method: 'solede_project.api.project_api.create_milestone_invoice',
                            args: {
                                project_name: frm.doc.name,
                                milestone_name: values.milestone_name,
                                percentage: values.percentage
                            },
                            freeze: true,
                            freeze_message: __('Creating Invoice...'),
                            callback: function(r) {
                                if (r.message && r.message.success) {
                                    frappe.msgprint({
                                        title: __('Success'),
                                        message: r.message.message,
                                        indicator: 'green'
                                    });
                                    d.hide();
                                    frappe.set_route('Form', 'Sales Invoice', r.message.invoice);
                                }
                            }
                        });
                    }
                });
                d.show();
            }, __('Create'));
        }
    }
});

async function show_grouped_tasks(frm) {
    // Recupera tutti i tasks del progetto
    const tasks = await frappe.call({
        method: 'frappe.client.get_list',
        args: {
            doctype: 'Task',
            filters: {
                project: frm.doc.name
            },
            fields: ['name', 'subject', 'description', 'status', 'service_group', 'parent_task', 'is_group', 'expected_hours', 'actual_hours', 'progress'],
            order_by: 'service_group, is_group desc, name',
            limit_page_length: 999
        }
    });

    if (!tasks.message || tasks.message.length === 0) {
        return;
    }

    // Raggruppa i tasks per service_group
    const grouped = {};

    tasks.message.forEach(task => {
        if (!task.service_group) {
            return;
        }

        if (!grouped[task.service_group]) {
            grouped[task.service_group] = {
                parent: null,
                children: []
            };
        }

        if (task.is_group) {
            grouped[task.service_group].parent = task;
        } else {
            grouped[task.service_group].children.push(task);
        }
    });

    // Genera HTML
    let html = '<div style="margin-top: 20px;">';
    html += '<h4 style="margin-bottom: 15px; color: #36414c;"><i class="fa fa-tasks" style="margin-right: 8px;"></i>Tasks by Service Group</h4>';

    for (const service_group in grouped) {
        const group_data = grouped[service_group];
        const parent = group_data.parent;

        html += '<div style="margin-bottom: 25px; border: 1px solid #d1d8dd; border-radius: 6px; padding: 15px; background-color: #f7f9fb; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">';

        // Header del gruppo
        html += '<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; padding-bottom: 10px; border-bottom: 2px solid #e0e6eb;">';
        html += `<h5 style="margin: 0; color: #36414c; font-size: 16px;"><i class="fa fa-folder-open" style="margin-right: 8px; color: #5e64ff;"></i>${service_group}</h5>`;

        if (parent) {
            const progress_color = parent.progress >= 100 ? '#28a745' : parent.progress >= 50 ? '#ffc107' : '#6c757d';
            html += `<div style="display: flex; align-items: center; gap: 15px; font-size: 13px;">`;
            html += `<span style="color: ${progress_color}; font-weight: bold; font-size: 16px;">${parent.progress || 0}%</span>`;
            html += `<span style="color: #6c757d;"><i class="fa fa-clock-o" style="margin-right: 4px;"></i>${parent.expected_hours || 0}h planned</span>`;
            html += `<span style="color: #6c757d;"><i class="fa fa-check-circle" style="margin-right: 4px;"></i>${parent.actual_hours || 0}h spent</span>`;
            html += `</div>`;
        }

        html += '</div>';

        // Tasks del gruppo
        if (group_data.children.length > 0) {
            html += '<div style="background: white; border-radius: 4px; overflow: hidden;">';

            group_data.children.forEach((task, index) => {
                const border_style = index < group_data.children.length - 1 ? 'border-bottom: 1px solid #f0f4f7;' : '';
                html += `<div style="padding: 12px; ${border_style} display: flex; align-items: center; gap: 15px; transition: background 0.2s;">`;

                // Task subject e link
                html += `<div style="flex: 1; min-width: 0;">`;
                html += `<a href="/app/task/${task.name}" style="color: #2490ef; text-decoration: none; font-weight: 500; font-size: 14px;">${task.subject}</a>`;
                html += `</div>`;

                // Status badge
                const status_colors = {
                    'Open': '#6c757d',
                    'Working': '#2490ef',
                    'Pending Review': '#ffc107',
                    'Completed': '#28a745',
                    'Cancelled': '#dc3545'
                };
                const status_color = status_colors[task.status] || '#6c757d';
                html += `<div style="flex-shrink: 0;">`;
                html += `<span style="background: ${status_color}; color: white; padding: 3px 10px; border-radius: 12px; font-size: 11px; font-weight: 500;">${task.status}</span>`;
                html += `</div>`;

                // Hours
                html += `<div style="flex-shrink: 0; min-width: 80px; text-align: right; font-size: 13px; color: #6c757d;">`;
                html += `<i class="fa fa-clock-o" style="margin-right: 4px;"></i>${task.expected_hours || 0}h / ${task.actual_hours || 0}h`;
                html += `</div>`;

                // Progress bar
                const progress = task.progress || 0;
                const progress_color = progress >= 100 ? '#28a745' : progress >= 50 ? '#ffc107' : '#6c757d';
                html += `<div style="flex-shrink: 0; min-width: 120px; display: flex; align-items: center;">`;
                html += `<div style="flex: 1; height: 8px; background: #e9ecef; border-radius: 4px; margin-right: 8px; overflow: hidden;">`;
                html += `<div style="width: ${progress}%; height: 100%; background: ${progress_color}; transition: width 0.3s;"></div>`;
                html += `</div>`;
                html += `<span style="font-size: 12px; color: ${progress_color}; font-weight: 600; min-width: 35px; text-align: right;">${progress}%</span>`;
                html += `</div>`;

                html += '</div>';
            });

            html += '</div>';
        } else {
            html += '<div style="padding: 20px; text-align: center; color: #6c757d; font-style: italic;">No tasks in this group</div>';
        }

        html += '</div>';
    }

    html += '</div>';

    // Trova o crea un campo HTML per mostrare i tasks
    if (!frm.fields_dict.tasks_html) {
        // Aggiungi un campo HTML dinamicamente
        frm.dashboard.add_section(html, __('Tasks Overview'));
    }
}
