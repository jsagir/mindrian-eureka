'use strict';
const fs = require('node:fs');
const crypto = require('node:crypto');
const { scoreBreakthrough } = require('./rs-breakthrough-scorer.cjs');

const request = JSON.parse(fs.readFileSync(0, 'utf8'));
const result = scoreBreakthrough(request.classified_pair, request.options || {});
process.stdout.write(JSON.stringify({
  result,
  input_fingerprint: crypto.createHash('sha256').update(JSON.stringify(request)).digest('hex'),
}));
