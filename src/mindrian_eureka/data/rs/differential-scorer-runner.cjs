'use strict';
const fs = require('node:fs');
const crypto = require('node:crypto');
const { score } = require('./rs-differential-scorer.cjs');
const { auditQueryObject } = require('./rs-expert-local-policy.cjs');
const request = JSON.parse(fs.readFileSync(0, 'utf8'));
(async () => {
  const vectors = [request.query_vector, request.doc_vector];
  const scores = await score(request.query_concept, request.doc_concept, {
    lexicalLeg: 'tfidf',
    encodeFn: () => vectors,
  });
  const evidence = [
    ...(request.query_source_ids || []).map(source_id => ({ source_id, side: 'problem' })),
    ...(request.doc_source_ids || []).map(source_id => ({ source_id, side: 'method' })),
  ];
  const result = {
    scored_pair: {
      query_concept: request.query_concept,
      doc_concept: request.doc_concept,
      diff: scores.diff,
      lsa: scores.lsa,
      bert: scores.bert,
      passes: scores.passes,
      ...(evidence.length ? { evidence } : {}),
    },
    ...(request.query_node_id ? { query_node_id: request.query_node_id } : {}),
    ...(request.doc_node_id ? { doc_node_id: request.doc_node_id } : {}),
  };
  auditQueryObject(result, 'rs-differential-scorer-result');
  process.stdout.write(JSON.stringify({
    result,
    input_fingerprint: crypto.createHash('sha256').update(JSON.stringify(request)).digest('hex'),
  }));
})().catch(error => { process.stderr.write(String(error && error.stack || error)); process.exitCode = 1; });
