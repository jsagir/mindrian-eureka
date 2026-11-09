// Phase 2.3.1 plan 08: one probe for the page routes, the knobs, the keys, the page content,
// the twin and the metrics of the pair and record pages. Every field is read; the test picks.
// Steps (in this order): theme, deleteKeys, go, select, focus, scroll, hash, click, key, back,
// waitPage, settle. Then the state is read.
const app = window.HubApp;
const root = document.documentElement;
const serialise = node => new XMLSerializer().serializeToString(node);
const style = node => (node ? getComputedStyle(node) : null);
const box = node => {
  if (!node) return null;
  const r = node.getBoundingClientRect();
  return {top: r.top, left: r.left, width: r.width, height: r.height, rects: node.getClientRects().length};
};
const shown = node => Boolean(node) && node.getClientRects().length > 0
  && style(node).visibility !== 'hidden' && style(node).display !== 'none';
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
const nextHashChange = (ms) => new Promise(resolve => {
  let done = false;
  const finish = () => { if (!done) { done = true; resolve(); } };
  window.addEventListener('hashchange', finish, {once: true});
  setTimeout(finish, ms || 2000);
});
const waitPage = async (predicate) => {
  const deadline = performance.now() + 5000;
  while (performance.now() < deadline) {
    if (predicate()) return true;
    await sleep(10);
  }
  return false;
};
if (args.theme !== undefined) {
  if (args.theme === null) root.removeAttribute('data-theme');
  else root.setAttribute('data-theme', args.theme);
}
if (args.deleteKeys && app && app.data) {
  for (const key of args.deleteKeys) delete app.data[key];
}
if (args.go && app) app.go(args.go, {focus: false});
if (args.select && app) app.select(args.select, document.querySelector('#hub-nav a'));
if (args.focus) {
  const target = document.querySelector(args.focus);
  if (target) target.focus({preventScroll: true});
}
if (args.scrollTo) {
  const target = document.querySelector(args.scrollTo);
  if (target) {
    target.scrollIntoView({block: 'center', behavior: 'instant'});
    await sleep(30);
  }
}
if (args.scroll !== undefined) { window.scrollTo({top: args.scroll, left: 0, behavior: 'instant'}); await sleep(30); }
const hashBefore = window.location.hash;
const lengthBefore = window.history.length;
const previousBefore = app && app.nav ? app.nav.previous : undefined;
if (args.hash !== undefined && args.hash !== window.location.hash) {
  const waiter = nextHashChange(3000);
  window.location.hash = args.hash;
  await waiter;
}
if (args.click) {
  // A synthetic click: the real pointer click is a driver step. Used for knobs and links where
  // the focus of the opener does not matter to the test.
  const target = document.querySelector(args.click);
  if (!target) throw new Error('pages-state: nothing matches ' + args.click);
  const waiter = nextHashChange(args.wait || 1500);
  target.click();
  await waiter;
}
if (args.key) {
  const target = (args.keyTarget ? document.querySelector(args.keyTarget) : null)
    || document.activeElement || document.body;
  const init = {key: args.key, bubbles: true, cancelable: true, altKey: Boolean(args.alt),
    ctrlKey: Boolean(args.ctrl), metaKey: Boolean(args.meta), shiftKey: Boolean(args.shift)};
  const waiter = nextHashChange(args.wait || 1200);
  target.dispatchEvent(new KeyboardEvent('keydown', init));
  await waiter;
}
if (args.back) {
  const waiter = nextHashChange(3000);
  window.history.back();
  await waiter;
}
if (args.waitPage === 'page') await waitPage(() => app && app.state && app.state.page !== null);
if (args.waitPage === 'view') await waitPage(() => app && app.state && app.state.page === null);
if (args.waitHash) await waitPage(() => window.location.hash === args.waitHash);
if (args.settle) await sleep(args.settle);
await document.fonts.ready;
await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));

const site = document.getElementById('hub-site');
const active = document.activeElement;
const textOf = node => (node ? node.textContent : null);
const linkOf = node => (node ? {text: node.textContent.trim(), href: node.getAttribute('href'),
  rel: node.getAttribute('rel'), label: node.getAttribute('aria-label'), tag: node.tagName,
  ariaHidden: node.getAttribute('aria-hidden'), tabindex: node.getAttribute('tabindex'),
  dataBack: node.getAttribute('data-back'), classes: node.className, box: box(node),
  role: node.getAttribute('role')} : null);
