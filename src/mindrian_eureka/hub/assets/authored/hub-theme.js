(function () { "use strict";
  // The light and dark theme toggle (Phase 2.3.1 plan 05, HUB-10). The early script in the
  // head applies a saved choice before paint; this script owns the button. The theme is one
  // attribute on the root element; the CSS token set does the rest. One storage key, two
  // values, every storage call inside try. No markup strings, no timer, no animation.
  // deck keys: G03.theme.dark G03.theme.light G03.theme.name
  var root = document.documentElement;
  var media = window.matchMedia("(prefers-color-scheme: dark)");
  var button = null;

  function copy(id) {
    var app = window.HubApp;
    if (app && app.copy && typeof app.copy[id] === "string") return app.fmt(id);
    var deck = window.HUB_COPY;
    return deck && typeof deck[id] === "string" ? deck[id] : "";
  }
  function current() {
    var set = root.getAttribute("data-theme");
    if (set === "dark" || set === "light") return set;
    return media.matches ? "dark" : "light";
  }
  function render() {
    if (!button) return;
    var dark = current() === "dark";
    button.setAttribute("aria-pressed", dark ? "true" : "false");
    var label = button.querySelector(".hub-theme-label");
    var text = copy(dark ? "G03.theme.dark" : "G03.theme.light");
    if (label && text) label.textContent = text;
  }
  function announce(name) {
    var app = window.HubApp;
    if (app && typeof app.emit === "function") app.emit("theme", name);
  }
  function onClick() {
    var next = current() === "dark" ? "light" : "dark";
    root.setAttribute("data-theme", next);
    try {
      localStorage.setItem("hub-theme", next);
    } catch (error) {
      // Storage can be blocked or full; the choice then holds for this page only.
    }
    render();
    announce(next);
  }
  function onSystemChange() {
    if (root.hasAttribute("data-theme")) return;
    render();
    announce(current());
  }

  document.addEventListener("DOMContentLoaded", function () {
    button = document.getElementById("hub-theme");
    if (!button) return;
    render();
    button.addEventListener("click", onClick);
    if (typeof media.addEventListener === "function") {
      media.addEventListener("change", onSystemChange);
    }
  });
})();
