'use strict';

// The upstream direction-convention.cjs is absent from LATEST. This adapter
// implements its documented Convention A behavior from rs-math.cjs: signed
// diff = semantic (BERT) - LSA; positive means structural transfer, zero or
// negative means semantic implementation.
function classify(lsa, semantic) {
  if (!Number.isFinite(lsa) || !Number.isFinite(semantic)) return 'none';
  return semantic - lsa > 0 ? 'structural_transfer' : 'semantic_implementation';
}
module.exports = { classify };
