'use strict';
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { mapExperts } = require('./rs-fetcher-experts.cjs');

const request = JSON.parse(fs.readFileSync(0, 'utf8'));
if (!Array.isArray(request.papers)) throw new TypeError('papers must be an array');
const options = {
  includeRetracted: request.include_retracted === true,
  inferFirstAuthorInstitution: request.infer_first_author_institution === true,
};
const mapped = mapExperts(request.papers, options);
const experts = Array.from(mapped);
const inputFingerprint = crypto.createHash('sha256')
  .update(JSON.stringify(request)).digest('hex');
process.stdout.write(JSON.stringify({
  experts,
  counts: mapped.provenance.counts,
  input_fingerprint: inputFingerprint,
}));
