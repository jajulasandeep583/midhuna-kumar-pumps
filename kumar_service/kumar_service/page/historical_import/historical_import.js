// Bringing the old spreadsheet in. Three steps in the order they must happen:
// download the template, check the file, then import it. The check step is not
// optional in the UI on purpose - an import that has not been read back first
// is how a plant ends up with 4,000 wrong warranty dates.

frappe.pages["historical-import"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Historical Serial Import"),
		single_column: true,
	});

	const state = { file_url: null, checked: false };

	$(wrapper).find(".layout-main-section").append(`
		<div class="ki-wrap">
			<p class="ki-lead">${__(
				"Load pumps that were built and sold before this system went live. Every row becomes a Serial No; every row that carries a sale date also becomes a submitted registration, with the warranty already running."
			)}</p>

			<div class="ki-step">
				<div class="ki-num">1</div>
				<div class="ki-body">
					<div class="ki-title">${__("Get the template")}</div>
					<div class="ki-sub">${__(
						"A CSV with the right columns and two worked examples taken from your own masters. Delete the examples before you upload."
					)}</div>
					<button class="btn btn-default btn-sm ki-template">${__("Download CSV template")}</button>
				</div>
			</div>

			<div class="ki-step">
				<div class="ki-num">2</div>
				<div class="ki-body">
					<div class="ki-title">${__("Check the file")}</div>
					<div class="ki-sub">${__(
						"Reads the file back and reports every problem, row by row. Nothing is written."
					)}</div>
					<button class="btn btn-default btn-sm ki-pick">${__("Choose file and check")}</button>
					<span class="ki-file text-muted"></span>
				</div>
			</div>

			<div class="ki-step">
				<div class="ki-num">3</div>
				<div class="ki-body">
					<div class="ki-title">${__("Import")}</div>
					<div class="ki-sub">${__(
						"Only the rows that passed the check are written. Re-running is safe - a serial that already exists is left alone."
					)}</div>
					<button class="btn btn-primary btn-sm ki-import" disabled>${__("Import now")}</button>
				</div>
			</div>

			<div class="ki-out"></div>
		</div>
		<style>
			.ki-wrap { max-width: 900px; margin: 0 auto; padding: 6px 0 40px; }
			.ki-lead { color: var(--text-muted); margin-bottom: 22px; max-width: 720px; }
			.ki-step { display:flex; gap:14px; padding:16px 18px; margin-bottom:12px;
					   border:1px solid var(--border-color); border-radius:12px;
					   background: var(--fg-color); }
			.ki-num { flex:0 0 30px; height:30px; border-radius:50%;
					  background: var(--control-bg); display:flex; align-items:center;
					  justify-content:center; font-weight:700; }
			.ki-title { font-weight:700; margin-bottom:3px; }
			.ki-sub { color: var(--text-muted); font-size:13px; margin-bottom:10px; max-width:660px; }
			.ki-file { margin-left:10px; font-size:12px; }
			.ki-out { margin-top:18px; }
			.ki-tiles { display:grid; grid-template-columns:repeat(auto-fit,minmax(140px,1fr));
						gap:10px; margin-bottom:16px; }
			.ki-tile { border:1px solid var(--border-color); border-radius:10px; padding:12px 14px; }
			.ki-tile .n { font-size:24px; font-weight:700; }
			.ki-tile .l { font-size:11px; text-transform:uppercase; letter-spacing:0.6px;
						  color: var(--text-muted); margin-top:2px; }
			.ki-bad .n { color: var(--red-500); }
			.ki-good .n { color: var(--green-600); }
			.ki-prob { border:1px solid var(--border-color); border-radius:10px; overflow:hidden; }
			.ki-prob table { width:100%; border-collapse:collapse; font-size:13px; }
			.ki-prob th, .ki-prob td { padding:8px 12px; text-align:left;
									   border-bottom:1px solid var(--border-color); }
			.ki-prob th { background: var(--control-bg); font-size:11px; text-transform:uppercase;
						  letter-spacing:0.6px; color: var(--text-muted); }
		</style>
	`);

	const $out = $(wrapper).find(".ki-out");

	function tiles(items) {
		return `<div class="ki-tiles">${items
			.map(
				(t) =>
					`<div class="ki-tile ${t.cls || ""}"><div class="n">${t.n}</div><div class="l">${
						t.l
					}</div></div>`
			)
			.join("")}</div>`;
	}

	function problems(list) {
		if (!list || !list.length) return "";
		const rows = list
			.map(
				(p) =>
					`<tr><td>${p.row}</td><td>${frappe.utils.escape_html(
						p.serial_no || ""
					)}</td><td>${p.problems.map(frappe.utils.escape_html).join("<br>")}</td></tr>`
			)
			.join("");
		return `<div class="ki-prob"><table>
			<thead><tr><th>${__("Row")}</th><th>${__("Serial No")}</th><th>${__(
			"What is wrong"
		)}</th></tr></thead>
			<tbody>${rows}</tbody></table></div>`;
	}

	$(wrapper).find(".ki-template").on("click", () => {
		window.open("/api/method/kumar_service.migration.template", "_blank");
	});

	$(wrapper).find(".ki-pick").on("click", () => {
		new frappe.ui.FileUploader({
			as_dataurl: false,
			allow_multiple: false,
			restrictions: { allowed_file_types: [".csv", "text/csv"] },
			on_success: (file) => {
				state.file_url = file.file_url;
				state.checked = false;
				$(wrapper).find(".ki-file").text(file.file_name);
				$(wrapper).find(".ki-import").prop("disabled", true);
				check();
			},
		});
	});

	function check() {
		$out.html(`<div class="text-muted">${__("Checking...")}</div>`);
		frappe.call({
			method: "kumar_service.migration.import_file",
			args: { file_url: state.file_url, dry: 1 },
			callback: (r) => {
				const d = r.message || {};
				state.checked = d.errors === 0 && d.rows > 0;
				$(wrapper).find(".ki-import").prop("disabled", !state.checked);
				$out.html(
					tiles([
						{ n: d.rows || 0, l: __("Rows read") },
						{ n: d.ok || 0, l: __("Ready"), cls: "ki-good" },
						{ n: d.errors || 0, l: __("With problems"), cls: d.errors ? "ki-bad" : "" },
						{ n: d.serials || 0, l: __("New serials") },
						{ n: d.registrations || 0, l: __("New registrations") },
						{ n: d.skipped || 0, l: __("Already on file") },
					]) + problems(d.problems)
				);
			},
		});
	}

	$(wrapper).find(".ki-import").on("click", () => {
		frappe.confirm(
			__("Import this file? Registrations are submitted, so they can only be cancelled afterwards, never deleted."),
			() => {
				$out.html(`<div class="text-muted">${__("Importing...")}</div>`);
				frappe.call({
					method: "kumar_service.migration.import_file",
					args: { file_url: state.file_url, dry: 0 },
					callback: (r) => {
						const d = r.message || {};
						if (d.queued) {
							$out.html(
								`<div class="ki-prob" style="padding:14px">${__(
									"{0} rows queued. They are being written in the background - reload this page in a few minutes and run the reconciliation report.",
									[d.rows]
								)}</div>`
							);
							return;
						}
						$out.html(
							tiles([
								{ n: d.serials || 0, l: __("Serials created"), cls: "ki-good" },
								{ n: d.registrations || 0, l: __("Registrations"), cls: "ki-good" },
								{ n: d.skipped || 0, l: __("Already on file") },
								{ n: d.failed || 0, l: __("Failed"), cls: d.failed ? "ki-bad" : "" },
							]) +
								problems(d.problems) +
								`<p style="margin-top:16px"><a href="/app/query-report/Stock vs Registration Reconciliation">${__(
									"Open the reconciliation report to see what is still unaccounted for"
								)}</a></p>`
						);
						$(wrapper).find(".ki-import").prop("disabled", true);
					},
				});
			}
		);
	});
};
