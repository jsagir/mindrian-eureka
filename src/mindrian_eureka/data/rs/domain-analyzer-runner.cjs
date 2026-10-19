'use strict';
const fs = require('node:fs');
const crypto = require('node:crypto');
const { analyzeDomain, _test } = require('./rs-domain-analyzer.cjs');
const { auditQueryObject } = require('./rs-expert-local-policy.cjs');
const request = JSON.parse(fs.readFileSync(0, 'utf8'));
const options = { ...(request.options || {}), substrate: request.substrate };
(async () => {
  const domain_analysis = await analyzeDomain(request.topic, options);
  const tokens = _test.tokenize(request.topic.trim());
  const grams = _test.ngrams(tokens);
  const top = request.substrate.slice(0, options.limit || 100);
  const ranked_domains = top.map((entry, index) => ({
    entry, index, score: _test.scoreEntryAgainstTopic(entry, grams, tokens.length),
  })).sort((a, b) => b.score - a.score || a.index - b.index).map(({ entry, score }) => ({
    node_id: entry.id, framework_name: entry.metadata.framework_name, score, source_ids: entry.source_ids || [],
  }));
  const result = { domain_analysis, ranked_domains };
  auditQueryObject(result, 'rs-domain-analyzer-result');
  process.stdout.write(JSON.stringify({
    result,
    input_fingerprint: crypto.createHash('sha256').update(JSON.stringify(request)).digest('hex'),
  }));
})().catch((error) => { process.stderr.write(String(error && error.stack || error)); process.exitCode = 1; });
