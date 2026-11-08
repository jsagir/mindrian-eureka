const app = window.HubApp;
const allRows = () => Array.from(document.querySelectorAll('#bank-list [data-pair-key]'));
const textTags = ['text', 'title', 'desc'];
const box = node => {
  if (!node) return null;
  const r = node.getBoundingClientRect();
  return {top: r.top, bottom: r.bottom, left: r.left, right: r.right, width: r.width, height: r.height};
};
function violations() {
  // Every row keeps the label once, the two source links in order, the engine word and the
  // Read button first; plan 06 adds one title link and one Open link to the same route.
  return allRows().flatMap(row => {
    const pair = app.index.pairs.get(row.dataset.pairKey);
    const labels = row.querySelectorAll('.hub-bank-status');
    const links = Array.from(row.querySelectorAll('a.hub-link'));
    const titles = row.querySelectorAll('a.hub-bank-open-link');
    const opens = row.querySelectorAll('a.hub-bank-open-btn');
    const route = '#/pair/' + pair.engine + '/' + pair.rank;
    const bad = [];
    if (labels.length !== 1 || labels[0].textContent !== app.data.label) bad.push('label:' + pair.key);
    if (links.length !== 2 || links[0].getAttribute('href') !== pair.left.source_link ||
        links[1].getAttribute('href') !== pair.right.source_link) bad.push('source:' + pair.key);
    if (titles.length !== 1 || titles[0].getAttribute('href') !== route) bad.push('title:' + pair.key);
    if (opens.length !== 1 || opens[0].getAttribute('href') !== route) bad.push('open:' + pair.key);
    if (!row.textContent.includes(app.data.engines[pair.engine].short_name)) bad.push('engine:' + pair.key);
    if (row.querySelector('button').textContent !== app.fmt('B08.read')) bad.push('action:' + pair.key);
    return bad;
  });
}
function tree(svg) {
  // A canonical form of the inserted figure: every element in document order with its
  // local name, its sorted attributes (namespace declarations aside) and its text.
  return [svg].concat(Array.from(svg.querySelectorAll('*'))).map(el => [
    el.localName,
    Array.from(el.attributes).filter(a => !a.name.startsWith('xmlns')).map(a => [a.name, a.value])
      .sort((a, b) => (a.join(',') < b.join(',') ? -1 : a.join(',') > b.join(',') ? 1 : 0)),
    textTags.includes(el.localName) ? el.textContent : ''
  ]);
}
function parts(row) {
  const rankN = row.querySelector('.hub-bank-rank .hub-bank-rank-n');
  const hidden = row.querySelector('.hub-bank-rank .hub-visually-hidden');
  const title = row.querySelector('h3.hub-bank-pair a.hub-bank-open-link');
  const records = row.querySelector('.hub-bank-records');
  const nums = row.querySelector('.hub-bank-nums');
  const body = row.querySelector('.hub-bank-body');
  const reading = row.querySelector('.hub-bank-reading');
  const actions = row.querySelector('.hub-bank-actions');
  const figure = row.querySelector('.hub-bank-figure');
  const svg = figure ? figure.querySelector('svg.hub-figure') : null;
  const classes = node => (node ? Array.from(node.children, child => child.className) : null);
  return {
    key: row.dataset.pairKey,
    children: Array.from(row.children, child => ({tag: child.tagName.toLowerCase(), class: child.className})),
    rankVisible: rankN ? rankN.textContent : null,
    rankAriaHidden: rankN ? rankN.getAttribute('aria-hidden') : null,
    rankHidden: hidden ? hidden.textContent : null,
    title: title ? {href: title.getAttribute('href'), text: title.textContent} : null,
    titleLinks: row.querySelectorAll('a.hub-bank-open-link').length,
    recordsOrder: classes(records),
    ids: Array.from(row.querySelectorAll('.hub-bank-ids a.hub-link'), a => ({
      href: a.getAttribute('href'), text: a.textContent, name: a.getAttribute('aria-label')})),
    numerals: Array.from(row.querySelectorAll('.hub-bank-num'), p => ({
      value: p.querySelector('.hub-bank-numeral')?.textContent ?? null,
      kind: p.querySelector('.hub-bank-numeral')?.className ?? null,
      caption: p.querySelector('.hub-bank-caption')?.textContent ?? null})),
    numsText: nums ? nums.textContent : null,
    bodyOrder: classes(body),
    labels: body?.querySelector('.hub-bank-labels:not(.hub-bank-extras)')?.textContent ?? null,
    readingOrder: classes(reading),
    reading: reading?.querySelector(':scope > p')?.textContent ?? null,
    shared: row.querySelector('.hub-bank-shared')?.textContent ?? null,
    use: row.querySelector('.hub-bank-use')?.textContent ?? null,
    useLabel: row.querySelector('.hub-bank-use strong')?.textContent ?? null,
    actions: actions ? Array.from(actions.children, c => ({tag: c.tagName, class: c.className,
      text: c.textContent, href: c.getAttribute('href')})) : null,
    figure: figure ? {
      tree: svg ? tree(svg) : null, role: svg ? svg.getAttribute('role') : null,
      svgCount: figure.querySelectorAll('svg').length,
      // Plan 11: the caption is a details element; the legend text is its p, the summary folds it.
      caption: figure.querySelector('figcaption p')?.textContent ?? null,
      captionSummary: figure.querySelector('figcaption summary')?.textContent ?? null,
      captionOpen: figure.querySelector('details.hub-bank-figure-caption')?.open ?? null,
      summaryVisible: (figure.querySelector('figcaption summary')?.getClientRects().length ?? 0) > 0,
      figureWidth: svg ? svg.getBoundingClientRect().width : null
    } : null,
    hasSeed: Boolean(row.querySelector('.hub-bank-seed')),
    seedLast: row.lastElementChild.classList.contains('hub-bank-seed')
  };
}
function points(row) {
  // Hit tests: the blank part of the row belongs to the stretched title link; each control
  // keeps its own hit area above it.
  row.scrollIntoView({block: 'center'});
  const describe = el => (el ? {
    tag: el.tagName, class: el.className, inRow: row.contains(el),
    title: Boolean(el.closest('a.hub-bank-open-link')), source: Boolean(el.closest('a.hub-link')),
    open: Boolean(el.closest('a.hub-bank-open-btn')), read: Boolean(el.closest('button.hub-bank-read'))
  } : null);
  const hit = (x, y) => describe(document.elementFromPoint(x, y));
  const centre = node => { const r = node.getBoundingClientRect(); return hit(r.left + r.width / 2, r.top + r.height / 2); };
  const rowBox = row.getBoundingClientRect();
  const title = row.querySelector('a.hub-bank-open-link');
  const open = row.querySelector('a.hub-bank-open-btn');
  const after = title ? getComputedStyle(title, '::after') : null;
  // Plan 11: the Read action is a cobalt text button (contract R10); its computed style.
  const read = row.querySelector('button.hub-bank-read');
  const readStyle = read ? getComputedStyle(read) : null;
  return {
    blank: hit(rowBox.left + 12, rowBox.bottom - 8),
    readStyle: readStyle ? {color: readStyle.color, backgroundColor: readStyle.backgroundColor,
      fontSize: readStyle.fontSize, fontWeight: readStyle.fontWeight,
      textDecorationLine: readStyle.textDecorationLine, borderTopWidth: readStyle.borderTopWidth,
      minHeight: readStyle.minHeight, height: read.getBoundingClientRect().height} : null,
    title: title ? centre(title) : null,
    sources: Array.from(row.querySelectorAll('a.hub-link'), centre),
    open: open ? centre(open) : null,
    read: centre(row.querySelector('button.hub-bank-read')),
    after: after ? {position: after.position, top: after.top, right: after.right, bottom: after.bottom,
      left: after.left, content: after.content} : null,
    rowPosition: getComputedStyle(row).position,
    sameHref: Boolean(title && open && title.getAttribute('href') === open.getAttribute('href'))
  };
}
function colours(row) {
  const color = selector => { const node = row.querySelector(selector); return node ? getComputedStyle(node).color : null; };
  return {key: row.dataset.pairKey, weak: row.classList.contains('hub-row--weak'),
    rank: color('.hub-bank-rank-n'), meaning: color('.hub-bank-numeral--meaning'),
    wording: color('.hub-bank-numeral--wording')};
}
function fit(row) {
  const rankN = row.querySelector('.hub-bank-rank-n');
  const rankStyle = rankN ? getComputedStyle(rankN) : null;
  return {key: row.dataset.pairKey, rank: Number(row.dataset.rank),
    index: rankN ? {text: rankN.textContent, scrollWidth: rankN.scrollWidth, clientWidth: rankN.clientWidth,
      height: rankN.getBoundingClientRect().height, lineHeight: parseFloat(rankStyle.lineHeight) || parseFloat(rankStyle.fontSize) * 1.5} : null,
    numerals: Array.from(row.querySelectorAll('.hub-bank-numeral'), b => ({text: b.textContent,
      scrollWidth: b.scrollWidth, clientWidth: b.clientWidth, height: b.getBoundingClientRect().height,
      fontSize: parseFloat(getComputedStyle(b).fontSize)}))};
}
if (args.more) {
  for (let index = 0; index < args.more; index += 1) document.getElementById('bank-more')?.click();
}
if (args.engine) app.setFilter('engine', args.engine);
if (args.weak !== undefined) app.setFilter('weak', args.weak);
if (args.clear) app.clearSelection();
if (args.views) { app.go('catalogue'); app.go('bank'); }
if (args.scroll) document.querySelector(args.scroll).scrollIntoView();
if (args.settle) await new Promise(resolve => setTimeout(resolve, args.settle));
await document.fonts.ready;
const beforeMutation = violations();
if (args.removeLabel) allRows()[0].querySelector('.hub-bank-status').remove();
const metrics = allRows().map(row => {
  const button = row.querySelector('button').getBoundingClientRect();
  const records = row.querySelector('.hub-bank-records').getBoundingClientRect();
  const body = box(row.querySelector('.hub-bank-body'));
  const reading = box(row.querySelector('.hub-bank-reading'));
  const figure = box(row.querySelector('.hub-bank-figure'));
  return {buttonTop: button.top, recordsTop: records.top, width: button.width, height: button.height,
    columns: getComputedStyle(row).gridTemplateColumns.split(' ').length,
    transition: getComputedStyle(row.querySelector('button')).transitionDuration,
    bodyTop: body ? body.top : null, bodyBottom: body ? body.bottom : null, bodyRight: body ? body.right : null,
    readingBottom: reading ? reading.bottom : null,
    figureLeft: figure ? figure.left : null, figureTop: figure ? figure.top : null,
    rowHeight: row.getBoundingClientRect().height};
});
const legend = Array.from(document.querySelectorAll('#bank-controls details.hub-bank-figures'), details => ({
  open: details.open, summary: details.querySelector('summary')?.textContent ?? null,
  body: Array.from(details.querySelectorAll('p'), p => p.textContent), text: details.textContent}));
