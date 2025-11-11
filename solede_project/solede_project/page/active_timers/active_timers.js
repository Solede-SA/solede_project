frappe.pages['active-timers'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Active Timers',
		single_column: true
	});

	page.main.html(`
		<div class="active-timers-container">
			<div class="filter-section" style="margin-bottom: 20px; padding: 15px; background: #f7f9fb; border-radius: 6px;">
				<div style="display: flex; gap: 15px; align-items: center;">
					<label style="font-weight: 600;">Filter by Employee:</label>
					<div id="employee-filter" style="flex: 1; max-width: 300px;"></div>
					<button class="btn btn-primary btn-sm" id="refresh-timers">
						<i class="fa fa-refresh"></i> Refresh
					</button>
				</div>
			</div>
			<div id="timers-list"></div>
		</div>
	`);

	// Create employee filter
	let employee_field = frappe.ui.form.make_control({
		parent: page.main.find('#employee-filter'),
		df: {
			fieldtype: 'Link',
			options: 'Employee',
			fieldname: 'employee',
			placeholder: __('All (Current User)'),
			onchange: function() {
				load_active_timers(page);
			}
		},
		render_input: true
	});

	// Auto-load current user's employee
	frappe.call({
		method: 'frappe.client.get_value',
		args: {
			doctype: 'Employee',
			filters: { user_id: frappe.session.user },
			fieldname: 'name'
		},
		callback: function(r) {
			if (r.message && r.message.name) {
				employee_field.set_value(r.message.name);
			}
		}
	});

	// Refresh button
	page.main.find('#refresh-timers').on('click', function() {
		load_active_timers(page);
	});

	// Function to load active timers
	function load_active_timers(page) {
		const employee = employee_field.get_value();

		frappe.call({
			method: 'solede_project.api.task_timer_api.get_active_timers',
			args: {
				employee: employee || null
			},
			callback: function(r) {
				render_timers(page, r.message || []);
			}
		});
	}

	// Function to render timers
	function render_timers(page, timers) {
		const container = page.main.find('#timers-list');

		if (!timers || timers.length === 0) {
			container.html(`
				<div style="padding: 40px; text-align: center; color: #6c757d;">
					<i class="fa fa-clock-o" style="font-size: 48px; margin-bottom: 15px; opacity: 0.3;"></i>
					<p style="font-size: 16px;">No active timers</p>
				</div>
			`);
			return;
		}

		let html = '<div class="timers-grid" style="display: grid; gap: 20px;">';

		timers.forEach(timer => {
			const started_formatted = frappe.datetime.str_to_user(timer.timer_started_at);

			html += `
				<div class="timer-card" data-task="${timer.task_name}" style="border: 1px solid #d1d8dd; border-radius: 8px; padding: 20px; background: white; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
					<div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 15px;">
						<div style="flex: 1;">
							<h4 style="margin: 0 0 8px 0; color: #36414c;">
								<a href="/app/task/${timer.task_name}" style="color: #36414c; text-decoration: none;">
									${timer.task_subject}
								</a>
							</h4>
							<div style="font-size: 12px; color: #6c757d;">
								<i class="fa fa-tag"></i> ${timer.task_name}
							</div>
						</div>
						<div style="text-align: right;">
							<div class="timer-display" data-started="${timer.timer_started_at}" style="font-size: 28px; font-weight: bold; color: #dc3545; font-family: monospace; margin-bottom: 5px;">
								${timer.elapsed_formatted}
							</div>
							<div style="font-size: 11px; color: #dc3545; font-weight: 600;">
								⏺ RUNNING
							</div>
						</div>
					</div>

					<div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; margin-bottom: 15px; padding: 12px; background: #f7f9fb; border-radius: 4px;">
						<div>
							<div style="font-size: 11px; color: #6c757d; margin-bottom: 4px;">PROJECT</div>
							<div style="font-size: 13px; font-weight: 500;">
								${timer.project ? `<a href="/app/project/${timer.project}">${timer.project_name || timer.project}</a>` : '-'}
							</div>
						</div>
						<div>
							<div style="font-size: 11px; color: #6c757d; margin-bottom: 4px;">CUSTOMER</div>
							<div style="font-size: 13px; font-weight: 500;">${timer.customer || '-'}</div>
						</div>
						<div>
							<div style="font-size: 11px; color: #6c757d; margin-bottom: 4px;">ACTIVITY TYPE</div>
							<div style="font-size: 13px; font-weight: 500;">${timer.activity_type || '-'}</div>
						</div>
						<div>
							<div style="font-size: 11px; color: #6c757d; margin-bottom: 4px;">STARTED AT</div>
							<div style="font-size: 13px; font-weight: 500;">${started_formatted}</div>
						</div>
					</div>

					<div style="display: flex; gap: 10px;">
						<button class="btn btn-sm btn-danger stop-timer-btn" data-task="${timer.task_name}" style="flex: 1;">
							<i class="fa fa-stop"></i> Stop Timer
						</button>
						<a href="/app/task/${timer.task_name}" class="btn btn-sm btn-default" style="flex: 1;">
							<i class="fa fa-external-link"></i> Open Task
						</a>
					</div>
				</div>
			`;
		});

		html += '</div>';
		container.html(html);

		// Start updating timers every second
		start_timer_updates(container);

		// Attach stop timer handlers
		container.find('.stop-timer-btn').on('click', function() {
			const task_name = $(this).data('task');
			stop_timer(task_name, page);
		});
	}

	// Function to update timer displays
	function start_timer_updates(container) {
		// Clear any existing interval
		if (page.timer_interval) {
			clearInterval(page.timer_interval);
		}

		page.timer_interval = setInterval(function() {
			container.find('.timer-display').each(function() {
				const $display = $(this);
				const started = new Date($display.data('started'));
				const now = new Date();
				const diff = Math.floor((now - started) / 1000); // seconds

				const hours = Math.floor(diff / 3600);
				const minutes = Math.floor((diff % 3600) / 60);
				const seconds = diff % 60;

				const formatted = `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
				$display.text(formatted);
			});
		}, 1000);
	}

	// Function to stop a timer
	function stop_timer(task_name, page) {
		frappe.confirm(
			__('Are you sure you want to stop the timer for this task?'),
			function() {
				frappe.call({
					method: 'solede_project.api.task_timer_api.stop_timer',
					args: {
						task_name: task_name
					},
					callback: function(r) {
						if (r.message && r.message.success) {
							frappe.show_alert({
								message: __('Timer stopped: {0} hours recorded', [r.message.hours.toFixed(2)]),
								indicator: 'green'
							}, 5);
							load_active_timers(page);
						}
					}
				});
			}
		);
	}

	// Initial load
	load_active_timers(page);

	// Cleanup on page unload
	$(wrapper).on('remove', function() {
		if (page.timer_interval) {
			clearInterval(page.timer_interval);
		}
	});
};
