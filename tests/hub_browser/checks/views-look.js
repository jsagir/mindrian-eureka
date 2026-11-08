// Phase 2.3.1 plan 07: one probe for the look, the links, the figures and the header wiring of
// the graph, the catalogue and the reading panel. Every field is read; the test picks.
const app = window.HubApp;
const root = document.documentElement;
const engines = ['unusual_pairs', 'wording_and_meaning'];
const serialise = node => new XMLSerializer().serializeToString(node);
const style = node => (node ? getComputedStyle(node) : null);
const typeOf = node => {
  const s = style(node);
  return s ? {color: s.color, fontFamily: s.fontFamily, fontSize: s.fontSize, fontWeight: s.fontWeight,
    letterSpacing: s.letterSpacing, backgroundColor: s.backgroundColor, backgroundImage: s.backgroundImage,
    borderBottomWidth: s.borderBottomWidth, borderBottomStyle: s.borderBottomStyle, borderBottomColor: s.borderBottomColor,
    borderTopWidth: s.borderTopWidth, borderTopColor: s.borderTopColor, borderTopStyle: s.borderTopStyle,
    borderInlineStartWidth: s.borderInlineStartWidth, borderInlineStartColor: s.borderInlineStartColor,
    textDecorationLine: s.textDecorationLine, padding: s.padding, display: s.display} : null;
};
const shown = node => Boolean(node && (typeof node.checkVisibility === 'function'
  ? node.checkVisibility() : node.getClientRects().length));
const box = node => {
  if (!node) return null;
  const r = node.getBoundingClientRect();
  return {top: r.top, bottom: r.bottom, x: r.x, width: r.width, height: r.height, rects: node.getClientRects().length};
};
function shownPairs(record) {
  return record.pair_keys.map(key => app.index.pairs.get(key)).filter(pair => pair && !pair.weak)
    .sort((a, b) => a.rank - b.rank || engines.indexOf(a.engine) - engines.indexOf(b.engine)
      || (a.key < b.key ? -1 : a.key > b.key ? 1 : 0));
}
function cardOf(key) {
  const figures = app.data.figures;
  const markup = figures && figures.pairs && figures.pairs[key] ? figures.pairs[key].card : null;
  if (typeof markup !== 'string') return null;
  return serialise(new DOMParser().parseFromString(markup, 'image/svg+xml').documentElement);
}
if (args.view) app.go(args.view, {focus: false});
if (args.waitGraph && app.data.graph.earned) {
  const deadline = performance.now() + 20000;
  while (!['3d', 'fallback'].includes(app.graphView.mode)) {
    if (performance.now() > deadline) throw new Error('views-look graph deadline exceeded');
    await new Promise(r => setTimeout(r, 16));
  }
}
if (args.more) for (let n = 0; n < args.more; n += 1) document.getElementById('catalogue-more')?.click();
let selectedPair = null;
if (args.pair) {
  const ordered = app.data.pairs.filter(pair => !pair.weak).sort((a, b) => a.rank - b.rank
    || engines.indexOf(a.engine) - engines.indexOf(b.engine) || (a.key < b.key ? -1 : a.key > b.key ? 1 : 0));
  selectedPair = args.pairKey ? app.index.pairs.get(args.pairKey) : ordered[0];
  app.select({type: 'pair', key: selectedPair.key}, document.querySelector('#hub-nav a'));
}
if (args.record) app.select({type: 'record', id: args.record}, document.querySelector('#hub-nav a'));
if (args.recordIndex !== undefined) app.select({type: 'record', id: app.data.records[args.recordIndex].id}, document.querySelector('#hub-nav a'));
if (args.clear) app.clearSelection();
// The camera position right before a theme emit: the refresh must not move it.
const instanceBefore = app.graphView.mode === '3d' ? app.graphView.instance : null;
const cameraBefore = instanceBefore ? {x: instanceBefore.camera().position.x, y: instanceBefore.camera().position.y,
  z: instanceBefore.camera().position.z} : null;
