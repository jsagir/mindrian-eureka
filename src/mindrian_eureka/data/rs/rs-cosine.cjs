'use strict';

// Read-only numeric helper shared by the source RS scorer. It performs no
// cache, room, provider, or network operations.
function cosineSimilarity(a, b) {
  if (!Array.isArray(a) || !Array.isArray(b) || a.length !== b.length || !a.length) return 0;
  let dot = 0, normA = 0, normB = 0;
  for (let i = 0; i < a.length; i += 1) {
    const x = a[i], y = b[i];
    if (typeof x !== 'number' || typeof y !== 'number' || !Number.isFinite(x) || !Number.isFinite(y)) return 0;
    dot += x * y; normA += x * x; normB += y * y;
  }
  if (normA === 0 || normB === 0) return 0;
  const score = dot / (Math.sqrt(normA) * Math.sqrt(normB));
  return Math.max(-1, Math.min(1, score));
}
module.exports = { cosineSimilarity };
