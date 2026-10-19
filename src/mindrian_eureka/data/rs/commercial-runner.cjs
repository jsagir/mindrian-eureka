'use strict';
const fs = require('node:fs');
const crypto = require('node:crypto');
const { assess } = require('./rs-commercial-assessor.cjs');
const { auditQueryObject } = require('./rs-expert-local-policy.cjs');
const request = JSON.parse(fs.readFileSync(0, 'utf8'));
const discovery = request.discovery;
const adapted = {
  ...discovery,
  resolved_authors: (discovery.resolved_authors || []).map((row) => ({ name: row.name })),
  resolved_institutions: (discovery.resolved_institutions || []).map((row) => row.name),
};
const result = assess(adapted);
const sourceQueues = new Map();
for (const [type, rows] of [['author', discovery.resolved_authors || []], ['institution', discovery.resolved_institutions || []]]) {
  for (const row of rows) {
    const key = `${type}\0${row.name}`;
    if (!sourceQueues.has(key)) sourceQueues.set(key, []);
    sourceQueues.get(key).push(row.source_ids || []);
  }
}
result.partnership_targets = result.partnership_targets.map((target) => {
  const key = `${target.type}\0${target.name}`;
  const queue = sourceQueues.get(key) || [];
  return { ...target, source_ids: queue.length ? queue.shift() : [] };
});
auditQueryObject(result, 'rs-commercial-assessor-result');
process.stdout.write(JSON.stringify({
  result,
  input_fingerprint: crypto.createHash('sha256').update(JSON.stringify(request)).digest('hex'),
}));
