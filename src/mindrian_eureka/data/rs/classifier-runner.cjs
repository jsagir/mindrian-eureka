'use strict';
const fs = require('node:fs');
const crypto = require('node:crypto');
const { classify } = require('./rs-innovation-classifier.cjs');
const request = JSON.parse(fs.readFileSync(0, 'utf8'));
const result = classify(request.scored_pair, request.options || {});
process.stdout.write(JSON.stringify({
  result,
  input_fingerprint: crypto.createHash('sha256').update(JSON.stringify(request)).digest('hex'),
}));
