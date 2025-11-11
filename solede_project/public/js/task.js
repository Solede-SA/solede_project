// Copyright (c) 2024, Solede SA and contributors
// Client Script for Task - Time Tracking

frappe.ui.form.on('Task', {
    refresh: function(frm) {
        // Mostra sezione time tracking solo se il task ha activity_type
        setup_time_tracking_ui(frm);
    },

    onload_post_render: function(frm) {
        // Avvia il contatore se timer è running
        if (frm.doc.timer_running && frm.doc.timer_started_at) {
            start_timer_counter(frm);
        }
    }
});

function setup_time_tracking_ui(frm) {
    // Rimuovi bottoni esistenti per evitare duplicati
    frm.page.clear_inner_toolbar();

    // Bottone Start/Stop Timer
    if (frm.doc.timer_running) {
        frm.add_custom_button(__('⏹️ Stop Timer'), () => {
            stop_timer(frm);
        }, __('Time Tracking')).addClass('btn-danger');
    } else {
        frm.add_custom_button(__('▶️ Start Timer'), () => {
            start_timer(frm);
        }, __('Time Tracking')).addClass('btn-primary');
    }

    // Bottone Add Manual Time
    frm.add_custom_button(__('⏱️ Add Manual Time'), () => {
        show_manual_time_dialog(frm);
    }, __('Time Tracking'));

    // Mostra stato timer
    show_timer_status(frm);
}

function show_timer_status(frm) {
    // Crea HTML per mostrare stato timer - larghezza piena all'inizio del form
    let html = '<div class="timer-status-section" style="padding: 20px; margin: 15px 0 20px 0; background: #f7f9fb; border-radius: 8px; border: 1px solid #d1d8dd;">';
    html += '<div style="display: flex; justify-content: space-between; align-items: center;">';

    // Colonna sinistra: Time info
    html += '<div style="flex: 1;">';
    html += `<div style="font-size: 14px; color: #6c757d; margin-bottom: 12px; font-weight: 600;">⏱️ Time Tracking</div>`;
    html += `<div style="display: flex; gap: 30px; align-items: center;">`;

    // Expected vs Actual
    const expected = frm.doc.expected_hours || 0;
    const actual = frm.doc.actual_hours || 0;
    const variance = actual - expected;
    const variance_color = variance > 0 ? '#dc3545' : variance < 0 ? '#28a745' : '#6c757d';

    html += `<div>`;
    html += `<span style="font-size: 12px; color: #6c757d;">Expected:</span><br>`;
    html += `<span style="font-size: 20px; font-weight: bold;">${expected.toFixed(2)}h</span>`;
    html += `</div>`;

    html += `<div>`;
    html += `<span style="font-size: 12px; color: #6c757d;">Actual:</span><br>`;
    html += `<span style="font-size: 20px; font-weight: bold;">${actual.toFixed(2)}h</span>`;
    html += `</div>`;

    html += `<div>`;
    html += `<span style="font-size: 12px; color: #6c757d;">Variance:</span><br>`;
    html += `<span style="font-size: 20px; font-weight: bold; color: ${variance_color};">${variance > 0 ? '+' : ''}${variance.toFixed(2)}h</span>`;
    html += `</div>`;

    html += `</div>`;
    html += `</div>`;

    // Colonna destra: Timer status
    html += '<div style="flex: 1; text-align: right;">';

    if (frm.doc.timer_running) {
        html += `<div id="timer-display" style="font-size: 36px; font-weight: bold; color: #dc3545; font-family: monospace;">00:00:00</div>`;
        html += `<div style="font-size: 12px; color: #dc3545; margin-top: 6px; font-weight: 600;">⏺ TIMER RUNNING</div>`;
    } else {
        html += `<div style="font-size: 16px; color: #6c757d; font-weight: 500;">Timer not running</div>`;
    }

    if (frm.doc.linked_timesheet) {
        html += `<div style="margin-top: 10px;">`;
        html += `<a href="/app/timesheet/${frm.doc.linked_timesheet}" style="font-size: 13px;">📄 View Timesheet →</a>`;
        html += `</div>`;
    }

    html += `</div>`;
    html += '</div>';
    html += '</div>';

    // Rimuovi HTML precedente se esiste
    $('.timer-status-section').remove();

    // Inserisci all'inizio del form (dopo il title)
    $(html).prependTo(frm.fields_dict.subject.$wrapper.closest('.form-layout'));
}

