// Copyright (c) 2024, Solede SA and contributors
// Client Script for Project

frappe.ui.form.on('Project', {
    refresh: function(frm) {
        // Mostra i tasks raggruppati per Service Group
        if (frm.doc.name) {
            show_grouped_tasks(frm);
        }

        // Button: Bulk Assign Tasks
        if (frm.doc.name) {
            frm.add_custom_button(__('Bulk Assign Tasks'), () => {
                show_bulk_assignment_dialog(frm);
            }, __('Actions'));
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

function render_task_row(task, is_last) {
    const border_style = !is_last ? 'border-bottom: 1px solid #f0f4f7;' : '';
    let html = `<div style="padding: 12px; ${border_style} display: flex; align-items: center; gap: 15px; transition: background 0.2s;">`;

    // Task subject e link
    html += `<div style="flex: 1; min-width: 0;">`;
    html += `<a href="/app/task/${task.name}" style="color: #2490ef; text-decoration: none; font-weight: 500; font-size: 14px;">${task.subject}</a>`;

    // Assigned users
    if (task._assign) {
        try {
            const assigned = JSON.parse(task._assign);
            if (assigned.length > 0) {
                html += `<div style="margin-top: 4px; font-size: 11px; color: #6c757d;">`;
                html += `<i class="fa fa-user" style="margin-right: 4px;"></i>`;
                const assignedNames = assigned.map(email => {
                    const username = email.split('@')[0];
                    return username.charAt(0).toUpperCase() + username.slice(1);
                });
                html += assignedNames.join(', ');
                html += `</div>`;
            }
        } catch (e) {
            // Ignora errori di parsing
        }
    }

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
    return html;
}

async function show_grouped_tasks(frm) {
    // Recupera tutti i tasks del progetto
    const tasks = await frappe.call({
        method: 'frappe.client.get_list',
        args: {
            doctype: 'Task',
            filters: {
                project: frm.doc.name
            },
            fields: ['name', 'subject', 'description', 'status', 'service_group', 'parent_task', 'is_group', 'expected_hours', 'actual_hours', 'progress', '_assign'],
            order_by: 'service_group, is_group desc, name',
            limit_page_length: 999
        }
    });

    if (!tasks.message || tasks.message.length === 0) {
        return;
    }

    // Raggruppa i tasks per service_group e raccogli quelli senza gruppo
    const grouped = {};
    const ungrouped_tasks = [];

    tasks.message.forEach(task => {
        if (!task.service_group) {
            // Raccogli i task senza service_group
            ungrouped_tasks.push(task);
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

    // Mostra header solo se ci sono task raggruppati
    if (Object.keys(grouped).length > 0) {
        html += '<h4 style="margin-bottom: 15px; color: #36414c;"><i class="fa fa-tasks" style="margin-right: 8px;"></i>Tasks by Service Group</h4>';
    }

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
                html += render_task_row(task, index === group_data.children.length - 1);
            });
            html += '</div>';
        } else {
            html += '<div style="padding: 20px; text-align: center; color: #6c757d; font-style: italic;">No tasks in this group</div>';
        }

        html += '</div>';
    }

    // Mostra i task non raggruppati
    if (ungrouped_tasks.length > 0) {
        html += '<h4 style="margin-bottom: 15px; margin-top: 25px; color: #36414c;"><i class="fa fa-list" style="margin-right: 8px;"></i>Other Tasks</h4>';
        html += '<div style="margin-bottom: 25px; border: 1px solid #d1d8dd; border-radius: 6px; padding: 15px; background-color: #f7f9fb; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">';
        html += '<div style="background: white; border-radius: 4px; overflow: hidden;">';
        ungrouped_tasks.forEach((task, index) => {
            html += render_task_row(task, index === ungrouped_tasks.length - 1);
        });
        html += '</div>';
        html += '</div>';
    }

    html += '</div>';

    // Popola il campo HTML "tasks_html" invece della dashboard
    if (frm.fields_dict.tasks_html) {
        frm.fields_dict.tasks_html.$wrapper.html(html);
    }
}

async function show_bulk_assignment_dialog(frm) {
    // Recupera tutti i tasks del progetto
    const tasks_response = await frappe.call({
        method: 'frappe.client.get_list',
        args: {
            doctype: 'Task',
            filters: {
                project: frm.doc.name,
                is_group: 0  // Solo child tasks, non i parent groups
            },
            fields: ['name', 'subject', 'service_group', 'status', '_assign'],
            order_by: 'service_group, name',
            limit_page_length: 999
        }
    });

    if (!tasks_response.message || tasks_response.message.length === 0) {
        frappe.msgprint(__('No tasks found in this project'));
        return;
    }

    const tasks = tasks_response.message;

    // Raggruppa tasks per service_group
    const service_groups = [...new Set(tasks.map(t => t.service_group).filter(Boolean))];

    // Crea il dialog
    const dialog = new frappe.ui.Dialog({
        title: __('Bulk Assign Tasks'),
        size: 'extra-large',
        fields: [
            {
                fieldtype: 'Section Break',
                label: __('Filter Tasks')
            },
            {
                fieldname: 'service_group_filter',
                fieldtype: 'Select',
                label: __('Filter by Service Group'),
                options: ['All', ...service_groups],
                default: 'All',
                onchange: function() {
                    update_tasks_list();
                }
            },
            {
                fieldname: 'status_filter',
                fieldtype: 'Select',
                label: __('Filter by Status'),
                options: ['All', 'Open', 'Working', 'Pending Review', 'Completed', 'Cancelled'],
                default: 'All',
                onchange: function() {
                    update_tasks_list();
                }
            },
            {
                fieldtype: 'Column Break'
            },
            {
                fieldname: 'select_all',
                fieldtype: 'Button',
                label: __('Select All'),
                click: function() {
                    select_all_tasks(true);
                }
            },
            {
                fieldname: 'deselect_all',
                fieldtype: 'Button',
                label: __('Deselect All'),
                click: function() {
                    select_all_tasks(false);
                }
            },
            {
                fieldtype: 'Section Break',
                label: __('Select Tasks')
            },
            {
                fieldname: 'tasks_list',
                fieldtype: 'HTML'
            },
            {
                fieldtype: 'Section Break',
                label: __('Assignment Options')
            },
            {
                fieldname: 'assign_to_manager',
                fieldtype: 'Check',
                label: __('Assign to Project Manager'),
                default: 0,
                onchange: function() {
                    const is_checked = dialog.get_value('assign_to_manager');
                    if (is_checked) {
                        // Usa il Project Manager dal form
                        if (frm.doc.project_manager) {
                            const project_manager = frm.doc.project_manager;
                            // Ottieni gli utenti già selezionati
                            let current_users = dialog.get_value('assign_to_users') || [];
                            // Aggiungi il project manager se non è già presente
                            if (!current_users.includes(project_manager)) {
                                current_users.push(project_manager);
                                dialog.set_value('assign_to_users', current_users);
                            }
                        } else {
                            frappe.msgprint(__('No Project Manager assigned to this project. Please set a Project Manager first.'));
                            dialog.set_value('assign_to_manager', 0);
                        }
                    }
                }
            },
            {
                fieldname: 'assign_to_users',
                fieldtype: 'MultiSelectPills',
                label: __('Assign To Users'),
                reqd: 1,
                get_data: function(txt) {
                    return frappe.db.get_link_options('User', txt, {
                        user_type: 'System User',
                        enabled: 1
                    });
                }
            },
            {
                fieldtype: 'Column Break'
            },
            {
                fieldname: 'due_date',
                fieldtype: 'Date',
                label: __('Due Date')
            },
            {
                fieldname: 'priority',
                fieldtype: 'Select',
                label: __('Priority'),
                options: ['Low', 'Medium', 'High'],
                default: 'Medium'
            },
            {
                fieldtype: 'Section Break'
            },
            {
                fieldname: 'description',
                fieldtype: 'Small Text',
                label: __('Description/Comment')
            }
        ],
        primary_action_label: __('Assign Tasks'),
        primary_action: function(values) {
            assign_selected_tasks(values);
        }
    });

    // Array per tenere traccia dei task selezionati
    let selected_tasks = [];

    // Funzione per aggiornare la lista dei tasks
    function update_tasks_list() {
        const service_group_filter = dialog.get_value('service_group_filter');
        const status_filter = dialog.get_value('status_filter');

        let filtered_tasks = tasks.filter(task => {
            const group_match = service_group_filter === 'All' || task.service_group === service_group_filter;
            const status_match = status_filter === 'All' || task.status === status_filter;
            return group_match && status_match;
        });

        let html = '<div style="max-height: 400px; overflow-y: auto;">';
        html += '<table class="table table-bordered table-hover" style="margin: 0;">';
        html += '<thead style="position: sticky; top: 0; background: white; z-index: 1;">';
        html += '<tr>';
        html += '<th style="width: 50px; text-align: center;"><input type="checkbox" id="select-all-checkbox"></th>';
        html += '<th>Task</th>';
        html += '<th style="width: 150px;">Service Group</th>';
        html += '<th style="width: 120px;">Status</th>';
        html += '<th style="width: 150px;">Assigned To</th>';
        html += '</tr>';
        html += '</thead>';
        html += '<tbody>';

        filtered_tasks.forEach(task => {
            const assigned = task._assign ? JSON.parse(task._assign) : [];
            const assigned_text = assigned.length ? assigned.map(u => u.split('@')[0]).join(', ') : 'Not assigned';

            html += `<tr data-task-name="${task.name}">`;
            html += `<td style="text-align: center;"><input type="checkbox" class="task-checkbox" data-task-name="${task.name}" ${selected_tasks.includes(task.name) ? 'checked' : ''}></td>`;
            html += `<td><a href="/app/task/${task.name}" target="_blank">${task.subject}</a></td>`;
            html += `<td>${task.service_group || '-'}</td>`;
            html += `<td><span class="badge badge-${get_status_color(task.status)}">${task.status}</span></td>`;
            html += `<td style="font-size: 12px; color: #6c757d;">${assigned_text}</td>`;
            html += '</tr>';
        });

        html += '</tbody>';
        html += '</table>';
        html += '</div>';

        dialog.fields_dict.tasks_list.$wrapper.html(html);

        // Event listeners per i checkbox
        dialog.fields_dict.tasks_list.$wrapper.find('.task-checkbox').on('change', function() {
            const task_name = $(this).data('task-name');
            if ($(this).is(':checked')) {
                if (!selected_tasks.includes(task_name)) {
                    selected_tasks.push(task_name);
                }
            } else {
                selected_tasks = selected_tasks.filter(t => t !== task_name);
            }
            update_select_all_checkbox();
        });

        // Select all checkbox
        dialog.fields_dict.tasks_list.$wrapper.find('#select-all-checkbox').on('change', function() {
            const is_checked = $(this).is(':checked');
            select_all_tasks(is_checked);
        });

        update_select_all_checkbox();
    }

    function update_select_all_checkbox() {
        const all_checkboxes = dialog.fields_dict.tasks_list.$wrapper.find('.task-checkbox');
        const checked_checkboxes = dialog.fields_dict.tasks_list.$wrapper.find('.task-checkbox:checked');
        const select_all = dialog.fields_dict.tasks_list.$wrapper.find('#select-all-checkbox');

        if (all_checkboxes.length === checked_checkboxes.length && all_checkboxes.length > 0) {
            select_all.prop('checked', true);
        } else {
            select_all.prop('checked', false);
        }
    }

    function select_all_tasks(select) {
        dialog.fields_dict.tasks_list.$wrapper.find('.task-checkbox').each(function() {
            $(this).prop('checked', select);
            const task_name = $(this).data('task-name');
            if (select) {
                if (!selected_tasks.includes(task_name)) {
                    selected_tasks.push(task_name);
                }
            } else {
                selected_tasks = selected_tasks.filter(t => t !== task_name);
            }
        });
        update_select_all_checkbox();
    }

    function get_status_color(status) {
        const colors = {
            'Open': 'secondary',
            'Working': 'primary',
            'Pending Review': 'warning',
            'Completed': 'success',
            'Cancelled': 'danger'
        };
        return colors[status] || 'secondary';
    }

    async function assign_selected_tasks(values) {
        if (selected_tasks.length === 0) {
            frappe.msgprint(__('Please select at least one task'));
            return;
        }

        const assign_to_list = values.assign_to_users || [];

        if (assign_to_list.length === 0) {
            frappe.msgprint(__('Please select users to assign'));
            return;
        }

        frappe.dom.freeze(__('Assigning tasks...'));

        try {
            // Usa l'API nativa di Frappe per bulk assignment
            for (const task_name of selected_tasks) {
                await frappe.call({
                    method: 'frappe.desk.form.assign_to.add',
                    args: {
                        assign_to: assign_to_list,
                        doctype: 'Task',
                        name: task_name,
                        description: values.description || `Assigned from project ${frm.doc.name}`,
                        priority: values.priority || 'Medium',
                        date: values.due_date || null
                    }
                });
            }

            frappe.dom.unfreeze();
            frappe.show_alert({
                message: __(`Successfully assigned ${selected_tasks.length} tasks`),
                indicator: 'green'
            }, 5);

            dialog.hide();

            // Refresh la visualizzazione dei tasks
            await show_grouped_tasks(frm);

        } catch (error) {
            frappe.dom.unfreeze();
            frappe.msgprint({
                title: __('Error'),
                message: __('Failed to assign tasks: ') + error.message,
                indicator: 'red'
            });
        }
    }

    // Inizializza la lista
    update_tasks_list();
    dialog.show();
}
