// Copyright (c) 2024, Solede SA and contributors
// Timesheet List - Emergency Timer Manager

frappe.listview_settings['Timesheet'] = {
	onload: function(listview) {
		// Aggiungi pulsante "Force Close All Timers" nella toolbar
		listview.page.add_inner_button(__('Force Close All Timers'), function() {
			force_close_all_timers_from_list();
		}).addClass('btn-danger');
	}
};

function force_close_all_timers_from_list() {
	// Prima mostra quanti timer sono attivi
	frappe.call({
		method: 'solede_project.api.timer_utils.get_active_timers_count',
		callback: function(r) {
			const count = r.message || 0;

			if (count === 0) {
				frappe.msgprint(__('Non ci sono timer attivi da chiudere.'));
				return;
			}

			// Mostra conferma con il conteggio
			frappe.confirm(
				__('Sei sicuro di voler chiudere <strong>{0} timer attivi</strong>?<br><br>Questa azione:<ul><li>Chiuderà tutti i timer aperti</li><li>Calcolerà le ore automaticamente</li><li>Resetterà i flag nei Task</li></ul>Questa azione non può essere annullata.', [count]),
				function() {
					// Conferma - esegui chiusura
					frappe.dom.freeze(__('Chiusura timer in corso...'));

					frappe.call({
						method: 'solede_project.api.timer_utils.force_close_all_timers',
						callback: function(r) {
							frappe.dom.unfreeze();

							if (r.message) {
								const result = r.message;

								let msg = __('<h4>✅ Timer chiusi con successo!</h4><ul>');
								msg += __('<li>Timesheet aggiornati: {0}</li>', [result.timesheets_updated]);
								msg += __('<li>Time logs chiusi: {0}</li>', [result.time_logs_closed]);
								msg += __('<li>Task aggiornati: {0}</li>', [result.tasks_updated]);
								msg += '</ul>';

								if (result.errors && result.errors.length > 0) {
									msg += '<h5>⚠️ Errori:</h5><ul>';
									result.errors.forEach(error => {
										msg += `<li>${error}</li>`;
									});
									msg += '</ul>';
								}

								frappe.msgprint({
									title: __('Force Close Timers'),
									message: msg,
									indicator: 'green'
								});

								// Ricarica la lista
								cur_list.refresh();
							}
						},
						error: function() {
							frappe.dom.unfreeze();
							frappe.msgprint({
								title: __('Errore'),
								message: __('Si è verificato un errore durante la chiusura dei timer.'),
								indicator: 'red'
							});
						}
					});
				}
			);
		}
	});
}
