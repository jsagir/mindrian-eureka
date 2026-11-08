const app = window.HubApp;
app.go('catalogue', {focus: false});
if (args.query !== undefined) app.setFilter('query', args.query);
if (args.file !== undefined) app.setFilter('file', args.file);
if (args.inPair !== undefined) app.setFilter('inPair', args.inPair);
if (args.more) for (let n = 0; n < args.more; n += 1) document.getElementById('catalogue-more')?.click();
if (args.views) { app.go('bank'); app.go('catalogue'); }
const measured = {};
if (args.timedQuery) {
  const began = performance.now();
  app.setFilter('query', args.timedQuery);
  measured.ms = performance.now() - began;
}
const rows = Array.from(document.querySelectorAll('#catalogue-list tbody tr'));
const violations = rows.flatMap(row => {
  const record = app.index.records.get(row.dataset.recordId);
  const link = row.querySelector('a');
  if (!link || link.getAttribute('href') !== record.source_link) return [record.id];
  return [];
});
const visibleRecords = rows.map(row => row.dataset.recordId);
const query = String(app.state.filters.query).trim().toLowerCase();
const expectedRecords = app.data.records.filter(record => {
  const haystack = (record.id + ' ' + record.title + ' ' + record.text).toLowerCase();
  const filters = app.state.filters;
  return query.split(/\s+/).filter(Boolean).every(token => haystack.includes(token)) &&
    (filters.file === 'all' || filters.file === record.source_file) &&
    (filters.inPair === 'all' || (filters.inPair === 'some' ? record.pair_count > 0 : record.pair_count === 0));
}).map(record => record.id).sort();
const table = document.querySelector('.hub-catalogue-table');
const header = table.querySelector('thead');
// Phase 2.3.1 plan 07: the sticky head follows the measured header height (the root custom
// property set by the core script), in px.
const headerVar = parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--hub-header-height'));
return {
  headerVar: headerVar,
  ids: visibleRecords, first: visibleRecords[0], last: visibleRecords[visibleRecords.length - 1],
  expected: expectedRecords, violations: violations, measured: measured,
  status: document.getElementById('catalogue-status').textContent,
  live: document.getElementById('catalogue-status').getAttribute('aria-live'),
  filters: app.state.filters, selection: app.state.selection,
  display: {table: getComputedStyle(table).display,
    row: rows.length ? getComputedStyle(rows[0]).display : null,
    cell: rows.length ? getComputedStyle(rows[0].cells[0]).display : null},
  header: {position: getComputedStyle(header).position, top: getComputedStyle(header).top,
    clip: getComputedStyle(header).clipPath,
    names: Array.from(header.querySelectorAll('th'), node => node.textContent),
    scopes: Array.from(header.querySelectorAll('th'), node => node.getAttribute('scope'))},
  anchors: rows.map(row => ({text: row.querySelector('a').textContent, href: row.querySelector('a').getAttribute('href')})),
  buttonNames: rows.map(row => row.querySelector('button').getAttribute('aria-label')),
  options: {file: Array.from(document.getElementById('catalogue-file').options, node => ({value: node.value, text: node.textContent})),
    inPair: Array.from(document.getElementById('catalogue-in-pair').options, node => node.textContent)},
  selected: table.querySelector('[aria-current="true"]')?.dataset.recordId || null,
  listText: document.getElementById('catalogue-list').textContent,
  tableCount: document.querySelectorAll('#catalogue-list table').length,
  rowCount: document.querySelectorAll('#catalogue-list tbody tr').length,
  injected: typeof window.__pwned !== 'undefined',
  titleTexts: rows.map(row => row.querySelector('button').textContent),
  sourceTexts: rows.map(row => row.querySelector('.hub-catalogue-file').textContent)
};
