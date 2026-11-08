// Read computed styles for the look parity test (Phase 2.3.1, plan 06).
// Runs in the page. Reads layout only; it changes nothing.
// args.probes: [{id, selector, visible, pseudo, props: [computed property names]}].
// For each probe the first match (the first visible match when `visible` is set) gives the
// computed values, its box and its computed font size.
await document.fonts.ready;
const out = {};
for (const probe of args.probes || []) {
  let node = null;
  for (const candidate of document.querySelectorAll(probe.selector)) {
    if (!probe.visible || candidate.getClientRects().length) { node = candidate; break; }
  }
  if (!node) { out[probe.id] = null; continue; }
  const style = getComputedStyle(node, probe.pseudo || null);
  const values = {};
  for (const name of probe.props || []) values[name] = style.getPropertyValue(name);
  const rect = node.getBoundingClientRect();
  out[probe.id] = {
    values: values,
    fontSize: parseFloat(style.fontSize),
    box: {x: rect.x, y: rect.y, width: rect.width, height: rect.height}
  };
}
return {
  probes: out,
  innerWidth: window.innerWidth,
  theme: document.documentElement.getAttribute('data-theme'),
  scrollWidth: document.documentElement.scrollWidth
};
