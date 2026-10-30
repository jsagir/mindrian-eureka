if (args.wait) {
  const deadline = performance.now() + 15000;
  while (performance.now() < deadline) {
    const status = document.getElementById('hub-locked-status')?.textContent || '';
    if (args.wait === 'unlocked' ? Boolean(window.HubApp.data) : status === args.wait) break;
    await new Promise(resolve => setTimeout(resolve, 10));
  }
}
const field = document.getElementById('hub-passphrase');
const toggle = document.getElementById('hub-passphrase-toggle');
const unlock = document.getElementById('hub-unlock');
const body = document.body.textContent;
const storage = {};
try { storage.local = window.localStorage.length; } catch (error) { storage.localError = error.name; }
try { storage.session = window.sessionStorage.length; } catch (error) { storage.sessionError = error.name; }
try { storage.cookie = document.cookie; } catch (error) { storage.cookieError = error.name; }
const targets = [field, toggle, unlock].filter(Boolean).map(node => {
  const box = node.getBoundingClientRect();
  return {id: node.id, width: box.width, height: box.height};
});
return {
  h1: document.getElementById('hub-title').textContent,
  status: document.getElementById('hub-locked-status')?.textContent || '',
  face: document.getElementById('hub-face').getAttribute('src'),
  focus: document.activeElement.id, title: document.title,
  locked: Boolean(document.getElementById('hub-locked')),
  limitCopy: document.getElementById('hub-locked')?.textContent.includes(window.HUB_COPY.L07) || false,
  meaning: document.getElementById('hub-meaning').textContent,
  hasTitle: (args.titles || []).some(title => body.includes(title)),
  hasDistinctID: body.includes('doc003'),
  bindings: document.querySelectorAll('[data-record-id],[data-pair-key]').length,
  noscript: document.querySelector('noscript').textContent,
  storage: storage,
  fieldValue: field?.value || '', fieldType: field?.type || '',
  autocomplete: field?.getAttribute('autocomplete') || '',
  toggleText: toggle?.textContent || '', togglePressed: toggle?.getAttribute('aria-pressed') || '',
  disabled: Boolean(unlock?.disabled), targets: targets,
  schema: window.HubApp.data?.schema || null,
  count: window.HubApp.data?.counts.records || null,
  transitions: window.__gateTransitions || [],
  unlockMs: window.__gateEnd && window.__gateBegin ? window.__gateEnd - window.__gateBegin : null,
  plaintextStored: Object.prototype.hasOwnProperty.call(window, 'HUB'),
  injected: typeof window.__pwned !== 'undefined',
  hidden: ['hub-counts','hub-nav','hub-results','hub-panel','hub-data-check'].map(id => ({
    id: id, visible: Boolean(document.getElementById(id).getClientRects().length)
  }))
};
