const app = window.HubApp;
const allRows = () => Array.from(document.querySelectorAll('#bank-list [data-pair-key]'));
function violations() {
  return allRows().flatMap(row => {
    const pair = app.index.pairs.get(row.dataset.pairKey);
    const labels = row.querySelectorAll('.hub-bank-status');
    const links = Array.from(row.querySelectorAll('a'));
    const bad = [];
    if (labels.length !== 1 || labels[0].textContent !== app.data.label) bad.push('label:' + pair.key);
    if (links.length !== 2 || links[0].getAttribute('href') !== pair.left.source_link ||
        links[1].getAttribute('href') !== pair.right.source_link) bad.push('source:' + pair.key);
    if (!row.textContent.includes(app.data.engines[pair.engine].short_name)) bad.push('engine:' + pair.key);
    if (row.querySelector('button').textContent !== app.fmt('B08.read')) bad.push('action:' + pair.key);
    return bad;
  });
}
if (args.more) {
  for (let index = 0; index < args.more; index += 1) document.getElementById('bank-more')?.click();
}
if (args.engine) app.setFilter('engine', args.engine);
if (args.weak !== undefined) app.setFilter('weak', args.weak);
if (args.clear) app.clearSelection();
if (args.views) { app.go('catalogue'); app.go('bank'); }
if (args.scroll) document.querySelector(args.scroll).scrollIntoView();
const beforeMutation = violations();
if (args.removeLabel) allRows()[0].querySelector('.hub-bank-status').remove();
const metrics = allRows().map(row => {
  const button = row.querySelector('button').getBoundingClientRect();
  const records = row.querySelector('.hub-bank-records').getBoundingClientRect();
  return {buttonTop: button.top, recordsTop: records.top, width: button.width, height: button.height,
    columns: getComputedStyle(row).gridTemplateColumns.split(' ').length,
    transition: getComputedStyle(row.querySelector('button')).transitionDuration};
});
return {
  rows: allRows().map(row => ({key: row.dataset.pairKey, rank: Number(row.dataset.rank),
    engine: row.dataset.engine, text: row.textContent,
    labels: row.querySelectorAll('.hub-bank-status').length,
    anchors: Array.from(row.querySelectorAll('a'), a => ({text: a.textContent,
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
  listText: document.getElementById('bank-list').textContent,
  focus: {tag: document.activeElement.tagName, text: document.activeElement.textContent,
    type: document.activeElement.type, name: document.activeElement.name, id: document.activeElement.id},
  injected: typeof window.__pwned !== 'undefined', metrics: metrics,
  animations: document.getAnimations().length
};
