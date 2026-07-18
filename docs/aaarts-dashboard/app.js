const state = {
	registry: null,
	selected: null,
	filter: "ALL",
	tab: "overview",
};
const $ = (selector) => document.querySelector(selector);
const esc = (value) =>
	String(value ?? "—").replace(
		/[&<>"']/g,
		(character) =>
			({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
				character
			],
	);
const pct = (value) =>
	Number.isFinite(Number(value)) ? `${(Number(value) * 100).toFixed(2)}%` : "—";
const num = (value) =>
	Number.isFinite(Number(value)) ? Number(value).toFixed(3) : "—";
const byId = (items = [], id) =>
	id == null
		? undefined
		: items.find((item) => item.stable_id === id || item.id === id);
const tag = (label, kind = label) =>
	'<span class="tag tag-' +
	String(kind).toLowerCase().replaceAll("_", "-") +
	'">' +
	esc(label) +
	"</span>";
const fact = (label, value) =>
	'<div class="fact"><label>' +
	esc(label) +
	"</label><div>" +
	value +
	"</div></div>";
const array = (value = []) => (value.length ? value.map(esc).join(" · ") : "—");
const requiredCollections = [
	"exploration_runs",
	"learning_events",
	"failure_constraints",
	"mutation_plans",
	"evolution_edges",
	"context_snapshots",
	"data_sources",
	"dataset_snapshots",
	"pit_assessments",
	"provenance_records",
	"data_quality_assessments",
	"hypotheses",
	"strategy_genomes",
	"strategy_versions",
	"implementation_variants",
	"protocol_snapshots",
	"research_runs",
	"evidence_artifacts",
	"gate_assessments",
	"factor_exposure_assessments",
	"trading_realism_assessments",
	"decision_records",
	"portfolio_candidates",
	"allocation_plans",
	"risk_budgets",
	"order_plans",
	"execution_runs",
	"performance_audits",
	"drift_events",
];
function assertRegistry(registry) {
	if (
		!registry ||
		registry.schema_version !== 1 ||
		registry.ontology_version !== "aaarts-ontology.v1"
	)
		throw new Error("Registry validation failed: ontology version mismatch");
	requiredCollections.forEach((key) => {
		if (!Array.isArray(registry[key]))
			throw new Error(`Registry validation failed: missing ${key}`);
		registry[key].forEach((item) => {
			[
				"stable_id",
				"created_at",
				"schema_version",
				"input_hash",
				"code_commit_sha",
			].forEach((field) => {
				if (typeof item[field] !== "string" || !item[field])
					throw new Error(
						`Registry validation failed: ${key} missing ${field}`,
					);
			});
		});
	});
	const states = ["CONFIRMED", "NOT_CONFIRMED", "CONTRADICTED", "UNVERIFIED"];
	const decisions = ["GO", "HOLD", "PIVOT"];
	const gates = ["PASS", "FAIL", "PARTIAL", "NOT_RUN", "UNVERIFIED"];
	registry.strategy_versions.forEach((item) => {
		if (
			!states.includes(item.evidence_state) ||
			!decisions.includes(item.lifecycle_decision)
		)
			throw new Error("Registry validation failed: invalid strategy state");
	});
	registry.gate_assessments.forEach((item) => {
		if (!gates.includes(item.status))
			throw new Error("Registry validation failed: invalid gate state");
	});
	registry.portfolio_candidates.forEach((item) => {
		const version = byId(registry.strategy_versions, item.strategy_version_id);
		if (item.eligibility === "ELIGIBLE" && version?.lifecycle_decision !== "GO")
			throw new Error("Registry validation failed: non-GO portfolio candidate");
	});
	return registry;
}
function activeVersions() {
	return state.registry.strategy_versions.filter(
		(item) => item.status === "ACTIVE",
	);
}
function allVersions() {
	return state.registry.strategy_versions;
}
function related(version) {
	const r = state.registry;
	const run =
		byId(r.research_runs, version.research_run_id) ||
		r.research_runs.find(
			(item) => item.strategy_version_id === version.stable_id,
		);
	const genome = byId(r.strategy_genomes, version.genome_id);
	const hypothesis = genome && byId(r.hypotheses, genome.hypothesis_id);
	const variant = r.implementation_variants.find(
		(item) => item.strategy_version_id === version.stable_id,
	);
	const evidence =
		run &&
		r.evidence_artifacts.find((item) => item.research_run_id === run.stable_id);
	const gates = run
		? r.gate_assessments.filter(
				(item) => item.research_run_id === run.stable_id,
			)
		: [];
	const decision = r.decision_records.find(
		(item) => item.strategy_version_id === version.stable_id,
	);
	const mutation = r.mutation_plans.filter(
		(item) => item.source_strategy_version_id === version.stable_id,
	);
	const learning = run
		? r.learning_events.filter((item) => item.research_run_id === run.stable_id)
		: [];
	const planned = r.strategy_versions.find(
		(item) => item.parent_strategy_version_id === version.stable_id,
	);
	const dataset = run && byId(r.dataset_snapshots, run.dataset_snapshot_id);
	const pit =
		dataset &&
		r.pit_assessments.find(
			(item) => item.dataset_snapshot_id === dataset.stable_id,
		);
	const provenance =
		run && byId(r.provenance_records, run.provenance_record_id);
	const context = run && byId(r.context_snapshots, run.context_snapshot_id);
	const source = dataset && byId(r.data_sources, dataset.data_source_id);
	const exposure =
		run &&
		r.factor_exposure_assessments.find(
			(item) => item.research_run_id === run.stable_id,
		);
	const realism =
		run &&
		r.trading_realism_assessments.find(
			(item) => item.research_run_id === run.stable_id,
		);
	const constraint =
		learning[0] &&
		r.failure_constraints.find(
			(item) => item.learning_event_id === learning[0].stable_id,
		);
	return {
		run,
		genome,
		hypothesis,
		variant,
		evidence,
		gates,
		decision,
		mutation,
		learning,
		planned,
		dataset,
		pit,
		provenance,
		context,
		source,
		exposure,
		realism,
		constraint,
	};
}
function renderMetrics() {
	const r = state.registry;
	const current = activeVersions();
	const gates = r.gate_assessments || [];
	const pass = gates.filter((item) => item.status === "PASS").length;
	const candidates = r.portfolio_candidates || [];
	$("#genomeCount").textContent = current.length;
	$("#notConfirmedCount").textContent = current.filter(
		(item) => item.evidence_state === "NOT_CONFIRMED",
	).length;
	$("#pivotCount").textContent = current.filter(
		(item) => item.lifecycle_decision === "PIVOT",
	).length;
	$("#gatePassRate").textContent =
		`${gates.length ? Math.round((pass / gates.length) * 100) : 0}%`;
	$("#tradeReadyCount").textContent = candidates.filter(
		(item) => item.eligibility === "ELIGIBLE",
	).length;
	$("#generatedAt").textContent = r.generated_at || "machine registry";
	$("#footerCount").textContent = current.length;
}
function renderUniverse() {
	const rows = allVersions().filter(
		(item) =>
			state.filter === "ALL" ||
			item.lifecycle_decision === state.filter ||
			item.evidence_state === state.filter,
	);
	$("#strategyList").innerHTML =
		rows
			.map((version) => {
				const x = related(version);
				const m = x.evidence?.gross || {};
				const n = x.evidence?.net || {};
				const late = x.evidence?.late_half_annualized_mean;
				const selected =
					state.selected === version.stable_id ? " selected" : "";
				const parent = version.parent_strategy_version_id || "ROOT";
				const gateCount = x.gates.length;
				const pass = x.gates.filter((item) => item.status === "PASS").length;
				const gateRate = gateCount
					? `${Math.round((pass / gateCount) * 100)}%`
					: "NOT_RUN";
				const dataEnd = x.dataset?.period_end || "NOT_RUN";
				const next = x.mutation[0]?.next_strategy_version_id || "—";
				const width = Math.min((Math.abs(Number(late) || 0) / 0.06) * 100, 100);
				return (
					'<button class="strategy' +
					selected +
					'" data-strategy="' +
					esc(version.stable_id) +
					'"><span><span class="strategy-title">' +
					esc(x.genome?.name || version.stable_id) +
					'</span><span class="strategy-id">' +
					esc(version.stable_id) +
					" · parent " +
					esc(parent) +
					'</span><span class="strategy-meta">' +
					esc(x.hypothesis?.title || "NOT_RUN") +
					"</span></span><span>" +
					tag(version.evidence_state) +
					"<br>" +
					tag(version.lifecycle_decision) +
					'</span><span class="metric-mini">' +
					pct(m.annualized_mean) +
					"<span>gross · net " +
					pct(n.annualized_mean) +
					"<br>late " +
					pct(late) +
					'</span><span class="bar"><i style="width:' +
					width +
					'%"></i></span></span><span class="strategy-meta">' +
					esc(x.variant?.implementation_type || "NOT_RUN") +
					" · gates " +
					gateRate +
					"<br>data " +
					esc(dataEnd) +
					'</span><span class="strategy-meta">next ' +
					esc(next) +
					"</span></button>"
				);
			})
			.join("") ||
		'<div style="padding:22px;color:var(--muted)">No strategies match this filter.</div>';
	document.querySelectorAll("[data-strategy]").forEach((button) => {
		button.addEventListener("click", () => {
			selectStrategy(button.dataset.strategy);
		});
	});
}
function renderDetail() {
	const version =
		byId(state.registry.strategy_versions, state.selected) ||
		activeVersions()[0];
	if (!version) return;
	state.selected = version.stable_id;
	const x = related(version);
	const r = state.registry;
	const h = byId(r.hypotheses, x.genome?.hypothesis_id) || {};
	const m = x.evidence?.gross || {};
	const n = x.evidence?.net || {};
	const decision = x.decision || {};
	$("#detailId").textContent = `${version.stable_id} · ${version.status}`;
	$("#detailTitle").textContent = x.genome?.name || version.stable_id;
	$("#detailTags").innerHTML =
		tag(version.evidence_state) +
		" " +
		tag(version.lifecycle_decision) +
		' <span class="strategy-meta" style="display:inline;margin-left:8px">verified ' +
		esc(version.last_verified_at || "NOT_RUN") +
		"</span>";
	$("#pane-overview").innerHTML =
		'<div class="fact-grid">' +
		fact("Version", esc(version.version)) +
		fact("Evidence state", tag(version.evidence_state)) +
		fact("Lifecycle decision", tag(version.lifecycle_decision)) +
		fact(
			"Implementation",
			esc(x.variant?.name || "—") +
				" · " +
				esc(x.variant?.implementation_type || "—"),
		) +
		fact("Research run", esc(x.run?.status || "NOT_RUN")) +
		fact("Last verified", esc(version.last_verified_at || "NOT_RUN")) +
		fact("Decision reason", esc(decision.reason || "—")) +
		fact("Parent strategy", esc(version.parent_strategy_version_id || "ROOT")) +
		"</div>";
	$("#pane-hypothesis").innerHTML =
		'<div class="fact-grid">' +
		fact("Claim", esc(h.claim || "—")) +
		fact(
			"Economic mechanism",
			esc(h.economic_mechanism || x.genome?.economic_mechanism || "—"),
		) +
		fact(
			"Primary source",
			esc((h.primary_source_ids || []).join(" · ") || "—"),
		) +
		fact("Hypothesis object", esc(h.stable_id || "—")) +
		"</div>";
	$("#pane-signal").innerHTML =
		'<div class="fact-grid">' +
		fact("Signal definition", esc(x.genome?.signal_definition)) +
		fact("Universe", esc(x.genome?.universe)) +
		fact("Allocation", esc(x.genome?.allocation)) +
		fact("Rebalance", esc(x.genome?.rebalance)) +
		fact("Variant definition", esc(x.variant?.definition)) +
		fact("Limitations", array(x.variant?.limitations || [])) +
		"</div>";
	$("#pane-evidence").innerHTML =
		'<div class="evidence-hero"><div class="evidence-number"><b>' +
		pct(m.annualized_mean) +
		'</b><span>full OOS annual mean</span></div><div class="evidence-number"><b>' +
		pct(x.evidence?.late_half_annualized_mean) +
		'</b><span>late-half annual mean</span></div><div class="evidence-number"><b>' +
		pct(n.annualized_mean) +
		'</b><span>25 bps net annual mean</span></div></div><p class="section-note">' +
		esc(x.evidence?.summary) +
		'</p><p style="margin-top:16px"><a href="./data/' +
		esc((x.evidence?.path || "").split("/").pop()) +
		'" target="_blank" rel="noreferrer">Open evidence artifact ↗</a></p>';
	$("#pane-gross-net").innerHTML =
		'<div class="fact-grid">' +
		fact("Gross annual mean", pct(m.annualized_mean)) +
		fact("Net annual mean", pct(n.annualized_mean)) +
		fact("Gross Sharpe", num(m.sharpe)) +
		fact("Net Sharpe", num(n.sharpe)) +
		fact("Gross CAGR", pct(m.cagr)) +
		fact("Net CAGR", pct(n.cagr)) +
		fact("Gross max drawdown", pct(m.max_drawdown)) +
		fact("Net max drawdown", pct(n.max_drawdown)) +
		"</div>";
	const exposure = x.exposure || {};
	const realism = x.realism || {};
	$("#pane-robustness").innerHTML =
		'<div class="fact-grid">' +
		fact("PIT", tag(x.pit?.status || "NOT_RUN")) +
		fact("Factor exposure", tag(exposure.status || "NOT_RUN")) +
		fact("Capacity", tag(realism.capacity || "NOT_RUN")) +
		fact("Liquidity", tag(realism.liquidity || "NOT_RUN")) +
		fact("Spread / slippage", tag(realism.spread_and_slippage || "NOT_RUN")) +
		fact("Cost model", esc(realism.cost_model || "—")) +
		fact("Exposure note", esc(exposure.note || "—")) +
		fact("Trading realism", tag(realism.status || "NOT_RUN")) +
		"</div>";
	const edge = (r.evolution_edges || []).find(
		(item) => item.from_strategy_version_id === version.stable_id,
	);
	$("#pane-lineage").innerHTML =
		'<div class="fact-grid">' +
		fact("Parent", esc(version.parent_strategy_version_id || "ROOT")) +
		fact("Next planned version", esc(x.planned?.stable_id || "NOT_CREATED")) +
		fact("Evolution relation", edge ? esc(edge.relation) : "—") +
		fact("Branch reason", esc(edge?.reason || "—")) +
		fact("Learning event", esc(x.learning[0]?.stable_id || "—")) +
		fact("Preserve branch", "Yes — no rejection deletion") +
		"</div>";
	$("#pane-provenance").innerHTML =
		'<div class="fact-grid">' +
		fact(
			"Dataset",
			`${esc(x.dataset?.stable_id || "—")} · ${esc(x.dataset?.path || "—")}`,
		) +
		fact("Dataset SHA-256", esc(x.dataset?.sha256 || "—")) +
		fact(
			"Source",
			x.source?.url
				? '<a href="' +
						esc(x.source.url) +
						'" target="_blank" rel="noreferrer">' +
						esc(x.source.name) +
						"</a>"
				: esc(x.source?.name || "—"),
		) +
		fact("Transformation", esc(x.provenance?.transformation || "—")) +
		fact("Environment", esc(x.context?.environment || "—")) +
		fact("Logic fingerprint", esc(x.run?.fingerprints?.logic || "—")) +
		fact(
			"Code commit",
			esc(x.run?.code_commit_sha || version.code_commit_sha || "—"),
		) +
		fact("Reproduction", esc(x.run?.reproduction_command || "—")) +
		"</div>";
	$("#pane-mutation").innerHTML = x.mutation.length
		? x.mutation
				.map(
					(item) =>
						'<div class="mutation"><b>' +
						esc(item.source_strategy_version_id) +
						" → " +
						esc(item.next_strategy_version_id) +
						"</b><p>" +
						esc(item.trigger) +
						"</p><p><strong>Changes:</strong> " +
						array(item.changes) +
						"</p><p><strong>Expected test:</strong> " +
						esc(item.expected_test) +
						"</p></div>",
				)
				.join("")
		: '<p class="section-note">No MutationPlan is linked to this version yet.</p>';
	renderGates(x);
	renderRunAudit(x);
	renderUniverse();
	renderTab();
}
function renderGates(x) {
	const m = x.evidence?.gross || {};
	$("#evidenceFullMean").textContent = pct(m.annualized_mean);
	$("#evidenceLateMean").textContent = pct(
		x.evidence?.late_half_annualized_mean,
	);
	$("#evidenceNetMean").textContent = pct(x.evidence?.net?.annualized_mean);
	$("#evidenceSummary").textContent = x.evidence?.summary || "—";
	$("#artifactLink").textContent = x.evidence?.path || "—";
	$("#artifactLink").href =
		`./data/${(x.evidence?.path || "").split("/").pop()}`;
	$("#gateList").innerHTML =
		x.gates
			.map(
				(gate) =>
					'<div class="gate-row"><span class="gate-name">' +
					esc(gate.gate) +
					'</span><span class="status status-' +
					gate.status.toLowerCase().replaceAll("_", "-") +
					'">' +
					esc(gate.status) +
					'</span><span class="gate-note">' +
					esc(gate.note) +
					"</span></div>",
			)
			.join("") || '<p class="section-note">No gate assessments.</p>';
}
function renderRunAudit(x) {
	const r = state.registry;
	const protocol =
		byId(r.protocol_snapshots, x.run?.protocol_snapshot_id) || {};
	const decision = x.decision || {};
	$("#runAudit").innerHTML =
		'<div class="fact-grid">' +
		fact(
			"ResearchRun",
			esc(x.run?.stable_id || "NOT_RUN") +
				" · " +
				esc(x.run?.status || "NOT_RUN"),
		) +
		fact("Input dataset", esc(x.dataset?.stable_id || "—")) +
		fact("PIT assessment", tag(x.pit?.status || "NOT_RUN")) +
		fact("Protocol", esc(protocol.name || protocol.stable_id || "—")) +
		fact("Protocol fingerprint", esc(protocol.logic_fingerprint || "—")) +
		fact(
			"Context / dependency hash",
			esc(x.context?.dependency_lock_hash || "—"),
		) +
		fact(
			"Environment fingerprint",
			esc(x.provenance?.environment_fingerprint || "—"),
		) +
		fact("Run fingerprints", esc(JSON.stringify(x.run?.fingerprints || {}))) +
		fact("Evidence artifact", esc(x.evidence?.stable_id || "—")) +
		fact(
			"Decision / evaluator",
			tag(decision.lifecycle_decision || "NOT_RUN") +
				" · " +
				esc(decision.deterministic_evaluator || "—"),
		) +
		fact(
			"LLM pass authority",
			esc(String(decision.llm_pass_authority ?? "—")),
		) +
		fact("Reproduction command", esc(x.run?.reproduction_command || "—")) +
		"</div>";
}
function renderEvolution() {
	const r = state.registry;
	$("#learningTimeline").innerHTML =
		"<h3>Learning events</h3>" +
		(r.learning_events || [])
			.slice(0, 8)
			.map(
				(event) =>
					'<div class="timeline-item"><strong>' +
					esc(event.trigger) +
					"</strong><p>" +
					esc(event.lesson) +
					"</p></div>",
			)
			.join("");
	$("#mutationList").innerHTML =
		"<h3>Mutation plans</h3>" +
		(r.mutation_plans || [])
			.slice(0, 8)
			.map(
				(item) =>
					'<div class="mutation"><b>' +
					esc(item.source_strategy_version_id) +
					" → " +
					esc(item.next_strategy_version_id) +
					"</b><p>" +
					array(item.changes) +
					"</p><p>" +
					tag(item.status, item.status === "PLANNED" ? "HOLD" : "GO") +
					"</p></div>",
			)
			.join("");
	$("#evolutionGraph").innerHTML =
		"<h3>Strategy lineage</h3>" +
			(r.evolution_edges || [])
				.map(
					(edge) =>
						'<div class="mutation"><b>' +
						esc(edge.from_strategy_version_id) +
						" → " +
						esc(edge.to_strategy_version_id) +
						"</b><p>" +
						esc(edge.reason) +
						"</p><p>" +
						tag(edge.relation, "HOLD") +
						" · learning " +
						esc(edge.learning_event_id) +
						"</p></div>",
				)
				.join("") || '<p class="section-note">No evolution edges.</p>';
}
function renderTab() {
	$(".tab.active")?.classList.remove("active");
	document
		.querySelector(`.tab[data-tab="${state.tab}"]`)
		?.classList.add("active");
	document.querySelectorAll(".detail-pane").forEach((pane) => {
		pane.classList.toggle("active", pane.id === `pane-${state.tab}`);
	});
}
function selectStrategy(id) {
	state.selected = id;
	renderDetail();
	document
		.querySelector("#detail")
		?.scrollIntoView({ behavior: "smooth", block: "start" });
}
function bind() {
	document.querySelectorAll(".filter").forEach((button) => {
		button.addEventListener("click", () => {
			state.filter = button.dataset.filter;
			document.querySelectorAll(".filter").forEach((item) => {
				item.classList.toggle("selected", item === button);
			});
			renderUniverse();
		});
	});
	document.querySelectorAll(".tab").forEach((button) => {
		button.addEventListener("click", () => {
			state.tab = button.dataset.tab;
			renderTab();
		});
	});
}
async function load() {
	const response = await fetch("./data/strategy_registry.json", {
		cache: "no-store",
	});
	if (!response.ok)
		throw new Error(`Strategy registry load failed: HTTP ${response.status}`);
	state.registry = assertRegistry(await response.json());
	state.selected = activeVersions()[0]?.stable_id;
	renderMetrics();
	renderDetail();
	renderEvolution();
	bind();
}
load().catch((error) => {
	const box = $("#loadError");
	box.hidden = false;
	box.textContent = error.message;
	console.error(error);
});
