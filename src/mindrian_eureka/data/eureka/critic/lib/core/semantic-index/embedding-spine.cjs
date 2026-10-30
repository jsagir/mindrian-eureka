// Adapter seam for MindrianOS-local embeddings. The host supplies vectors from
// its configured local encoder; this package never loads a second model/index.
'use strict';
function cosineSimilarity(a, b) {
  if (!Array.isArray(a) || !Array.isArray(b) || a.length !== b.length || !a.length) return NaN;
  let dot = 0, aa = 0, bb = 0;
  for (let i = 0; i < a.length; i += 1) {
    dot += a[i] * b[i]; aa += a[i] * a[i]; bb += b[i] * b[i];
  }
  return aa && bb ? dot / Math.sqrt(aa * bb) : NaN;
}
async function embedTexts(texts, opts) {
  const options = opts || {};
  if (typeof options.encodeFn !== 'function') return { success: false, error: 'encoder_unavailable' };
  try {
    const vectors = await options.encodeFn(texts);
    if (!Array.isArray(vectors)) return { success: false, error: 'embed_failed' };
    return { success: true, vectors, provenance: { model: options._hostModel || 'unspecified-host-model' } };
  } catch (error) {
    return { success: false, error: 'embed_failed', detail: String(error && error.message || error) };
  }
}
module.exports = { embedTexts, cosineSimilarity };
