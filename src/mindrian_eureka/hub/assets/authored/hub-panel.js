(function () {
  "use strict";

  const HubApp = window.HubApp;
  if (!HubApp || !HubApp.copy) return;
  const panel = document.getElementById("hub-panel");
  const root = document.documentElement;
  const desktop = window.matchMedia("(min-width: 1024px)");

  function text(tag, key, values, attrs) {
    return HubApp.el(tag, attrs || {}, HubApp.fmt(key, values));
  }
  function role(key) { return text("span", "P06." + key, {}, { class: "hub-role hub-role--" + key }); }
  function label(value) { return HubApp.el("span", { class: "hub-chip hub-panel-label" }, value); }
  function heading(key, values) { return text("h3", key, values); }
  function sourceLink(record, key) {
    return text("a", key || "P05.open", {}, { class: "hub-link", href: record.source_link });
  }
  function scoreLines(pair) {
    return HubApp.el("div", { class: "hub-panel-scores" }, [
      role("inferred"), text("p", "B08.wording", { x: pair.wording_text }),
      text("p", "B08.meaning", { y: pair.meaning_text }),
      text("p", "B08.rank_score", { z: pair.rank_score_text })
    ]);
  }
  function flags(record) {
    const lines = [];
    if (record.identical_to.length) lines.push(text("p", "P09.identical", { ID: record.identical_to[0] }, { class: "hub-flag" }));
    if (record.no_text) lines.push(text("p", "P09.no_text", {}, { class: "hub-flag" }));
    return lines;
  }
  function meanings(keys) {
    const section = HubApp.el("section", { class: "hub-panel-meaning" }, [heading("P03.meaning"), text("p", "G16")]);
    keys.forEach(function (key) {
      section.appendChild(HubApp.el("details", {}, [
        HubApp.el("summary", {}, HubApp.data.engines[key].name),
        HubApp.el("p", {}, HubApp.data.engines[key].score_meaning)
      ]));
    });
    return section;
  }
  function recordButton(record, key) {
    const button = text("button", key || "P05.read", { ID: record.id }, {
      class: "hub-button hub-button--quiet", type: "button", "data-read-record": record.id
    });
    button.addEventListener("click", function () { HubApp.select({ type: "record", id: record.id }, button); });
    return button;
  }
  function pairButton(pair) {
    const button = text("button", "P05.read_pair", {}, { class: "hub-button hub-button--quiet", type: "button" });
    button.addEventListener("click", function () { HubApp.select({ type: "pair", key: pair.key }, button); });
    return button;
  }
  function header(title, id, bridge) {
    const close = text("button", "P02.close", {}, {
      class: "hub-button hub-button--quiet", type: "button", id: "hub-panel-close",
      "aria-label": HubApp.fmt("P02.close_name")
    });
    close.addEventListener("click", function () { HubApp.clearSelection(); });
    const strip = HubApp.el("div", { class: "hub-panel-header" });
    if (id !== null) strip.appendChild(HubApp.el("bdi", { class: "hub-mono" }, id));
    if (bridge) strip.appendChild(text("span", "P06.eureka", {}, { class: "hub-role hub-role--bridge" }));
    strip.appendChild(close);
    panel.appendChild(strip);
    panel.appendChild(HubApp.el("h2", { id: "hub-panel-title", tabindex: "-1" }, title));
  }
  function sourceProse(value, className) {
    const chunks = [];
    let buffer = "", count = 0, boundary = 0;
    (value.match(/\S+\s*|\s+/gu) || []).forEach(function (token) {
      buffer += token;
      if (token.trim()) count++;
      if (/[.!?][)"'\]]*\s*$/u.test(token)) boundary = buffer.length;
      if (count >= 80 && boundary) {
        chunks.push(buffer.slice(0, boundary));
        buffer = buffer.slice(boundary);
        count = buffer.trim() ? buffer.trim().split(/\s+/u).length : 0;
        boundary = 0;
      } else if (count >= 100) {
        chunks.push(buffer); buffer = ""; count = 0; boundary = 0;
      }
    });
    if (buffer) chunks.push(buffer);
    return HubApp.el("div", { class: "hub-source-prose" + (className ? " " + className : "") },
      chunks.map(function (chunk) { return HubApp.el("p", {}, chunk); }));
  }
  function recordView(record) {
    header(record.title || HubApp.fmt("P02.record"), record.id, record.bridge);
    panel.appendChild(label(record.label));
    const source = HubApp.el("section", { class: "hub-evidence hub-panel-source" }, [
      heading("P03.source"), role("source"),
      text("h4", "P04.file"), HubApp.el("p", { class: "hub-mono" }, record.source_file),
      text("h4", "P04.ref"), HubApp.el("p", { class: "hub-mono" }, record.source_ref),
      sourceLink(record)
    ]);
    if (record.file_link) source.appendChild(text("a", "P05.catalogue", {}, { class: "hub-link", href: record.catalogue_link }));
    panel.appendChild(source);
    const characters = Array.from(record.text);
    const limit = HubApp.data.config.panel_text_chars;
    const content = HubApp.el("section", { class: "hub-panel-text" }, [heading("P03.text"),
      sourceProse(characters.slice(0, limit).join(""), "hub-panel-excerpt")]);
    if (characters.length > limit) content.appendChild(HubApp.el("details", { class: "hub-panel-full" }, [
      text("summary", "P05.full"), sourceProse(characters.slice(limit).join(""))
    ]));
    panel.appendChild(content);
    if (record.hood !== null) {
      const hood = HubApp.index.hoods.get(record.hood);
      panel.appendChild(HubApp.el("section", {}, [heading("P03.hood"), role("inferred"),
        text("p", "P08", { k: hood.number, n: hood.size })]));
    }
    const checks = flags(record);
    if (checks.length) panel.appendChild(HubApp.el("section", {}, [heading("P03.check"), ...checks]));
    const pairs = record.pair_keys.map(function (key) { return HubApp.index.pairs.get(key); });
    const pairSection = HubApp.el("section", { class: "hub-panel-pairs" }, [
      heading("P03.pairs", { n: pairs.length }), role("proposed")
    ]);
    pairs.forEach(function (pair) {
      const partner = HubApp.index.records.get(pair.left.id === record.id ? pair.right.id : pair.left.id);
      const partnerButton = HubApp.el("button", { class: "hub-button hub-button--quiet", type: "button" },
        HubApp.el("bdi", { class: "hub-mono" }, partner.id));
      partnerButton.addEventListener("click", function () { HubApp.select({ type: "record", id: partner.id }, partnerButton); });
      const block = HubApp.el("article", { class: "hub-panel-pair-block", "data-pair-key": pair.key }, [
        partnerButton, HubApp.el("p", {}, partner.title),
        HubApp.el("p", {}, HubApp.data.engines[pair.engine].name),
        text("p", "B08.rank", { n: pair.rank }), scoreLines(pair), label(pair.label)
      ]);
      // Every proposed pair block carries both source references as well as its status.
      [pair.left, pair.right].forEach(function (side) {
        block.appendChild(HubApp.el("a", { class: "hub-link hub-mono", href: side.source_link },
          HubApp.el("bdi", {}, side.id)));
      });
      block.appendChild(pairButton(pair));
      pairSection.appendChild(block);
    });
    panel.appendChild(pairSection);
    if (record.bridge) {
      const names = record.bridge_hoods.map(function (number) { return HubApp.fmt("P03.hood") + " " + number; });
      panel.appendChild(HubApp.el("section", { class: "hub-panel-why" }, [
        heading("P03.why"), role("proposed"),
        text("p", "P07", { n: names.length, list: names.join(", ") })
      ]));
    }
    const engineKeys = Array.from(new Set(pairs.map(function (pair) { return pair.engine; })));
    panel.appendChild(meanings(engineKeys.length ? engineKeys : ["unusual_pairs", "wording_and_meaning"]));
  }
  function pairView(pair) {
    header(HubApp.fmt("P02.pair"), null, false);
    panel.appendChild(HubApp.el("section", {}, [role("proposed"),
      text("p", "B08.rank", { n: pair.rank }), HubApp.el("p", {}, HubApp.data.engines[pair.engine].name)]));
    panel.appendChild(label(pair.label));
    const sources = HubApp.el("section", {}, [heading("P03.two")]);
    [pair.left, pair.right].forEach(function (side) {
      sources.appendChild(HubApp.el("div", { class: "hub-evidence hub-panel-source" }, [role("source"),
        HubApp.el("a", { class: "hub-link hub-mono", href: side.source_link }, HubApp.el("bdi", {}, side.id)),
        HubApp.el("h4", {}, side.title), HubApp.el("p", { class: "hub-mono" }, side.source_file)
      ]));
    });
    panel.appendChild(sources);
    panel.appendChild(HubApp.el("section", {}, [heading("P03.scores"), scoreLines(pair)]));
    panel.appendChild(HubApp.el("section", {}, [heading("P03.reading"), HubApp.el("p", {}, pair.reading)]));
    const checks = [pair.left, pair.right].flatMap(function (side) { return flags(HubApp.index.records.get(side.id)); });
    if (checks.length) panel.appendChild(HubApp.el("section", {}, [heading("D01"), ...checks]));
    panel.appendChild(meanings([pair.engine]));
    panel.appendChild(HubApp.el("div", { class: "hub-panel-actions" }, [
      recordButton(HubApp.index.records.get(pair.left.id)), recordButton(HubApp.index.records.get(pair.right.id))
    ]));
  }
  function measure() {
    if (HubApp.state.panelOpen && !desktop.matches) root.style.setProperty("--hub-sheet-height", panel.getBoundingClientRect().height + "px");
    else root.style.removeProperty("--hub-sheet-height");
  }
  function empty() {
    panel.classList.add("hub-panel-empty");
    panel.replaceChildren(text("h2", "P01.heading", {}, { id: "hub-panel-title", tabindex: "-1" }),
      text("p", "P01.body"), HubApp.el("img", {
        src: "assets/faces/theo-rest.svg", alt: "", "aria-hidden": "true"
      }));
  }
  function show(selection) {
    const value = selection.type === "record" ? HubApp.index.records.get(selection.id) : HubApp.index.pairs.get(selection.key);
    if (!value) return;
    panel.replaceChildren();
    panel.classList.remove("hub-panel-empty");
    panel.hidden = false;
    root.setAttribute("data-panel-open", "");
    root.setAttribute("data-panel-view", HubApp.state.view);
    panel.setAttribute("data-panel-open", "");
    if (selection.type === "record") recordView(value); else pairView(value);
    measure();
    document.getElementById("hub-panel-title").focus();
  }
  function hide() {
    root.removeAttribute("data-panel-open");
    root.removeAttribute("data-panel-view");
    panel.removeAttribute("data-panel-open");
    root.style.removeProperty("--hub-sheet-height");
    empty();
  }
  HubApp.registerPanel({ show: show, hide: hide, isOpen: function () { return HubApp.state.panelOpen; } });
  HubApp.on("start", function () { if (!HubApp.state.selection) empty(); });
  HubApp.on("view", function (view) { root.setAttribute("data-panel-view", view); measure(); });
  const stage = document.getElementById("graph-stage");
  if (stage) stage.addEventListener("click", function (event) {
    if (event.target === stage && HubApp.state.panelOpen) HubApp.clearSelection();
  });
  window.addEventListener("resize", measure);
})();
