(function () {
  "use strict";

  const HubApp = window.HubApp;
  if (!HubApp) return;
  const engines = ["unusual_pairs", "wording_and_meaning"];
  // The finding rows (Phase 2.3.1 plan 06, owner decision D-01 and the prototype of
  // 2026-11-08) fill these keys by the numeral kind and the reading kind of a pair.
  // deck keys: B08.use.meaning B08.use.wording B08.use.agree B08.caption.meaning B08.caption.wording B08.shared B08.shared_none B08.open B08.use.label
  const readingKinds = ["meaning", "wording", "agree"];
  // From 768 px the figure caption shows open; under it the caption folds (plan 11).
  const wide = window.matchMedia("(min-width: 768px)");
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
  function own(object, key) {
    return Boolean(object) && typeof object === "object" && Object.prototype.hasOwnProperty.call(object, key);
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
  // The page route of a pair (the router and the pages are plan 08). The engine key is one
  // of two fixed keys and the rank is an integer, so the route is a fixed grammar.
  function route(pair) {
    return "#/pair/" + pair.engine + "/" + pair.rank;
  }
  function numeral(kind, value) {
    return HubApp.el("p", { class: "hub-bank-num" }, [
      HubApp.el("b", { class: "hub-bank-numeral hub-bank-numeral--" + kind }, value),
      text("span", "B08.caption." + kind, {}, { class: "hub-bank-caption" })
    ]);
  }
  // The shared distinctive words of a pair, or the line that none is shared.
  function sharedLine(pair) {
    const terms = HubApp.data.terms;
    const words = terms && own(terms.pairs, pair.pair_id) ? terms.pairs[pair.pair_id] : null;
    if (Array.isArray(words) && words.length) {
      return text("p", "B08.shared", { list: words.join(", ") }, { class: "hub-bank-shared" });
    }
    return text("p", "B08.shared_none", {}, { class: "hub-bank-shared" });
  }
  // The card figure of plan 04 through the safe inserter of plan 03, or null. Its caption
  // folds under 768 px: a details element whose summary is the legend summary of the payload;
  // from 768 px it shows open. One media query, no clock, no storage (plan 11).
  function figure(pair) {
    const figures = HubApp.data.figures;
    if (!figures || !own(figures.pairs, pair.key) || !figures.legend) return null;
    const picture = HubApp.figure(figures.pairs[pair.key].card);
    if (!picture) return null;
    const caption = HubApp.el("details", { class: "hub-bank-figure-caption" }, [
      HubApp.el("summary", {}, figures.legend.summary),
      HubApp.el("p", {}, figures.legend.caption)
    ]);
    // The property, not the attribute: an attribute value "false" would open the element.
    caption.open = wide.matches;
    return HubApp.el("figure", { class: "hub-bank-figure" }, [
      picture, HubApp.el("figcaption", {}, caption)
    ]);
  }
  if (typeof wide.addEventListener === "function") {
    wide.addEventListener("change", function (event) {
      document.querySelectorAll("#bank-list details.hub-bank-figure-caption").forEach(function (node) {
        node.open = event.matches;
      });
    });
  }
  function row(pair) {
    const item = HubApp.el("li", {
      class: "hub-row hub-bank-row" + (pair.weak ? " hub-row--weak" : ""),
      "data-pair-key": pair.key, "data-engine": pair.engine, "data-rank": pair.rank
    });
    const href = route(pair);
    // (1) The index: a two-digit number for the eye, the word Rank for assistive technology.
    const rank = HubApp.el("p", { class: "hub-bank-rank" }, [
      HubApp.el("span", { class: "hub-bank-rank-n", "aria-hidden": "true" }, String(pair.rank).padStart(2, "0")),
      text("span", "B08.rank", { n: pair.rank }, { class: "hub-visually-hidden" })
    ]);
    // (2) The two titles as one stretched link to the pair page, then the two source ids.
    const title = HubApp.el("a", { class: "hub-bank-open-link", href: href }, [
      pair.left.title,
      HubApp.el("span", { class: "hub-bank-and" }, " " + HubApp.fmt("B08.and") + " "),
      pair.right.title
    ]);
    const records = HubApp.el("div", { class: "hub-bank-records" }, [
      HubApp.el("h3", { class: "hub-bank-pair" }, title),
      HubApp.el("div", { class: "hub-bank-ids" }, [source(pair.left), source(pair.right)])
    ]);
    // (3) The two numerals: meaning in cobalt, wording in red (owner ruling O-02).
    const nums = HubApp.el("div", { class: "hub-bank-nums" }, [
      numeral("meaning", pair.meaning_text),
      numeral("wording", pair.wording_text),
      text("span", "P06.inferred", {}, { class: "hub-role hub-role--inferred" }),
      text("p", "B08.rank_score", { z: pair.rank_score_text }, { class: "hub-bank-rank-score" })
    ]);
    // (4) The body: labels, carried cells, the reading, the words, the actions.
    const role = HubApp.el("div", { class: "hub-bank-labels" }, [
      HubApp.el("p", { class: "hub-bank-engine" }, HubApp.data.engines[pair.engine].short_name),
      text("span", "P06.proposed", {}, { class: "hub-role hub-role--proposed" }),
      HubApp.el("span", { class: "hub-chip hub-bank-status" }, pair.label)
    ]);
    if (pair.weak) role.appendChild(text("span", "P06.hidden", {}, { class: "hub-hidden-label" }));
    if (pair.pair_class) {
      role.appendChild(HubApp.el("span", { class: "hub-chip hub-bank-class" }, HubApp.fmt("P10." + pair.pair_class)));
    }
    const reading = HubApp.el("div", { class: "hub-bank-reading" }, HubApp.el("p", {}, pair.reading));
    reading.appendChild(sharedLine(pair));
    if (readingKinds.includes(pair.reading_kind)) {
      reading.appendChild(HubApp.el("p", { class: "hub-bank-use" }, [
        text("strong", "B08.use.label"), " " + HubApp.fmt("B08.use." + pair.reading_kind)
      ]));
    }
    [pair.left, pair.right].forEach(function (side) {
      const record = HubApp.index.records.get(side.id);
      if (pair.flag_identical && record.identical_to.length) {
        reading.appendChild(text("p", "P09.identical", { ID: record.identical_to[0] }, { class: "hub-flag" }));
      }
      if (pair.flag_no_text && record.no_text) {
        reading.appendChild(text("p", "P09.no_text", {}, { class: "hub-flag" }));
      }
    });
    const open = text("a", "B08.open", {}, { class: "hub-button hub-button--quiet hub-bank-open-btn", href: href });
    const button = text("button", "B08.read", {}, { type: "button", class: "hub-button hub-bank-read" });
    button.addEventListener("click", function () { HubApp.select({ type: "pair", key: pair.key }, button); });
    const actions = HubApp.el("div", { class: "hub-bank-actions" }, [open, button]);
    const extrasRows = [extrasRow(pair.left, pair.left_extras), extrasRow(pair.right, pair.right_extras)];
    const body = HubApp.el("div", { class: "hub-bank-body" });
    [role].concat(extrasRows).concat([reading, actions]).forEach(function (part) {
      if (part) body.appendChild(part);
    });
    // Reading order stays index, titles and sources, numerals, body, picture, seed. CSS places
    // the picture in its own column from 1024 px; it only adds a description of the same facts.
    [rank, records, nums, body, figure(pair)].forEach(function (part) {
      if (part) item.appendChild(part);
    });
    // Phase 2.3 (D-04): the exact seed command as text to copy. It is the last child.
    // The page runs nothing: no button, no handler, no copy code.
    if (typeof pair.seed_command === "string") {
      item.appendChild(HubApp.el("div", { class: "hub-bank-seed" }, [
        text("span", "B16.label", {}, { class: "hub-chip hub-bank-seed-label" }),
        HubApp.el("code", { class: "hub-mono hub-bank-seed-command" }, pair.seed_command)
      ]));
    }
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
  // One legend for the pictures of the rows: the payload carries its words (plan 04).
  function figureLegend() {
    const figures = HubApp.data.figures;
    if (!figures || !figures.legend) return null;
    return HubApp.el("details", { class: "hub-bank-figures" }, [
      HubApp.el("summary", {}, figures.legend.summary),
      HubApp.el("p", {}, figures.legend.card)
    ]);
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
    const legend = figureLegend();
    if (legend) controls.appendChild(legend);
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
    if (HubApp.data.has_seed_commands === true) {
      controls.appendChild(text("p", "B16.hint", {}, { class: "hub-bank-seed-hint" }));
    }
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
