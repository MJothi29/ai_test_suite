frappe.pages['ai-test-runner'].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'AI Test Runner',
		single_column: true,
	});

	new AITestRunner(page);
};

class AITestRunner {
	constructor(page) {
		this.page = page;
		this.make_controls();
		this.make_layout();
		this.load_history();
	}

	make_controls() {
		this.module_field = this.page.add_field({
			fieldname: 'module',
			label: 'Module',
			fieldtype: 'Link',
			options: 'Module Def',
			change: () => this.workflow_field.set_value(''),
		});

		this.workflow_field = this.page.add_field({
			fieldname: 'workflow',
			label: 'Test Workflow',
			fieldtype: 'Link',
			options: 'Test Workflow',
			get_query: () => ({
				filters: this.module_field.get_value()
					? { module: this.module_field.get_value(), disabled: 0 }
					: { disabled: 0 },
			}),
		});

		// NOTE: 'MultiCheck' is not supported via page.add_field() in this
		// Frappe version (it crashed with "make_input is not a function").
		// Using three plain Check fields instead - simpler and works everywhere.
		this.level_fields = {};
		['Functional', 'UI', 'Technical'].forEach((level) => {
			this.level_fields[level] = this.page.add_field({
				fieldname: `level_${level.toLowerCase()}`,
				label: level,
				fieldtype: 'Check',
				default: 1,
			});
		});

		this.page.set_primary_action(__('Run'), () => this.run_test(), 'play');
	}

	make_layout() {
		// IMPORTANT: append a new wrapper rather than replacing page.main's
		// innerHTML - page.add_field() inserts the Module/Workflow/Level
		// controls directly into page.main, and calling page.main.html(...)
		// here would wipe them out.
		const $wrapper = $(`
			<div class="ai-test-runner" style="margin-top:15px;">
				<div class="text-muted small">
					Select a Module-wise or DocType-to-DocType Test Workflow, tick which
					levels to run (Functional / UI / Technical), then click Run. Progress
					streams live below.
				</div>
				<div class="progress-log" style="max-height:320px;overflow-y:auto;
					font-family:monospace;font-size:12px;background:#f8f8f8;
					padding:10px;border-radius:4px;margin-top:15px;border:1px solid #ddd;"></div>
				<div class="summary-cards" style="display:flex;gap:15px;margin-top:15px;"></div>
				<div class="report-actions" style="margin-top:10px;"></div>
				<hr>
				<div class="history-table"></div>
			</div>
		`).appendTo(this.page.main);

		this.log_el = $wrapper.find('.progress-log');
		this.summary_el = $wrapper.find('.summary-cards');
		this.actions_el = $wrapper.find('.report-actions');
		this.history_el = $wrapper.find('.history-table');
	}

	get_selected_levels() {
		return Object.keys(this.level_fields).filter((level) =>
			this.level_fields[level].get_value()
		);
	}

	run_test() {
		const workflow = this.workflow_field.get_value();
		const levels = this.get_selected_levels();

		if (!workflow) {
			frappe.msgprint(__('Please select a Test Workflow'));
			return;
		}
		if (!levels.length) {
			frappe.msgprint(__('Please tick at least one test level'));
			return;
		}

		this.log_el.empty();
		this.summary_el.empty();
		this.actions_el.empty();

		frappe.call({
			method: 'ai_test_suite.ai_test_suite.test_engine.runner.start_test_execution',
			args: { workflow, levels: levels.join(',') },
			callback: (r) => {
				this.current_execution = r.message;
				this.log(`<b>Execution ${r.message} started...</b>`);
				this.listen();
			},
			error: (r) => {
				this.log(`<span style="color:red">Failed to start execution - check browser console / server error log.</span>`);
			},
		});
	}

	listen() {
		if (this._bound) return;
		this._bound = true;

		frappe.realtime.on('ai_test_progress', (data) => {
			if (data.execution !== this.current_execution) return;

			if (data.event === 'progress') {
				const d = data.data;
				const color = { Pass: 'green', Fail: 'red', Warning: 'orange', Skipped: 'gray' }[d.status] || 'black';
				this.log(
					`[${d.test_level}] ${d.step_name} (${d.reference_doctype}) - ` +
					`<span style="color:${color};font-weight:bold;">${d.status}</span>: ${frappe.utils.escape_html(d.message || '')}`
				);
			}

			if (data.event === 'completed') {
				this.show_summary(data.data);
				this.show_actions();
				this.load_history();
			}
		});
	}

	log(html) {
		this.log_el.append(`<div>${html}</div>`);
		this.log_el.scrollTop(this.log_el[0].scrollHeight);
	}

	show_summary(data) {
		const card = (label, value, cls) => `
			<div class="card ${cls}" style="flex:1;padding:10px;border:1px solid #ddd;border-radius:4px;text-align:center;">
				<div style="font-size:11px;text-transform:uppercase;color:#888;">${label}</div>
				<div style="font-size:22px;font-weight:bold;">${value}</div>
			</div>`;
		this.summary_el.html(
			card('Total', data.total, '') +
			card('Passed', data.passed, 'text-success') +
			card('Failed', data.failed, 'text-danger') +
			card('Warnings', data.warnings, 'text-warning')
		);
	}

	show_actions() {
		this.actions_el.html(`
			<button class="btn btn-sm btn-default" id="export-pdf">${__('Export PDF')}</button>
			<button class="btn btn-sm btn-default" id="export-excel">${__('Export Excel')}</button>
			<button class="btn btn-sm btn-default" id="view-doc">${__('Open Execution Record')}</button>
		`);
		this.actions_el.find('#export-pdf').on('click', () => this.export('PDF'));
		this.actions_el.find('#export-excel').on('click', () => this.export('Excel'));
		this.actions_el.find('#view-doc').on('click', () => {
			frappe.set_route('Form', 'Test Execution', this.current_execution);
		});
	}

	export(format) {
		frappe.call({
			method: 'ai_test_suite.ai_test_suite.reports_export.export.export_report',
			args: { execution: this.current_execution, format },
			callback: (r) => {
				if (r.message) window.open(r.message);
			},
		});
	}

	load_history() {
		frappe.call({
			method: 'ai_test_suite.ai_test_suite.api.get_execution_history',
			callback: (r) => {
				const rows = r.message || [];
				let html = `<h5>${__('Execution History')}</h5>
					<table class="table table-bordered table-sm">
					<tr>
						<th>${__('Execution')}</th><th>${__('Workflow')}</th><th>${__('Status')}</th>
						<th>${__('Total')}</th><th>${__('Passed')}</th><th>${__('Failed')}</th>
						<th>${__('Warnings')}</th><th>${__('Started')}</th>
					</tr>`;
				rows.forEach((row) => {
					html += `<tr>
						<td><a href="/app/test-execution/${row.name}">${row.name}</a></td>
						<td>${row.workflow || ''}</td>
						<td>${row.status || ''}</td>
						<td>${row.total_tests || 0}</td>
						<td>${row.passed || 0}</td>
						<td>${row.failed || 0}</td>
						<td>${row.warnings || 0}</td>
						<td>${row.start_time || ''}</td>
					</tr>`;
				});
				html += '</table>';
				this.history_el.html(html);
			},
		});
	}
}