// Copyright (c) 2024, Solede SA and contributors
// Client Script for Timesheet - Timer personalizzato per Task

frappe.ui.form.on('Timesheet', {
    refresh: function(frm) {
        if (frm.doc.task) {
            // Timesheet associato a Task - mostra messaggio informativo
            show_task_sync_message(frm);

            if (frm.doc.docstatus < 1) {
                // Aggiungi il nostro bottone personalizzato con campi pre-compilati
                setup_custom_timer_button(frm);
            }
        }
    }
});

frappe.ui.form.on('Timesheet Detail', {
    before_time_logs_remove: function(frm, cdt, cdn) {
        // Impedisci la rimozione di time_logs se associato a Task
        if (frm.doc.task) {
            let row = locals[cdt][cdn];
            if (row.task === frm.doc.task) {
                frappe.msgprint(__('Non puoi rimuovere time logs associati al Task. Usa il timer per gestire il tempo.'));
                frappe.validated = false;
            }
        }
    }
});

function show_task_sync_message(frm) {
    if (!frm.doc.task) return;

    // Mostra messaggio informativo sulla sincronizzazione - larghezza piena all'inizio del form
    const html = `
        <div class="task-timer-message" style="padding: 20px; margin: 15px 0 20px 0; background: #e3f2fd; border-radius: 8px; border: 1px solid #90caf9;">
            <div style="display: flex; align-items: center; gap: 15px;">
                <span style="font-size: 32px;">🔄</span>
                <div style="flex: 1;">
                    <div style="font-size: 16px; font-weight: 600; color: #1976d2; margin-bottom: 8px;">
                        Timer sincronizzato con Task
                    </div>
                    <div style="font-size: 13px; color: #424242; line-height: 1.6;">
                        Questo Timesheet è sincronizzato con il Task <a href="/app/task/${frm.doc.task}" target="_blank" style="font-weight: 600;">${frm.doc.task}</a>.<br>
                        Puoi avviare/fermare il timer da qui o dal Task - i due timer sono sincronizzati.
                    </div>
                </div>
            </div>
        </div>
    `;

    // Rimuovi messaggio precedente se esiste
    $('.task-timer-message').remove();

    // Inserisci all'inizio del form (dopo il title)
    $(html).prependTo(frm.fields_dict.employee.$wrapper.closest('.form-layout'));
}

function setup_custom_timer_button(frm) {
    // Verifica se c'è già un timer attivo
    let button_label = __('🎯 Start Task Timer');

    $.each(frm.doc.time_logs || [], function(i, row) {
        if (row.from_time <= frappe.datetime.now_datetime() && !row.completed) {
            button_label = __('🎯 Resume Task Timer');
        }
    });

    // Aggiungi il nostro bottone personalizzato con emoji per distinguerlo
    frm.add_custom_button(button_label, function() {
        start_custom_timer(frm);
    }).addClass('btn-success');
}

function start_custom_timer(frm) {
    // Carica i dati del Task
    frappe.call({
        method: 'frappe.client.get',
        args: {
            doctype: 'Task',
            name: frm.doc.task
        },
        callback: function(r) {
            if (r.message) {
                const task = r.message;

                // Verifica se c'è già un timer attivo da riprendere
                let active_row = null;
                $.each(frm.doc.time_logs || [], function(i, row) {
                    if (row.from_time <= frappe.datetime.now_datetime() && !row.completed) {
                        active_row = row;
                        return false;
                    }
                });

                if (active_row) {
                    // Riprendi timer esistente
                    let timestamp = moment(frappe.datetime.now_datetime()).diff(
                        moment(active_row.from_time),
                        "seconds"
                    );
                    show_custom_timer_dialog(frm, active_row, timestamp, task);
                } else {
                    // Crea nuovo timer
                    show_custom_timer_dialog(frm, null, 0, task);
                }
            }
        }
    });
}

