'use strict';
const fs = require('node:fs');
const crypto = require('node:crypto');
const { assessPairSetQuality } = require('./rs-corpus-quality-gate.cjs');
const { auditQueryObject } = require('./rs-expert-local-policy.cjs');
const request = JSON.parse(fs.readFileSync(0, 'utf8'));
const pairs = request.scored_pairs;
const quality = assessPairSetQuality(pairs.map(pair => ({
  semantic_score: pair.bert,
  lsa_score: pair.lsa,
  signed_diff: pair.bert - pair.lsa,
})));
const result = {
  quality,
  pair_lineage: pairs.map(pair => ({
    pair_id: pair.pair_id,
    ...(pair.query_node_id ? { query_node_id: pair.query_node_id } : {}),
    ...(pair.doc_node_id ? { doc_node_id: pair.doc_node_id } : {}),
    source_ids: pair.source_ids || [],
  })),
};
auditQueryObject(result, 'rs-corpus-quality-result');
process.stdout.write(JSON.stringify({
  result,
  input_fingerprint: crypto.createHash('sha256').update(JSON.stringify(request)).digest('hex'),
}));