if (args.theme !== undefined) { root.setAttribute('data-theme', args.theme); app.emit('theme', args.theme); }
if (args.toggleGuide) document.getElementById('graph-guide-toggle').click();
if (args.scrollTo) document.querySelector(args.scrollTo)?.scrollIntoView({block: 'start'});
await document.fonts.ready;
await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));
const token = name => style(root).getPropertyValue(name).trim();
const header = document.getElementById('hub-header');
// Catalogue
const table = document.querySelector('.hub-catalogue-table');
const thead = table ? table.querySelector('thead') : null;
const th = thead ? thead.querySelector('th') : null;
const rows = Array.from(document.querySelectorAll('#catalogue-list tbody tr'));
const catalogue = table ? {
  headPosition: style(thead).position, headTop: style(thead).top, headBackground: style(thead).backgroundColor,
  th: typeOf(th), rowCell: rows.length ? typeOf(rows[0].cells[0]) : null,
  title: rows.length ? typeOf(rows[0].querySelector('.hub-catalogue-title')) : null,
  idLink: rows.length ? typeOf(rows[0].querySelector('.hub-catalogue-id a')) : null,
  openLink: rows.length ? typeOf(rows[0].querySelector('a.hub-catalogue-open')) : null,
  rows: rows.map(row => {
    const record = app.index.records.get(row.dataset.recordId);
    const opens = Array.from(row.querySelectorAll('a.hub-catalogue-open'));
    const figures = Array.from(row.querySelectorAll('.hub-catalogue-figure'));
    const svg = figures[0]?.querySelector('svg.hub-figure');
    const best = shownPairs(record)[0] || null;
    return {id: record.id, openCount: opens.length,
      open: opens[0] ? {text: opens[0].textContent, label: opens[0].getAttribute('aria-label'), href: opens[0].getAttribute('href'),
        box: box(opens[0])} : null,
      sourceLinks: Array.from(row.querySelectorAll('.hub-catalogue-id a.hub-link')).map(a => a.getAttribute('href')),
      idText: row.querySelector('.hub-catalogue-id bdi')?.textContent || '',
      titleText: row.querySelector('.hub-catalogue-title')?.textContent || '',
      fileText: row.querySelector('.hub-catalogue-file')?.textContent || '',
      countText: (row.querySelector('.hub-catalogue-inline-count')?.textContent || '') + (row.querySelector('.hub-catalogue-pairs')?.textContent || ''),
      cellsVisible: Array.from(row.cells, cell => Boolean(cell.getClientRects().length)),
      figureCount: figures.length,
      figure: figures[0] ? {ariaHidden: figures[0].getAttribute('aria-hidden'), pairKey: figures[0].dataset.pairKey || null,
        svgCount: figures[0].querySelectorAll('svg').length, hasClass: Boolean(svg),
        width: svg ? svg.getBoundingClientRect().width : null, box: box(figures[0]),
        serialised: svg ? serialise(svg) : null, links: figures[0].querySelectorAll('a,button').length} : null,
      expectedKey: best ? best.key : null, expectedCard: best ? cardOf(best.key) : null};
  })
} : null;
// Graph
const stage = document.getElementById('graph-stage');
const graph = app.graphView.instance;
const accessor = (value, item) => (typeof value === 'function' ? value(item) : value);
let stageColors = null;
if (graph && app.graphView.mode === '3d') {
  const data = graph.graphData();
  const bridge = data.nodes.find(n => n.record.bridge) || null;
  const plain = data.nodes.find(n => !n.record.bridge) || null;
  stageColors = {background: graph.backgroundColor(),
    bridge: bridge ? accessor(graph.nodeColor(), bridge) : null,
    plain: plain ? accessor(graph.nodeColor(), plain) : null,
    nodes: data.nodes.map(n => accessor(graph.nodeColor(), n)),
    links: data.links.map(l => accessor(graph.linkColor(), l)),
    shells: data.nodes.filter(n => n.record.bridge && n.__threeObj).map(n => {
      const shell = n.__threeObj.children.find(c => c.name === 'hub-ink-shell');
      return shell ? shell.material.color.getHexString() : null;
    }),
    position: {x: graph.camera().position.x, y: graph.camera().position.y, z: graph.camera().position.z}};
}
const guide = document.querySelector('.hub-graph-guide');
const guideToggle = document.getElementById('graph-guide-toggle');
const guideBody = document.getElementById('graph-guide-body');
const graphSection = document.getElementById('graph');
const graphRows = Array.from(document.querySelectorAll('.hub-graph-pair')).map(row => {
  const pair = app.index.pairs.get(row.dataset.pairKey);
  const opens = Array.from(row.querySelectorAll('a.hub-graph-open'));
  return {key: pair.key, engine: pair.engine, rank: pair.rank, openCount: opens.length,
    open: opens[0] ? {text: opens[0].textContent, href: opens[0].getAttribute('href'), box: box(opens[0]), style: typeOf(opens[0])} : null,
    readButton: Boolean(row.querySelector('button')),
    sourceLinks: Array.from(row.querySelectorAll('a.hub-link:not(.hub-graph-open)'), a => a.getAttribute('href'))};
});
// Panel
const panel = document.getElementById('hub-panel');
const figureBox = panel.querySelector('.hub-panel-figure');
const figureSvg = figureBox?.querySelector('svg.hub-figure');
const legendBox = panel.querySelector('details.hub-panel-legend');
const panelStyle = style(panel);
const panelOpen = panel.hasAttribute('data-panel-open');
const selection = app.state.selection;
const selectedKey = selection && selection.type === 'pair' ? selection.key : null;
const panelInfo = {
  open: panelOpen, selection, bounds: box(panel), position: panelStyle.position,
  background: panelStyle.backgroundColor, borderWidth: panelStyle.borderTopWidth, borderColor: panelStyle.borderTopColor,
  borderStyle: panelStyle.borderTopStyle,
  evidence: Array.from(panel.querySelectorAll('.hub-evidence'), n => ({width: style(n).borderInlineStartWidth, color: style(n).borderInlineStartColor})),
  sourceLinkColors: Array.from(panel.querySelectorAll('.hub-panel-source a.hub-link'), n => style(n).color),
  roles: Array.from(panel.querySelectorAll('.hub-role'), n => ({class: n.className, image: style(n).backgroundImage, border: style(n).borderBottomWidth})),
  minFont: Math.min(...Array.from(panel.querySelectorAll('*')).filter(n => n.getClientRects().length
    && Array.from(n.childNodes).some(c => c.nodeType === Node.TEXT_NODE && c.textContent.trim()))
    .map(n => parseFloat(style(n).fontSize)), Infinity),
  pageLinks: Array.from(panel.querySelectorAll('a.hub-panel-page'), n => ({text: n.textContent, href: n.getAttribute('href'),
    box: box(n), color: style(n).color, fontSize: style(n).fontSize, fontWeight: style(n).fontWeight})),
  figureCount: panel.querySelectorAll('.hub-panel-figure').length,
  figure: figureBox ? {containerAriaHidden: figureBox.getAttribute('aria-hidden'), svgCount: figureBox.querySelectorAll('svg').length,
    ariaHidden: figureSvg?.getAttribute('aria-hidden') ?? null, role: figureSvg?.getAttribute('role') ?? null,
    title: figureSvg?.querySelector('title')?.textContent || '', desc: figureSvg?.querySelector('desc')?.textContent || '',
    serialised: figureSvg ? serialise(figureSvg) : null, width: figureSvg ? figureSvg.getBoundingClientRect().width : null,
    box: box(figureBox)} : null,
  expectedCard: selectedKey ? cardOf(selectedKey) : null,
  legendCount: panel.querySelectorAll('details.hub-panel-legend').length,
  legend: legendBox ? {open: legendBox.open, summary: legendBox.querySelector('summary')?.textContent || '',
    body: Array.from(legendBox.querySelectorAll('p'), n => n.textContent),
    // Closed details content keeps a box under content-visibility: hidden in Chromium, so
    // checkVisibility (which honours it) decides, not getClientRects.
    bodyVisible: shown(legendBox.querySelector('p')),
    summaryBox: box(legendBox.querySelector('summary')), summaryFont: style(legendBox.querySelector('summary'))?.fontSize} : null,
  focusId: document.activeElement.id
};
return {
  innerWidth, innerHeight, scrollWidth: root.scrollWidth,
  header: header ? {height: header.offsetHeight, top: header.getBoundingClientRect().top, bottom: header.getBoundingClientRect().bottom} : null,
  headerVar: parseFloat(token('--hub-header-height')),
  tokens: {hasTheme: Boolean(token('--hub-dim')), dim: token('--hub-dim'), paper: token('--mos-paper'), blue: token('--mos-blue'),
    yellow: token('--mos-yellow'), ink: token('--mos-ink'), theme: root.getAttribute('data-theme')},
  catalogue,
  stage: {mode: app.graphView.mode, box: box(stage), colors: stageColors},
  guide: guide ? Object.assign(typeOf(guide), {box: box(guide), expanded: guideToggle?.getAttribute('aria-expanded'),
    bodyHidden: guideBody ? guideBody.hidden : null, toggleBox: box(guideToggle),
    legendSizes: Array.from(document.querySelectorAll('#graph-legend li span:last-child'), n => parseFloat(style(n).fontSize)),
    paragraphSizes: Array.from(guide.querySelectorAll('p'), n => parseFloat(style(n).fontSize)),
    linkColors: Array.from(graphSection.querySelectorAll('a'), n => style(n).color)}) : null,
  graphRows,
  panel: panelInfo,
  selectedPair: selectedPair ? {key: selectedPair.key, engine: selectedPair.engine, rank: selectedPair.rank} : null,
  cameraBefore,
  animations: typeof document.getAnimations === 'function' ? document.getAnimations().length : 0,
  reduced: app.motion.reduced
};
