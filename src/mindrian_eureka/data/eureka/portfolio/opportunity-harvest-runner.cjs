'use strict';

const harvest = require('./opportunity-harvest.cjs');

try {
  let input = '';
  process.stdin.setEncoding('utf8');
  process.stdin.on('data', (chunk) => { input += chunk; });
  process.stdin.on('end', () => {
    try {
      const request = JSON.parse(input);
      if (request.snapshot.completeness !== 'complete_authorized_scope') {
        throw new Error('SNAPSHOT_INCOMPLETE: harvest requires a complete projection of the authorized scope');
      }
      if (request.snapshot.omitted_nodes !== 0 || request.snapshot.omitted_edges !== 0) {
        throw new Error('SNAPSHOT_INCOMPLETE: omitted graph records prevent complete candidate discovery');
      }
      const result = harvest.harvestSnapshot(request.snapshot, {
        banked_opportunity_names: request.banked_opportunity_names,
        bank_dedup_complete: request.bank_dedup_complete,
        portfolio_rows: request.portfolio_rows,
      });
      if (!result.ok) throw new Error(result.reason || 'HARVEST_FAILED');
      process.stdout.write(JSON.stringify(result) + '\n');
    } catch (error) {
      process.stderr.write(String(error && error.message || error) + '\n');
      process.exitCode = 2;
    }
  });
} catch (error) {
  process.stderr.write(String(error && error.message || error) + '\n');
  process.exitCode = 2;
}
