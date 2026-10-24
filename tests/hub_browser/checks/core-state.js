if (args.filter) window.HubApp.setFilter(args.filter.name, args.filter.value);
if (args.select) window.HubApp.select(args.select, document.querySelector('#hub-nav a'));
if (args.go) window.HubApp.go(args.go);
if (args.hash) {
  window.location.hash = args.hash;
  await new Promise(resolve => window.addEventListener('hashchange', resolve, {once: true}));
}
if (args.clear) window.HubApp.clearSelection();
const app = window.HubApp || {state: null, motion: {reduced: false, ms: () => 0}};
const visible = node => Boolean(node.getClientRects().length) && getComputedStyle(node).visibility !== 'hidden';
const checks = {};
if (args.safety) {
  for (const url of ['https://host/x', '//host/x', 'javascript:alert(1)', '\\host', '/absolute']) {
    try { app.el('a', {href: url}, 'test'); checks[url] = false; }
    catch (_) { checks[url] = true; }
  }
  for (const key of ['missing-copy', 'G14']) {
    try { app.fmt(key); checks[key] = false; }
    catch (_) { checks[key] = true; }
  }
}
const extension = {};
if (args.extension) {
  extension.renders = 0;
  extension.shown = 0;
  extension.hidden = 0;
  extension.events = [];
  app.registerView('bank', {
    render: () => { extension.renders += 1; },
    onEvent: name => { extension.events.push(name); }
  });
  app.start(app.data);
  app.registerPanel({
    show: () => { extension.shown += 1; },
    hide: () => { extension.hidden += 1; },
    isOpen: () => app.state.panelOpen
  });
  app.select({type: 'record', id: 'doc003'}, document.querySelector('#hub-nav a'));
  app.clearSelection();
  extension.emptySearch = app.search('');
  extension.exactSearch = app.search('DOC003');
}
const heading = document.getElementById('hub-title');
return {
  extension: extension,
  api: Object.keys(app), state: app.state, title: document.title,
  shellWords: ['hub-title-band', 'hub-nav', 'hub-counts', 'hub-data-check', 'hub-footer']
    .flatMap(id => {
      const walker = document.createTreeWalker(document.getElementById(id), NodeFilter.SHOW_TEXT);
      const texts = [];
      while (walker.nextNode()) {
        const text = walker.currentNode.textContent.trim();
        if (text && visible(walker.currentNode.parentElement)) texts.push(text);
      }
      return texts;
    }),
  active: ['bank', 'graph', 'catalogue'].filter(id => visible(document.getElementById(id))),
  focus: {id: document.activeElement.id, tag: document.activeElement.tagName, href: document.activeElement.getAttribute("href"), class: document.activeElement.className},
  h1: heading.textContent, h1Count: document.querySelectorAll('h1').length,
  face: document.getElementById('hub-face').getAttribute('src'),
  status: document.getElementById('hub-status').textContent,
  counts: Array.from(document.querySelectorAll('.hub-count strong'), n => Number(n.textContent)),
  notice: document.getElementById('hub-notice')?.textContent || '',
  footer: document.getElementById('hub-footer').textContent,
  check: document.getElementById('hub-data-check').textContent,
  current: document.querySelector('#hub-nav [aria-current="page"]')?.getAttribute('href'),
  reduced: app.motion.reduced, duration: app.motion.ms('--mos-time-reframe'),
  animations: document.getAnimations().length,
  motionControls: Array.from(document.querySelectorAll('button'), n => n.textContent)
    .filter(text => /^(pause|play|still)$/i.test(text.trim())),
  js: document.documentElement.classList.contains('js'),
  noscript: document.querySelector('noscript').textContent,
  bankRows: document.querySelectorAll('#bank-list li').length,
  graphRows: document.querySelectorAll('#graph-list li').length,
  catalogueRows: document.querySelectorAll('#catalogue-list tbody tr').length,
  injected: typeof window.__pwned !== 'undefined',
  scripts: document.querySelectorAll('script').length,
  search: app.data ? app.search(args.query || 'doc003') : [],
  safe: checks,
  outline: getComputedStyle(document.activeElement).outlineWidth,
  hash: window.location.hash
};
