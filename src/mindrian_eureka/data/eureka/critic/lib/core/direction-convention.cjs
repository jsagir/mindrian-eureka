// Minimal compatibility contract for the source module. Stage A does not call
// these Stage-B direction helpers; they are deliberately not a second engine.
'use strict';
const DIRECTIONS = Object.freeze(['structural_transfer', 'semantic_implementation']);
const NONE = 'none';
function classify(lsa, semantic) {
  const l = Number(lsa), s = Number(semantic);
  return Number.isFinite(l) && Number.isFinite(s)
    ? (s - l > 0 ? DIRECTIONS[0] : DIRECTIONS[1]) : NONE;
}
module.exports = { DIRECTIONS, NONE, classify };
