if (args.wait === 'unlocked') {
  const deadline = performance.now() + 15000;
  while (performance.now() < deadline) {
    if (window.HubApp && window.HubApp.data) break;
    await new Promise(resolve => setTimeout(resolve, 10));
  }
}
if (args.settle) await new Promise(resolve => setTimeout(resolve, args.settle));
await document.fonts.ready;
const band = document.getElementById('hub-band');
const app = window.HubApp || {state: null};
const visible = node => Boolean(node.getClientRects().length) && getComputedStyle(node).visibility !== 'hidden';
const colour = (selector, property) => {
  const node = band ? band.querySelector(selector) : null;
  return node ? getComputedStyle(node)[property] : null;
};
let minimum = Infinity;
if (band) {
  for (const node of band.querySelectorAll('*')) {
    const style = getComputedStyle(node);
    const rect = node.getBoundingClientRect();
    if (!rect.width || !rect.height || style.display === 'none') continue;
    const text = Array.from(node.childNodes).some(child => child.nodeType === Node.TEXT_NODE && child.textContent.trim());
    if (text) minimum = Math.min(minimum, parseFloat(style.fontSize));
  }
}
const columnsValue = band ? getComputedStyle(band).gridTemplateColumns : 'none';
const link = band ? band.querySelector('.hub-band-link') : null;
const linkBox = link ? link.getBoundingClientRect() : null;
const mark = band ? band.querySelector('.hub-band-mark') : null;
return {
  present: Boolean(band),
  hidden: band ? band.hidden : null,
  rects: band ? band.getClientRects().length : 0,
  text: band ? band.textContent : '',
  label: band && band.querySelector('.hub-band-label') ? band.querySelector('.hub-band-label').textContent : '',
  reading: band && band.querySelector('.hub-band-reading') ? band.querySelector('.hub-band-reading').textContent : '',
  limit: band && band.querySelector('.hub-band-limit') ? band.querySelector('.hub-band-limit').textContent : '',
  linkHref: link ? link.getAttribute('href') : null,
  linkText: link ? link.textContent : '',
  linkBox: linkBox ? {width: linkBox.width, height: linkBox.height} : null,
  bandBackground: band ? getComputedStyle(band).backgroundColor : null,
  bandColor: band ? getComputedStyle(band).color : null,
  readingColor: colour('.hub-band-reading', 'color'),
  limitColor: colour('.hub-band-limit', 'color'),
  markBackground: colour('.hub-band-mark', 'backgroundColor'),
  markText: mark ? mark.textContent : null,
  columns: columnsValue === 'none' ? 1 : columnsValue.trim().split(/\s+/).length,
  minimum: minimum,
  scrollWidth: document.documentElement.scrollWidth,
  innerWidth: window.innerWidth,
  selection: app.state ? app.state.selection : null,
  notice: document.getElementById('hub-notice') ? document.getElementById('hub-notice').textContent : '',
  hash: window.location.hash,
  active: ['bank', 'graph', 'catalogue'].filter(id => document.getElementById(id) && visible(document.getElementById(id))),
  animations: document.getAnimations().length,
  started: Boolean(app.data)
};
