(function () {
  "use strict";

  // The pair page and the record page of the mini site (Phase 2.3.1 plan 08, HUB-11, HUB-06).
  // This file touches no DOM at load: it registers two page builders with the core, which
  // calls them on a page route. Text nodes only, through HubApp.el; figures only through
  // HubApp.figure; no network, no storage.
  const HubApp = window.HubApp;
  if (!HubApp || !HubApp.copy) return;
  const engines = ["unusual_pairs", "wording_and_meaning"];
  const EXCERPT_WORDS = 60;
  const lists = new Map();
  // deck keys: G19.prev.pair G19.next.pair G19.prev.record G19.next.record G19.knobs.pair
  // deck keys: G19.knobs.record G19.pos.pair G19.pos.record G19.back.bank G19.back.catalogue
  // deck keys: B08.use.meaning B08.use.wording B08.use.agree

  function text(tag, key, values, attrs) {
    return HubApp.el(tag, attrs || {}, HubApp.fmt(key, values));
  }
  function own(object, key) {
    return Boolean(object) && typeof object === "object" && Object.prototype.hasOwnProperty.call(object, key);
  }
  function pairHref(pair) { return "#/pair/" + pair.engine + "/" + pair.rank; }
  function recordHref(id) { return "#/record/" + encodeURIComponent(id); }
  function engineList(engine) {
    if (!lists.has(engine)) {
      lists.set(engine, HubApp.data.pairs.filter(function (pair) { return pair.engine === engine; })
        .sort(function (a, b) { return a.rank - b.rank; }));
    }
    return lists.get(engine);
  }
  function words(id) {
    const terms = HubApp.data.terms;
    const list = terms && own(terms.records, id) ? terms.records[id] : null;
    return Array.isArray(list) ? list.map(String) : null;
  }
  function sharedWords(pairId) {
    const terms = HubApp.data.terms;
    const list = terms && own(terms.pairs, pairId) ? terms.pairs[pairId] : null;
    return Array.isArray(list) ? list.map(String) : null;
  }
  function figureEntry(key) {
    const figures = HubApp.data.figures;
    return figures && own(figures.pairs, key) ? figures.pairs[key] : null;
  }
  // The same chunking as the reading panel: about 80 to 100 words, cut at a sentence end.
  function sourceProse(value, className) {
    const chunks = [];
    let buffer = "", count = 0, boundary = 0;
    (String(value).match(/\S+\s*|\s+/gu) || []).forEach(function (token) {
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
  function excerpt(value) {
    const all = String(value).split(/\s+/u).filter(Boolean);
    const cut = all.length > EXCERPT_WORDS;
    return all.slice(0, EXCERPT_WORDS).join(" ") + (cut ? HubApp.fmt("G19.more") : "");
  }
  function crumbs(items) {
    const list = HubApp.el("ol");
    items.forEach(function (item, index) {
      const last = index === items.length - 1;
      list.appendChild(HubApp.el("li", {}, last
        ? HubApp.el("span", { "aria-current": "page" }, item.text)
        : HubApp.el("a", { href: item.href }, item.text)));
    });
    return HubApp.el("nav", { class: "hub-crumbs", "aria-label": HubApp.fmt("G19.crumb.label") }, list);
  }
  function knob(kind, direction, href) {
    const word = HubApp.fmt(direction === "prev" ? "G19.prev" : "G19.next");
    if (!href) {
      return HubApp.el("span", {
        class: "hub-knob hub-knob--" + direction + " hub-knob--off", "aria-hidden": "true"
      }, word);
    }
    return HubApp.el("a", {
      class: "hub-knob hub-knob--" + direction, href: href, rel: direction,
      "aria-label": HubApp.fmt("G19." + direction + "." + kind)
    }, word);
  }
  // config: { kind: "pair" | "record", parent: "bank" | "catalogue", index, count, prevHref, nextHref }
  function knobs(config) {
    const parentHref = config.parent === "bank" ? "#/" : "#/catalogue";
    return HubApp.el("nav", { class: "hub-knobs", "aria-label": HubApp.fmt("G19.knobs." + config.kind) }, [
      text("a", "G19.back." + config.parent, {}, {
        class: "hub-knob hub-knob--back", href: parentHref, "data-back": config.parent
      }),
      text("span", "G19.pos." + config.kind, { n: config.index + 1, k: config.count }, { class: "hub-knob-pos" }),
      HubApp.el("span", { class: "hub-knob-pair" }, [
        knob(config.kind, "prev", config.prevHref), knob(config.kind, "next", config.nextHref)
      ])
    ]);
  }
  function eyebrow(children) {
    return HubApp.el("p", { class: "hub-eyebrow" },
      [HubApp.el("span", { class: "hub-eyebrow-dot", "aria-hidden": "true" })].concat(children));
  }
  function numeral(kind, value) {
    return HubApp.el("p", { class: "hub-bank-num" }, [
      HubApp.el("b", { class: "hub-bank-numeral hub-bank-numeral--" + kind }, value),
      text("span", "B08.caption." + kind, {}, { class: "hub-bank-caption" })
    ]);
  }
  function chip(value) { return HubApp.el("span", { class: "hub-chip" }, value); }
  function group(label, value) {
    return HubApp.el("div", {}, [HubApp.el("dt", {}, label), HubApp.el("dd", {}, value)]);
  }
  // The real-text twin of the detail figure: every fact of the drawing as text, read by
  // assistive technology at every width and shown under 768 px (the drawing text would fall
  // under the 13 px floor there). Built only when the words and the figure exist.
  function twin(pair, node) {
    const labels = HubApp.data.figures.labels || {};
    const wordsA = words(pair.left.id);
    const wordsB = words(pair.right.id);
    const shared = sharedWords(pair.pair_id);
    if (!wordsA || !wordsB || !shared) return null;
    const recordA = HubApp.el("div", {}, [
      HubApp.el("dt", {}, String(labels.record_a)), HubApp.el("dd", {}, pair.left.title),
      HubApp.el("dt", {}, String(labels.distinctive)), HubApp.el("dd", {}, wordsA.join(", "))
    ]);
    const recordB = HubApp.el("div", {}, [
      HubApp.el("dt", {}, String(labels.record_b)), HubApp.el("dd", {}, pair.right.title),
      HubApp.el("dt", {}, String(labels.distinctive)), HubApp.el("dd", {}, wordsB.join(", "))
    ]);
    const list = HubApp.el("dl", {}, [
      recordA, recordB,
      group(String(labels.shared), shared.length ? shared.join(", ") : String(labels.none_shared)),
      group(String(labels.meaning), pair.meaning_text),
      group(String(labels.wording), pair.wording_text)
    ]);
    const desc = node.querySelector("desc");
    return HubApp.el("section", { class: "hub-pair-twin" }, [
      text("h2", "G19.twin.heading"), list, HubApp.el("p", {}, desc ? desc.textContent : "")
    ]);
  }
  function figureBlock(pair) {
    const entry = figureEntry(pair.key);
    const node = entry && typeof entry.detail === "string" ? HubApp.figure(entry.detail) : null;
    if (!node) return [];
    const legend = HubApp.data.figures.legend || {};
    const parts = [HubApp.el("div", { class: "hub-pair-figure", "aria-hidden": "true" }, node)];
    const twinNode = twin(pair, node);
    if (twinNode) parts.push(twinNode);
    parts.push(HubApp.el("figcaption", {}, String(legend.caption || "")));
    return [
      HubApp.el("figure", { class: "hub-pair-figure-block" }, parts),
      HubApp.el("details", { class: "hub-pair-legend" }, [
        HubApp.el("summary", {}, String(legend.summary || "")),
        HubApp.el("p", {}, String(legend.detail || ""))
      ])
    ];
  }
  function recordCard(side) {
    const record = HubApp.index.records.get(side.id);
    const source = HubApp.el("a", {
      class: "hub-link hub-mono", href: side.source_link,
      "aria-label": HubApp.fmt("B08.source_name", { ID: side.id, title: side.title })
    }, HubApp.el("bdi", {}, side.id));
    return HubApp.el("article", { class: "hub-site-record" }, [
      source,
      HubApp.el("h3", {}, HubApp.el("a", { href: recordHref(side.id) }, side.title)),
      HubApp.el("p", { class: "hub-site-excerpt" }, excerpt(record ? record.text : "")),
      text("a", "G19.record.read", {}, { class: "hub-link hub-site-record-read", href: recordHref(side.id) })
    ]);
  }
  function meanings(keys) {
    const section = HubApp.el("section", { class: "hub-site-meaning" }, [text("h2", "P03.meaning"), text("p", "G16")]);
    keys.forEach(function (key) {
      section.appendChild(HubApp.el("details", {}, [
        HubApp.el("summary", {}, HubApp.data.engines[key].name),
        HubApp.el("p", {}, HubApp.data.engines[key].score_meaning)
      ]));
    });
    return section;
  }
  function buildPair(pair) {
    const list = engineList(pair.engine);
    const index = list.indexOf(pair);
    if (index < 0) return null;
    const engine = HubApp.data.engines[pair.engine];
    const config = {
      kind: "pair", parent: "bank", index: index, count: list.length,
      prevHref: index > 0 ? pairHref(list[index - 1]) : null,
      nextHref: index < list.length - 1 ? pairHref(list[index + 1]) : null
    };
    const heading = HubApp.el("h1", { class: "hub-site-title", tabindex: "-1" }, [
      pair.left.title, " ", text("span", "G19.and", {}, { class: "hub-site-and" }), " ", pair.right.title
    ]);
    const head = HubApp.el("header", { class: "hub-site-head" }, [
      eyebrow([HubApp.fmt("G19.pair.eyebrow", { n: pair.rank, engine: engine.short_name }), " ",
        text("span", "P06.proposed", {}, { class: "hub-role hub-role--proposed" })]),
      heading, chip(pair.label)
    ]);
    if (pair.weak) head.appendChild(text("span", "P06.hidden", {}, { class: "hub-hidden-label" }));
    const nodes = [
      crumbs([{ text: HubApp.fmt("G19.crumb.bank"), href: "#/" }, { text: HubApp.fmt("G19.crumb.pair", { n: pair.rank }) }]),
      knobs(config), head,
      HubApp.el("div", { class: "hub-site-nums" }, [
        numeral("meaning", pair.meaning_text), numeral("wording", pair.wording_text),
        text("p", "B08.rank_score", { z: pair.rank_score_text }, { class: "hub-mono" })
      ]),
      HubApp.el("p", { class: "hub-site-reading" }, pair.reading)
    ];
    const otherKey = engines[1 - engines.indexOf(pair.engine)];
    const other = engineList(otherKey).find(function (item) { return item.pair_id === pair.pair_id; });
    if (other) {
      nodes.push(HubApp.el("p", { class: "hub-pair-also-line" }, text("a", "G19.pair.also", {
        engine: HubApp.data.engines[otherKey].short_name, n: other.rank
      }, { class: "hub-link hub-pair-also", href: pairHref(other) })));
    }
    figureBlock(pair).forEach(function (node) { nodes.push(node); });
    if (["meaning", "wording", "agree"].includes(pair.reading_kind)) {
      nodes.push(HubApp.el("p", { class: "hub-site-use" }, [
        text("strong", "B08.use.label"), " " + HubApp.fmt("B08.use." + pair.reading_kind)
      ]));
    }
    nodes.push(meanings([pair.engine]));
    nodes.push(HubApp.el("section", { class: "hub-site-records" }, [
      text("h2", "P03.two"),
      HubApp.el("div", { class: "hub-site-record-list" }, [recordCard(pair.left), recordCard(pair.right)])
    ]));
    nodes.push(knobs(config));
    return {
      title: HubApp.fmt("G19.doc.pair", { n: pair.rank, x: pair.left.title, y: pair.right.title }),
      heading: heading, nodes: nodes
    };
  }
  function pairItem(record, pair) {
    const partnerId = pair.left.id === record.id ? pair.right.id : pair.left.id;
    const partner = HubApp.index.records.get(partnerId);
    const thumb = HubApp.el("div", { class: "hub-site-thumb", "aria-hidden": "true" });
    const entry = figureEntry(pair.key);
    const card = entry && typeof entry.card === "string" ? HubApp.figure(entry.card) : null;
    if (card) thumb.appendChild(card);
    const body = HubApp.el("div", { class: "hub-site-pair-body" }, [
      HubApp.el("p", { class: "hub-site-pair-line" }, [
        text("a", "B08.rank", { n: pair.rank }, { class: "hub-link hub-site-pair-link", href: pairHref(pair) }),
        " ",
        HubApp.el("span", { class: "hub-site-pair-engine" }, HubApp.data.engines[pair.engine].short_name)
      ]),
      HubApp.el("p", { class: "hub-site-partner-line" }, HubApp.el("a", {
        class: "hub-link hub-site-partner", href: recordHref(partnerId)
      }, partner ? partner.title : partnerId)),
      HubApp.el("div", { class: "hub-site-pair-nums" }, [
        numeral("meaning", pair.meaning_text), numeral("wording", pair.wording_text)
      ])
    ]);
    return HubApp.el("li", { class: "hub-site-pair" }, [thumb, body]);
  }
  function buildRecord(record) {
    const list = HubApp.data.records;
    const index = list.indexOf(record);
    if (index < 0) return null;
    const config = {
      kind: "record", parent: "catalogue", index: index, count: list.length,
      prevHref: index > 0 ? recordHref(list[index - 1].id) : null,
      nextHref: index < list.length - 1 ? recordHref(list[index + 1].id) : null
    };
    const heading = HubApp.el("h1", { class: "hub-site-title", tabindex: "-1" }, record.title);
    const nodes = [
      crumbs([{ text: HubApp.fmt("G19.crumb.catalogue"), href: "#/catalogue" }, { text: record.id }]),
      knobs(config),
      HubApp.el("header", { class: "hub-site-head" }, [
        eyebrow([HubApp.fmt("G19.record.eyebrow")]), heading, chip(record.label)
      ]),
      HubApp.el("div", { class: "hub-site-source hub-mono" }, [
        HubApp.el("bdi", {}, record.id),
        HubApp.el("span", {}, [text("span", "P04.file"), " ", HubApp.el("bdi", {}, record.source_file)]),
        HubApp.el("span", {}, [text("span", "P04.ref"), " ", HubApp.el("bdi", {}, record.source_ref)]),
        text("a", "P05.open", {}, { class: "hub-link", href: record.source_link })
      ])
    ];
    if (record.identical_to.length) {
      nodes.push(text("p", "P09.identical", { ID: record.identical_to[0] }, { class: "hub-flag" }));
    }
    if (record.no_text) nodes.push(text("p", "P09.no_text", {}, { class: "hub-flag" }));
    nodes.push(HubApp.el("section", { class: "hub-site-text" }, [
      text("h2", "P03.text"), sourceProse(record.text, "hub-site-prose")
    ]));
    const list2 = words(record.id);
    const wordsSection = HubApp.el("section", { class: "hub-site-words" }, text("h2", "G19.record.words"));
    if (list2 && list2.length) {
      wordsSection.appendChild(HubApp.el("ul", {}, list2.map(function (word) {
        return HubApp.el("li", { class: "hub-chip" }, word);
      })));
    } else {
      wordsSection.appendChild(text("p", "G19.record.no_words"));
    }
    nodes.push(wordsSection);
    const pairs = record.pair_keys.map(function (key) { return HubApp.index.pairs.get(key); })
      .filter(Boolean);
    const pairSection = HubApp.el("section", { class: "hub-site-pairs" }, text("h2", "P03.pairs", { n: pairs.length }));
    if (pairs.length) {
      pairSection.appendChild(HubApp.el("ul", { class: "hub-site-pair-list" }, pairs.map(function (pair) {
        return pairItem(record, pair);
      })));
    } else {
      pairSection.appendChild(text("p", "G19.record.no_pairs"));
    }
    nodes.push(pairSection);
    nodes.push(knobs(config));
    return { title: HubApp.fmt("G19.doc.record", { title: record.title }), heading: heading, nodes: nodes };
  }
  HubApp.registerPage("pair", buildPair);
  HubApp.registerPage("record", buildRecord);
})();
