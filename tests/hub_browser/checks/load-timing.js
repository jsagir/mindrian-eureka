// Plan 10, G3: the load time of a hub whose figures stay inline in hub-data.js.
// An eval body (see band-state.js): `args.bytes` is the size of hub-data.js on disk, passed
// back so the printed line pairs the time with the size. No network, no storage.
const deadline = performance.now() + 15000;
while (performance.now() < deadline) {
  if (window.HubApp && window.HubApp.data) break;
  await new Promise(resolve => setTimeout(resolve, 10));
}
await document.fonts.ready;
const entries = performance.getEntriesByType('navigation');
const entry = entries.length ? entries[0] : null;
const whole = value => Math.round(value || 0);
return {
  domContentLoadedEventEnd: entry ? whole(entry.domContentLoadedEventEnd) : null,
  loadEventEnd: entry ? whole(entry.loadEventEnd) : null,
  duration: entry ? whole(entry.duration) : null,
  readyState: document.readyState,
  bankRows: document.querySelectorAll('.hub-bank-row').length,
  started: Boolean(window.HubApp && window.HubApp.data),
  bytes: args.bytes
};
