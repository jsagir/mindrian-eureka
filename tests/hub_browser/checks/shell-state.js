if (args.wait === 'unlocked') {
  const deadline = performance.now() + 15000;
  while (performance.now() < deadline) {
    if (window.HubApp && window.HubApp.data) break;
    await new Promise(resolve => setTimeout(resolve, 10));
  }
}
const app = window.HubApp || {state: null, data: null};
if (args.go && app.data) app.go(args.go, {focus: false});
if (args.panel === 'pair' && app.data) app.select({type: 'pair', key: app.data.pairs[0].key});
if (typeof args.scroll === 'number') window.scrollTo(0, args.scroll);
if (args.settle) await new Promise(resolve => setTimeout(resolve, args.settle));
await document.fonts.ready;
await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
const byId = id => document.getElementById(id);
const one = selector => document.querySelector(selector);
const style = node => (node ? getComputedStyle(node) : null);
const box = node => {
  if (!node) return null;
  const rect = node.getBoundingClientRect();
  return {top: rect.top, bottom: rect.bottom, left: rect.left, width: rect.width, height: rect.height,
    rects: node.getClientRects().length};
};
const typeOf = node => {
  const s = style(node);
  return s ? {color: s.color, fontFamily: s.fontFamily, fontSize: s.fontSize, fontWeight: s.fontWeight,
    letterSpacing: s.letterSpacing, lineHeight: s.lineHeight, textDecorationLine: s.textDecorationLine,
    textDecorationThickness: s.textDecorationThickness, backgroundColor: s.backgroundColor,
    borderRadius: s.borderRadius, transform: s.transform, transitionDuration: s.transitionDuration} : null;
};
const header = byId('hub-header');
const headerStyle = style(header);
const links = one('.hub-header-links');
const nav = byId('hub-nav');
const action = byId('hub-header-action');
const row = one('.hub-title-row');
const counts = byId('hub-counts');
const countColumns = counts ? style(counts).gridTemplateColumns : 'none';
const check = byId('hub-data-check');
const footer = byId('hub-footer');
let link = one('#hub-data-check a') || one('#hub-footer a') || one('#catalogue-list a.hub-link');
const button = one(args.button || '.hub-bank-read');
const root = document.documentElement;
return {
  header: headerStyle ? {
    position: headerStyle.position, top: headerStyle.top, zIndex: headerStyle.zIndex,
    backgroundColor: headerStyle.backgroundColor, backdropFilter: headerStyle.backdropFilter || 'none',
    borderBottomWidth: headerStyle.borderBottomWidth, borderBottomColor: headerStyle.borderBottomColor,
    offsetHeight: header.offsetHeight, box: box(header)
  } : null,
  variable: root.style.getPropertyValue('--hub-header-height').trim(),
  scrollPaddingTop: style(root).scrollPaddingTop,
  lockup: Object.assign({}, box(one('#hub-header img')), {inlineSize: style(one('#hub-header img')) ? style(one('#hub-header img')).width : null}),
  context: box(one('.hub-header-context')),
  links: box(links),
  linkChildren: links ? Array.from(links.children, node => box(node)) : [],
  navLinks: nav ? Array.from(nav.querySelectorAll('a'), node => Object.assign({
    href: node.getAttribute('href'), current: node.getAttribute('aria-current'),
    fontWeight: style(node).fontWeight, fontSize: style(node).fontSize, color: style(node).color,
    textDecorationLine: style(node).textDecorationLine,
    borderBottomWidth: style(node).borderBottomWidth, borderBottomColor: style(node).borderBottomColor
  }, box(node))) : [],
  nav: box(nav),
  action: action ? Object.assign({href: action.getAttribute('href'), text: action.textContent,
    fontSize: style(action).fontSize, borderWidth: style(action).borderTopWidth,
    borderColor: style(action).borderTopColor}, box(action)) : null,
  eyebrow: typeOf(one('.hub-eyebrow')),
  dot: Object.assign({}, typeOf(one('.hub-eyebrow-dot')), box(one('.hub-eyebrow-dot'))),
  heading: Object.assign({text: byId('hub-title') ? byId('hub-title').textContent : ''}, typeOf(byId('hub-title'))),
  titleRow: row ? {borderBottomWidth: style(row).borderBottomWidth, borderBottomStyle: style(row).borderBottomStyle,
    borderBottomColor: style(row).borderBottomColor} : null,
  face: box(byId('hub-face')),
  counts: counts ? {
    columns: countColumns === 'none' ? 1 : countColumns.trim().split(/\s+/).length,
    borderTopWidth: style(counts).borderTopWidth, borderTopColor: style(counts).borderTopColor,
    borderBottomWidth: style(counts).borderBottomWidth, borderBottomColor: style(counts).borderBottomColor,
    numeral: typeOf(one('.hub-count strong')), caption: typeOf(one('.hub-count span')), box: box(counts)
  } : null,
  body: typeOf(document.body),
  dataCheck: check ? {backgroundColor: style(check).backgroundColor, borderWidth: style(check).borderTopWidth,
    borderColor: style(check).borderTopColor, box: box(check)} : null,
  footer: footer ? {borderTopWidth: style(footer).borderTopWidth, borderTopColor: style(footer).borderTopColor} : null,
  link: link ? Object.assign({href: link.getAttribute('href')}, typeOf(link)) : null,
  button: button ? Object.assign({text: button.textContent}, typeOf(button)) : null,
  band: box(byId('hub-band')),
  notice: byId('hub-notice') ? byId('hub-notice').textContent : '',
  hash: window.location.hash,
  scrollY: window.scrollY,
  scrollWidth: root.scrollWidth,
  innerWidth: window.innerWidth,
  innerHeight: window.innerHeight,
  started: Boolean(app.data),
  panelOpen: Boolean(app.state && app.state.panelOpen)
};
