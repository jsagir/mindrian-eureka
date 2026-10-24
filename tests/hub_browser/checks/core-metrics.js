await document.fonts.ready;
const small = [];
const targets = [];
let minimum = Infinity;
for (const node of document.body.querySelectorAll('*')) {
  const style = getComputedStyle(node);
  const rect = node.getBoundingClientRect();
  if (!rect.width || !rect.height || style.visibility === 'hidden' || style.display === 'none') continue;
  if (node.closest('.hub-visually-hidden') || (node.classList.contains('hub-skip') && node !== document.activeElement)) continue;
  const text = Array.from(node.childNodes).some(child => child.nodeType === Node.TEXT_NODE && child.textContent.trim());
  const size = parseFloat(style.fontSize);
  if (text) {
    minimum = Math.min(minimum, size);
    if (size < 13) small.push({tag: node.tagName, class: node.className, size: size, width: rect.width});
  }
  if (node.matches('button,input,select,#hub-nav a') && (rect.width < 43.9 || rect.height < 43.9)) {
    targets.push({tag: node.tagName, id: node.id, width: rect.width, height: rect.height});
  }
}
return {small: small, targets: targets, minimum: minimum,
  scrollWidth: document.documentElement.scrollWidth, innerWidth: window.innerWidth};
