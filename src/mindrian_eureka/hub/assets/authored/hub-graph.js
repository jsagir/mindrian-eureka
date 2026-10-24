(function () {
  "use strict";

  // Deviation from the book graph guide (GUIDE lines 17 to 27): the guide draws bridge links thick yellow with red particles. The hub draws every pair in cobalt, width 1.6 for pairs that cross neighborhoods, and draws no particles. Reason: D-21 no ambient motion (rule 19), and yellow alone is 1.54:1 on paper. Status: deviation, not book-derived; proposed segment.
  const HubApp = window.HubApp;
  if (!HubApp) return;
  const engines = ["unusual_pairs", "wording_and_meaning"];
  const NS = "http://www.w3.org/2000/svg";
  // Hook contract for plan 18
  const G = { mode: "empty", stageEl: null, instance: null, stage: null };
  let stageButtons;
  let pairBlock;
  let pairList;
  let pairStatus;
  let pairs = [];
  let shown = 25;
  let diagram = null;
  let guideToggle;
  let guideBody;
  let diagramObserver;
  let lastWidth = 0;
  function text(tag, key, values, attrs) {
    return HubApp.el(tag, attrs || {}, HubApp.fmt(key, values));
  }
  function button(key, attrs) {
    return text("button", key, {}, { type: "button", class: "hub-button hub-button--quiet", ...attrs });
  }
  function showStageButtons() { stageButtons.hidden = false; }
  function showFallback() {
    G.mode = "fallback";
    G.instance = null;
    G.stage = null;
    stageButtons.hidden = true;
    G.stageEl.classList.remove("hub-graph-stage--3d");
    G.stageEl.replaceChildren(text("p", "Gr12", {}, { id: "graph-fallback" }), pairBlock);
  }
  function startStage(stageEl) { showFallback(); }
  Object.defineProperty(HubApp, "graphView", { value: Object.freeze({
    get mode() { return G.mode; },
    get instance() { return G.instance; },
    flyTo: function (id) { return G.stage ? G.stage.flyTo(id) : false; }
  }), writable: false });
  function marks() {
    const sel = HubApp.state.selection;
    const record = sel && sel.type === "record" ? HubApp.index.records.get(sel.id) : null;
    if (diagram) {
      diagram.querySelectorAll("[data-diagram-record]").forEach(function (node) {
        const value = HubApp.index.records.get(node.dataset.diagramRecord);
        node.classList.toggle("is-selected", Boolean(record && value.id === record.id));
        node.classList.toggle("is-dimmed", Boolean(record && value.hood !== record.hood));
      });
    }
    if (pairList) pairList.querySelectorAll("[data-pair-key]").forEach(function (row) {
      const selected = Boolean(sel && sel.type === "pair" && sel.key === row.dataset.pairKey);
      row.classList.toggle("hub-row--selected", selected);
      if (selected) row.setAttribute("aria-current", "true");
      else row.removeAttribute("aria-current");
    });
  }
  function pairRow(pair) {
    const item = HubApp.el("li", { class: "hub-row hub-graph-pair", "data-pair-key": pair.key });
    item.appendChild(text("p", "B08.rank", { n: pair.rank }, { class: "hub-mono" }));
    item.appendChild(HubApp.el("p", {}, HubApp.data.engines[pair.engine].short_name));
    item.appendChild(text("span", "P06.proposed", {}, { class: "hub-role hub-role--proposed" }));
    item.appendChild(HubApp.el("span", { class: "hub-chip" }, pair.label));
    [pair.left, pair.right].forEach(function (side) {
      item.appendChild(HubApp.el("div", { class: "hub-graph-source" }, [
        HubApp.el("a", { href: side.source_link, class: "hub-link hub-mono",
          "aria-label": HubApp.fmt("B08.source_name", { ID: side.id, title: side.title }) },
          HubApp.el("bdi", {}, side.id)), HubApp.el("p", {}, side.title)
      ]));
      const record = HubApp.index.records.get(side.id);
      if (pair.flag_identical && record.identical_to.length) {
        item.appendChild(text("p", "P09.identical", { ID: record.identical_to[0] }, { class: "hub-flag" }));
      }
      if (pair.flag_no_text && record.no_text) item.appendChild(text("p", "P09.no_text", {}, { class: "hub-flag" }));
    });
    item.appendChild(text("span", "P06.inferred", {}, { class: "hub-role hub-role--inferred" }));
    item.appendChild(text("p", "B08.wording", { x: pair.wording_text }));
    item.appendChild(text("p", "B08.meaning", { y: pair.meaning_text }));
    item.appendChild(text("p", "B08.rank_score", { z: pair.rank_score_text }));
    item.appendChild(HubApp.el("p", {}, pair.reading));
    const read = button("B08.read");
    read.addEventListener("click", function () { HubApp.select({ type: "pair", key: pair.key }, read); });
    item.appendChild(read);
    return item;
  }
  function listPairs() {
    pairList.replaceChildren();
    pairs.slice(0, shown).forEach(function (pair) { pairList.appendChild(pairRow(pair)); });
    const old = pairBlock.querySelector("#graph-more");
    if (old) old.remove();
    if (shown < pairs.length) {
      const more = button("B09.more", { id: "graph-more" });
      more.addEventListener("click", function () {
        shown += HubApp.data.config.bank_page;
        listPairs();
        const target = document.getElementById("graph-more") || pairStatus;
        target.focus();
      });
      pairBlock.appendChild(more);
    }
    pairStatus.textContent = HubApp.fmt("B09.status", { a: Math.min(shown, pairs.length), b: pairs.length });
    marks();
  }
  function svg(tag, attrs, value) {
    const node = document.createElementNS(NS, tag);
    Object.entries(attrs || {}).forEach(function (entry) { node.setAttribute(entry[0], String(entry[1])); });
    if (value !== undefined) node.textContent = value;
    return node;
  }
  function drawDiagram() {
    if (!diagram) return;
    const width = Math.max(240, Math.floor(diagram.clientWidth || 280));
    if (width === lastWidth) return;
    lastWidth = width;
    const height = Math.max(360, Math.min(width, 560));
    const radius = Math.min((width - 90) / 2, (height - 90) / 2);
    const records = HubApp.data.records.filter(function (record) { return record.visible_pair_count > 0; })
      .sort(function (a, b) { return a.hood - b.hood || (a.id < b.id ? -1 : a.id > b.id ? 1 : 0); });
    const points = new Map();
    records.forEach(function (record, i) {
      const angle = i * Math.PI * 2 / records.length - Math.PI / 2;
      points.set(record.id, { x: width / 2 + radius * Math.cos(angle), y: height / 2 + radius * Math.sin(angle) });
    });
    const image = svg("svg", { width: width, height: height, viewBox: "0 0 " + width + " " + height,
      "aria-hidden": "true", focusable: "false" });
    const controls = HubApp.el("div", { class: "hub-diagram-controls" });
    pairs.forEach(function (pair) {
      const a = points.get(pair.left.id);
      const b = points.get(pair.right.id);
      image.appendChild(svg("line", { x1: a.x, y1: a.y, x2: b.x, y2: b.y,
        class: "hub-diagram-chord" + (pair.crosses ? " hub-diagram-chord--crossing" : ""),
        "stroke-dasharray": "7 8", "data-pair-key": pair.key }));
    });
    records.forEach(function (record) {
      const p = points.get(record.id);
      const group = svg("g", { "data-diagram-record": record.id,
        class: "hub-diagram-record hub-diagram-hood-" + record.hood });
      group.appendChild(svg("circle", { cx: p.x, cy: p.y, r: 12 }));
      // IDs stay 13 CSS px: the SVG viewport is rebuilt at its measured width, never scaled down.
      const onEnd = p.x > width / 2;
      group.appendChild(svg("text", { x: p.x + (onEnd ? -18 : 18), y: p.y - 17,
        "text-anchor": onEnd ? "end" : "start" }, record.id));
      image.appendChild(group);
      const read = text("button", "P05.read", { ID: record.id }, {
        type: "button", class: "hub-diagram-hit", "data-diagram-record": record.id });
      read.style.insetInlineStart = (p.x - 22) + "px";
      read.style.insetBlockStart = (p.y - 22) + "px";
      read.addEventListener("click", function () { HubApp.select({ type: "record", id: record.id }, read); });
      controls.appendChild(read);
    });
    diagram.replaceChildren(image, controls);
    marks();
  }
  function drawSmall() {
    G.mode = "diagram";
    diagram = HubApp.el("div", { class: "hub-diagram" });
    G.stageEl.replaceChildren(text("p", "Gr10", {}, { id: "graph-small" }), diagram);
    diagramObserver = new ResizeObserver(drawDiagram);
    diagramObserver.observe(diagram);
    drawDiagram();
  }
  function guide() {
    guideToggle = button("Gr05.show_guide", { id: "graph-guide-toggle", "aria-controls": "graph-guide-body" });
    guideBody = HubApp.el("div", { id: "graph-guide-body" });
    const legend = HubApp.el("ul", { id: "graph-legend" });
    ["record", "eureka", "unusual_pairs", "wording_and_meaning", "crossing", "selected"].forEach(function (kind) {
      legend.appendChild(HubApp.el("li", {}, [
        HubApp.el("span", { class: "hub-graph-swatch hub-graph-swatch--" + kind, "aria-hidden": "true" }),
        text("span", "Gr03." + kind)
      ]));
    });
    guideBody.appendChild(legend);
    guideBody.appendChild(text("p", "Gr19"));
    const data = HubApp.data.engines;
    if (engines.every(function (key) { return data[key].floor !== null; })) {
      guideBody.appendChild(text("p", "B05", { floor_unusual_pairs: data.unusual_pairs.floor_text,
        floor_wording_and_meaning: data.wording_and_meaning.floor_text }));
    } else engines.forEach(function (key) {
      guideBody.appendChild(data[key].floor === null ? text("p", "B06")
        : text("p", "B05.one." + key, { floor: data[key].floor_text }));
    });
    guideBody.appendChild(text("p", "Gr07"));
    guideBody.appendChild(text("p", "Gr06"));
    function open(value) {
      guideBody.hidden = !value;
      guideToggle.setAttribute("aria-expanded", String(value));
      guideToggle.textContent = HubApp.fmt(value ? "Gr05.hide_guide" : "Gr05.show_guide");
    }
    guideToggle.addEventListener("click", function () { open(guideBody.hidden); });
    const media = window.matchMedia("(min-width: 768px)");
    open(media.matches);
    media.addEventListener("change", function () { open(media.matches); });
    return HubApp.el("div", { class: "hub-graph-guide" }, [guideToggle, guideBody]);
  }
  function find() {
    const input = HubApp.el("input", { id: "graph-find", class: "hub-field", type: "search",
      placeholder: HubApp.fmt("Gr04.placeholder"), autocomplete: "off" });
    const count = HubApp.el("p", { id: "graph-find-count", "aria-live": "polite" });
    const matches = HubApp.el("ul", { id: "graph-find-matches" });
    const submit = button("Gr04.button", { type: "submit" });
    const form = HubApp.el("form", { class: "hub-graph-find" }, [
      text("label", "Gr04.label", {}, { for: input.id }), input, submit, count, matches
    ]);
    form.addEventListener("submit", function (event) {
      event.preventDefault();
      const ids = HubApp.search(input.value);
      count.textContent = HubApp.fmt(ids.length ? "Gr04.count" : "Gr04.none", { n: ids.length });
      matches.replaceChildren();
      ids.forEach(function (id) {
        const record = HubApp.index.records.get(id);
        const read = HubApp.el("button", { type: "button", class: "hub-button hub-button--quiet" },
          [HubApp.el("bdi", {}, id), " ", record.title]);
        read.addEventListener("click", function () { HubApp.select({ type: "record", id: id }, read); });
        matches.appendChild(HubApp.el("li", {}, read));
      });
    });
    form.addEventListener("keydown", function (event) {
      if (event.key === "Escape") {
        matches.replaceChildren(); count.textContent = "";
        input.focus(); event.stopPropagation();
      }
    });
    return form;
  }
  function tour() {
    let index = 0;
    const go = button("Gr05.tour", { id: "graph-tour", hidden: !HubApp.data.bridges.length });
    const empty = text("p", "Gr09", {}, { id: "graph-tour-empty", hidden: Boolean(HubApp.data.bridges.length) });
    go.addEventListener("click", function () {
      if (!HubApp.data.bridges.length) return;
      const bridge = HubApp.data.bridges[index];
      HubApp.select({ type: "record", id: bridge.record_id }, go);
      go.textContent = HubApp.fmt("Gr05.next", { i: index + 1, n: HubApp.data.bridges.length });
      index = (index + 1) % HubApp.data.bridges.length;
    });
    return HubApp.el("div", { class: "hub-graph-tour" }, [go, empty]);
  }
  function render(container) {
    if (diagramObserver) diagramObserver.disconnect();
    diagram = null;
    lastWidth = 0;
    pairs = HubApp.data.pairs.filter(function (pair) { return !pair.weak; }).sort(function (a, b) {
      return a.rank - b.rank || engines.indexOf(a.engine) - engines.indexOf(b.engine)
        || (a.key < b.key ? -1 : a.key > b.key ? 1 : 0);
    });
    pairList = HubApp.el("ol", { class: "hub-graph-pairs" });
    pairStatus = HubApp.el("p", { id: "graph-pair-status", "aria-live": "polite", tabindex: "-1" });
    pairBlock = HubApp.el("div", { id: "graph-list" }, [text("h3", "Gr16"), pairStatus, pairList]);
    G.stageEl = HubApp.el("div", { id: "graph-stage", class: "hub-graph-stage" });
    G.stageEl.addEventListener("click", function (event) {
      if (event.target === G.stageEl) HubApp.clearSelection();
    });
    stageButtons = HubApp.el("div", { id: "graph-stage-buttons", hidden: true });
    [["Gr05.zoom_in", 1.25], ["Gr05.zoom_out", .8], ["Gr05.reset", null]].forEach(function (entry) {
      const control = button(entry[0]);
      control.addEventListener("click", function () {
        if (!G.stage) return;
        if (entry[1] === null) G.stage.reset();
        else G.stage.zoom(entry[1]);
      });
      stageButtons.appendChild(control);
    });
    const scene = HubApp.el("div", { class: "hub-graph-scene" }, [guide(), G.stageEl]);
    container.replaceChildren(text("h2", "Gr01", {}, { "data-view-heading": "" }), text("p", "Gr02"),
      scene, stageButtons, find(), tour());
    if (HubApp.data.graph.earned) startStage(G.stageEl);
    else if (pairs.length) { drawSmall(); container.appendChild(pairBlock); }
    else {
      G.mode = "empty";
      G.stageEl.replaceChildren(text("h3", "Gr17", {}, { id: "graph-empty-title" }),
        text("p", "Gr18", {}, { id: "graph-empty-body" }));
    }
    if (HubApp.data.graph.not_drawn > 0) container.appendChild(text("p", "Gr08", { n: HubApp.data.graph.not_drawn }));
    shown = HubApp.data.config.bank_page;
    listPairs();
    HubApp.emit("graph-ready");
  }
  HubApp.registerView("graph", { render: render, onEvent: function (name, detail) {
    if (name === "select" || name === "clear") {
      marks();
      if (G.stage) { if (name === "select") G.stage.select(detail); else G.stage.clear(); }
    }
    if (name === "view" && detail === "graph") drawDiagram();
  } });
})();
