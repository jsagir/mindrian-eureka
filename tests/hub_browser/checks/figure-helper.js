const app = window.HubApp;
const result = {hasFunction: typeof app.figure === 'function', threw: false, bad: [], other: []};
const serialise = node => new XMLSerializer().serializeToString(node);
let node = null;
try {
  node = app.figure(args.good);
} catch (error) {
  result.threw = true;
}
result.returned = Boolean(node);
if (node) {
  const elements = [node, ...node.querySelectorAll('*')];
  result.tag = node.localName;
  result.namespace = node.namespaceURI;
  result.role = node.getAttribute('role');
  result.className = node.getAttribute('class');
  result.children = Array.from(node.children, child => child.localName);
  result.tags = Array.from(new Set(elements.map(element => element.localName)));
  result.attrs = Array.from(new Set(elements.flatMap(element => Array.from(element.attributes, a => a.name))));
  result.ids = elements.filter(element => element.hasAttribute('id')).length;
  const before = document.querySelectorAll('script').length;
  const holder = document.createElement('div');
  holder.appendChild(node);
  document.getElementById('hub-results').appendChild(holder);
  await new Promise(resolve => setTimeout(resolve, 50));
  result.scriptsAdded = document.querySelectorAll('script').length - before;
  result.inserted = holder.firstElementChild === node && node.isConnected;
  result.serialised = serialise(node);
  holder.remove();
}
result.pwned = typeof window.__pwned !== 'undefined';
const parsed = new DOMParser().parseFromString(args.good, 'image/svg+xml');
result.inputSerialised = serialise(parsed.documentElement);
for (const bad of args.bad) {
  try { result.bad.push(app.figure(bad) === null); }
  catch (error) { result.threw = true; result.bad.push(false); }
}
for (const other of args.other) {
  try { result.other.push(app.figure(other) === null); }
  catch (error) { result.threw = true; result.other.push(false); }
}
try { result.other.push(app.figure(undefined) === null); }
catch (error) { result.threw = true; result.other.push(false); }
result.pwnedAfter = typeof window.__pwned !== 'undefined';
return result;
