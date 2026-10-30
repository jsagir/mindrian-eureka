"use strict";

const fs = require("node:fs");
const path = require("node:path");
const crypto = require("node:crypto");

const sourcePath = path.join(__dirname, "GenesisDomainIdentifier_v3_IPFinance.js");
const DomainIdentifier = require(sourcePath);
const SOURCE_SHA256 = "55ef917bb46da7065e668aba8e3df019e24259fc1b593a20a5a726597931319d";
const AMBIGUOUS_ACRONYMS = new Set(["pd", "pe", "vc", "car", "sep", "ar", "vr", "xr", "ros", "roi", "ltv", "fto", "ipc", "cpc", "rwa", "npl", "lgd", "ead", "abl"]);

async function main() {
  const request = JSON.parse(fs.readFileSync(0, "utf8"));
  const sourceBytes = fs.readFileSync(sourcePath);
  const sourceHash = crypto.createHash("sha256").update(sourceBytes).digest("hex");
  if (sourceHash !== SOURCE_SHA256) throw new Error("Packaged IP-finance domain source hash does not match the pinned LATEST source.");
  DomainIdentifier.silent = true;

  const segmentResults = request.segments.map((segment) => {
    const classification = DomainIdentifier.analyzeDomainIndicators(segment.text);
    const observed = [...classification.indicators, ...(classification.secondaryDomains || []).flatMap((item) => item.indicators || [])];
    const ambiguous = [...new Set(observed.filter((term) => AMBIGUOUS_ACRONYMS.has(term)))];
    return {
      id: segment.id,
      source_ref: segment.source_ref,
      text_sha256: crypto.createHash("sha256").update(segment.text, "utf8").digest("hex"),
      classification,
      classification_warnings: ambiguous.length ? [
        `Short acronym match(es) ${ambiguous.join(", ")} may have another meaning in this source context; verify the original text before routing this as an IP or finance signal.`,
      ] : [],
    };
  });
  const warnings = segmentResults.flatMap((segment) => segment.classification_warnings.length ? [{
    code: "ambiguous_acronym_match",
    segment_id: segment.id,
    source_ref: segment.source_ref,
    tokens: [...new Set([...segment.classification.indicators, ...(segment.classification.secondaryDomains || []).flatMap((item) => item.indicators || [])]
      .filter((term) => AMBIGUOUS_ACRONYMS.has(term)))],
    message: segment.classification_warnings[0],
  }] : []);
  const domains = await DomainIdentifier.identifyDomains({
    segments: request.segments.map(({ text }) => ({ text })),
    elements: { methodologies: [] },
  });
  process.stdout.write(JSON.stringify({
    status: "completed_lexical_domain_scan",
    capability_id: "research.classify_ip_finance_domain_signals",
    capability_version: "0.1.0",
    scope_id: request.scope_id,
    snapshot_id: request.snapshot_id,
    input_fingerprint: crypto.createHash("sha256").update(JSON.stringify(request), "utf8").digest("hex"),
    segment_results: segmentResults,
    warnings,
    domain_rollup: domains,
    provenance: {
      source: "LATEST GenesisDomainIdentifier_v3_IPFinance.js",
      source_sha256: SOURCE_SHA256,
      method: "rule-based domain patterns, acronym lexicons, hit-count confidence, and source-defined thresholds",
    },
    limitations: [
      "Classification is lexical pattern matching; domain scores are hit-count heuristics, not calibrated probabilities.",
      "Only the highest-scoring domain and up to three secondary domains are returned for each segment; ties follow source lexicon order.",
      "A domain signal does not verify a claim, establish creditworthiness, assess legal status, or demonstrate an opportunity.",
      "Acronym patterns are case-sensitive and can still be ambiguous in context.",
      "Source authorship and reuse rights are unresolved; local evaluation only.",
    ],
  }));
}

main().catch((error) => {
  process.stderr.write(`${error && error.message ? error.message : String(error)}\n`);
  process.exitCode = 1;
});
