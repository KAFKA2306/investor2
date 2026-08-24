const SECTION_LABELS = {
  results: "Results",
  research: "Research",
  contracts: "Contracts",
  data: "Data",
  generated: "Generated",
  api: "API",
};

const state = {
  manifest: null,
  artifacts: [],
  filtered: [],
  selectedPath: null,
};

const $ = (id) => document.getElementById(id);

function formatBytes(bytes) {
  if (!Number.isFinite(bytes)) return "—";
  const units = ["B", "KiB", "MiB", "GiB"];
  let value = bytes;
  let unit = units[0];
  for (let i = 1; i < units.length && value >= 1024; i += 1) {
    value /= 1024;
    unit = units[i];
  }
  return `${value >= 10 || unit === "B" ? value.toFixed(0) : value.toFixed(1)} ${unit}`;
}

function resetSelect(select, values, labelFor = (value) => value) {
  const previous = select.value;
  select.replaceChildren();
  const all = document.createElement("option");
  all.value = "";
  all.textContent = "All";
  select.append(all);
  for (const value of values) {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = labelFor(value);
    select.append(option);
  }
  if (values.includes(previous)) select.value = previous;
}

function artifactSearchText(item) {
  return `${item.path} ${item.module} ${item.section} ${item.category} ${item.viewer} ${item.media_type}`.toLowerCase();
}

function refreshModuleFilter() {
  const section = $("section-filter").value;
  const modules = [...new Set(
    state.artifacts
      .filter((item) => !section || item.section === section)
      .map((item) => item.module),
  )].sort((a, b) => a.localeCompare(b));
  resetSelect($("module-filter"), modules);
}

function applyFilters() {
  const query = $("search").value.trim().toLowerCase();
  const section = $("section-filter").value;
  const moduleName = $("module-filter").value;
  const viewer = $("viewer-filter").value;

  state.filtered = state.artifacts.filter(
    (item) =>
      (!query || artifactSearchText(item).includes(query)) &&
      (!section || item.section === section) &&
      (!moduleName || item.module === moduleName) &&
      (!viewer || item.viewer === viewer),
  );
  renderCatalog();
}

function createArtifactCard(item) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = "artifact-card";
  button.setAttribute("role", "listitem");
  button.setAttribute("aria-current", String(item.path === state.selectedPath));
  button.addEventListener("click", () => selectArtifact(item.path));

  const path = document.createElement("span");
  path.className = "artifact-path";
  path.textContent = item.path;

  const sub = document.createElement("span");
  sub.className = "artifact-sub";
  for (const text of [
    item.viewer,
    formatBytes(item.size_bytes),
    item.local_url ? "mirrored" : "source-only",
  ]) {
    const badge = document.createElement("span");
    badge.className = "badge";
    badge.textContent = text;
    sub.append(badge);
  }

  button.append(path, sub);
  return button;
}

function renderCatalog() {
  const list = $("artifact-list");
  list.replaceChildren();
  $("visible-count").textContent = state.filtered.length.toLocaleString();

  let currentGroup = null;
  let groupBody = null;
  for (const item of state.filtered) {
    const groupKey = `${item.section}\u0000${item.module}`;
    if (groupKey !== currentGroup) {
      currentGroup = groupKey;
      const group = document.createElement("section");
      group.className = "artifact-group";
      const heading = document.createElement("div");
      heading.className = "artifact-group-heading";
      const sectionLabel = document.createElement("span");
      sectionLabel.className = "artifact-group-section";
      sectionLabel.textContent = SECTION_LABELS[item.section] || item.section;
      const moduleLabel = document.createElement("strong");
      moduleLabel.textContent = item.module;
      heading.append(sectionLabel, moduleLabel);
      groupBody = document.createElement("div");
      group.append(heading, groupBody);
      list.append(group);
    }
    groupBody.append(createArtifactCard(item));
  }
}

function parseDelimited(text, delimiter) {
  const rows = [];
  let row = [];
  let cell = "";
  let quoted = false;

  for (let i = 0; i < text.length; i += 1) {
    const char = text[i];
    if (quoted) {
      if (char === '"') {
        if (text[i + 1] === '"') {
          cell += '"';
          i += 1;
        } else {
          quoted = false;
        }
      } else {
        cell += char;
      }
    } else if (char === '"') {
      quoted = true;
    } else if (char === delimiter) {
      row.push(cell);
      cell = "";
    } else if (char === "\n") {
      row.push(cell.replace(/\r$/, ""));
      rows.push(row);
      row = [];
      cell = "";
    } else {
      cell += char;
    }
  }
  if (quoted) throw new Error("unterminated quoted field in delimited artifact");
  if (cell.length || row.length) {
    row.push(cell.replace(/\r$/, ""));
    rows.push(row);
  }
  return rows;
}

function renderTable(rows, target) {
  const maxRows = 200;
  const maxColumns = 40;
  const visible = rows.slice(0, maxRows);
  const wrap = document.createElement("div");
  wrap.className = "table-wrap";
  const table = document.createElement("table");

  if (visible.length) {
    const thead = document.createElement("thead");
    const headerRow = document.createElement("tr");
    for (const value of visible[0].slice(0, maxColumns)) {
      const th = document.createElement("th");
      th.textContent = value;
      headerRow.append(th);
    }
    thead.append(headerRow);
    table.append(thead);

    const tbody = document.createElement("tbody");
    for (const values of visible.slice(1)) {
      const tr = document.createElement("tr");
      for (const value of values.slice(0, maxColumns)) {
        const td = document.createElement("td");
        td.textContent = value;
        tr.append(td);
      }
      tbody.append(tr);
    }
    table.append(tbody);
  }

  wrap.append(table);
  target.append(wrap);
  if (
    rows.length > maxRows ||
    rows.some((values) => values.length > maxColumns)
  ) {
    const note = document.createElement("p");
    note.className = "notice";
    note.textContent = `Preview limited to ${maxRows} rows × ${maxColumns} columns. Use Raw for the complete file.`;
    target.append(note);
  }
}

