// Phase 2.3.1 plan 08: measure every text of the detail figure on the open pair page with the
// vendored fonts loaded. Boxes are in canvas units (getBBox reads the user space of the svg).
// The test decides; this probe only measures and names the container of every text.
await document.fonts.ready;
const svg = document.querySelector('#hub-site .hub-pair-figure svg.hub-figure');
if (!svg) return {found: false};
const fonts = {
  mono: document.fonts.check('500 28px "JetBrains Mono"'),
  display: document.fonts.check('700 36px Figtree'),
  body: document.fonts.check('500 34px "DM Sans"')
};
// Layout constants of the generator, in canvas units (docs/brand/hub-figure-rules.md).
const PANEL_A = [50, 570];
const PANEL_B = [830, 1350];
const COLUMN = [570, 830];
const BAND = {x1: 50, x2: 1350, y1: 702, y2: 912};
const CANVAS = {w: 1400, h: 934};
const box = node => {
  const b = node.getBBox();
  return {x: b.x, y: b.y, w: b.width, h: b.height, x2: b.x + b.width, y2: b.y + b.height};
};
const texts = Array.from(svg.querySelectorAll('text'));
const items = texts.map(node => {
  const classes = node.getAttribute('class') || '';
  const b = box(node);
  const x = Number(node.getAttribute('x'));
  const y = Number(node.getAttribute('y'));
  const size = Number(node.getAttribute('font-size'));
  const text = node.textContent;
  let container, kind;
  if (classes.includes('f-chip-t')) {
    // The chip rect is the element right before the text.
    const rect = node.previousElementSibling;
    const rx = Number(rect.getAttribute('x')), ry = Number(rect.getAttribute('y'));
    const rw = Number(rect.getAttribute('width')), rh = Number(rect.getAttribute('height'));
    container = {x1: rx, x2: rx + rw, y1: ry, y2: ry + rh};
    kind = 'chip';
  } else if (classes.includes('f-band-t')) {
    container = BAND;
    kind = 'band';
  } else if (classes.includes('f-num') || (x >= COLUMN[0] && x < COLUMN[1])) {
    container = {x1: COLUMN[0], x2: COLUMN[1], y1: 100, y2: 670};
    kind = 'column';
  } else {
    const panel = x < PANEL_B[0] ? PANEL_A : PANEL_B;
    container = {x1: panel[0], x2: panel[1], y1: 100, y2: 670};
    kind = classes.includes('f-title') ? 'title' : 'label';
  }
  const advance = text.length ? b.w / text.length / size : null;
  return {text, classes, kind, size, x, y, box: b, container, advance,
    ratio: b.w / (container.x2 - container.x1),
    insideCanvas: b.x >= 0 && b.y >= 0 && b.x2 <= CANVAS.w && b.y2 <= CANVAS.h,
    insideContainer: b.x >= container.x1 - 0.5 && b.x2 <= container.x2 + 0.5
      && b.y >= container.y1 - 0.5 && b.y2 <= container.y2 + 0.5};
});
const overlaps = [];
for (let i = 0; i < items.length; i += 1) {
  for (let j = i + 1; j < items.length; j += 1) {
    const a = items[i].box, b = items[j].box;
    const dx = Math.min(a.x2, b.x2) - Math.max(a.x, b.x);
    const dy = Math.min(a.y2, b.y2) - Math.max(a.y, b.y);
    if (dx > 0 && dy > 0) overlaps.push({a: items[i].text, b: items[j].text, dx, dy});
  }
}
const byFace = {};
for (const item of items) {
  const face = item.classes.includes('f-mono') ? 'mono' : item.classes.includes('f-title') || item.classes.includes('f-num') ? 'display' : 'body';
  if (item.advance !== null) (byFace[face] = byFace[face] || []).push(item.advance);
}
const advances = {};
for (const face of Object.keys(byFace)) {
  const list = byFace[face];
  advances[face] = {min: Math.min(...list), max: Math.max(...list), count: list.length};
}
return {found: true, fonts, items, overlaps, advances,
  maxRatio: Math.max(...items.map(item => item.ratio)),
  rendered: svg.getBoundingClientRect().width};
