'use strict';

const dimensions = require('./portfolio-dimensions.cjs');
const ahp = require('./ahp-weights.cjs');

function run(input) {
  const byId = new Map(input.items.map((item) => [item.id, item]));
  const a = byId.get(input.pair.a_id);
  const b = byId.get(input.pair.b_id);
  if (!a || !b) throw new Error('PAIR_ENDPOINT: pair endpoints must exist in items');

  const prepared = dimensions.prepareCohort(input.items);
  const aDimensions = dimensions.scoreTechDimensions(a, input.items, prepared);
  const bDimensions = dimensions.scoreTechDimensions(b, input.items, prepared);
  const pairDimensions = dimensions.scorePairDimensions({
    a: aDimensions,
    b: bDimensions,
    rs: input.pair.rs,
  });
  const weights = ahp.computeAhpWeights(input.criteria_matrix);
  if (!weights.consistent) {
    throw new Error('AHP_INCONSISTENT: consistency ratio ' + weights.cr.toFixed(6) +
      ' exceeds ' + weights.cr_max);
  }

  return {
    candidate_ids: [a.id, b.id],
    source_refs: {
      [a.id]: a.source_refs,
      [b.id]: b.source_refs,
      rs: input.pair.rs_source_ref,
    },
    criteria: ahp.CRITERIA,
    a_dimensions: aDimensions,
    b_dimensions: bDimensions,
    pair_dimensions: pairDimensions,
    weak_dimensions: {
      [a.id]: dimensions.weakDimensions(aDimensions),
      [b.id]: dimensions.weakDimensions(bDimensions),
    },
    complementary: dimensions.complementary(aDimensions, bDimensions),
    weighting: {
      method: weights.method,
      weights: weights.weights,
      lambda_max: weights.lambdaMax,
      consistency_index: weights.ci,
      consistency_ratio: weights.cr,
      consistency_limit: weights.cr_max,
      consistent: weights.consistent,
      out_of_scale: weights.out_of_scale,
    },
    portfolio_priority_signal: ahp.composeScore(pairDimensions, weights.weights),
  };
}

try {
  let input = '';
  process.stdin.setEncoding('utf8');
  process.stdin.on('data', (chunk) => { input += chunk; });
  process.stdin.on('end', () => {
    try {
      const request = JSON.parse(input);
      process.stdout.write(JSON.stringify(run(request)) + '\n');
    } catch (error) {
      process.stderr.write(String(error && error.message || error) + '\n');
      process.exitCode = 2;
    }
  });
} catch (error) {
  process.stderr.write(String(error && error.message || error) + '\n');
  process.exitCode = 2;
}
