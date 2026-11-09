(function () {
  "use strict";

  const views = new Map();
  const listeners = new Map();
  const names = ["bank", "graph", "catalogue"];
  const headings = { bank: "B01", graph: "Gr01", catalogue: "C01" };
  // The run reading band (Phase 2.3.1, D-04) fills the keys that payload.pattern carries.
  // deck keys: G16 G17.label G17.link G17.read G17.both G17.spread G17.hoods G17.single
  // deck keys: G17.bridges G17.weak G17.copies G17.classes G17.top_k G17.none G17.hidden Gr09
  // In-page anchors of the shell. Record ids that start with "hub-" use the "#record:" form
  // (deepLink), so no record collides with these names.
  const anchors = ["hub-results", "hub-data-check", "hub-footer", "hub-band"];
  const attrsAllowed = new Set([
    "id", "class", "type", "href", "src", "alt", "title", "role", "tabindex",
    "hidden", "disabled", "value", "name", "for", "placeholder", "scope",
    "autocomplete", "autocapitalize", "spellcheck", "checked", "selected",
    "open", "min", "max", "step", "width", "height", "colspan", "rowspan", "rel"
  ]);
  const tagsAllowed = new Set([
    "a", "abbr", "article", "aside", "b", "bdi", "br", "button", "caption", "code",
    "dd", "details", "div", "dl", "dt", "em", "fieldset", "figcaption", "figure",
    "form", "h1", "h2", "h3", "h4", "header", "hr", "img", "input", "label", "legend",
    "li", "nav", "ol", "option", "p", "section", "select", "small", "span",
    "strong", "summary", "table", "tbody", "td", "th", "thead", "tr", "ul"
  ]);
  // The pages of the mini site (Phase 2.3.1 plan 08, HUB-11): two page kinds, built by the
  // page script through registerPage. The route grammar is fixed (docs/brand/hub-site-rules.md).
  const pageKinds = ["pair", "record"];
  const pages = new Map();
  const pageParents = { pair: "bank", record: "catalogue" };
  const RANK = /^[1-9][0-9]{0,8}$/;
  let site = null;
  // Generated figures (Phase 2.3.1, D-07): the only tags and attributes a figure string may
  // carry. The figure generator of the build uses the same two lists; a static test compares
  // them. Anything else makes app.figure return null. Nothing is ever executed.
  const SVG_NS = "http://www.w3.org/2000/svg";
  const figureTags = ["svg", "title", "desc", "rect", "line", "circle", "text"];
  const figureAttrs = [
    "xmlns", "viewBox", "role", "class", "x", "y", "width", "height", "x1", "y1", "x2", "y2",
    "cx", "cy", "r", "fill", "stroke", "stroke-width", "stroke-dasharray", "opacity", "aria-hidden",
    "font-size"
  ];
  const figureTextTags = ["text", "title", "desc"];
  let panel = null;
  let opener = null;
  let started = false;
  const media = window.matchMedia("(prefers-reduced-motion: reduce)");
  const app = {
    data: null,
    copy: window.HUB_COPY || null,
    state: {
      view: "bank", selection: null,
      filters: { engine: "both", weak: false, query: "", file: "all", inPair: "all", pairClass: "all" },
      panelOpen: false, page: null
    },
    // Where the person is and was (a view name or "kind:key"), the scroll offset and the
    // opener link of each view, so a return from a page keeps the place.
    nav: { current: null, previous: null, scroll: {}, opener: {} },
    index: { records: new Map(), pairs: new Map(), hoods: new Map(), byRank: new Map() },
    fmt: function (id, values) {
      const text = app.copy && app.copy[id];
      if (typeof text !== "string") throw new Error("Unknown copy key: " + id);
      return text.replace(/\{([A-Za-z_][A-Za-z0-9_]*)\}/g, function (_, key) {
        if (!values || !Object.prototype.hasOwnProperty.call(values, key)) {
          throw new Error("Missing copy value: " + key);
        }
        return String(values[key]);
      });
    },
    el: function (tag, attrs, children) {
      if (!tagsAllowed.has(tag)) throw new Error("Unsupported element");
      const node = document.createElement(tag);
      Object.entries(attrs || {}).forEach(function (entry) {
        const key = entry[0];
        const value = entry[1];
        if (!attrsAllowed.has(key) && !/^(?:aria|data)-[a-z0-9-]+$/.test(key)) {
          throw new Error("Unsupported attribute");
        }
        if (value === null || value === undefined || (value === false && !key.startsWith("aria-"))) return;
        if ((key === "href" || key === "src") && !localURL(String(value))) {
          throw new Error("Link must be relative and local");
        }
        node.setAttribute(key, value === true && !key.startsWith("aria-") ? "" : String(value));
      });
      const items = Array.isArray(children) ? children : [children];
      items.forEach(function (child) {
        if (child === undefined || child === null) return;
        if (child instanceof Node) node.appendChild(child);
        else node.appendChild(document.createTextNode(String(child)));
      });
      return node;
    },
    on: function (name, fn) {
      if (!listeners.has(name)) listeners.set(name, []);
      listeners.get(name).push(fn);
    },
    emit: function (name, detail) {
      (listeners.get(name) || []).forEach(function (fn) {
        try { fn(detail); } catch (error) { console.error(error); }
      });
      views.forEach(function (view) {
        if (typeof view.onEvent === "function") {
          try { view.onEvent(name, detail); } catch (error) { console.error(error); }
        }
      });
    },
    registerView: function (name, view) {
      if (!names.includes(name)) throw new Error("Unknown view");
      views.set(name, view);
      if (started) view.render(document.getElementById(name));
    },
    registerPanel: function (value) {
      panel = value;
      if (app.state.selection) panel.show(app.state.selection, opener);
    },
    registerPage: function (kind, builder) {
      if (!pageKinds.includes(kind)) throw new Error("Unknown page kind");
      if (typeof builder !== "function") throw new Error("A page builder is a function");
      pages.set(kind, builder);
    },
    select: function (selection, source) {
      const index = selection && selection.type === "record" ? app.index.records : app.index.pairs;
      const key = selection && (selection.type === "record" ? selection.id : selection.key);
      if (!selection || !["record", "pair"].includes(selection.type) || !index.has(key)) return;
      app.state.selection = { ...selection };
      opener = source || document.activeElement;
      app.state.panelOpen = true;
      if (selection.type === "record") address(deepLink(selection.id));
      app.emit("select", app.state.selection);
      if (panel) panel.show(app.state.selection, opener);
    },
    clearSelection: function () {
      app.state.selection = null;
      app.state.panelOpen = false;
      if (panel) panel.hide();
      app.emit("clear", null);
      const target = opener && opener !== document.body && document.contains(opener)
        && typeof opener.focus === "function" && opener.matches("a[href],button,input,select,textarea,summary,[tabindex]")
        && !opener.matches(":disabled") && opener.getClientRects().length
        && getComputedStyle(opener).visibility !== "hidden"
        ? opener : document.getElementById("hub-title");
      if (target) target.focus();
      opener = null;
    },
    setFilter: function (name, value) {
      if (!Object.prototype.hasOwnProperty.call(app.state.filters, name)) {
        throw new Error("Unknown filter");
      }
      app.state.filters[name] = value;
      app.emit("filter", { name: name, value: value });
    },
    go: function (name, options) {
      if (!started || !names.includes(name)) return;
      leavePage();
      app.state.view = name;
      names.forEach(function (view) {
        const section = document.getElementById(view);
        section.hidden = false;
        section.classList.toggle("is-active", view === name);
        section.querySelectorAll("[data-view-heading]").forEach(function (heading) {
          heading.hidden = true;
        });
        const link = document.querySelector('#hub-nav a[href="#' + view + '"]');
        if (link) {
          if (name === view) link.setAttribute("aria-current", "page");
          else link.removeAttribute("aria-current");
        }
      });
      document.getElementById("hub-title").textContent = app.fmt(headings[name]);
      document.title = app.fmt("G01." + name);
      if (!options || !options.route) address("#" + name);
      track(name);
      app.emit("view", name);
      if (!options || options.focus !== false) document.getElementById("hub-title").focus();
    },
    search: function (query, limit) {
      const text = String(query).trim().toLowerCase();
      if (!text || !app.data) return [];
      const tokens = text.split(/\s+/);
      const matches = [];
      app.index.records.forEach(function (record) {
        const id = record.id.toLowerCase();
        const title = record.title.toLowerCase();
        const body = record.text.toLowerCase();
        const haystack = id + " " + title + " " + body;
        if (tokens.every(function (token) { return haystack.includes(token); })) {
          const rank = id === text ? 0 : id.startsWith(text) ? 1
            : tokens.every(function (token) { return title.includes(token); }) ? 2 : 3;
          matches.push({ id: record.id, rank: rank });
        }
      });
      matches.sort(function (a, b) {
        return a.rank - b.rank || (a.id < b.id ? -1 : a.id > b.id ? 1 : 0);
      });
      return matches.slice(0, limit === undefined ? app.data.config.find_max : Math.max(0, limit))
        .map(function (item) { return item.id; });
    },
    motion: {
      reduced: media.matches,
      ms: function (name) {
        if (app.motion.reduced) return 0;
        const value = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
        const parsed = parseFloat(value);
        return Number.isFinite(parsed) ? parsed * (value.endsWith("ms") ? 1 : 1000) : 0;
      }
    },
    figure: function (markup) { return safeFigure(markup); },
    notice: function (text) {
      let region = document.getElementById("hub-notice");
      if (!region) {
        region = app.el("p", { id: "hub-notice", "aria-live": "polite" });
        document.getElementById("hub-results").prepend(region);
      }
      region.textContent = String(text);
    },
    start: function (payload) {
      if (started) return;
      app.copy = window.HUB_COPY || app.copy;
      if (!app.copy) { fallback(); return; }
      if (!payload || payload.schema !== "eureka.hub-data.v1") {
        showError(payload ? "E03" : "E01", payload ? "E04" : "E02");
        return;
      }
      app.data = payload;
      app.index.records = new Map(payload.records.map(function (r) { return [r.id, r]; }));
      app.index.pairs = new Map(payload.pairs.map(function (p) { return [p.key, p]; }));
      app.index.hoods = new Map(payload.hoods.map(function (h) { return [h.number, h]; }));
      app.index.byRank = new Map(payload.pairs.map(function (p) { return [p.engine + ":" + p.rank, p]; }));
      started = true;
      document.documentElement.classList.add("js");
      document.getElementById("hub-meaning").textContent = app.fmt("G07");
      document.getElementById("hub-status").textContent = payload.pairs.length
        ? app.fmt("G06") : app.fmt("B10") + " " + app.fmt("B11");
      face(payload.pairs.length ? "handover" : "limit");
      const counts = document.getElementById("hub-counts");
      counts.replaceChildren();
      ["records", "unusual_pairs", "wording_and_meaning", "hoods"].forEach(function (key) {
        const value = key === "records" || key === "hoods" ? payload.counts[key] : payload.counts.pairs[key];
        counts.appendChild(app.el("div", { class: "hub-count" }, [
          app.el("strong", {}, value), app.el("span", {}, app.fmt("G11." + key))
        ]));
      });
      band(payload.pattern);
      const nav = document.getElementById("hub-nav");
      nav.replaceChildren();
      names.forEach(function (name) {
        const link = app.el("a", { href: "#" + name, "aria-label": app.fmt("G09." + name + ".long") }, [
          app.el("span", { class: "hub-nav-short", "aria-hidden": "true" }, app.fmt("G09." + name + ".short")),
          app.el("span", { class: "hub-nav-long", "aria-hidden": "true" }, app.fmt("G09." + name + ".long"))
        ]);
        link.addEventListener("click", function (event) {
          event.preventDefault();
          // From a page the view is a route change, so the page stays in the history and the
          // browser's own Back returns to it. On a view the switch is in place, as before.
          if (app.state.page) window.location.hash = "#/" + (name === "bank" ? "" : name);
          else app.go(name);
        });
        nav.appendChild(link);
      });
      const check = payload.data_check;
      const removed = app.fmt("D02.removed", { n: check.removed_count, reason: check.removed_text })
        .replace(". .", ".");
      document.getElementById("hub-data-check").replaceChildren(
        app.el("h2", {}, app.fmt("D01")),
        app.el("p", {}, app.fmt("D02.same", { n: check.identical_records })),
        app.el("p", {}, app.fmt("D02.empty", { n: check.no_text_records })),
        app.el("p", {}, removed), app.el("p", {}, app.fmt("D02.boilerplate")),
        app.el("p", {}, app.fmt("D03"))
      );
      document.getElementById("hub-footer").replaceChildren(
        app.el("p", {}, app.fmt("G05")),
        app.el("p", {}, app.fmt("G14", { version: payload.tool_version,
          fingerprint: payload.run_fingerprint.slice(0, 12), records: payload.counts.records }))
      );
      ["hub-counts", "hub-nav", "hub-header-action", "hub-results", "hub-data-check", "hub-panel"]
        .forEach(function (id) {
          const node = document.getElementById(id);
          if (node) node.hidden = false;
        });
      app.notice("");
      // The hub places the scroll itself: a page opens at its top and a view gets its saved
      // offset back (restorePlace), so the browser's own restoration must not overwrite it.
      if ("scrollRestoration" in window.history) window.history.scrollRestoration = "manual";
      // The page section sits after the views; empty and hidden until a page route is shown.
      site = app.el("section", { id: "hub-site", hidden: true });
      document.getElementById("hub-results").appendChild(site);
      views.forEach(function (view, name) { view.render(document.getElementById(name)); });
      app.go("bank", { focus: false, route: true });
      route(false);
      // A page opened by a direct link has no previous page in this document.
      app.nav.previous = null;
      measureHeader();
      app.emit("start", payload);
    }
  };

  function measureHeader() {
    // The sticky header exposes its measured height, so scroll-padding and the stage of
    // plan 07 follow the real header (book layout: a sticky stage sets scroll-padding-top
    // from its own height variable). One read on start, resize and fonts ready; no loop,
    // because the header height never depends on the variable.
    const header = document.getElementById("hub-header");
    if (!header) return;
    document.documentElement.style.setProperty("--hub-header-height", header.offsetHeight + "px");
  }
  function figureNodeOk(element) {
    if (element.namespaceURI !== SVG_NS || !figureTags.includes(element.localName)) return false;
    const attributes = Array.from(element.attributes);
    for (let i = 0; i < attributes.length; i += 1) {
      const name = attributes[i].name;
      const value = String(attributes[i].value).toLowerCase();
      if (name === "id" || !figureAttrs.includes(name)) return false;
      if (value.includes("url(") || value.includes("javascript:") || value.includes("href")) return false;
    }
    const children = Array.from(element.childNodes);
    if (figureTextTags.includes(element.localName)) {
      return children.length === 0 || (children.length === 1 && children[0].nodeType === Node.TEXT_NODE);
    }
    return children.every(function (child) {
      return child.nodeType === Node.ELEMENT_NODE && figureNodeOk(child);
    });
  }
  function safeFigure(markup) {
    // Turn a figure string into a safe SVG element, or return null. XML parse only, an
    // allow-list of tags and attributes, no id, no url(), no javascript:, no href. The node
    // is imported, never written as HTML text.
    if (typeof markup !== "string" || markup.length === 0) return null;
    try {
      const parsed = new DOMParser().parseFromString(markup, "image/svg+xml");
      if (!parsed || parsed.doctype || parsed.getElementsByTagName("parsererror").length) return null;
      const root = parsed.documentElement;
      if (!root || root.namespaceURI !== SVG_NS || root.localName !== "svg") return null;
      if (!figureNodeOk(root)) return null;
      return document.importNode(root, true);
    } catch (_) {
      return null;
    }
  }

  function localURL(value) {
    return value.length > 0 && !/^[\\/]|[\u0000-\u0020\u007f]|^[a-z][a-z0-9+.-]*:/i.test(value);
  }
  function address(hash) { window.history.replaceState(null, "", hash); }
  function deepLink(id) {
    const reserved = names.includes(id) || /^(hub-|bank-|graph-|catalogue-|record:)/.test(id);
    // Match the Python deep_link contract including escaped shell and route prefixes.
    return "#" + (reserved ? "record:" : "") + encodeURIComponent(id).replace(/[!'()*]/g, function (c) {
      return "%" + c.charCodeAt(0).toString(16).toUpperCase();
    });
  }
  function face(state) {
    document.getElementById("hub-face").setAttribute("src", "assets/faces/theo-" + state + ".svg");
  }
  function fallback() { document.documentElement.classList.remove("js"); }
  function band(pattern) {
    // Render the run reading band from the same deck strings as the server markup. Without
    // a pattern the band stays empty and hidden (a locked page before unlock has none).
    const section = document.getElementById("hub-band");
    if (!section) return;
    section.replaceChildren();
    if (!pattern || !Array.isArray(pattern.lines) || !pattern.lines.length) {
      section.hidden = true;
      return;
    }
    const lines = pattern.lines.slice(0, -1);
    const reading = lines.map(function (line) { return app.fmt(line.key, line.values); }).join(" ");
    section.appendChild(app.el("p", { id: "hub-band-label", class: "hub-band-label" }, [
      app.el("span", { class: "hub-band-mark", "aria-hidden": "true" }), app.fmt("G17.label")
    ]));
    section.appendChild(app.el("p", { class: "hub-band-reading" }, reading));
    section.appendChild(app.el("p", { class: "hub-band-limit mos-secondary" }, app.fmt("G16")));
    section.appendChild(app.el("a", { class: "hub-band-link", href: "#hub-data-check" }, app.fmt("G17.link")));
    section.className = "hub-band mos-ground-ink";
    section.setAttribute("aria-labelledby", "hub-band-label");
    section.hidden = false;
  }
  function showError(heading, body) {
    fallback();
    face("limit");
    const status = document.getElementById("hub-status");
    status.classList.add("hub-error");
    status.replaceChildren(app.el("h2", {}, app.fmt(heading)), app.el("p", {}, app.fmt(body)));
  }
  function track(key) {
    if (app.nav.current === key) return;
    app.nav.previous = app.nav.current;
    app.nav.current = key;
  }
  // The route grammar of the mini site (plan 08). Every hash that starts with "/" is parsed
  // here; any other hash keeps the Phase 2.1 path (view names, in-page anchors, record ids).
  // A rank is 1 to 9 digits with no leading zero; an engine key must be an own property of
  // the payload engines; a record id is decoded in a try block and looked up in the index.
  function parseHash(raw) {
    if (raw === "/") return { kind: "view", name: "bank" };
    if (raw === "/graph" || raw === "/catalogue") return { kind: "view", name: raw.slice(1) };
    if (raw.startsWith("/pair/")) {
      const parts = raw.slice(6).split("/");
      if (parts.length !== 2 || !RANK.test(parts[1])) return { kind: "unknown" };
      if (!Object.prototype.hasOwnProperty.call(app.data.engines, parts[0])) return { kind: "unknown" };
      const pair = app.index.byRank.get(parts[0] + ":" + parts[1]);
      return pair ? { kind: "pair", key: pair.key, item: pair } : { kind: "unknown" };
    }
    if (raw.startsWith("/record/")) {
      let id;
      try { id = decodeURIComponent(raw.slice(8)); } catch (_) { return { kind: "unknown" }; }
      const record = app.index.records.get(id);
      return record ? { kind: "record", key: id, item: record } : { kind: "unknown" };
    }
    return { kind: "unknown" };
  }
  function leavePage() {
    if (!app.state.page) return;
    document.getElementById("hub-page").classList.remove("hub-on-page");
    if (site) { site.hidden = true; site.replaceChildren(); }
    app.state.page = null;
    app.emit("page", null);
  }
  function showPage(kind, key, item, focus) {
    const builder = pages.get(kind);
    const built = builder ? builder(item) : null;
    if (!built || !site) { app.notice(app.fmt("E05", { ID: window.location.hash.slice(1) })); return; }
    if (app.state.panelOpen) app.clearSelection();
    if (!app.state.page) {
      // Coming from a view: keep its place (the scroll offset and the link that was used).
      const view = app.state.view;
      const section = document.getElementById(view);
      const active = document.activeElement;
      // Only the view that was just left keeps its place; an older place of another view
      // would otherwise come back when the knob follows its link to that view.
      app.nav.scroll = {};
      app.nav.opener = {};
      app.nav.scroll[view] = window.scrollY;
      app.nav.opener[view] = active && active.tagName === "A" && section && section.contains(active)
        ? active.getAttribute("href") : null;
    }
    app.state.page = { kind: kind, key: key };
    document.getElementById("hub-page").classList.add("hub-on-page");
    site.replaceChildren.apply(site, built.nodes);
    site.hidden = false;
    document.querySelectorAll("#hub-nav a").forEach(function (link) { link.removeAttribute("aria-current"); });
    const parent = document.querySelector('#hub-nav a[href="#' + pageParents[kind] + '"]');
    if (parent) parent.setAttribute("aria-current", "true");
    document.title = String(built.title);
    track(kind + ":" + key);
    const region = document.getElementById("hub-notice");
    if (region && region.textContent) region.textContent = "";
    if (focus !== false) {
      window.scrollTo({ top: 0, left: 0, behavior: "instant" });
      built.heading.focus({ preventScroll: true });
    }
    app.emit("page", app.state.page);
  }
  function restorePlace(name, fromPage) {
    if (!fromPage) return;
    const section = document.getElementById(name);
    const href = app.nav.opener[name];
    if (section && typeof href === "string") {
      const match = Array.from(section.querySelectorAll("a[href]")).find(function (link) {
        return link.getAttribute("href") === href && link.getClientRects().length > 0;
      });
      if (match) match.focus({ preventScroll: true });
    }
    if (typeof app.nav.scroll[name] === "number") {
      window.scrollTo({ top: app.nav.scroll[name], left: 0, behavior: "instant" });
    }
  }
  function route(focus) {
    if (!started) return;
    const raw = window.location.hash.slice(1);
    // Read before the view changes: a return from a page (by the Back knob through
    // history.back(), which lands on the entry's own hash, "" or "#bank" as well as "#/")
    // gets its place on the list back.
    const fromPage = app.state.page !== null;
    if (raw.startsWith("/")) {
      const parsed = parseHash(raw);
      if (parsed.kind === "view") {
        app.go(parsed.name, { focus: focus, route: true });
        restorePlace(parsed.name, fromPage);
      } else if (parsed.kind === "unknown") {
        app.notice(app.fmt("E05", { ID: raw }));
      } else {
        showPage(parsed.kind, parsed.key, parsed.item, focus);
      }
      return;
    }
    if (!raw || names.includes(raw)) {
      app.go(raw || "bank", { focus: focus, route: true });
      restorePlace(raw || "bank", fromPage);
      return;
    }
    // An in-page anchor is not a record: the browser scrolls to it by itself, and no E05
    // notice is raised. Record ids that start with "hub-" use the "#record:" form, so no
    // record collides with these four names.
    if (anchors.includes(raw)) return;
    let id;
    try { id = decodeURIComponent(raw.startsWith("record:") ? raw.slice(7) : raw); }
    catch (_) { app.notice(app.fmt("E05", { ID: raw })); return; }
    const record = app.index.records.get(id);
    if (!record) { app.notice(app.fmt("E05", { ID: id })); return; }
    // Records in visible pairs open the graph; other records open the catalogue.
    app.go(record.visible_pair_count > 0 ? "graph" : "catalogue", { focus: focus, route: true });
    app.select({ type: "record", id: id }, document.getElementById("hub-title"));
  }
  media.addEventListener("change", function (event) { app.motion.reduced = event.matches; });
  window.addEventListener("hashchange", function () { route(true); });
  function backKnob() { return site ? site.querySelector("a[data-back]") : null; }
  // The Back knob rule (plan 08): when the previous page is the parent of this page, go back
  // in the history so the place on the list returns; otherwise the link navigates.
  document.addEventListener("click", function (event) {
    if (event.defaultPrevented || event.button !== 0) return;
    if (event.altKey || event.ctrlKey || event.metaKey || event.shiftKey) return;
    const knob = event.target instanceof Element ? event.target.closest("#hub-site a[data-back]") : null;
    if (!knob) return;
    if (app.nav.previous === knob.getAttribute("data-back") && window.history.length > 1) {
      event.preventDefault();
      window.history.back();
    }
  });
  document.addEventListener("keydown", function (event) {
    if (event.defaultPrevented || event.altKey || event.ctrlKey || event.metaKey) return;
    const target = event.target instanceof Element ? event.target : null;
    if (target && (target.matches("input, textarea, select") || target.isContentEditable)) return;
    if (event.key === "Escape") {
      if (app.state.panelOpen) { app.clearSelection(); return; }
      const knob = app.state.page ? backKnob() : null;
      if (knob) knob.click();
      return;
    }
    if (!app.state.page || !site) return;
    if (event.key === "ArrowLeft" || event.key === "ArrowRight") {
      const link = site.querySelector(event.key === "ArrowLeft" ? 'a[rel="prev"]' : 'a[rel="next"]');
      if (link) window.location.hash = link.getAttribute("href");
    }
  });
  window.HubApp = app;
  window.addEventListener("resize", measureHeader);
  document.addEventListener("DOMContentLoaded", function () {
    measureHeader();
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(measureHeader);
    if (!window.HUB_COPY) { fallback(); return; }
    if (!window.HUB && document.getElementById("hub-locked")) return;
    app.start(window.HUB);
  });
})();
