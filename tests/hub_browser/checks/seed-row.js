// Measure the seed command row under each pair of the bank (Phase 2.3, plan 04).
// Runs in the page. Reads layout only; it changes nothing.
await document.fonts.ready;
const rows = Array.from(document.querySelectorAll('#bank-list [data-pair-key]')).map(row => {
  const seed = row.querySelector('.hub-bank-seed');
  const others = Array.from(row.children).filter(child => child !== seed);
  const rowBox = row.getBoundingClientRect();
  if (!seed) return {key: row.dataset.pairKey, seed: false};
  const seedBox = seed.getBoundingClientRect();
  return {
    key: row.dataset.pairKey,
    seed: true,
    seedCount: row.querySelectorAll('.hub-bank-seed').length,
    command: seed.querySelector('code')?.textContent ?? null,
    label: seed.querySelector('.hub-chip')?.textContent ?? null,
    seedTop: seedBox.top,
    seedRight: seedBox.right,
    seedWidth: seedBox.width,
    othersBottom: Math.max(...others.map(child => child.getBoundingClientRect().bottom)),
    rowRight: rowBox.right,
    rowWidth: rowBox.width,
    isLast: row.lastElementChild === seed,
    hasLabelsClass: seed.classList.contains('hub-bank-labels'),
    buttons: row.querySelectorAll('button').length,
    statusLabels: row.querySelectorAll('.hub-bank-status').length
  };
});
const extras = document.querySelector('.hub-bank-extras');
const labels = extras?.closest('[data-pair-key]')
  ?.querySelector('.hub-bank-labels:not(.hub-bank-extras)') ?? null;
const box = node => {
  if (!node) return null;
  const r = node.getBoundingClientRect();
  return {top: r.top, bottom: r.bottom, left: r.left, right: r.right};
};
return {
  rows: rows,
  hint: document.querySelectorAll('.hub-bank-seed-hint').length,
  hintText: document.querySelector('.hub-bank-seed-hint')?.textContent ?? null,
  overflow: document.documentElement.scrollWidth - window.innerWidth,
  pwned: typeof window.__pwned,
  extrasBox: box(extras),
  labelsBox: box(labels)
};
