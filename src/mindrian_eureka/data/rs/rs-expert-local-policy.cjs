'use strict';

// Local-source hygiene only. This stage performs no outbound egress and does
// not call the Brain. Keep the source package's content-set exclusions local
// to this adapter; MindrianOS remains responsible for any external-egress gate.
const FORBIDDEN_PATTERNS = Object.freeze([
  /meeting_transcript/i,
  /decision_log/i,
  /governing_thought/i,
  /\b\d{3}-\d{3}-\d{4}\b/,
  /\bSSN\b/,
]);

class ExternalEgressViolation extends Error {
  constructor(message, meta) {
    super(message);
    this.name = 'ExternalEgressViolation';
    this.meta = meta || {};
  }
}

function auditQueryObject(value, surface) {
  const serialized = JSON.stringify(value);
  for (const pattern of FORBIDDEN_PATTERNS) {
    pattern.lastIndex = 0;
    if (pattern.test(serialized)) {
      throw new ExternalEgressViolation('forbidden content in local expert result', { surface });
    }
  }
  return value;
}

function auditQueryString(value, surface) {
  if (typeof value !== 'string') return value;
  for (const pattern of FORBIDDEN_PATTERNS) {
    pattern.lastIndex = 0;
    if (pattern.test(value)) {
      throw new ExternalEgressViolation('forbidden content in local RS result', { surface });
    }
  }
  return value;
}

module.exports = { ExternalEgressViolation, FORBIDDEN_PATTERNS, auditQueryObject, auditQueryString };
