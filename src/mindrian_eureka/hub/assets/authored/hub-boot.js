// Local class switch only; no network use.
document.documentElement.classList.replace("no-js", "js");
// The saved theme choice (plan 02.3.1-05) is applied here, before the first paint, so the page
// does not flash. Only the two exact values are applied; any other stored value is ignored.
(function () {
  try {
    var savedTheme = localStorage.getItem("hub-theme");
    if (savedTheme === "dark" || savedTheme === "light") {
      document.documentElement.setAttribute("data-theme", savedTheme);
    }
  } catch (error) {
    // Storage can be blocked or missing. The system preference then applies through the CSS.
  }
})();
