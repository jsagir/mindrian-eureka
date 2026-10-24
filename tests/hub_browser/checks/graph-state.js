const app = window.HubApp;
const root = document.getElementById('graph');
app.go('graph', {focus: false});
await document.fonts.ready;
await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
if (args.find !== undefined) {
  const input = document.getElementById('graph-find');
  input.value = args.find;
  input.closest('form').requestSubmit();
}
if (args.focusFind) document.getElementById('graph-find').focus();
if (args.chooseFind) root.querySelector('#graph-find-matches button').click();
if (args.allPairs) {
  let more;
  while ((more = document.getElementById('graph-more'))) more.click();
}
const tourStates = [];
if (args.tour) {
  for (let i = 0; i < args.tour; i++) {
    document.getElementById('graph-tour').click();
    tourStates.push({selection: app.state.selection, text: document.getElementById('graph-tour').textContent,
      panel: document.getElementById('hub-panel').textContent});
  }
}
if (args.circle) root.querySelector('.hub-diagram-hit').click();
if (args.pair) root.querySelector('.hub-graph-pair button').click();
if (args.clear) app.clearSelection();
if (args.guide) document.getElementById('graph-guide-toggle').click();
const label = app.data.label;
function visible(node) {return Boolean(node && node.getClientRects().length && !node.hidden);}
function message(id) {const n = document.getElementById(id); return {visible: visible(n), text: n ? n.textContent : ''};}
function dimensions(node) {const r = node.getBoundingClientRect(); return {width:r.width,height:r.height};}
const rows = Array.from(root.querySelectorAll('.hub-graph-pair')).map(row => {
  const pair = app.index.pairs.get(row.dataset.pairKey);
  const anchors = Array.from(row.querySelectorAll('a')).map(a => ({text:a.textContent,href:a.getAttribute('href')}));
  return {key:pair.key, labelCount:Array.from(row.querySelectorAll('.hub-chip')).filter(n => n.textContent === label).length,
    anchors, expected:[pair.left.source_link,pair.right.source_link],
    proposed:row.querySelector('.hub-role--proposed').textContent,
    selected:row.classList.contains('hub-row--selected')};
});
let negative = null;
if (args.negative && rows.length) {
  const row = root.querySelector('.hub-graph-pair'); row.querySelector('.hub-chip').remove();
  negative = !Array.from(row.querySelectorAll('.hub-chip')).some(n => n.textContent === label);
}
const circles = Array.from(root.querySelectorAll('.hub-diagram-record'));
const chords = Array.from(root.querySelectorAll('.hub-diagram-chord'));
const stage = document.getElementById('graph-stage');
return {mode:app.graphView.mode, instance:app.graphView.instance === null, fly:app.graphView.flyTo('missing'),
  legend:Array.from(root.querySelectorAll('#graph-legend li')).map(li => li.textContent),
  swatches:Array.from(root.querySelectorAll('.hub-graph-swatch')).map(n => n.className),
  findCount:document.getElementById('graph-find-count').textContent,
  matches:Array.from(root.querySelectorAll('#graph-find-matches button')).map(n => n.textContent),
  tourText:document.getElementById('graph-tour').textContent, tourHidden:document.getElementById('graph-tour').hidden,
  tourEmpty:message('graph-tour-empty'), tourStates, bridges:app.data.bridges.map(b => b.record_id),
  guide:{text:document.getElementById('graph-guide-toggle').textContent,
    expanded:document.getElementById('graph-guide-toggle').getAttribute('aria-expanded')},
  rows, negative, pairCount:app.data.pairs.filter(p => !p.weak).length,
  pairStatus:document.getElementById('graph-pair-status')?.textContent,
  selection:app.state.selection, panel:document.getElementById('hub-panel').textContent,
  circleCount:circles.length, circleButtons:Array.from(root.querySelectorAll('.hub-diagram-hit')).map(dimensions),
  circleData:circles.map(n => ({id:n.dataset.diagramRecord,selected:n.classList.contains('is-selected'),
    dimmed:n.classList.contains('is-dimmed'),fill:getComputedStyle(n.querySelector('circle')).fill,
    stroke:getComputedStyle(n.querySelector('circle')).strokeWidth})),
  effectiveFonts:Array.from(root.querySelectorAll('.hub-diagram-record text')).map(n =>
    parseFloat(getComputedStyle(n).fontSize) * n.getScreenCTM().a),
  chords:chords.map(n => ({dash:n.getAttribute('stroke-dasharray'),width:getComputedStyle(n).strokeWidth,
    crosses:n.classList.contains('hub-diagram-chord--crossing')})),
  small:message('graph-small'), fallback:message('graph-fallback'), emptyTitle:message('graph-empty-title'),
  emptyBody:message('graph-empty-body'), stage:dimensions(stage),
  listInStage:Boolean(stage.querySelector('#graph-list')), stageTab:stage.getAttribute('tabindex'),
  buttonsHidden:document.getElementById('graph-stage-buttons').hidden,
  datalist:root.querySelectorAll('datalist').length,
  scrollWidth:document.documentElement.scrollWidth, width:innerWidth,
  injected:typeof window.__pwned !== 'undefined' || Boolean(root.querySelector('script,img[onerror],svg[onload]')),
  text:root.textContent, names:Array.from(root.querySelectorAll('button')).filter(visible).map(n => n.textContent || n.getAttribute('aria-label')),
  focus:document.activeElement.id, focusText:document.activeElement.textContent,
  controls:Array.from(root.querySelectorAll('button,input')).filter(visible).map(n => n.id || n.textContent),
  chips:Array.from(root.querySelectorAll('.hub-chip,.hub-graph-chip')).map(n => ({text:n.textContent,size:parseFloat(getComputedStyle(n).fontSize)}))};
