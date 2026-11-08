const app = window.HubApp;
const panel = document.getElementById('hub-panel');
function problems(selection) {
  const issues = [];
  const chip = panel.querySelector(':scope > .hub-panel-label');
  if (!chip || chip.textContent !== app.data.label) issues.push('status');
  const links = Array.from(panel.querySelectorAll('a'));
  const item = selection.type === 'record' ? app.index.records.get(selection.id) : app.index.pairs.get(selection.key);
  const expected = selection.type === 'record' ? [item.source_link] : [item.left.source_link, item.right.source_link];
  if (!expected.every(href => links.some(link => link.getAttribute('href') === href))) issues.push('source');
  panel.querySelectorAll('.hub-panel-pair-block').forEach(block => {
    const pair = app.index.pairs.get(block.dataset.pairKey);
    if (block.querySelector('.hub-panel-label')?.textContent !== pair.label) issues.push('pair-status');
    const sourceLinks = Array.from(block.querySelectorAll('a'), a => a.getAttribute('href'));
    if (!sourceLinks.includes(pair.left.source_link) || !sourceLinks.includes(pair.right.source_link)) issues.push('pair-source');
  });
  return issues;
}
const audit = {};
if (args.audit) {
  audit.checked = 0;
  audit.failures = [];
  const selections = [
    ...app.data.records.map(record => ({type: 'record', id: record.id})),
    ...app.data.pairs.map(pair => ({type: 'pair', key: pair.key}))
  ];
  for (const selection of selections) {
    app.select(selection, document.querySelector('#hub-nav a'));
    const failures = problems(selection);
    if (failures.length) audit.failures.push({selection: selection, failures: failures});
    audit.checked += 1;
  }
  panel.querySelector(':scope > .hub-panel-label').remove();
  audit.negative = problems(app.state.selection);
}
if (args.record === 'bridge') app.select({type: 'record', id: app.data.bridges[0].record_id});
else if (args.record === 'clean') app.select({type: 'record', id: app.data.records.find(r => !r.identical_to.length && !r.no_text && !r.bridge).id});
else if (args.record === 'copy') app.select({type: 'record', id: app.data.records.find(r => r.identical_to.length).id});
else if (args.record === 'long') app.select({type: 'record', id: app.data.records.find(r => Array.from(r.text).length > 600).id});
else if (args.record === 'short') app.select({type: 'record', id: app.data.records.find(r => Array.from(r.text).length < 600).id});
else if (args.record) app.select({type: 'record', id: args.record}, document.querySelector('#hub-nav a'));
if (args.surrogate) {
  const record = app.data.records[0];
  record.text = 'a'.repeat(599) + String.fromCodePoint(0x1f9ea) + 'b'.repeat(100);
  app.select({type: 'record', id: record.id});
}
if (args.pair) app.select({type: 'pair', key: app.data.pairs[0].key}, document.querySelector('#hub-nav a'));
if (args.clear) app.clearSelection();
if (args.background) {
  app.go('graph', {focus: false});
  document.getElementById('graph-stage').click();
}
if (args.hideOpener) {
  app.go('bank');
  document.querySelector('#bank-list .hub-bank-read').click();
  app.go('catalogue');
  app.clearSelection();
}
if (args.removeOpener) {
  const button = document.querySelector('#bank-list .hub-bank-read');
  button.click();
  app.setFilter('engine', 'wording_and_meaning');
  app.clearSelection();
}
if (args.focusLast) {
  const nodes = Array.from(panel.querySelectorAll('a,button,summary')).filter(n => n.getClientRects().length);
  nodes[nodes.length - 1].focus();
}
if (args.scrollWhy) panel.querySelector(".hub-panel-why").scrollIntoView({block: "start"});
const selected = app.state.selection;
const record = selected?.type === 'record' ? app.index.records.get(selected.id) : null;
// Phase 2.3.1 plan 07: the card figure, its legend and the page link of the open panel.
const figureBox = panel.querySelector('.hub-panel-figure');
const figureSvg = figureBox?.querySelector('svg.hub-figure');
const legendBox = panel.querySelector('details.hub-panel-legend');
const figure = figureBox ? {
  containerAriaHidden: figureBox.getAttribute('aria-hidden'), svgCount: figureBox.querySelectorAll('svg').length,
  ariaHidden: figureSvg?.getAttribute('aria-hidden') ?? null, role: figureSvg?.getAttribute('role') ?? null,
  title: figureSvg?.querySelector('title')?.textContent || '', desc: figureSvg?.querySelector('desc')?.textContent || '',
  serialised: figureSvg ? new XMLSerializer().serializeToString(figureSvg) : ''
} : null;
const legend = legendBox ? {open: legendBox.open, summary: legendBox.querySelector('summary')?.textContent || '',
  body: Array.from(legendBox.querySelectorAll('p'), n => n.textContent),
  bodyVisible: Boolean(legendBox.querySelector('p') && (typeof legendBox.querySelector('p').checkVisibility === 'function'
    ? legendBox.querySelector('p').checkVisibility() : legendBox.querySelector('p').getClientRects().length))} : null;
