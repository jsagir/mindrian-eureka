'use strict';
const fs = require('node:fs');
const crypto = require('node:crypto');
const critic = require('./lib/core/eureka-critic.cjs');
const request = JSON.parse(fs.readFileSync(0, 'utf8'));
async function main() {
const hashText = value => crypto.createHash('sha256').update(value, 'utf8').digest('hex');
const variants = critic.prepareMechanismVariants(request.candidate && request.candidate.mechanismText);
const hashes = variants.map(text => crypto.createHash('sha256').update(text, 'utf8').digest('hex'));
if (request.action === 'prepare') {
  process.stdout.write(JSON.stringify({ mechanism_variants: variants, mechanism_variant_sha256: hashes,
    required_model: 'MindrianOS configured local embedding model', required_graph_query:
      'Return bounded nearest neighbors for the original mechanism vector from the authorized local graph projection.' }));
} else if (request.action === 'prepare_rubric') {
  const options = { maxChars: request.prompt_max_chars };
  const neutral = critic.buildNeutralPrompt(request.candidate, options);
  const adversarial = critic.buildAdversarialPrompt(request.candidate, options);
  process.stdout.write(JSON.stringify({
    candidate_id: request.candidate_id, source_node_id: request.source_node_id,
    scope_id: request.scope_id, snapshot_id: request.snapshot_id,
    neutral_prompt: neutral, adversarial_prompt: adversarial,
    prompt_sha256: { neutral: hashText(neutral), adversarial: hashText(adversarial) },
    prompt_max_chars: request.prompt_max_chars === undefined ? 8000 : request.prompt_max_chars,
    judge_policy: 'MindrianOS must use its approved local judge; do not send candidate text to an external model.'
  }));
} else if (request.action === 'evaluate') {
  const embedding = request.embedding || {};
  const vectors = embedding.vectors;
  const neighbors = request.nearest_neighbors;
  if (!Array.isArray(vectors) || vectors.length !== variants.length) throw new Error('embedding vector count does not match prepared mechanism variants');
  if (!Array.isArray(neighbors)) throw new Error('nearest_neighbors must be a host-prepared array (empty is allowed)');
  const result = await critic.stageA(request.candidate, {
    _hostModel: embedding.model,
    sourcedQuantities: request.sourced_quantities === true,
    encodeFn: async () => vectors,
    knnFn: async () => neighbors,
  });
  process.stdout.write(JSON.stringify({
    stage: 'A', status: result.pass ? 'passed_deterministic_gates' : (result.degraded ? 'degraded' : 'gate_failed'),
    pass: result.pass, route: result.route || null, tag: result.tag || null,
    features: result.features || {},
    host_context: { scope_id: request.scope_id, snapshot_id: request.snapshot_id,
      candidate_id: request.candidate_id, source_node_id: request.source_node_id,
      embedding_model: embedding.model, embedding_dim: vectors[0] && vectors[0].length,
      embedding_variant_sha256: hashes,
      nearest_neighbor_ids: neighbors.map(n => n.node_id), nearest_neighbor_count: neighbors.length },
    next_step: result.pass ? 'Stage B rubric is not included; MindrianOS must route this candidate to its approved local review.' : null,
    graph_write: 'not_performed',
    limitations: ['This is Stage A deterministic triage only; a pass is not a validated opportunity or transfer.',
      'Embeddings and nearest neighbors were supplied by MindrianOS and are not independently verified by Eureka.',
      'MindrianOS must confirm the vector hashes were generated from the returned exact variant texts using the stated local model.',
      'No graph read, graph write, search, or model call occurred in Eureka.']
  }));
} else if (request.action === 'evaluate_rubric') {
  const stageA = request.stage_a_result;
  const stageAContext = stageA && stageA.host_context || {};
  if (!stageA || stageA.pass !== true || stageA.status !== 'passed_deterministic_gates' ||
      stageAContext.candidate_id !== request.candidate_id || stageAContext.snapshot_id !== request.snapshot_id ||
      stageAContext.scope_id !== request.scope_id || stageAContext.source_node_id !== request.source_node_id) {
    throw new Error('a passing Stage A result for the same candidate and snapshot is required');
  }
  const promptOptions = { maxChars: request.prompt_max_chars };
  const prompts = {
    neutral: critic.buildNeutralPrompt(request.candidate, promptOptions),
    adversarial: critic.buildAdversarialPrompt(request.candidate, promptOptions),
  };
  const expectedHashes = { neutral: hashText(prompts.neutral), adversarial: hashText(prompts.adversarial) };
  if (!request.prompt_sha256 || request.prompt_sha256.neutral !== expectedHashes.neutral || request.prompt_sha256.adversarial !== expectedHashes.adversarial) {
    throw new Error('prompt_sha256 does not match source-generated prompts for this candidate');
  }
  const rawResponses = { neutral: request.judge_responses.neutral, adversarial: request.judge_responses.adversarial };
  const rubric = await critic.runRubric(request.candidate, {
    repeats: 1, maxChars: request.prompt_max_chars,
    judgeFn: async (prompt, meta) => {
      if (hashText(prompt) !== expectedHashes[meta.pass]) throw new Error('source rubric prompt changed during evaluation');
      return rawResponses[meta.pass];
    },
  });
  process.stdout.write(JSON.stringify({
    status: rubric.disagreement ? 'rubric_disagreement' : 'completed_rubric_triage',
    candidate_id: request.candidate_id, source_node_id: request.source_node_id,
    scope_id: request.scope_id, snapshot_id: request.snapshot_id,
    stage_a_status: stageA.status, judge_model: request.judge_model,
    prompt_sha256: expectedHashes,
    rubric_pattern: rubric.rubric_pattern, verdict: rubric.verdict,
    reasoning_tag: rubric.reasoning_tag, agreement: rubric.agreement,
    judgments: rubric.judgments, calls: rubric.calls, repeats: rubric.repeats,
    confidence: 'not_calibrated', graph_write: 'not_performed',
    limitations: ['Judge responses were supplied by MindrianOS; Eureka made no model call and cannot attest to model locality or response integrity.',
      'The rubric verdict is deterministic triage over two judge responses, not a validated transfer or opportunity judgment.',
      'No calibration baseline is loaded and no confidence level is inferred.',
      'No graph read, graph write, or external research occurred in Eureka.']
  }));
} else {
  throw new Error('action must be prepare, evaluate, prepare_rubric, or evaluate_rubric');
}
}
main().catch(error => { process.stderr.write(String(error && error.stack || error)); process.exitCode = 1; });
