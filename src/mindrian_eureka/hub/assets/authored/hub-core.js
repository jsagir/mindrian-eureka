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
    "open", "min", "max", "step", "width", "height", "colspan", "rowspan"
  ]);
  const tagsAllowed = new Set([
    "a", "abbr", "article", "aside", "b", "bdi", "br", "button", "caption", "code",
    "dd", "details", "div", "dl", "dt", "em", "fieldset", "figcaption", "figure",
    "form", "h1", "h2", "h3", "h4", "hr", "img", "input", "label", "legend",
    "li", "nav", "ol", "option", "p", "section", "select", "small", "span",
    "strong", "summary", "table", "tbody", "td", "th", "thead", "tr", "ul"
  ]);
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
      panelOpen: false
    },
    index: { records: new Map(), pairs: new Map(), hoods: new Map() },
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
        link.addEventListener("click", function (event) { event.preventDefault(); app.go(name); });
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
      views.forEach(function (view, name) { view.render(document.getElementById(name)); });
      app.go("bank", { focus: false, route: true });
      route(false);
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
  function route(focus) {
    if (!started) return;
    const raw = window.location.hash.slice(1);
    if (!raw || names.includes(raw)) { app.go(raw || "bank", { focus: focus, route: true }); return; }
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
  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape" && app.state.panelOpen) app.clearSelection();
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
