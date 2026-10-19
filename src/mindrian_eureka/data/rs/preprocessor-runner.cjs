'use strict';
const fs = require('node:fs');
const crypto = require('node:crypto');
const { preprocess } = require('./rs-preprocessor.cjs');
const request = JSON.parse(fs.readFileSync(0, 'utf8'));
const result = preprocess(request.documents, { domain_analysis: request.domain_analysis });
process.stdout.write(JSON.stringify({
  result,
  input_fingerprint: crypto.createHash('sha256').update(JSON.stringify(request)).digest('hex'),
}));
