if (args.wait === 'unlocked') {
  const deadline = performance.now() + 15000;
  while (performance.now() < deadline) {
    if (window.HubApp && window.HubApp.data) break;
    await new Promise(resolve => setTimeout(resolve, 10));
  }
}
if (args.listen && window.HubApp && !window.__themeListening) {
  window.__themeEvents = [];
  window.HubApp.on('theme', name => window.__themeEvents.push(name));
  window.__themeListening = true;
}
if (args.settle) await new Promise(resolve => setTimeout(resolve, args.settle));
await document.fonts.ready;
// Plan 11: under 768 px the links row scrolls sideways; the toggle must be reachable by scroll.
if (args.scrollToggle && document.getElementById('hub-theme')) {
  document.getElementById('hub-theme').scrollIntoView({inline: 'end', block: 'nearest'});
}
await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
const root = document.documentElement;
const style = node => (node ? getComputedStyle(node) : null);
const box = node => {
  if (!node) return null;
  const rect = node.getBoundingClientRect();
  return {top: rect.top, left: rect.left, width: rect.width, height: rect.height,
    rects: node.getClientRects().length};
};
const toggle = document.getElementById('hub-theme');
const label = toggle ? toggle.querySelector('.hub-theme-label') : null;
const links = document.querySelector('.hub-header-links');
const action = document.getElementById('hub-header-action');
const lockups = Array.from(document.querySelectorAll('#hub-header img'), img => ({
  src: img.getAttribute('src'), rects: img.getClientRects().length,
  display: style(img).display, filter: style(img).filter, width: img.getBoundingClientRect().width
}));
const visible = lockups.find(item => item.rects > 0);
const face = document.getElementById('hub-face');
const panelImage = document.querySelector('#hub-panel img');
let figure = null;
if (args.figure !== undefined) {
  if (window.HubApp && typeof window.HubApp.figure === 'function') {
    const node = window.HubApp.figure(args.figure);
    if (node) {
      document.getElementById('hub-page').appendChild(node);
      const fill = name => {
        const shape = node.querySelector('.' + name);
        return shape ? style(shape).fill : null;
      };
      const stroke = name => {
        const shape = node.querySelector('.' + name);
        return shape ? style(shape).stroke : null;
      };
      figure = {inserted: true, paper: fill('f-paper'), ink: fill('f-ink'), blue: fill('f-blue'),
        red: fill('f-red'), yellow: fill('f-yellow'), band: fill('f-band'), bandText: fill('f-band-t'),
        soft: fill('f-soft'), frame: stroke('f-frame'), panel: fill('f-panel'), track: fill('f-track'),
        classes: Array.from(node.querySelectorAll('[class]'), shape => shape.getAttribute('class'))};
      node.remove();
    } else {
      figure = {inserted: false};
    }
  } else {
    figure = {inserted: false, noHelper: true};
  }
}
let saved;
try { saved = localStorage.getItem('hub-theme'); } catch (error) { saved = 'unavailable'; }
const active = document.activeElement;
const band = document.getElementById('hub-band');
// A running-text link (cobalt), not the band link, which is paper on the ink ground.
const link = ['#hub-data-check a', '#hub-footer a', '#catalogue-list a.hub-link', '#catalogue-list a']
  .map(selector => document.querySelector(selector)).find(Boolean) || null;
return {
  theme: root.getAttribute('data-theme'),
  colorScheme: style(root).colorScheme,
  rootBackground: style(root).backgroundColor,
  bodyBackground: style(document.body).backgroundColor,
  bodyColor: style(document.body).color,
  bodyTransition: style(document.body).transitionDuration,
  toggle: toggle ? {
    pressed: toggle.getAttribute('aria-pressed'), name: toggle.getAttribute('aria-label'),
    label: label ? label.textContent : null, box: box(toggle), fontSize: style(toggle).fontSize,
    color: style(toggle).color, background: style(toggle).backgroundColor,
    borderColor: style(toggle).borderTopColor, borderWidth: style(toggle).borderTopWidth,
    transition: style(toggle).transitionDuration, display: style(toggle).display,
    hidden: toggle.hidden, type: toggle.getAttribute('type'),
    scrollWidth: toggle.scrollWidth, clientWidth: toggle.clientWidth,
    justifyContent: style(toggle).justifyContent, labelBox: box(label)
  } : null,
  // Plan 11: the links row and the Data check link, whose words were cut at 320 px.
  links: links ? {box: box(links), scrollWidth: links.scrollWidth, clientWidth: links.clientWidth,
    scrollLeft: links.scrollLeft} : null,
  action: action ? {box: box(action), scrollWidth: action.scrollWidth, clientWidth: action.clientWidth,
    text: action.textContent} : null,
  lockups,
  visibleLockup: visible ? visible.src : null,
  face: face ? {boxShadow: style(face).boxShadow, outlineStyle: style(face).outlineStyle,
    filter: style(face).filter, rects: face.getClientRects().length} : null,
  panelImage: panelImage ? {boxShadow: style(panelImage).boxShadow, filter: style(panelImage).filter} : null,
  figure,
  saved,
  events: window.__themeEvents || null,
  paint: window.__paint || null,
  active: active ? {id: active.id, tag: active.tagName, outlineWidth: style(active).outlineWidth,
    outlineStyle: style(active).outlineStyle} : null,
  link: link ? style(link).color : null,
  band: band ? {background: style(band).backgroundColor, color: style(band).color,
    rects: band.getClientRects().length} : null,
  scrollWidth: root.scrollWidth,
  innerWidth: window.innerWidth,
  started: Boolean(window.HubApp && window.HubApp.data)
};
