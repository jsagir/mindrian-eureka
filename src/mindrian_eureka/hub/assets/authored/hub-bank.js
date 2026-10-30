(function () {
  "use strict";

  const HubApp = window.HubApp;
  if (!HubApp) return;
  const engines = ["unusual_pairs", "wording_and_meaning"];
  let shown = 0;
  let controls;
  let list;
  let status;
  let radios = [];
  let classRadios = [];
  let weak = null;
  const classKeys = ["all", "cross", "open_open", "licensed_licensed"];

  function text(tag, key, values, attrs) {
    return HubApp.el(tag, attrs || {}, HubApp.fmt(key, values));
  }
  // The carried outcome cells of one record as ink-on-paper chips (Phase 2.2, D-03).
  // Blank cells are skipped; keys are sorted; text nodes only.
  function extrasRow(side, extras) {
    const keys = Object.keys(extras || {}).filter(function (key) { return extras[key] !== ""; }).sort();
    if (!keys.length) return null;
    const chips = keys.map(function (key) {
      return HubApp.el("span", { class: "hub-chip hub-bank-extra" }, key + ": " + extras[key]);
    });
    return HubApp.el("div", { class: "hub-bank-labels hub-bank-extras" },
      [HubApp.el("span", { class: "hub-chip hub-bank-extra-id" }, side.id)].concat(chips));
  }
  function selection() {
    if (!list) return;
    const current = HubApp.state.selection;
    list.querySelectorAll("[data-pair-key]").forEach(function (row) {
      const selected = current && current.type === "pair" && current.key === row.dataset.pairKey;
      row.classList.toggle("hub-row--selected", Boolean(selected));
      if (selected) row.setAttribute("aria-current", "true");
      else row.removeAttribute("aria-current");
    });
  }
  function source(side) {
    return HubApp.el("a", {
      href: side.source_link, class: "hub-link hub-mono",
      "aria-label": HubApp.fmt("B08.source_name", { ID: side.id, title: side.title })
    }, HubApp.el("bdi", {}, side.id));
  }
  function row(pair) {
    const item = HubApp.el("li", {
      class: "hub-row hub-bank-row" + (pair.weak ? " hub-row--weak" : ""),
      "data-pair-key": pair.key, "data-engine": pair.engine, "data-rank": pair.rank
    });
    const rank = text("p", "B08.rank", { n: pair.rank }, { class: "hub-bank-rank hub-mono" });
    const role = HubApp.el("div", { class: "hub-bank-labels" }, [
      HubApp.el("p", { class: "hub-bank-engine" }, HubApp.data.engines[pair.engine].short_name),
      text("span", "P06.proposed", {}, { class: "hub-role hub-role--proposed" }),
      HubApp.el("span", { class: "hub-chip hub-bank-status" }, pair.label)
    ]);
    if (pair.weak) role.appendChild(text("span", "P06.hidden", {}, { class: "hub-hidden-label" }));
    if (pair.pair_class) {
      role.appendChild(HubApp.el("span", { class: "hub-chip hub-bank-class" }, HubApp.fmt("P10." + pair.pair_class)));
    }
    const records = HubApp.el("div", { class: "hub-bank-records" });
    [pair.left, pair.right].forEach(function (side) {
      records.appendChild(HubApp.el("div", { class: "hub-bank-record" }, [
        source(side), HubApp.el("p", { class: "hub-bank-title" }, side.title)
      ]));
    });
    const scores = HubApp.el("div", { class: "hub-bank-scores" }, [
      text("span", "P06.inferred", {}, { class: "hub-role hub-role--inferred" }),
      text("p", "B08.wording", { x: pair.wording_text }),
      text("p", "B08.meaning", { y: pair.meaning_text }),
      text("p", "B08.rank_score", { z: pair.rank_score_text })
    ]);
    const reading = HubApp.el("div", { class: "hub-bank-reading" },
      HubApp.el("p", {}, pair.reading));
    [pair.left, pair.right].forEach(function (side) {
      const record = HubApp.index.records.get(side.id);
      if (pair.flag_identical && record.identical_to.length) {
        reading.appendChild(text("p", "P09.identical", { ID: record.identical_to[0] }, { class: "hub-flag" }));
      }
      if (pair.flag_no_text && record.no_text) {
        reading.appendChild(text("p", "P09.no_text", {}, { class: "hub-flag" }));
      }
    });
    const button = text("button", "B08.read", {}, { type: "button", class: "hub-button hub-bank-read" });
    button.addEventListener("click", function () { HubApp.select({ type: "pair", key: pair.key }, button); });
    // Reading order stays rank, words/status, source records, scores, reading, action.
    // CSS places these fields in the prescribed responsive grid without focus reordering.
    const extrasRows = [extrasRow(pair.left, pair.left_extras), extrasRow(pair.right, pair.right_extras)];
    [rank, role].concat(extrasRows).concat([records, scores, reading, button]).forEach(function (part) {
      if (part) item.appendChild(part);
    });
    return item;
  }
  function update() {
    if (!list || !HubApp.data) return;
    const filter = HubApp.state.filters;
    radios.forEach(function (radio) { radio.checked = radio.value === filter.engine; });
    classRadios.forEach(function (radio) { radio.checked = radio.value === filter.pairClass; });
    if (weak) weak.checked = Boolean(filter.weak);
    const pairs = HubApp.data.pairs.filter(function (pair) {
      return (filter.engine === "both" || pair.engine === filter.engine) && (!pair.weak || filter.weak)
        && (filter.pairClass === "all" || pair.pair_class === filter.pairClass);
    }).sort(function (a, b) {
      return a.rank - b.rank || engines.indexOf(a.engine) - engines.indexOf(b.engine)
        || (a.key < b.key ? -1 : a.key > b.key ? 1 : 0);
    });
    list.replaceChildren();
    if (!HubApp.data.pairs.length) {
      list.appendChild(text("h2", "B10"));
      list.appendChild(text("p", "B11"));
      const notes = HubApp.el("ul");
      engines.forEach(function (engine) {
        HubApp.data.engines[engine].notes.forEach(function (note) {
          notes.appendChild(HubApp.el("li", {}, note));
        });
      });
      list.appendChild(notes);
    } else if (!pairs.length) {
      list.appendChild(text("h2", "B12"));
      list.appendChild(text("p", "B13.body"));
      const reset = text("button", "B13.button", {}, { class: "hub-button", type: "button" });
      reset.addEventListener("click", function () {
        HubApp.setFilter("engine", "both");
        document.getElementById("bank-engine-both").focus();
      });
      list.appendChild(reset);
    } else {
      const rows = HubApp.el("ol", { class: "hub-bank-list" });
      pairs.slice(0, shown).forEach(function (pair) { rows.appendChild(row(pair)); });
      list.appendChild(rows);
      if (shown < pairs.length) {
        const more = text("button", "B09.more", {}, {
          class: "hub-button hub-button--quiet", id: "bank-more", type: "button"
        });
        more.addEventListener("click", function () {
          shown += HubApp.data.config.bank_page;
          update();
          const next = document.getElementById("bank-more");
          // The old button was replaced. Keep keyboard focus on an available action.
          if (next) next.focus();
          else status.focus();
        });
        list.appendChild(more);
      }
    }
    status.textContent = HubApp.fmt("B09.status", { a: Math.min(shown, pairs.length), b: pairs.length });
    selection();
  }
  function cutoffs() {
    const data = HubApp.data.engines;
    const box = HubApp.el("div", { class: "hub-bank-cutoffs" });
    if (engines.every(function (key) { return data[key].floor !== null; })) {
      box.appendChild(text("p", "B05", {
        floor_unusual_pairs: data.unusual_pairs.floor_text,
        floor_wording_and_meaning: data.wording_and_meaning.floor_text
      }));
    } else {
      engines.forEach(function (key) {
        box.appendChild(data[key].floor === null ? text("p", "B06")
          : text("p", "B05.one." + key, { floor: data[key].floor_text }));
      });
    }
    return box;
  }
  function render(container) {
    const heading = text("h2", "B01", {}, { "data-view-heading": "" });
    const lede = text("p", "B02");
    controls = HubApp.el("div", { id: "bank-controls" });
    list = HubApp.el("div", { id: "bank-list" });
    status = HubApp.el("p", { id: "bank-status", "aria-live": "polite", tabindex: "-1" });
    const about = HubApp.el("details", {}, [text("summary", "B04.summary"), text("p", "B04.body")]);
    const filters = HubApp.el("fieldset", { class: "hub-bank-engines" }, text("legend", "B03.legend"));
    radios = [];
    ["both", ...engines].forEach(function (key) {
      const input = HubApp.el("input", {
        type: "radio", id: "bank-engine-" + key, name: "bank-engine", value: key
      });
      input.addEventListener("change", function () { if (input.checked) HubApp.setFilter("engine", key); });
      radios.push(input);
      filters.appendChild(HubApp.el("label", { for: input.id }, [input, text("span", "B03." + key)]));
    });
    controls.appendChild(about);
    controls.appendChild(filters);
    classRadios = [];
    if (HubApp.data.has_pair_classes === true) {
      const classes = HubApp.el("fieldset", { class: "hub-bank-engines hub-bank-classes" },
        text("legend", "B15.legend"));
      classKeys.forEach(function (key) {
        const input = HubApp.el("input", {
          type: "radio", id: "bank-class-" + key, name: "bank-class", value: key
        });
        input.addEventListener("change", function () { if (input.checked) HubApp.setFilter("pairClass", key); });
        classRadios.push(input);
        classes.appendChild(HubApp.el("label", { for: input.id }, [input, text("span", "B15." + key)]));
      });
      controls.appendChild(classes);
    }
    controls.appendChild(cutoffs());
    weak = null;
    if (HubApp.data.counts.weak_pairs > 0) {
      weak = HubApp.el("input", { type: "checkbox", id: "bank-weak" });
      weak.addEventListener("change", function () { HubApp.setFilter("weak", weak.checked); });
      controls.appendChild(HubApp.el("label", { class: "hub-bank-weak", for: "bank-weak" },
        [weak, text("span", "B07")]));
    }
    container.replaceChildren(heading, lede, controls, status, list);
    shown = HubApp.data.config.bank_page;
    update();
  }
  HubApp.registerView("bank", {
    render: render,
    onEvent: function (name) {
      if (name === "filter") {
        if (!HubApp.data) return;
        shown = HubApp.data.config.bank_page;
        update();
      } else if (name === "select" || name === "clear") selection();
    }
  });
})();