function knobsOf(nav) {
  if (!nav) return null;
  return {
    label: nav.getAttribute('aria-label'),
    back: linkOf(nav.querySelector('a.hub-knob--back')),
    prev: linkOf(nav.querySelector('a[rel="prev"]')),
    next: linkOf(nav.querySelector('a[rel="next"]')),
    prevOff: linkOf(nav.querySelector('span.hub-knob--prev.hub-knob--off')),
    nextOff: linkOf(nav.querySelector('span.hub-knob--next.hub-knob--off')),
    position: textOf(nav.querySelector('.hub-knob-pos')),
    prevText: textOf(nav.querySelector('.hub-knob--prev')),
    nextText: textOf(nav.querySelector('.hub-knob--next'))
  };
}
const crumbs = site ? Array.from(site.querySelectorAll('nav.hub-crumbs li'), li => {
  const a = li.querySelector('a');
  const span = li.querySelector('[aria-current]');
  return {text: li.textContent.trim(), href: a ? a.getAttribute('href') : null,
    current: span ? span.getAttribute('aria-current') : null, isLink: Boolean(a)};
}) : [];
const crumbNav = site ? site.querySelector('nav.hub-crumbs') : null;
const knobNavs = site ? Array.from(site.querySelectorAll('nav.hub-knobs')) : [];
const visibleH1s = Array.from(document.querySelectorAll('h1')).filter(shown);
const state = {
  hash: window.location.hash, hashBefore, lengthBefore, previousBefore,
  path: window.location.pathname,
  view: app ? app.state.view : null,
  page: app ? app.state.page : null,
  nav: app && app.nav ? {current: app.nav.current, previous: app.nav.previous} : null,
  panelOpen: app ? app.state.panelOpen : null,
  selection: app ? app.state.selection : null,
  visible: {
    site: shown(site), bank: shown(document.getElementById('bank')),
    graph: shown(document.getElementById('graph')), catalogue: shown(document.getElementById('catalogue')),
    titleBand: shown(document.getElementById('hub-title-band')), counts: shown(document.getElementById('hub-counts')),
    band: shown(document.getElementById('hub-band')), panel: shown(document.getElementById('hub-panel')),
    header: shown(document.getElementById('hub-header')), footer: shown(document.getElementById('hub-footer')),
    dataCheck: shown(document.getElementById('hub-data-check'))
  },
  onPage: document.getElementById('hub-page').classList.contains('hub-on-page'),
  h1s: visibleH1s.map(h => h.textContent),
  h1Count: document.querySelectorAll('h1').length,
  focus: active ? {tag: active.tagName, text: active.textContent.trim().slice(0, 120),
    href: active.getAttribute('href'), id: active.id, classes: active.className,
    isPageHeading: Boolean(site && site.contains(active) && active.tagName === 'H1'),
    outline: style(active).outlineWidth, outlineStyle: style(active).outlineStyle} : null,
  title: document.title,
  notice: document.getElementById('hub-notice') ? document.getElementById('hub-notice').textContent : '',
  scrollY: window.scrollY,
  historyLength: window.history.length,
  knobs: knobsOf(knobNavs[0] || null),
  knobsBottom: knobsOf(knobNavs[1] || null),
  knobNavCount: knobNavs.length,
  crumbLabel: crumbNav ? crumbNav.getAttribute('aria-label') : null,
  crumbs,
  current: Array.from(document.querySelectorAll('#hub-nav a[aria-current]'), a => ({href: a.getAttribute('href'),
    value: a.getAttribute('aria-current')})),
  animations: document.getAnimations().length,
  reduced: app ? app.motion.reduced : null,
  pwned: typeof window.__pwned !== 'undefined',
  siteCounts: site ? {script: site.querySelectorAll('script').length, img: site.querySelectorAll('img').length,
    svg: site.querySelectorAll('svg').length, svgFigure: site.querySelectorAll('svg.hub-figure').length,
    iframe: site.querySelectorAll('iframe,object,embed').length} : null,
  siteText: site ? site.textContent : '',
  graphList: {rows: document.querySelectorAll('#graph-list li').length,
    openLinks: document.querySelectorAll('#graph-list a.hub-graph-open').length}
};
if (args.content && site && app && app.state.page) {
  const head = site.querySelector('.hub-site-head');
  const h1 = site.querySelector('h1.hub-site-title');
  const eyebrow = site.querySelector('.hub-site-head .hub-eyebrow');
  const dot = eyebrow ? eyebrow.querySelector('.hub-eyebrow-dot') : null;
  const content = {
    eyebrow: eyebrow ? eyebrow.textContent.trim() : null,
    eyebrowDotHidden: dot ? dot.getAttribute('aria-hidden') : null,
    eyebrowRole: textOf(eyebrow ? eyebrow.querySelector('.hub-role') : null),
    h1: textOf(h1), h1Tabindex: h1 ? h1.getAttribute('tabindex') : null,
    h1Parts: h1 ? Array.from(h1.childNodes, n => ({type: n.nodeType, text: n.textContent,
      cls: n.nodeType === 1 ? n.className : null})) : [],
    chip: textOf(head ? head.querySelector('.hub-chip') : null),
    hiddenLabel: textOf(head ? head.querySelector('.hub-hidden-label') : null),
    numerals: Array.from(site.querySelectorAll('.hub-site-nums .hub-bank-numeral'), b => ({
      text: b.textContent, classes: b.className, caption: textOf(b.parentElement.querySelector('.hub-bank-caption'))})),
    rankScore: textOf(site.querySelector('.hub-site-nums .hub-mono')),
    reading: textOf(site.querySelector('.hub-site-reading')),
    use: textOf(site.querySelector('.hub-site-use')),
    useLabel: textOf(site.querySelector('.hub-site-use strong')),
    also: linkOf(site.querySelector('a.hub-pair-also')),
    meaningHeading: textOf(site.querySelector('.hub-site-meaning h2')),
    meaningLine: textOf(site.querySelector('.hub-site-meaning > p')),
    meaningDetails: Array.from(site.querySelectorAll('.hub-site-meaning details'), d => ({
      summary: textOf(d.querySelector('summary')), body: textOf(d.querySelector('p'))})),
    recordsHeading: textOf(site.querySelector('.hub-site-records h2')),
    records: Array.from(site.querySelectorAll('article.hub-site-record'), card => ({
      sourceHref: card.querySelector('a.hub-mono') ? card.querySelector('a.hub-mono').getAttribute('href') : null,
      sourceLabel: card.querySelector('a.hub-mono') ? card.querySelector('a.hub-mono').getAttribute('aria-label') : null,
      sourceText: textOf(card.querySelector('a.hub-mono')),
      titleHref: card.querySelector('h3 a') ? card.querySelector('h3 a').getAttribute('href') : null,
      title: textOf(card.querySelector('h3 a')),
      excerpt: textOf(card.querySelector('.hub-site-excerpt')),
      read: linkOf(card.querySelector('a.hub-site-record-read'))
    })),
    figureBlock: (() => {
      const block = site.querySelector('figure.hub-pair-figure-block');
      if (!block) return null;
      const wrap = block.querySelector('.hub-pair-figure');
      const svg = wrap ? wrap.querySelector('svg.hub-figure') : null;
      const legend = site.querySelector('details.hub-pair-legend');
      return {
        wrapHidden: wrap ? wrap.getAttribute('aria-hidden') : null,
        wrapDisplay: wrap ? style(wrap).display : null,
        wrapBox: box(wrap), svgBox: box(svg),
        svg: svg ? serialise(svg) : null,
        desc: svg && svg.querySelector('desc') ? svg.querySelector('desc').textContent : null,
        texts: svg ? Array.from(svg.querySelectorAll('text'), t => t.textContent) : [],
        caption: textOf(block.querySelector('figcaption')),
        legendOpen: legend ? legend.open : null,
        legendSummary: textOf(legend ? legend.querySelector('summary') : null),
        legendBody: textOf(legend ? legend.querySelector('p') : null)
      };
    })(),
    twin: (() => {
      const twin = site.querySelector('section.hub-pair-twin');
      if (!twin) return null;
      const s = style(twin);
      return {
        ariaHidden: twin.getAttribute('aria-hidden'), heading: textOf(twin.querySelector('h2')),
        text: twin.textContent, display: s.display, visibility: s.visibility, position: s.position,
        clipPath: s.clipPath, box: box(twin),
        dts: Array.from(twin.querySelectorAll('dt'), textOf), dds: Array.from(twin.querySelectorAll('dd'), textOf),
        desc: textOf(twin.querySelector('dl + p'))
      };
    })(),
    // The record page.
    source: (() => {
      const line = site.querySelector('.hub-site-source');
      if (!line) return null;
      const link = line.querySelector('a');
      return {text: line.textContent, mono: style(line).fontFamily, linkHref: link ? link.getAttribute('href') : null,
        linkText: textOf(link), linkCount: line.querySelectorAll('a').length};
    })(),
    flags: Array.from(site.querySelectorAll('.hub-flag'), textOf),
    textHeading: textOf(site.querySelector('.hub-site-text h2')),
    paragraphs: Array.from(site.querySelectorAll('.hub-site-text .hub-site-prose p'), textOf),
    wordsHeading: textOf(site.querySelector('.hub-site-words h2')),
    words: Array.from(site.querySelectorAll('.hub-site-words li.hub-chip'), textOf),
    noWords: textOf(site.querySelector('.hub-site-words p')),
    pairsHeading: textOf(site.querySelector('.hub-site-pairs h2')),
    pairs: Array.from(site.querySelectorAll('li.hub-site-pair'), item => {
      const thumb = item.querySelector('.hub-site-thumb');
      const svg = thumb ? thumb.querySelector('svg') : null;
      return {
        thumbHidden: thumb ? thumb.getAttribute('aria-hidden') : null, thumbBox: box(thumb),
        thumbSvg: svg ? serialise(svg) : null,
        pairLink: linkOf(item.querySelector('a.hub-site-pair-link')),
        engine: textOf(item.querySelector('.hub-site-pair-engine')),
        partner: linkOf(item.querySelector('a.hub-site-partner')),
        numerals: Array.from(item.querySelectorAll('.hub-bank-numeral'), b => ({text: b.textContent,
          classes: b.className, caption: textOf(b.parentElement.querySelector('.hub-bank-caption'))}))
      };
    }),
    noPairs: textOf(site.querySelector('.hub-site-pairs > p'))
  };
  state.content = content;
}
if (args.metrics && site) {
  const small = [];
  let minimum = Infinity;
  for (const node of document.body.querySelectorAll('*')) {
    const s = style(node);
    const rect = node.getBoundingClientRect();
    if (!rect.width || !rect.height || s.visibility === 'hidden' || s.display === 'none') continue;
    if (node.closest('.hub-visually-hidden, .hub-pair-twin') || (node.classList.contains('hub-skip') && node !== active)) continue;
    const text = Array.from(node.childNodes).some(child => child.nodeType === Node.TEXT_NODE && child.textContent.trim());
    if (text) {
      const size = parseFloat(s.fontSize);
      minimum = Math.min(minimum, size);
      if (size < 13) small.push({tag: node.tagName, class: node.className, size});
    }
  }
  const targetSelector = '.hub-knob, nav.hub-crumbs a, article.hub-site-record a, li.hub-site-pair a, '
    + 'a.hub-pair-also, details.hub-pair-legend summary, .hub-site-source a';
  const targets = Array.from(site.querySelectorAll(targetSelector)).filter(shown).map(node => {
    const r = node.getBoundingClientRect();
    return {tag: node.tagName, classes: node.className, text: node.textContent.trim().slice(0, 40),
      width: r.width, height: r.height, isKnob: node.classList.contains('hub-knob'),
      off: node.classList.contains('hub-knob--off')};
  });
  const backKnob = site.querySelector('a.hub-knob--back');
  let ring = null;
  if (backKnob) {
    backKnob.focus({preventScroll: true});
    // Keyboard focus: a programmatic focus after a key event shows :focus-visible in both
    // engines; the driver's Tab press is the real path, this is the measurement.
    ring = {outlineWidth: style(backKnob).outlineWidth, outlineStyle: style(backKnob).outlineStyle,
      matches: backKnob.matches(':focus-visible')};
  }
  const figureWrap = site.querySelector('.hub-pair-figure');
  const twin = site.querySelector('section.hub-pair-twin');
  state.metrics = {
    scrollWidth: root.scrollWidth, innerWidth: window.innerWidth, small, minimum, targets, ring,
    figureDisplay: figureWrap ? style(figureWrap).display : null,
    figureSvgWidth: figureWrap && figureWrap.querySelector('svg') ? figureWrap.querySelector('svg').getBoundingClientRect().width : null,
    twin: twin ? {display: style(twin).display, visibility: style(twin).visibility, box: box(twin),
      position: style(twin).position, clipPath: style(twin).clipPath} : null,
    knobTransition: backKnob ? style(backKnob).transitionDuration : null
  };
}
return state;
