(function () {
  "use strict";

  const HubApp = window.HubApp;
  if (!HubApp) return;
  let entries = [];
  let matches = [];
  let shown = 0;
  let body;
  let list;
  let status;
  let search;
  let file;
  let inPair;
  let table;
  let more;
  let empty;

  function text(tag, key, values, attrs) {
    return HubApp.el(tag, attrs || {}, HubApp.fmt(key, values));
  }
  function pairCount(record) {
    return HubApp.fmt(record.pair_count === 0 ? "C06.no_pairs"
      : record.pair_count === 1 ? "C06.one_pair" : "C06.n_pairs", { n: record.pair_count });
  }
  function mark() {
    if (!body) return;
    const selected = HubApp.state.selection;
    body.querySelectorAll("[data-record-id]").forEach(function (row) {
      const active = selected && selected.type === "record" && selected.id === row.dataset.recordId;
      row.classList.toggle("hub-row--selected", Boolean(active));
      if (active) row.setAttribute("aria-current", "true");
      else row.removeAttribute("aria-current");
    });
  }
  function row(record) {
    const item = HubApp.el("tr", {
      id: record.catalogue_link.slice(1), "data-record-id": record.id, class: "hub-catalogue-row"
    });
    const link = HubApp.el("a", { href: record.source_link, class: "hub-link" },
      HubApp.el("bdi", { class: "hub-mono" }, record.id));
    const title = HubApp.el("button", {
      type: "button", class: "hub-catalogue-title hub-link", "aria-label": HubApp.fmt("C07", { ID: record.id })
    }, record.title);
    title.addEventListener("click", function () { HubApp.select({ type: "record", id: record.id }, title); });
    item.addEventListener("click", function (event) {
      if (window.matchMedia("(min-width: 768px)").matches || event.target.closest("a, button")) return;
      HubApp.select({ type: "record", id: record.id }, title);
    });
    const idCell = HubApp.el("td", { class: "hub-catalogue-id" }, [link,
      HubApp.el("span", { class: "hub-catalogue-inline-count" }, pairCount(record))]);
    const titleCell = HubApp.el("td", { class: "hub-catalogue-name" }, title);
    const fileCell = HubApp.el("td", { class: "hub-catalogue-file" },
      HubApp.el("bdi", { class: "hub-mono" }, record.source_file));
    const pairCell = HubApp.el("td", { class: "hub-catalogue-pairs" }, pairCount(record));
    [idCell, titleCell, fileCell, pairCell].forEach(function (cell) { item.appendChild(cell); });
    return item;
  }
  function page() {
    const limit = Math.min(shown + HubApp.data.config.catalogue_page, matches.length);
    matches.slice(shown, limit).forEach(function (record) { body.appendChild(row(record)); });
    shown = limit;
    more.hidden = shown >= matches.length;
    status.textContent = HubApp.fmt("C05", { a: shown, b: matches.length });
    mark();
  }
  function update() {
    if (!body) return;
    const filters = HubApp.state.filters;
    const tokens = String(filters.query).trim().toLowerCase().split(/\s+/).filter(Boolean);
    search.value = filters.query;
    file.value = filters.file;
    inPair.value = filters.inPair;
    matches = entries.filter(function (entry) {
      return tokens.every(function (token) { return entry.text.includes(token); })
        && (filters.file === "all" || entry.record.source_file === filters.file)
        && (filters.inPair === "all" || (filters.inPair === "some"
          ? entry.record.pair_count > 0 : entry.record.pair_count === 0));
    }).map(function (entry) { return entry.record; });
    body.replaceChildren();
    shown = 0;
    table.hidden = !matches.length;
    empty.hidden = Boolean(matches.length);
    page();
  }
  function labelledSelect(id, label, options) {
    const select = HubApp.el("select", { id: id, class: "hub-field" });
    options.forEach(function (option) {
      select.appendChild(HubApp.el("option", { value: option[0] }, option[1]));
    });
    return { field: select, group: HubApp.el("div", { class: "hub-catalogue-control" },
      [text("label", label, {}, { for: id }), select]) };
  }
  function render(container) {
    entries = HubApp.data.records.map(function (record) {
      return { record: record, text: (record.id + " " + record.title + " " + record.text).toLowerCase() };
    }).sort(function (a, b) { return a.record.id < b.record.id ? -1 : a.record.id > b.record.id ? 1 : 0; });
    const controls = HubApp.el("div", { id: "catalogue-controls", class: "hub-catalogue-controls" });
    search = HubApp.el("input", { type: "search", id: "catalogue-search", class: "hub-field",
      placeholder: HubApp.fmt("C03.placeholder"), autocomplete: "off" });
    search.addEventListener("input", function () { HubApp.setFilter("query", search.value); });
    controls.appendChild(HubApp.el("div", { class: "hub-catalogue-search" }, [
      text("label", "C03.label", {}, { for: "catalogue-search" }), search
    ]));
    const files = Array.from(new Set(entries.map(function (entry) { return entry.record.source_file; }))).sort();
    const fileSelect = labelledSelect("catalogue-file", "C04.file.label",
      [["all", HubApp.fmt("C04.file.all")], ...files.map(function (name) { return [name, name]; })]);
    file = fileSelect.field;
    file.addEventListener("change", function () { HubApp.setFilter("file", file.value); });
    const pairSelect = labelledSelect("catalogue-in-pair", "C04.pair.label", [
      ["all", HubApp.fmt("C04.pair.any")], ["some", HubApp.fmt("C04.pair.some")],
      ["none", HubApp.fmt("C04.pair.none")]
    ]);
    inPair = pairSelect.field;
    inPair.addEventListener("change", function () { HubApp.setFilter("inPair", inPair.value); });
    status = HubApp.el("p", { id: "catalogue-status", "aria-live": "polite", tabindex: "-1" });
    controls.appendChild(fileSelect.group);
    controls.appendChild(pairSelect.group);
    controls.appendChild(status);
    table = HubApp.el("table", { class: "hub-catalogue-table" }, [
      text("caption", "C02", {}, { class: "hub-visually-hidden" }),
      HubApp.el("thead", {}, HubApp.el("tr", {}, ["id", "title", "file", "pairs"].map(function (key) {
        return text("th", "C06." + key, {}, { scope: "col", class: "hub-catalogue-" + (key === "title" ? "name" : key) });
      })))
    ]);
    body = HubApp.el("tbody");
    table.appendChild(body);
    more = text("button", "C10", {}, { id: "catalogue-more", class: "hub-button hub-button--quiet", type: "button" });
    more.addEventListener("click", function () { page(); if (more.hidden) status.focus(); });
    const clear = text("button", "C09.button", {}, { type: "button", class: "hub-button", id: "catalogue-clear" });
    clear.addEventListener("click", function () {
      HubApp.setFilter("query", ""); HubApp.setFilter("file", "all"); HubApp.setFilter("inPair", "all");
      search.focus();
    });
    empty = HubApp.el("div", { class: "hub-catalogue-empty" }, [text("h2", "C08"), text("p", "C09.body"), clear]);
    list = HubApp.el("div", { id: "catalogue-list" }, [table, empty, more]);
    container.replaceChildren(text("h2", "C01", {}, { "data-view-heading": "" }), text("p", "C02"), controls, list);
    update();
  }
  HubApp.registerView("catalogue", {
    render: render,
    onEvent: function (name) {
      if (name === "filter") update();
      else if (name === "select" || name === "clear") mark();
    }
  });
})();
