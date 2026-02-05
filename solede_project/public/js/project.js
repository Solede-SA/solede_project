// Copyright (c) 2024, Solede SA and contributors
// Client Script for Project

frappe.ui.form.on('Project', {
    setup: function(frm) {
        // Filtro per project_manager: mostra solo utenti con ruolo Projects Manager o Projects Supervisor
        frm.set_query('project_manager', function() {
            return {
                query: 'solede_project.api.project_permission.get_project_manager_users'
            };
        });
    },

    refresh: function(frm) {
        // Mostra i tasks attivi e conclusi
        if (frm.doc.name) {
            show_grouped_tasks(frm, 'active');
            show_grouped_tasks(frm, 'completed');
            show_procurement(frm);
        }

        // Verifica ruoli utente per mostrare/nascondere funzionalità
        const user_roles = frappe.user_roles || [];
        const is_supervisor = user_roles.includes('Projects Supervisor') || user_roles.includes('System Manager');
        const is_pm = user_roles.includes('Projects Manager');

        // Campo project_manager: solo Supervisor può modificarlo su progetti esistenti
        if (frm.doc.name && !frm.doc.__islocal) {
            if (!is_supervisor) {
                frm.set_df_property('project_manager', 'read_only', 1);
            }
        }

        // Button: Add Task
        if (frm.doc.name) {
            frm.add_custom_button(__('Add Task'), () => {
                show_add_task_dialog(frm);
            }, __('Create')).addClass('btn-primary');
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

async function show_grouped_tasks(frm, filter_type = 'active') {
    // Recupera tutti i tasks del progetto
    const tasks = await frappe.call({
        method: 'frappe.client.get_list',
        args: {
            doctype: 'Task',
            filters: {
                project: frm.doc.name
            },
            fields: ['name', 'subject', 'description', 'status', 'parent_task', 'is_group', 'expected_hours', 'actual_hours', 'progress', '_assign'],
            order_by: 'is_group desc, name',
            limit_page_length: 999
        }
    });

    if (!tasks.message || tasks.message.length === 0) {
        return;
    }

    // Status considerati "conclusi"
    const completed_statuses = ['Completed', 'Cancelled'];

    // Filtra i task in base al tipo
    let filtered_tasks = tasks.message;
    if (filter_type === 'completed') {
        // Mostra solo task conclusi (status Completed o Cancelled)
        filtered_tasks = tasks.message.filter(task => completed_statuses.includes(task.status));
    } else {
        // Mostra solo task attivi (non Completed/Cancelled)
        filtered_tasks = tasks.message.filter(task => !completed_statuses.includes(task.status));
    }

    if (filtered_tasks.length === 0) {
        return;
    }

    // Raggruppa i tasks usando la gerarchia nativa parent_task
    const grouped = {};
    const root_tasks = [];

    filtered_tasks.forEach(task => {
        if (task.is_group) {
            // Task di tipo gruppo
            grouped[task.name] = {
                parent: task,
                children: []
            };
        }
    });

    filtered_tasks.forEach(task => {
        if (!task.is_group) {
            if (task.parent_task && grouped[task.parent_task]) {
                // Ha un parent, aggiungilo ai children
                grouped[task.parent_task].children.push(task);
            } else {
                // Task root senza parent
                root_tasks.push(task);
            }
        }
    });

    // Se filter_type è 'completed', rimuovi gruppi senza children (tutti i children sono completati in un altro gruppo)
    if (filter_type === 'completed') {
        for (const group_name in grouped) {
            if (grouped[group_name].children.length === 0) {
                delete grouped[group_name];
            }
        }
    }

    // Se filter_type è 'active', rimuovi gruppi dove tutti i children sono completati
    if (filter_type === 'active') {
        for (const group_name in grouped) {
            const all_children_completed = grouped[group_name].children.every(child =>
                completed_statuses.includes(child.status)
            );
            if (all_children_completed && grouped[group_name].children.length > 0) {
                delete grouped[group_name];
            }
        }
    }

    // Genera HTML
    let html = '<div style="margin-top: 20px;">';

    // Mostra i gruppi con i loro children
    if (Object.keys(grouped).length > 0) {
        html += '<h4 style="margin-bottom: 15px; color: #36414c;"><i class="fa fa-tasks" style="margin-right: 8px;"></i>Task Groups</h4>';

        for (const group_name in grouped) {
            const group_data = grouped[group_name];
            const parent = group_data.parent;

            html += '<div style="margin-bottom: 25px; border: 1px solid #d1d8dd; border-radius: 6px; padding: 15px; background-color: #f7f9fb; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">';

            // Header del gruppo
            html += '<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; padding-bottom: 10px; border-bottom: 2px solid #e0e6eb;">';
            html += `<h5 style="margin: 0; color: #36414c; font-size: 16px;">`;
            html += `<a href="/app/task/${parent.name}" style="color: #36414c; text-decoration: none;">`;
            html += `<i class="fa fa-folder-open" style="margin-right: 8px; color: #5e64ff;"></i>${parent.subject}`;
            html += `</a></h5>`;

            const progress_color = parent.progress >= 100 ? '#28a745' : parent.progress >= 50 ? '#ffc107' : '#6c757d';
            html += `<div style="display: flex; align-items: center; gap: 15px; font-size: 13px;">`;
            html += `<span style="color: ${progress_color}; font-weight: bold; font-size: 16px;">${parent.progress || 0}%</span>`;
            html += `<span style="color: #6c757d;"><i class="fa fa-clock-o" style="margin-right: 4px;"></i>${parent.expected_hours || 0}h planned</span>`;
            html += `<span style="color: #6c757d;"><i class="fa fa-check-circle" style="margin-right: 4px;"></i>${parent.actual_hours || 0}h spent</span>`;
            html += `</div>`;

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
    }

    // Mostra i task root (senza parent)
    if (root_tasks.length > 0) {
        html += '<h4 style="margin-bottom: 15px; margin-top: 25px; color: #36414c;"><i class="fa fa-list" style="margin-right: 8px;"></i>Other Tasks</h4>';
        html += '<div style="margin-bottom: 25px; border: 1px solid #d1d8dd; border-radius: 6px; padding: 15px; background-color: #f7f9fb; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">';
        html += '<div style="background: white; border-radius: 4px; overflow: hidden;">';
        root_tasks.forEach((task, index) => {
            html += render_task_row(task, index === root_tasks.length - 1);
        });
        html += '</div>';
        html += '</div>';
    }

    html += '</div>';

    // Popola il campo HTML corrispondente
    const field_name = filter_type === 'completed' ? 'completed_tasks_html' : 'tasks_html';
    if (frm.fields_dict[field_name]) {
        frm.fields_dict[field_name].$wrapper.html(html);
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
            fields: ['name', 'subject', 'parent_task', 'status', '_assign'],
            order_by: 'parent_task, name',
            limit_page_length: 999
        }
    });

    if (!tasks_response.message || tasks_response.message.length === 0) {
        frappe.msgprint(__('No tasks found in this project'));
        return;
    }

    const tasks = tasks_response.message;

    // Ottieni i parent task con i loro subject
    const parent_task_ids = [...new Set(tasks.map(t => t.parent_task).filter(Boolean))];

    let parent_tasks_map = {};
    if (parent_task_ids.length > 0) {
        const parent_tasks_response = await frappe.call({
            method: 'frappe.client.get_list',
            args: {
                doctype: 'Task',
                filters: {
                    name: ['in', parent_task_ids]
                },
                fields: ['name', 'subject']
            }
        });

        parent_tasks_response.message.forEach(pt => {
            parent_tasks_map[pt.name] = `${pt.name} - ${pt.subject}`;
        });
    }

    // Crea le opzioni per il dropdown
    const parent_task_options = ['All', ...Object.values(parent_tasks_map)];

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
                fieldname: 'parent_task_filter',
                fieldtype: 'Select',
                label: __('Filter by Parent Task'),
                options: parent_task_options,
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
        const parent_task_filter_value = dialog.get_value('parent_task_filter');
        const status_filter = dialog.get_value('status_filter');

        // Estrai il nome del task dalla selezione (formato: "TASK-XXX - Subject")
        let parent_task_filter = parent_task_filter_value;
        if (parent_task_filter_value && parent_task_filter_value !== 'All') {
            parent_task_filter = parent_task_filter_value.split(' - ')[0];
        }

        let filtered_tasks = tasks.filter(task => {
            const parent_match = parent_task_filter === 'All' || task.parent_task === parent_task_filter;
            const status_match = status_filter === 'All' || task.status === status_filter;
            return parent_match && status_match;
        });

        let html = '<div style="max-height: 400px; overflow-y: auto;">';
        html += '<table class="table table-bordered table-hover" style="margin: 0;">';
        html += '<thead style="position: sticky; top: 0; background: white; z-index: 1;">';
        html += '<tr>';
        html += '<th style="width: 50px; text-align: center;"><input type="checkbox" id="select-all-checkbox"></th>';
        html += '<th>Task</th>';
        html += '<th style="width: 150px;">Parent Task</th>';
        html += '<th style="width: 120px;">Status</th>';
        html += '<th style="width: 150px;">Assigned To</th>';
        html += '</tr>';
        html += '</thead>';
        html += '<tbody>';

        filtered_tasks.forEach(task => {
            const assigned = task._assign ? JSON.parse(task._assign) : [];
            const assigned_text = assigned.length ? assigned.map(u => u.split('@')[0]).join(', ') : 'Not assigned';

            // Mostra parent task con subject se disponibile
            const parent_display = task.parent_task ? (parent_tasks_map[task.parent_task] || task.parent_task) : '-';

            html += `<tr data-task-name="${task.name}">`;
            html += `<td style="text-align: center;"><input type="checkbox" class="task-checkbox" data-task-name="${task.name}" ${selected_tasks.includes(task.name) ? 'checked' : ''}></td>`;
            html += `<td><a href="/app/task/${task.name}" target="_blank">${task.subject}</a></td>`;
            html += `<td style="font-size: 12px;">${parent_display}</td>`;
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

async function show_add_task_dialog(frm) {
    // Recupera tutti i task di tipo gruppo per popolare il dropdown parent_task
    const group_tasks_response = await frappe.call({
        method: 'frappe.client.get_list',
        args: {
            doctype: 'Task',
            filters: {
                project: frm.doc.name,
                is_group: 1
            },
            fields: ['name', 'subject'],
            order_by: 'name',
            limit_page_length: 999
        }
    });

    const group_tasks = group_tasks_response.message || [];
    const parent_task_options = group_tasks.map(t => ({ label: t.subject, value: t.name }));

    const dialog = new frappe.ui.Dialog({
        title: __('Add New Task'),
        size: 'large',
        fields: [
            {
                fieldtype: 'Section Break',
                label: __('Basic Information')
            },
            {
                fieldname: 'subject',
                fieldtype: 'Data',
                label: __('Task Subject'),
                reqd: 1
            },
            {
                fieldname: 'is_group',
                fieldtype: 'Check',
                label: __('Is Group Task'),
                description: __('Check this if this task is a parent/group task')
            },
            {
                fieldtype: 'Column Break'
            },
            {
                fieldname: 'parent_task',
                fieldtype: 'Link',
                label: __('Parent Task'),
                options: 'Task',
                get_query: function() {
                    return {
                        filters: {
                            project: frm.doc.name,
                            is_group: 1
                        }
                    };
                },
                description: __('Select a group task to organize this task under')
            },
            {
                fieldname: 'is_milestone',
                fieldtype: 'Check',
                label: __('Is Milestone')
            },
            {
                fieldtype: 'Section Break',
                label: __('Details')
            },
            {
                fieldname: 'description',
                fieldtype: 'Text Editor',
                label: __('Task Description')
            },
            {
                fieldtype: 'Section Break',
                label: __('Planning')
            },
            {
                fieldname: 'activity_type',
                fieldtype: 'Link',
                label: __('Activity Type'),
                options: 'Activity Type',
                description: __('Required for time tracking')
            },
            {
                fieldname: 'expected_hours',
                fieldtype: 'Float',
                label: __('Expected Hours'),
                default: 0
            },
            {
                fieldtype: 'Column Break'
            },
            {
                fieldname: 'exp_start_date',
                fieldtype: 'Date',
                label: __('Expected Start Date')
            },
            {
                fieldname: 'exp_end_date',
                fieldtype: 'Date',
                label: __('Expected End Date')
            },
            {
                fieldtype: 'Section Break',
                label: __('Assignment')
            },
            {
                fieldname: 'assign_to_users',
                fieldtype: 'MultiSelectPills',
                label: __('Assign To'),
                get_data: function(txt) {
                    return frappe.db.get_link_options('User', txt, {
                        user_type: 'System User',
                        enabled: 1
                    });
                }
            },
            {
                fieldname: 'priority',
                fieldtype: 'Select',
                label: __('Priority'),
                options: ['Low', 'Medium', 'High', 'Urgent'],
                default: 'Medium'
            }
        ],
        primary_action_label: __('Create Task'),
        primary_action: async function(values) {
            frappe.dom.freeze(__('Creating task...'));

            try {
                // Crea il task
                const task = await frappe.call({
                    method: 'frappe.client.insert',
                    args: {
                        doc: {
                            doctype: 'Task',
                            subject: values.subject,
                            project: frm.doc.name,
                            company: frm.doc.company,
                            is_group: values.is_group || 0,
                            parent_task: values.parent_task || null,
                            is_milestone: values.is_milestone || 0,
                            description: values.description || '',
                            activity_type: values.activity_type || null,
                            expected_hours: values.expected_hours || 0,
                            exp_start_date: values.exp_start_date || null,
                            exp_end_date: values.exp_end_date || null,
                            priority: values.priority || 'Medium',
                            status: 'Open'
                        }
                    }
                });

                // Se ci sono utenti da assegnare, usa l'API di assignment
                if (values.assign_to_users && values.assign_to_users.length > 0) {
                    await frappe.call({
                        method: 'frappe.desk.form.assign_to.add',
                        args: {
                            assign_to: values.assign_to_users,
                            doctype: 'Task',
                            name: task.message.name,
                            description: `Task created from project ${frm.doc.name}`,
                            priority: values.priority || 'Medium'
                        }
                    });
                }

                frappe.dom.unfreeze();

                dialog.hide();

                // Refresh la visualizzazione dei tasks
                await show_grouped_tasks(frm);

                // Mostra messaggio di successo con link al task
                frappe.show_alert({
                    message: __('Task {0} created successfully', [`<a href="/app/task/${task.message.name}" target="_blank">${task.message.name}</a>`]),
                    indicator: 'green'
                }, 5);

            } catch (error) {
                frappe.dom.unfreeze();
                frappe.msgprint({
                    title: __('Error'),
                    message: __('Failed to create task: ') + error.message,
                    indicator: 'red'
                });
            }
        }
    });

    dialog.show();
}

async function show_procurement(frm) {
    if (!frm.fields_dict.procurement_html) return;

    const resp = await frappe.call({
        method: 'solede_project.api.project_api.get_project_procurement',
        args: { project_name: frm.doc.name }
    });

    const data = resp.message || {};
    const po_items = data.po_items || [];
    const mr_items = data.mr_items || [];
    const po_map = data.purchase_orders || {};
    const mr_map = data.material_requests || {};

    // Get unique parent names (preserving order)
    const po_names = [...new Set(po_items.map(i => i.parent))];
    const mr_names = [...new Set(mr_items.map(i => i.parent))];

    // Group items by parent
    const po_grouped = {};
    po_items.forEach(item => {
        if (!po_grouped[item.parent]) po_grouped[item.parent] = [];
        po_grouped[item.parent].push(item);
    });
    const mr_grouped = {};
    mr_items.forEach(item => {
        if (!mr_grouped[item.parent]) mr_grouped[item.parent] = [];
        mr_grouped[item.parent].push(item);
    });

    // Status colors
    const status_colors = {
        'Draft': '#6c757d',
        'To Receive and Bill': '#2490ef',
        'To Bill': '#ffc107',
        'To Receive': '#17a2b8',
        'Completed': '#28a745',
        'Cancelled': '#dc3545',
        'Closed': '#6c757d',
        'On Hold': '#ffc107',
        'Partially Ordered': '#17a2b8',
        'Ordered': '#2490ef',
        'Pending': '#ffc107',
        'Partially Received': '#17a2b8',
        'Received': '#28a745',
        'Transferred': '#28a745',
        'Material Transferred': '#28a745',
        'Material Issued': '#28a745'
    };

    let html = '<div style="margin-top: 15px;">';

    // ---- Purchase Orders section ----
    html += '<h4 style="margin-bottom: 15px; color: #36414c;"><i class="fa fa-shopping-cart" style="margin-right: 8px;"></i>Purchase Orders</h4>';

    if (po_names.length === 0) {
        html += '<div style="padding: 20px; text-align: center; color: #6c757d; font-style: italic; border: 1px solid #d1d8dd; border-radius: 6px; background: #f7f9fb; margin-bottom: 25px;">Nessun ordine di acquisto collegato</div>';
    } else {
        po_names.forEach(po_name => {
            const po = po_map[po_name] || {};
            const items = po_grouped[po_name] || [];
            const s_color = status_colors[po.status] || '#6c757d';

            html += '<div style="margin-bottom: 20px; border: 1px solid #d1d8dd; border-radius: 6px; padding: 15px; background-color: #f7f9fb; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">';

            // Header
            html += '<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; padding-bottom: 10px; border-bottom: 2px solid #e0e6eb; flex-wrap: wrap; gap: 8px;">';
            html += '<div style="display: flex; align-items: center; gap: 10px; flex-wrap: wrap;">';
            html += `<a href="/app/purchase-order/${po_name}" style="color: #36414c; text-decoration: none; font-weight: 600; font-size: 15px;">${po_name}</a>`;
            html += `<span style="background: ${s_color}; color: white; padding: 3px 10px; border-radius: 12px; font-size: 11px; font-weight: 500;">${po.status || ''}</span>`;
            html += '</div>';
            html += '<div style="display: flex; align-items: center; gap: 15px; font-size: 13px; color: #6c757d; flex-wrap: wrap;">';
            if (po.supplier_name) html += `<span><i class="fa fa-building" style="margin-right: 4px;"></i>${po.supplier_name}</span>`;
            if (po.transaction_date) html += `<span><i class="fa fa-calendar" style="margin-right: 4px;"></i>${frappe.datetime.str_to_user(po.transaction_date)}</span>`;
            html += `<span style="font-weight: 600; color: #36414c;">${format_currency(po.grand_total || 0)}</span>`;
            html += `<span>Rcv: ${flt(po.per_received || 0, 1)}%</span>`;
            html += `<span>Bill: ${flt(po.per_billed || 0, 1)}%</span>`;
            html += '</div>';
            html += '</div>';

            // Items table
            html += '<div style="background: white; border-radius: 4px; overflow-x: auto;">';
            html += '<table style="width: 100%; border-collapse: collapse; font-size: 13px;">';
            html += '<thead><tr style="background: #f0f4f7; color: #6c757d; font-size: 11px; text-transform: uppercase;">';
            html += '<th style="padding: 8px 10px; text-align: left;">Item</th>';
            html += '<th style="padding: 8px 10px; text-align: right;">Qty</th>';
            html += '<th style="padding: 8px 10px; text-align: left;">UOM</th>';
            html += '<th style="padding: 8px 10px; text-align: right;">Rate</th>';
            html += '<th style="padding: 8px 10px; text-align: right;">Amount</th>';
            html += '<th style="padding: 8px 10px; text-align: right;">Received</th>';
            html += '</tr></thead><tbody>';
            items.forEach(item => {
                html += '<tr style="border-bottom: 1px solid #f0f4f7;">';
                html += `<td style="padding: 8px 10px;">${item.item_name || item.item_code}</td>`;
                html += `<td style="padding: 8px 10px; text-align: right;">${flt(item.qty, 2)}</td>`;
                html += `<td style="padding: 8px 10px;">${item.uom || ''}</td>`;
                html += `<td style="padding: 8px 10px; text-align: right;">${format_currency(item.rate || 0)}</td>`;
                html += `<td style="padding: 8px 10px; text-align: right;">${format_currency(item.amount || 0)}</td>`;
                html += `<td style="padding: 8px 10px; text-align: right;">${flt(item.received_qty || 0, 2)}</td>`;
                html += '</tr>';
            });
            html += '</tbody></table></div>';
            html += '</div>';
        });
    }

    // ---- Material Requests section ----
    html += '<h4 style="margin-bottom: 15px; margin-top: 25px; color: #36414c;"><i class="fa fa-clipboard" style="margin-right: 8px;"></i>Material Requests</h4>';

    if (mr_names.length === 0) {
        html += '<div style="padding: 20px; text-align: center; color: #6c757d; font-style: italic; border: 1px solid #d1d8dd; border-radius: 6px; background: #f7f9fb;">Nessuna richiesta materiale collegata</div>';
    } else {
        mr_names.forEach(mr_name => {
            const mr = mr_map[mr_name] || {};
            const items = mr_grouped[mr_name] || [];
            const s_color = status_colors[mr.status] || '#6c757d';

            html += '<div style="margin-bottom: 20px; border: 1px solid #d1d8dd; border-radius: 6px; padding: 15px; background-color: #f7f9fb; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">';

            // Header
            html += '<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; padding-bottom: 10px; border-bottom: 2px solid #e0e6eb; flex-wrap: wrap; gap: 8px;">';
            html += '<div style="display: flex; align-items: center; gap: 10px; flex-wrap: wrap;">';
            html += `<a href="/app/material-request/${mr_name}" style="color: #36414c; text-decoration: none; font-weight: 600; font-size: 15px;">${mr_name}</a>`;
            html += `<span style="background: ${s_color}; color: white; padding: 3px 10px; border-radius: 12px; font-size: 11px; font-weight: 500;">${mr.status || ''}</span>`;
            if (mr.material_request_type) html += `<span style="background: #e9ecef; color: #495057; padding: 3px 10px; border-radius: 12px; font-size: 11px;">${mr.material_request_type}</span>`;
            html += '</div>';
            html += '<div style="font-size: 13px; color: #6c757d;">';
            if (mr.transaction_date) html += `<span><i class="fa fa-calendar" style="margin-right: 4px;"></i>${frappe.datetime.str_to_user(mr.transaction_date)}</span>`;
            html += '</div>';
            html += '</div>';

            // Items table
            html += '<div style="background: white; border-radius: 4px; overflow-x: auto;">';
            html += '<table style="width: 100%; border-collapse: collapse; font-size: 13px;">';
            html += '<thead><tr style="background: #f0f4f7; color: #6c757d; font-size: 11px; text-transform: uppercase;">';
            html += '<th style="padding: 8px 10px; text-align: left;">Item</th>';
            html += '<th style="padding: 8px 10px; text-align: right;">Qty</th>';
            html += '<th style="padding: 8px 10px; text-align: left;">UOM</th>';
            html += '<th style="padding: 8px 10px; text-align: right;">Ordered</th>';
            html += '</tr></thead><tbody>';
            items.forEach(item => {
                html += '<tr style="border-bottom: 1px solid #f0f4f7;">';
                html += `<td style="padding: 8px 10px;">${item.item_name || item.item_code}</td>`;
                html += `<td style="padding: 8px 10px; text-align: right;">${flt(item.qty, 2)}</td>`;
                html += `<td style="padding: 8px 10px;">${item.uom || ''}</td>`;
                html += `<td style="padding: 8px 10px; text-align: right;">${flt(item.ordered_qty || 0, 2)}</td>`;
                html += '</tr>';
            });
            html += '</tbody></table></div>';
            html += '</div>';
        });
    }

    html += '</div>';

    frm.fields_dict.procurement_html.$wrapper.html(html);
}