function start_timer_counter(frm) {
    // Ferma timer esistente
    if (frm.timer_interval) {
        clearInterval(frm.timer_interval);
    }

    // Avvia contatore
    frm.timer_interval = setInterval(() => {
        if (!frm.doc.timer_running || !frm.doc.timer_started_at) {
            clearInterval(frm.timer_interval);
            return;
        }

        const started = new Date(frm.doc.timer_started_at);
        const now = new Date();
        const diff = Math.floor((now - started) / 1000); // secondi

        const hours = Math.floor(diff / 3600);
        const minutes = Math.floor((diff % 3600) / 60);
        const seconds = diff % 60;

        const display = `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;

        $('#timer-display').text(display);
    }, 1000);
}

function start_timer(frm) {
    if (!frm.doc.activity_type) {
        frappe.msgprint(__('Please set Activity Type before starting timer'));
        return;
    }

    // Mostra dialog per inserire descrizione opzionale
    const d = new frappe.ui.Dialog({
        title: __('Start Timer'),
        fields: [
            {
                fieldname: 'description',
                fieldtype: 'Small Text',
                label: __('Description'),
                description: __('Optional comment for this time log')
            }
        ],
        primary_action_label: __('Start Timer'),
        primary_action: function(values) {
            frappe.dom.freeze(__('Starting timer...'));

            frappe.call({
                method: 'solede_project.api.task_timer_api.start_timer',
                args: {
                    task_name: frm.doc.name,
                    description: values.description
                },
                callback: function(r) {
                    frappe.dom.unfreeze();

                    if (r.message && r.message.success) {
                        frappe.show_alert({
                            message: __('Timer started'),
                            indicator: 'green'
                        }, 3);

                        d.hide();
                        frm.reload_doc();
                    }
                },
                error: function(r) {
                    frappe.dom.unfreeze();
                }
            });
        }
    });

    d.show();
}

function stop_timer(frm) {
    frappe.dom.freeze(__('Stopping timer...'));

    frappe.call({
        method: 'solede_project.api.task_timer_api.stop_timer',
        args: {
            task_name: frm.doc.name
        },
        callback: function(r) {
            frappe.dom.unfreeze();

            if (r.message && r.message.success) {
                frappe.show_alert({
                    message: __('Timer stopped. {0} hours recorded', [r.message.hours.toFixed(2)]),
                    indicator: 'green'
                }, 5);

                // Ferma contatore
                if (frm.timer_interval) {
                    clearInterval(frm.timer_interval);
                }

                frm.reload_doc();
            }
        },
        error: function(r) {
            frappe.dom.unfreeze();
        }
    });
}

function show_manual_time_dialog(frm) {
    if (!frm.doc.activity_type) {
        frappe.msgprint(__('Please set Activity Type before adding time'));
        return;
    }

    const d = new frappe.ui.Dialog({
        title: __('Add Time Manually'),
        fields: [
            {
                fieldname: 'from_time',
                fieldtype: 'Datetime',
                label: __('From Time'),
                reqd: 1,
                default: frappe.datetime.now_datetime()
            },
            {
                fieldname: 'to_time',
                fieldtype: 'Datetime',
                label: __('To Time'),
                reqd: 1,
                default: frappe.datetime.now_datetime()
            },
            {
                fieldname: 'hours',
                fieldtype: 'Float',
                label: __('Hours'),
                description: __('Leave empty to auto-calculate from time range'),
                precision: 2
            },
            {
                fieldname: 'description',
                fieldtype: 'Small Text',
                label: __('Description'),
                description: __('Optional comment for this time log')
            }
        ],
        primary_action_label: __('Add Time'),
        primary_action: function(values) {
            frappe.dom.freeze(__('Adding time...'));

            frappe.call({
                method: 'solede_project.api.task_timer_api.add_manual_time',
                args: {
                    task_name: frm.doc.name,
                    from_time: values.from_time,
                    to_time: values.to_time,
                    hours: values.hours,
                    description: values.description
                },
                callback: function(r) {
                    frappe.dom.unfreeze();

                    if (r.message && r.message.success) {
                        frappe.show_alert({
                            message: __('Time added: {0} hours', [r.message.hours.toFixed(2)]),
                            indicator: 'green'
                        }, 5);

                        d.hide();
                        frm.reload_doc();
                    }
                },
                error: function(r) {
                    frappe.dom.unfreeze();
                }
            });
        }
    });

    d.show();
}