async function renderArtifact(item) {
  const target = $("render-target");
  target.replaceChildren();
  const url = item.local_url || item.raw_url;

  if (item.viewer === "image") {
    const image = document.createElement("img");
    image.src = url;
    image.alt = item.name;
    target.append(image);
    return;
  }

  if (item.viewer === "html" || item.viewer === "pdf") {
    const frame = document.createElement("iframe");
    frame.src = url;
    frame.title = item.name;
    if (item.viewer === "html") frame.setAttribute("sandbox", "");
    target.append(frame);
    return;
  }

  if (item.viewer === "download") {
    const notice = document.createElement("p");
    notice.className = "notice";
    notice.textContent = item.local_url
      ? "No inline renderer is defined for this file type. Open the mirrored file or exact GitHub source."
      : "This file is source-only because it exceeds the Pages mirror threshold or is not browser-renderable. Open the exact GitHub revision.";
    target.append(notice);
    return;
  }

  const response = await fetch(url);
  if (!response.ok)
    throw new Error(`HTTP ${response.status} while loading ${item.path}`);
  const text = await response.text();

  if (item.viewer === "json") {
    const pre = document.createElement("pre");
    pre.textContent = JSON.stringify(JSON.parse(text), null, 2);
    target.append(pre);
    return;
  }

  if (item.viewer === "table") {
    renderTable(
      parseDelimited(text, item.extension === ".tsv" ? "\t" : ","),
      target,
    );
    return;
  }

  const pre = document.createElement("pre");
  pre.textContent = text;
  target.append(pre);
}

async function selectArtifact(path) {
  const item = state.artifacts.find((artifact) => artifact.path === path);
  if (!item) return;
  state.selectedPath = path;
  renderCatalog();

  $("viewer-empty").hidden = true;
  $("viewer-content").hidden = false;
  $("artifact-module").textContent =
    `${SECTION_LABELS[item.section] || item.section} · ${item.module} · ${item.viewer}`;
  $("artifact-title").textContent = item.path;
  $("artifact-meta").textContent =
    `${item.media_type} · ${formatBytes(item.size_bytes)} · ${item.local_url ? "mirrored" : "source-only"}`;
  $("source-link").href = item.source_url;
  $("raw-link").href = item.local_url || item.raw_url;
  $("raw-link").textContent = item.local_url
    ? "Open mirrored file"
    : "Raw source";

  const params = new URLSearchParams(window.location.search);
  params.set("path", item.path);
  history.replaceState(
    null,
    "",
    `${window.location.pathname}?${params.toString()}`,
  );

  try {
    await renderArtifact(item);
  } catch (error) {
    const target = $("render-target");
    target.replaceChildren();
    const message = document.createElement("p");
    message.className = "notice error";
    message.textContent =
      error instanceof Error ? error.message : String(error);
    target.append(message);
  }
}

async function init() {
  const response = await fetch("manifest.json", { cache: "no-store" });
  if (!response.ok) throw new Error(`manifest HTTP ${response.status}`);
  const manifest = await response.json();
  if (!Array.isArray(manifest.section_order))
    throw new Error("manifest is missing canonical section_order");
  state.manifest = manifest;
  state.artifacts = [...manifest.artifacts];

  $("artifact-count").textContent = manifest.totals.artifacts.toLocaleString();
  $("local-count").textContent = manifest.totals.local_files.toLocaleString();
  $("source-count").textContent =
    manifest.totals.source_only_files.toLocaleString();
  $("total-size").textContent = formatBytes(manifest.totals.bytes);
  $("roots").textContent = `Roots: ${manifest.content_roots.join(", ")}`;

  const revision = manifest.revision;
  $("revision-link").textContent = revision.slice(0, 12);
  $("revision-link").href =
    `https://github.com/${manifest.repository}/commit/${revision}`;

  resetSelect(
    $("section-filter"),
    manifest.section_order.filter((section) => manifest.totals.sections?.[section] > 0),
    (section) => SECTION_LABELS[section] || section,
  );
  if (manifest.totals.sections?.results > 0) {
    $("section-filter").value = "results";
  }
  refreshModuleFilter();
  resetSelect(
    $("viewer-filter"),
    [...new Set(state.artifacts.map((item) => item.viewer))].sort((a, b) => a.localeCompare(b)),
  );

  $("search").addEventListener("input", applyFilters);
  $("module-filter").addEventListener("change", applyFilters);
  $("viewer-filter").addEventListener("change", applyFilters);
  $("section-filter").addEventListener("change", () => {
    refreshModuleFilter();
    applyFilters();
  });

  applyFilters();
  const requestedPath = new URLSearchParams(window.location.search).get("path");
  if (
    requestedPath &&
    state.artifacts.some((item) => item.path === requestedPath)
  ) {
    const requested = state.artifacts.find((item) => item.path === requestedPath);
    $("section-filter").value = requested.section;
    refreshModuleFilter();
    applyFilters();
    await selectArtifact(requestedPath);
  }
}

init().catch((error) => {
  const empty = $("viewer-empty");
  empty.replaceChildren();
  const heading = document.createElement("h2");
  heading.textContent = "Evidence browser failed to initialize";
  const message = document.createElement("p");
  message.className = "error";
  message.textContent = error instanceof Error ? error.message : String(error);
  empty.append(heading, message);
});