const pageLinks = Array.from(panel.querySelectorAll('a.hub-panel-page'), n => ({text: n.textContent, href: n.getAttribute('href')}));
const bounds = panel.getBoundingClientRect();
const face = panel.querySelector('img');
const opener = document.querySelector('#bank-list .hub-bank-read');
if (args.scrollOpener && opener) opener.scrollIntoView({block: "center"});
const buttonBounds = opener?.getBoundingClientRect();
let uncovered = null;
if (buttonBounds && buttonBounds.top >= 0 && buttonBounds.bottom <= innerHeight) {
  uncovered = document.elementFromPoint(buttonBounds.x + buttonBounds.width / 2,
    buttonBounds.y + buttonBounds.height / 2) === opener;
}
const full = panel.querySelector('.hub-panel-full');
const bridgeMark = panel.querySelector(".hub-role--bridge");
const texts = [];
const sourceGroups = new Set();
const walker = document.createTreeWalker(panel, NodeFilter.SHOW_TEXT);
while (walker.nextNode()) {
  const group = walker.currentNode.parentElement.closest('.hub-source-prose');
  if (group && sourceGroups.has(group)) continue;
  if (group) sourceGroups.add(group);
  const value = (group ? group.textContent : walker.currentNode.textContent).trim();
  if (value) texts.push(value);
}
return {
  texts: texts,
  figure: figure, legend: legend, pageLinks: pageLinks,
  audit: audit, text: panel.textContent,
  headings: Array.from(panel.querySelectorAll('h2,h3'), n => n.textContent),
  roles: Array.from(panel.querySelectorAll('.hub-role'), n => n.textContent),
  labels: panel.querySelectorAll('.hub-panel-label').length,
  anchors: Array.from(panel.querySelectorAll('a'), n => ({text: n.textContent, href: n.getAttribute('href')})),
  buttons: Array.from(panel.querySelectorAll('button'), n => n.getAttribute('aria-label') || n.textContent),
  details: Array.from(panel.querySelectorAll('details'), n => ({summary: n.querySelector('summary').textContent, open: n.open})),
  selection: selected, focus: {id: document.activeElement.id, text: document.activeElement.textContent,
    inPanel: panel.contains(document.activeElement)},
  rootOpen: document.documentElement.hasAttribute('data-panel-open'),
  panelOpen: panel.hasAttribute('data-panel-open'),
  bounds: {x: bounds.x, y: bounds.y, width: bounds.width, height: bounds.height,
    bottom: bounds.bottom, right: bounds.right},
  position: getComputedStyle(panel).position,
  faceVisible: Boolean(face && face.getClientRects().length),
  live: panel.getAttribute('aria-live'), labelledby: panel.getAttribute('aria-labelledby'),
  modal: Boolean(document.querySelector('[aria-modal],[inert]')),
  sheetHeight: document.documentElement.style.getPropertyValue('--hub-sheet-height'),
  scrollHeight: panel.scrollHeight, clientHeight: panel.clientHeight,
  scrollWidth: document.documentElement.scrollWidth, innerWidth: innerWidth,
  bodyScrollHeight: document.documentElement.scrollHeight, innerHeight: innerHeight,
  excerpt: panel.querySelector('.hub-panel-excerpt')?.textContent || '',
  rest: full?.querySelector('.hub-source-prose')?.textContent || '',
  recordText: record?.text || '',
  why: panel.querySelector('.hub-panel-why')?.textContent || '',
  bridge: record?.bridge || false,
  bridgeChip: bridgeMark?.textContent || '',
  bridgeStyle: bridgeMark ? {background: getComputedStyle(bridgeMark).backgroundColor,
    color: getComputedStyle(bridgeMark).color, border: getComputedStyle(bridgeMark).borderColor,
    width: getComputedStyle(bridgeMark).borderWidth} : null,
  sourceLink: record?.source_link || '',
  labelValid: selected && !args.audit ? problems(selected).length === 0 : null,
  injected: typeof window.__pwned !== 'undefined',
  uncovered: uncovered
};