function show_custom_timer_dialog(frm, row, timestamp, task) {
    let dialog = new frappe.ui.Dialog({
        title: __("Timer"),
        fields: [
            {
                fieldtype: "Link",
                label: __("Activity Type"),
                fieldname: "activity_type",
                reqd: 1,
                options: "Activity Type",
                default: task.activity_type,
                read_only: 1
            },
            {
                fieldtype: "Link",
                label: __("Project"),
                fieldname: "project",
                options: "Project",
                default: task.project,
                read_only: 1
            },
            {
                fieldtype: "Link",
                label: __("Task"),
                fieldname: "task",
                options: "Task",
                default: task.name,
                read_only: 1
            },
            {
                fieldtype: "Float",
                label: __("Expected Hrs"),
                fieldname: "expected_hours"
            },
            {
                fieldtype: "Small Text",
                label: __("Description"),
                fieldname: "description",
                description: __("Optional comment for this time log")
            },
            {
                fieldtype: "Section Break"
            },
            {
                fieldtype: "HTML",
                fieldname: "timer_html"
            }
        ]
    });

    if (row) {
        dialog.set_values({
            activity_type: task.activity_type,
            project: task.project,
            task: task.name,
            expected_hours: row.expected_hours,
            description: row.description || ""
        });
    }

    // Aggiungi HTML del timer
    dialog.get_field("timer_html").$wrapper.append(`
        <div class="stopwatch">
            <span class="hours">00</span>
            <span class="colon">:</span>
            <span class="minutes">00</span>
            <span class="colon">:</span>
            <span class="seconds">00</span>
        </div>
        <div class="playpause text-center">
            <button class="btn btn-primary btn-start"> ${__("Start")} </button>
            <button class="btn btn-primary btn-complete"> ${__("Complete")} </button>
        </div>
    `);

    control_custom_timer(frm, dialog, row, timestamp, task);
    dialog.show();
}

function control_custom_timer(frm, dialog, row, timestamp, task) {
    var $btn_start = dialog.$wrapper.find(".playpause .btn-start");
    var $btn_complete = dialog.$wrapper.find(".playpause .btn-complete");
    var interval = null;
    var currentIncrement = timestamp;
    var initialized = row ? true : false;

    if (row) {
        initialized = true;
        $btn_start.hide();
        $btn_complete.show();
        initializeTimer();
    }

    if (!initialized) {
        $btn_complete.hide();
    }

    $btn_start.click(function(e) {
        if (!initialized) {
            // Crea nuova riga con i campi pre-compilati
            var args = dialog.get_values();
            if (!args) return;

            if (frm.doc.time_logs.length == 1 && !frm.doc.time_logs[0].activity_type && !frm.doc.time_logs[0].from_time) {
                frm.doc.time_logs = [];
            }

            row = frappe.model.add_child(frm.doc, "Timesheet Detail", "time_logs");
            row.activity_type = task.activity_type;
            row.from_time = frappe.datetime.get_datetime_as_string();
            row.project = task.project;
            row.task = task.name;
            row.expected_hours = args.expected_hours;
            row.description = args.description || "";
            row.completed = 0;
            row.is_billable = 1;

            let d = moment(row.from_time);
            if (row.expected_hours) {
                d.add(row.expected_hours, "hours");
                row.to_time = d.format(frappe.defaultDatetimeFormat);
            }

            frm.refresh_field("time_logs");
            frm.save();
        }

        if (!initialized) {
            initialized = true;
            $btn_start.hide();
            $btn_complete.show();
            initializeTimer();
        }
    });

    $btn_complete.click(function() {
        var grid_row = cur_frm.fields_dict["time_logs"].grid.get_row(row.idx - 1);
        var args = dialog.get_values();
        grid_row.doc.completed = 1;
        grid_row.doc.hours = currentIncrement / 3600;
        grid_row.doc.to_time = frappe.datetime.now_datetime();
        grid_row.refresh();
        frm.dirty();
        frm.save();
        reset();
        dialog.hide();
    });

    function initializeTimer() {
        interval = setInterval(function() {
            var current = setCurrentIncrement();
            updateStopwatch(current);
        }, 1000);
    }

    function updateStopwatch(increment) {
        var hours = Math.floor(increment / 3600);
        var minutes = Math.floor((increment - hours * 3600) / 60);
        var seconds = increment - hours * 3600 - minutes * 60;

        if (!$(".modal-dialog").is(":visible")) {
            reset();
        }
        if (hours > 99999) reset();

        dialog.$wrapper.find(".hours").text(hours < 10 ? "0" + hours.toString() : hours.toString());
        dialog.$wrapper.find(".minutes").text(minutes < 10 ? "0" + minutes.toString() : minutes.toString());
        dialog.$wrapper.find(".seconds").text(seconds < 10 ? "0" + seconds.toString() : seconds.toString());
    }

    function setCurrentIncrement() {
        currentIncrement += 1;
        return currentIncrement;
    }

    function reset() {
        currentIncrement = 0;
        initialized = false;
        clearInterval(interval);
        dialog.$wrapper.find(".hours").text("00");
        dialog.$wrapper.find(".minutes").text("00");
        dialog.$wrapper.find(".seconds").text("00");
        $btn_complete.hide();
        $btn_start.show();
    }
}
