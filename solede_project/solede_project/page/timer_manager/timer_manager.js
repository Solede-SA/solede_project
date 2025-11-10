frappe.pages['timer-manager'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Timer Manager',
		single_column: true
	});

	page.main.html(`
		<div class="timer-manager-container" style="padding: 20px;">
			<div class="card" style="padding: 30px; text-align: center;">
				<h3 style="color: #dc3545; margin-bottom: 20px;">⚠️ Emergency Timer Manager</h3>
				<p style="margin-bottom: 30px;">
					Questa utility chiude <strong>tutti i timer attivi</strong> nel sistema.<br>
					Usa solo in caso di timer bloccati o problemi di sincronizzazione.
				</p>

				<div id="timer-stats" style="margin-bottom: 30px; padding: 20px; background: #f7f9fb; border-radius: 8px;">
					<div class="spinner-border" role="status">
						<span class="sr-only">Loading...</span>
					</div>
					<p>Caricamento...</p>
				</div>

				<button class="btn btn-danger btn-lg" id="force-close-btn" disabled>
					<i class="fa fa-times-circle"></i> Force Close All Timers
				</button>
			</div>
		</div>
	`);

	// Carica statistiche
	load_timer_stats(page);

	// Gestisci click bottone
	page.main.find('#force-close-btn').on('click', function() {
		force_close_all_timers(page);
	});
};

function load_timer_stats(page) {
	frappe.call({
		method: 'solede_project.api.timer_utils.get_active_timers_count',
		callback: function(r) {
			const count = r.message || 0;

			let html = `
				<h2 style="font-size: 48px; color: ${count > 0 ? '#dc3545' : '#28a745'}; margin: 0;">
					${count}
				</h2>
				<p style="margin: 10px 0 0 0; color: #6c757d;">
					Timer attivi nel sistema
				</p>
			`;

			page.main.find('#timer-stats').html(html);

			// Abilita bottone solo se ci sono timer attivi
			if (count > 0) {
				page.main.find('#force-close-btn').prop('disabled', false);
			}
		}
	});
}

function force_close_all_timers(page) {
	frappe.confirm(
		'Sei sicuro di voler chiudere <strong>tutti i timer attivi</strong>?<br>Questa azione non può essere annullata.',
		function() {
			// Conferma
			page.main.find('#force-close-btn').prop('disabled', true).html('<i class="fa fa-spinner fa-spin"></i> Chiusura in corso...');

			frappe.call({
				method: 'solede_project.api.timer_utils.force_close_all_timers',
				callback: function(r) {
					if (r.message) {
						frappe.show_alert({
							message: 'Timer chiusi con successo!',
							indicator: 'green'
						}, 5);

						// Ricarica stats
						load_timer_stats(page);

						// Reset bottone
						page.main.find('#force-close-btn').html('<i class="fa fa-times-circle"></i> Force Close All Timers');
					}
				},
				error: function() {
					page.main.find('#force-close-btn').prop('disabled', false).html('<i class="fa fa-times-circle"></i> Force Close All Timers');
				}
			});
		},
		function() {
			// Annulla
		}
	);
}
