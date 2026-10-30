'use strict';

const statement = require('./opportunity-statement.cjs');
const dimensions = require('./portfolio-dimensions.cjs');

function run(input) {
  const a = Object.assign({}, input.candidate.a, {
    weak_dimensions: dimensions.weakDimensions(input.candidate.a.dimensions),
  });
  const b = Object.assign({}, input.candidate.b, {
    weak_dimensions: dimensions.weakDimensions(input.candidate.b.dimensions),
  });

  // This engine surface prepares a draft only. Do not load or invoke a critic
  // in Eureka; MindrianOS owns its approved local critic and human review gate.
  statement._test.setCriticForTest(null);
  const result = statement.buildOpportunityStatement({
    a,
    b,
    shared_problems: input.candidate.shared_problems,
    score: input.candidate.priority_signal,
    rank: input.candidate.rank,
    tail: input.candidate.tail,
  });

  if (result.critic !== 'pending' || result.banked !== false) {
    throw new Error('DRAFT_GATE_INVARIANT: draft must remain critic-pending and unbanked');
  }
  return {
    text: result.text,
    fields: result.fields,
    critic: 'pending',
    banked: false,
    weak_dimensions: result.weak_dimensions,
    node_source_refs: {
      [a.id]: a.source_refs,
      [b.id]: b.source_refs,
    },
    shared_problem_source_refs: input.candidate.shared_problem_source_refs,
    priority_signal_source_ref: input.candidate.priority_signal_source_ref,
    rank_source_ref: input.candidate.rank_source_ref,
  };
}

try {
  let input = '';
  process.stdin.setEncoding('utf8');
  process.stdin.on('data', (chunk) => { input += chunk; });
  process.stdin.on('end', () => {
    try {
      process.stdout.write(JSON.stringify(run(JSON.parse(input))) + '\n');
    } catch (error) {
      process.stderr.write(String(error && error.message || error) + '\n');
      process.exitCode = 2;
    }
  });
} catch (error) {
  process.stderr.write(String(error && error.message || error) + '\n');
  process.exitCode = 2;
}
