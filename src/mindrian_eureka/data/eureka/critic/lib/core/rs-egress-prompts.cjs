// Stage-A-only guard. The packaged surface never runs the source's rubric,
// critic-payload construction, or external egress path.
'use strict';
function unavailable() {
  throw new Error('Eureka critic Stage B is not enabled in this capability');
}
module.exports = { auditQueryString: unavailable, auditQueryObject: unavailable };
