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
    if (cameraFrame !== null) { cancelAnimationFrame(cameraFrame); cameraFrame = null; }
    if (resizeStage) resizeStage.disconnect();
    if (G.instance && typeof G.instance._destructor === "function") G.instance._destructor();
    G.stageEl.removeAttribute("role");
    G.stageEl.removeAttribute("aria-label");
    G.mode = "fallback";
    G.instance = null;
    G.stage = null;
    stageButtons.hidden = true;
    G.stageEl.classList.remove("hub-graph-stage--3d");
    G.stageEl.replaceChildren(text("p", "Gr12", {}, { id: "graph-fallback" }), pairBlock);
    emitReady();
  }
  let readySent = false;
  let stageStarted = false;
  let startPending = null;
  let resizeStage = null;
  let cameraFrame = null;
  const INK = "#111111";
  const PAPER = "#F7F5EE";
  const COBALT = "#1F3FBF";
  const YELLOW = "#F2C200";
  const DIM = "#d8d4c8";
  function emitReady() {
    if (!readySent) { readySent = true; HubApp.emit("graph-ready"); }
  }
  function xyz(value) { return { x: value.x, y: value.y, z: value.z }; }
  function easeProgress(progress) {
    const token = getComputedStyle(document.documentElement).getPropertyValue("--mos-ease");
    const values = token.match(/cubic-bezier\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)\s*\)/);
    if (!values) return progress;
    const a = Number(values[1]), b = Number(values[2]), c = Number(values[3]), d = Number(values[4]);
    function curve(t, first, second) {
      return 3 * (1 - t) * (1 - t) * t * first + 3 * (1 - t) * t * t * second + t * t * t;
    }
    let low = 0, high = 1;
    for (let i = 0; i < 20; i++) {
      const mid = (low + high) / 2;
      if (curve(mid, a, c) < progress) low = mid; else high = mid;
    }
    return progress === 1 ? 1 : curve((low + high) / 2, b, d);
  }
  // The only authored camera player. Library duration is never supplied.
  function moveCamera(graph, destination, aim, placeLabels, instant) {
    if (cameraFrame !== null) cancelAnimationFrame(cameraFrame);
    cameraFrame = null;
    const from = xyz(graph.camera().position);
    const fromAim = xyz(graph.controls().target);
    const duration = instant ? 0 : HubApp.motion.ms("--mos-time-reframe");
    const began = performance.now();
    function frame() {
      const now = performance.now();
      const fraction = HubApp.motion.reduced ? 1 : duration ? Math.min(1, (now - began) / duration) : 1;
      const amount = easeProgress(fraction);
      const position = {}, target = {};
      ["x", "y", "z"].forEach(function (axis) {
        position[axis] = from[axis] + (destination[axis] - from[axis]) * amount;
        target[axis] = fromAim[axis] + (aim[axis] - fromAim[axis]) * amount;
      });
      graph.cameraPosition(position, target);
      placeLabels();
      if (fraction < 1) cameraFrame = requestAnimationFrame(frame);
      else cameraFrame = null;
    }
    if (duration === 0) frame();
    else cameraFrame = requestAnimationFrame(frame);
  }
  function webglAvailable() {
    const canvas = document.createElement("canvas");
    let context = null;
    try { context = canvas.getContext("webgl2") || canvas.getContext("webgl"); }
    catch (_) { return false; }
    if (!context) return false;
    const release = context.getExtension("WEBGL_lose_context");
    if (release) release.loseContext();
    return true;
  }
  function loadStageLibrary() {
    if (typeof window.ForceGraph3D === "function") return Promise.resolve();
    return new Promise(function (resolve, reject) {
      const script = document.createElement("script");
      script.src = "vendor/3d-force-graph.min.js";
      script.addEventListener("load", function () {
        if (typeof window.ForceGraph3D === "function") resolve();
        else reject(new Error("Graph library unavailable"));
      }, { once: true });
      script.addEventListener("error", function () { reject(new Error("Graph library unavailable")); }, { once: true });
      document.head.appendChild(script);
    });
  }
  function startStage(stageEl) {
    stageEl.replaceChildren(text("p", "Gr11", {}, { class: "hub-mono", id: "graph-loading" }));
    // Wait until the graph view is visible so its initial dimensions and fit are real.
    startPending = function () {
      if (stageStarted || HubApp.state.view !== "graph") return;
      stageStarted = true;
      if (!webglAvailable()) { showFallback(); return; }
      loadStageLibrary().then(function () { createStage(stageEl); }).catch(function () {
        console.error("Graph stage unavailable");
        showFallback();
      });
    };
    startPending();
  }
  function createStage(stageEl) {
    const nodes = HubApp.data.records.filter(function (record) { return record.visible_pair_count > 0; })
      .map(function (record) { return { id: record.id, record: record }; });
    const nodeIndex = new Map(nodes.map(function (node) { return [node.id, node]; }));
    const links = pairs.map(function (pair) {
      return { source: pair.left.id, target: pair.right.id, pair: pair };
    });
    const labels = HubApp.el("div", { class: "hub-stage-labels", "aria-hidden": "true" });
    const chips = new Map();
    HubApp.data.bridges.forEach(function (bridge) {
      const record = HubApp.index.records.get(bridge.record_id);
      const chip = HubApp.el("div", { class: "hub-stage-chip", "data-bridge-id": record.id }, [
        text("a", "Gr15", { ID: record.id }, { href: record.source_link, class: "hub-graph-chip" }),
        HubApp.el("span", { class: "hub-stage-chip-status" }, record.label)
      ]);
      chips.set(record.id, chip);
      labels.appendChild(chip);
    });
    const selectedChip = HubApp.el("div", { class: "hub-graph-chip hub-stage-chip hub-stage-chip--selected", hidden: true });
    labels.appendChild(selectedChip);
    const tooltip = HubApp.el("div", { id: "graph-tooltip", class: "hub-graph-tooltip", "aria-hidden": "true", hidden: true });
    const host = HubApp.el("div", { class: "hub-stage-canvas" });
    host.style.visibility = "hidden";
    stageEl.classList.add("hub-graph-stage--3d");
    stageEl.setAttribute("role", "img");
    stageEl.setAttribute("aria-label", HubApp.fmt("Gr13"));
    stageEl.removeAttribute("tabindex");
    const loading = text("p", "Gr11", {}, { class: "hub-mono", id: "graph-loading" });
    stageEl.replaceChildren(host, labels, tooltip, loading);
    let graph;
    let fitted = null;
    let active = null;
    let selectedNode = null;
    let finished = false;
    function nodeColor(node) {
      if (active && !active.has(node.id)) return DIM;
      return node.record.bridge ? YELLOW : HubApp.index.hoods.get(node.record.hood).tint;
    }
    function linkColor(link) {
      return active && !(active.has(link.pair.left.id) && active.has(link.pair.right.id)) ? DIM : COBALT;
    }
    function placeLabels() {
      if (!graph || !finished) return;
      const width = labels.clientWidth;
      const desktop = window.matchMedia("(min-width: 1024px)").matches;
      const sheet = parseFloat(document.documentElement.style.getPropertyValue("--hub-sheet-height")) || 0;
      const height = !desktop && HubApp.state.panelOpen
        ? Math.max(80, Math.min(stageEl.clientHeight, innerHeight - sheet - stageEl.getBoundingClientRect().y))
        : stageEl.clientHeight;
      const occupied = [];
      function place(chip, node, hidden) {
        chip.hidden = hidden;
        if (hidden) return;
        const point = graph.graph2ScreenCoords(node.x, node.y, node.z);
        const w = chip.offsetWidth, h = chip.offsetHeight;
        const x = Math.max(4, Math.min(width - w - 4, point.x + 10));
        let y = Math.max(4, Math.min(height - h - 4, point.y + 10));
        for (let tries = 0; tries < 8 && occupied.some(function (box) {
          return x < box.x + box.w && x + w > box.x && y < box.y + box.h && y + h > box.y;
        }); tries++) y = (y + h + 8 > height - h - 4) ? 4 : y + h + 8;
        chip.style.insetInlineStart = x + "px";
        chip.style.insetBlockStart = y + "px";
        occupied.push({ x: x, y: y, w: w, h: h });
      }
      chips.forEach(function (chip, id) { place(chip, nodeIndex.get(id), Boolean(active && !active.has(id))); });
      if (selectedNode) {
        selectedChip.textContent = selectedNode.id;
        place(selectedChip, selectedNode, false);
      } else selectedChip.hidden = true;
    }
    function shell() {
      nodes.forEach(function (node) {
        if (!node.record.bridge || !node.__threeObj) return;
        const mesh = node.__threeObj;
        let outline = mesh.children.find(function (child) { return child.name === "hub-ink-shell"; });
        if (!outline) {
          outline = mesh.clone(false);
          outline.name = "hub-ink-shell";
          outline.material = mesh.material.clone();
          outline.material.side = 1;
          outline.material.opacity = 1;
          outline.material.transparent = false;
          outline.position.set(0, 0, 0);
          outline.scale.setScalar(1.18);
          mesh.add(outline);
        }
        outline.material.color.set(active && !active.has(node.id) ? DIM : INK);
      });
    }
    function flyTo(id) {
      const node = nodeIndex.get(id);
      if (!node || !finished) return false;
      const camera = graph.camera().position;
      const target = graph.controls().target;
      const delta = { x: camera.x - target.x, y: camera.y - target.y, z: camera.z - target.z };
      const length = Math.hypot(delta.x, delta.y, delta.z) || 1;
      const distance = 100;
      const aim = xyz(node);
      // Keep the selected mark in the area left visible by the specified panel.
      if (HubApp.state.panelOpen) {
        const matrix = graph.camera().matrixWorld.elements;
        const halfView = distance * Math.tan(graph.camera().fov * Math.PI / 360);
        const desktop = window.matchMedia("(min-width: 1024px)").matches;
        const covered = desktop ? Math.min(400, stageEl.clientWidth * .8)
          : Math.max(0, stageEl.clientHeight - innerHeight * .38);
        const amount = halfView * covered / (desktop ? stageEl.clientWidth : stageEl.clientHeight);
        ["x", "y", "z"].forEach(function (axis, index) {
          aim[axis] += (desktop ? matrix[index] : -matrix[index + 4]) * amount;
        });
      }
      const destination = { x: aim.x + delta.x / length * distance,
        y: aim.y + delta.y / length * distance, z: aim.z + delta.z / length * distance };
      moveCamera(graph, destination, aim, placeLabels);
      return true;
    }
    function refreshSelection(sel, move) {
      active = null;
      selectedNode = null;
      if (sel) {
        const ids = sel.type === "record" ? [sel.id] : [HubApp.index.pairs.get(sel.key).left.id, HubApp.index.pairs.get(sel.key).right.id];
        active = new Set(ids);
        pairs.forEach(function (pair) {
          if (ids.includes(pair.left.id)) active.add(pair.right.id);
          if (ids.includes(pair.right.id)) active.add(pair.left.id);
        });
        selectedNode = nodeIndex.get(ids[0]) || null;
      }
      graph.nodeColor(nodeColor).linkColor(linkColor);
      shell();
      placeLabels();
      if (move && selectedNode) flyTo(selectedNode.id);
    }
    function showNodeTip(node) {
      tooltip.hidden = !node;
      if (!node) return;
      const record = node.record;
      let value = HubApp.fmt("Gr14.sphere", { ID: record.id, title: record.title })
        + "\n" + HubApp.fmt("Gr14.hood", { k: record.hood });
      if (record.bridge) value += "\n" + HubApp.fmt("Gr14.bridge");
      tooltip.textContent = value + "\n" + record.label;
    }
    function showLinkTip(link) {
      tooltip.hidden = !link;
      if (link) tooltip.textContent = HubApp.fmt("Gr14.line", {
        engine: HubApp.data.engines[link.pair.engine].short_name, z: link.pair.rank_score_text });
    }
    // Stage follows the deviation recorded at the top of this file: every link cobalt, width 1.6 for crossing pairs, no particles.
    graph = window.ForceGraph3D({ controlType: "orbit" })(host)
      .width(stageEl.clientWidth).height(stageEl.clientHeight).backgroundColor(PAPER)
      .nodeId("id").nodeVal(function (node) { return node.record.bridge ? 5 : 2.2; })
      .nodeResolution(16).nodeOpacity(.95).nodeColor(nodeColor)
      .nodeLabel(function () { return ""; }).linkLabel(function () { return ""; })
      .linkColor(linkColor).linkOpacity(1).linkWidth(function (link) { return link.pair.width; })
      .linkDirectionalParticles(0).warmupTicks(300).cooldownTicks(0)
      .enableNodeDrag(false).showNavInfo(false)
      .onNodeClick(function (node) { HubApp.select({ type: "record", id: node.id }, stageEl); })
      .onLinkClick(function (link) { HubApp.select({ type: "pair", key: link.pair.key }, stageEl); })
      .onBackgroundClick(function () { HubApp.clearSelection(); })
      .onNodeHover(showNodeTip).onLinkHover(showLinkTip)
      .onEngineStop(function () {
        if (finished) { shell(); return; }
        if (graph.graphData().nodes.length !== nodes.length || nodes.some(function (node) {
          return !node.__threeObj || ![node.x, node.y, node.z].every(Number.isFinite);
        })) return;
        finished = true;
        // Freeze the settled coordinates as well as using zero cooldown ticks.
        nodes.forEach(function (node) { node.fx = node.x; node.fy = node.y; node.fz = node.z; });
        requestAnimationFrame(function () {
          if (G.instance !== graph) return;
          shell();
          // The vendor fit reads mesh world matrices, which can still be from the empty frame.
          graph.scene().updateMatrixWorld(true);
          graph.zoomToFit(0, 40);
          fitted = { position: xyz(graph.camera().position), aim: xyz(graph.controls().target) };
          host.style.visibility = "visible";
          loading.remove();
          G.mode = "3d";
          showStageButtons();
          placeLabels();
          if (HubApp.state.selection) refreshSelection(HubApp.state.selection, false);
          requestAnimationFrame(function () { placeLabels(); emitReady(); });
        });
      });
    G.instance = graph;
    graph.controls().autoRotate = false;
    graph.controls().enableDamping = false;
    graph.d3Force("link").distance(function (link) { return link.pair.crosses ? 60 : 40; })
      .strength(function (link) { return link.pair.crosses ? .08 : .15; });
    graph.d3Force("charge").strength(-55);
    G.stage = {
      select: function (sel) {
        if (HubApp.state.view === "graph") stageEl.scrollIntoView({ block: "start", behavior: "instant" });
        refreshSelection(sel, true);
      },
      clear: function () { refreshSelection(null, false); }, flyTo: flyTo,
      zoom: function (factor) {
        if (!finished) return;
        const camera = graph.camera().position, aim = graph.controls().target;
        moveCamera(graph, { x: aim.x + (camera.x - aim.x) / factor,
          y: aim.y + (camera.y - aim.y) / factor, z: aim.z + (camera.z - aim.z) / factor }, xyz(aim), placeLabels);
      },
      reset: function () { if (fitted) moveCamera(graph, fitted.position, fitted.aim, placeLabels); }
    };
    graph.controls().addEventListener("change", placeLabels);
    graph.controls().addEventListener("start", function () {
      if (cameraFrame !== null) { cancelAnimationFrame(cameraFrame); cameraFrame = null; }
    });
    stageEl.addEventListener("pointermove", function (event) {
      const box = stageEl.getBoundingClientRect();
      tooltip.style.insetInlineStart = Math.max(4, Math.min(box.width - tooltip.offsetWidth - 4, event.clientX - box.x + 12)) + "px";
      tooltip.style.insetBlockStart = Math.max(4, Math.min(box.height - tooltip.offsetHeight - 4, event.clientY - box.y + 12)) + "px";
    });
    stageEl.addEventListener("pointerleave", function () { tooltip.hidden = true; });
    stageEl.addEventListener("webglcontextlost", function (event) { event.preventDefault(); showFallback(); }, true);
    resizeStage = new ResizeObserver(function () {
      if (!stageEl.clientWidth) return;
      graph.width(stageEl.clientWidth).height(stageEl.clientHeight);
      placeLabels();
    });
    resizeStage.observe(stageEl);
    graph.graphData({ nodes: nodes, links: links });
    host.querySelectorAll("canvas").forEach(function (canvas) { canvas.removeAttribute("tabindex"); });
  }

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
    if (!diagram || !diagram.clientWidth) return;
    const width = Math.max(240, Math.floor(diagram.clientWidth));
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
    diagram.replaceChildren(image, controls);
    const labels = [];
    records.forEach(function (record) {
      const p = points.get(record.id);
      const group = svg("g", { "data-diagram-record": record.id,
        class: "hub-diagram-record hub-diagram-hood-" + record.hood });
      group.appendChild(svg("circle", { cx: p.x, cy: p.y, r: 12 }));
      // IDs stay 13 CSS px: the SVG viewport is rebuilt at its measured width, never scaled down.
      const label = svg("text", {}, record.id);
      group.appendChild(label);
      image.appendChild(group);
      labels.push({ node: label, point: p });
      const read = text("button", "P05.read", { ID: record.id }, {
        type: "button", class: "hub-diagram-hit", "data-diagram-record": record.id });
      read.style.insetInlineStart = (p.x - 22) + "px";
      read.style.insetBlockStart = (p.y - 22) + "px";
      read.addEventListener("click", function () { HubApp.select({ type: "record", id: record.id }, read); });
      controls.appendChild(read);
    });
    const occupied = Array.from(points.values()).map(function (p) {
      return { x: p.x - 15, y: p.y - 15, width: 30, height: 30 };
    });
    function overlaps(a, b) {
      return a.x < b.x + b.width + 3 && a.x + a.width + 3 > b.x
        && a.y < b.y + b.height + 3 && a.y + a.height + 3 > b.y;
    }
    labels.forEach(function (item) {
      const p = item.point;
      const glyph = item.node.getBBox();
      const length = Math.max(item.node.getComputedTextLength(), glyph.width) + 4;
      const candidates = [p.x + 20, p.x - length - 20].map(function (x) {
        return { x: Math.max(4, Math.min(width - length - 4, x)),
          y: p.y - (glyph.height + 4) / 2, width: length, height: glyph.height + 4 };
      });
      for (let distance = 20; distance < height; distance += 18) {
        [p.x + 18, p.x - length - 18, p.x - length / 2].forEach(function (x) {
          [p.y - distance, p.y + distance].forEach(function (baseline) {
            candidates.push({ x: Math.max(4, Math.min(width - length - 4, x)),
              y: baseline + glyph.y - 2, width: length, height: glyph.height + 4 });
          });
        });
      }
      const box = candidates.find(function (candidate) {
        return candidate.y >= 4 && candidate.y + candidate.height <= height - 4
          && !occupied.some(function (other) { return overlaps(candidate, other); });
      });
      if (box) {
        item.node.setAttribute("x", String(box.x - glyph.x + 2));
        item.node.setAttribute("y", String(box.y - glyph.y + 2));
        occupied.push(box);
      }
    });
    marks();
  }
  function drawSmall() {
    G.mode = "diagram";
    diagram = HubApp.el("div", { class: "hub-diagram" });
    G.stageEl.replaceChildren(text("p", "Gr10", {}, { id: "graph-small" }), diagram);
    diagramObserver = new ResizeObserver(drawDiagram);
    diagramObserver.observe(diagram);
    const current = diagram;
    document.fonts.ready.then(function () {
      if (diagram === current) { lastWidth = 0; drawDiagram(); }
    });
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
    readySent = false;
    stageStarted = false;
    startPending = null;
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
    if (HubApp.data.graph.earned) {
      container.appendChild(pairBlock);
      startStage(G.stageEl);
    }
    else if (pairs.length) { drawSmall(); container.appendChild(pairBlock); }
    else {
      G.mode = "empty";
      G.stageEl.replaceChildren(text("h3", "Gr17", {}, { id: "graph-empty-title" }),
        text("p", "Gr18", {}, { id: "graph-empty-body" }));
    }
    if (HubApp.data.graph.not_drawn > 0) container.appendChild(text("p", "Gr08", { n: HubApp.data.graph.not_drawn }));
    shown = HubApp.data.config.bank_page;
    listPairs();
    if (!HubApp.data.graph.earned) emitReady();
  }
  HubApp.registerView("graph", { render: render, onEvent: function (name, detail) {
    if (name === "select" || name === "clear") {
      marks();
      if (G.stage) { if (name === "select") G.stage.select(detail); else G.stage.clear(); }
    }
    if (name === "view" && detail === "graph") {
      drawDiagram();
      if (startPending) startPending();
    }
  } });
})();
