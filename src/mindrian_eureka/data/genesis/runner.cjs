"use strict";

const fs = require("node:fs");
const path = require("node:path");
const root = __dirname;
const Context = require(path.join(root, "GenesisContextDecomposer.js"));
const Domains = require(path.join(root, "GenesisDomainIdentifier.js"));
const Personas = require(path.join(root, "GenesisPersonaGenerator.js"));
const Orchestrator = require(path.join(root, "GenesisResearchOrchestrator.js"));
const Handoff = require(path.join(root, "GenesisHandoffProtocol.js"));

async function main() {
  const request = JSON.parse(fs.readFileSync(0, "utf8"));
  for (const module of [Context, Domains, Personas, Orchestrator, Handoff]) module.silent = true;
  if (Number.isInteger(request.research_year)) Personas.options.year = request.research_year;

  const lines = [`Investigation objective: ${request.objective}`];
  const included = [];
  const omittedIds = [];
  let remaining = 200000 - lines[0].length;
  for (const artifact of request.artifacts) {
    if (remaining <= 0) { omittedIds.push(artifact.id); continue; }
    const prefix = `\n\n[Graph node ${artifact.id}; ${artifact.title || "untitled"}]\n`;
    const room = Math.max(0, remaining - prefix.length);
    if (room <= 0) { omittedIds.push(artifact.id); continue; }
    const text = artifact.text.slice(0, room);
    lines.push(prefix + text);
    included.push({ id: artifact.id, source_ref: artifact.source_ref, sha256: artifact.sha256 || null,
      included_chars: text.length, source_chars: artifact.text.length, truncated: text.length < artifact.text.length });
    if (text.length < artifact.text.length) omittedIds.push(artifact.id);
    remaining -= prefix.length + text.length;
  }
  const manifest = { included_artifacts: included, omitted_artifact_count: omittedIds.length,
    omitted_artifact_ids: omittedIds, snapshot_id: request.snapshot_id || null, scope_id: request.scope_id };
  const context = lines.join("").slice(0, 200000);
  const analysis = await Context.analyzeContext(context);
  const domains = await Domains.identifyDomains(analysis);
  const personas = await Personas.generatePersonas(domains, analysis.complexity);
  const segmentDiagnostics = analysis.segments.map((segment, index) => ({
    index, type: segment.type, word_count: segment.wordCount
  }));
  if (personas.length === 0) {
    process.stdout.write(JSON.stringify({
      status: "insufficient_domain_signal",
      analysis: { segments: segmentDiagnostics, elements: analysis.elements, complexity: analysis.complexity,
        diagnostics: analysis.diagnostics, provenance: analysis.provenance },
      domains, personas: [], persona_diagnostics: personas.diagnostics || {},
      research_plan: { status: "not_generated", reason: "No primary, technical, or methodological domain produced a persona." },
      handoff: {},
      source_manifest: manifest
    }));
    return;
  }
  const plan = await Orchestrator.orchestrateResearch(personas, context);
  const handoff = await Handoff.generateHandoff(analysis, domains, personas, plan);

  // The source pipeline echoes supplied context in these fields. Strip it from
  // the result; provenance is carried by graph IDs, source refs, and hashes.
  delete handoff.contextSummary.originalProblem;
  delete plan.context;
  process.stdout.write(JSON.stringify({
    status: "plan_ready_for_host_review",
    analysis: { segments: segmentDiagnostics, elements: analysis.elements, complexity: analysis.complexity,
      diagnostics: analysis.diagnostics, provenance: analysis.provenance },
    domains,
    personas: Array.from(personas),
    persona_diagnostics: personas.diagnostics || {},
    research_plan: plan,
    handoff,
    source_manifest: manifest
  }));
}

main().catch(error => {
  process.stderr.write(`${error && error.message ? error.message : String(error)}\n`);
  process.exitCode = 1;
});