// The row text without the picture: the figure's title and desc are the picture's own
// accessible text (they repeat the label by D-07), not words of the row.
const rowText = row => {
  const copy = row.cloneNode(true);
  copy.querySelectorAll('svg').forEach(node => node.remove());
  return copy.textContent;
};
return {
  rows: allRows().map(row => ({key: row.dataset.pairKey, rank: Number(row.dataset.rank),
    engine: row.dataset.engine, text: rowText(row),
    labels: row.querySelectorAll('.hub-bank-status').length,
    anchors: Array.from(row.querySelectorAll('a.hub-link'), a => ({text: a.textContent,
      href: a.getAttribute('href'), name: a.getAttribute('aria-label')})),
    buttons: Array.from(row.querySelectorAll('button'), b => b.textContent)})),
  violations: beforeMutation, afterMutation: violations(),
  status: document.getElementById('bank-status').textContent,
  radios: Array.from(document.querySelectorAll('[name="bank-engine"]'), node => ({value: node.value, checked: node.checked})),
  weakPresent: Boolean(document.getElementById('bank-weak')),
  weakChecked: Boolean(document.getElementById('bank-weak')?.checked),
  weakRows: document.querySelectorAll('.hub-row--weak').length,
  cutoffs: document.querySelector('.hub-bank-cutoffs').textContent,
  selected: document.querySelector('#bank-list [aria-current="true"]')?.dataset.pairKey || null,
  selection: app.state.selection, filters: app.state.filters,
  panelOpen: document.documentElement.hasAttribute('data-panel-open'),
  listText: document.getElementById('bank-list').textContent,
  focus: {tag: document.activeElement.tagName, text: document.activeElement.textContent,
    type: document.activeElement.type, name: document.activeElement.name, id: document.activeElement.id,
    class: document.activeElement.className, href: document.activeElement.getAttribute('href')},
  injected: typeof window.__pwned !== 'undefined', metrics: metrics,
  legend: legend,
  parts: args.parts ? allRows().slice(0, args.parts).map(parts) : null,
  points: args.points ? points(allRows()[0]) : null,
  colours: args.colours ? allRows().map(colours) : null,
  fit: args.fit ? allRows().map(fit) : null,
  overlap: args.overlap ? allRows().map(row => ({key: row.dataset.pairKey,
    extras: Array.from(row.querySelectorAll('.hub-bank-extras'), box),
    labels: box(row.querySelector('.hub-bank-labels:not(.hub-bank-extras)'))})) : null,
  animations: document.getAnimations().length
};
