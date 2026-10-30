'use strict';
const fs = require('node:fs');
const crypto = require('node:crypto');
const { generateQueryMatrix } = require('./rs-query-matrix.cjs');
const { auditQueryObject } = require('./rs-expert-local-policy.cjs');
const request = JSON.parse(fs.readFileSync(0, 'utf8'));
const matrix = generateQueryMatrix(request.domain_analysis);
if (matrix.error) {
  process.stdout.write(JSON.stringify({ result: matrix, input_fingerprint: crypto.createHash('sha256').update(JSON.stringify(request)).digest('hex') }));
} else {
  const query_count = Object.values(matrix.categories).reduce((total, category) => total + category.length, 0);
  const result = { ...matrix, query_count };
  auditQueryObject(result, 'rs-query-matrix-result');
  process.stdout.write(JSON.stringify({ result, input_fingerprint: crypto.createHash('sha256').update(JSON.stringify(request)).digest('hex') }));
}
