# IP finance domain signals

**Capability:** `research.classify_ip_finance_domain_signals`  
**Status:** Experimental; CLI and MCP  
**Source:** LATEST Genesis `GenesisDomainIdentifier_v3_IPFinance.js` (SHA-256 is recorded in the [source ledger](../engine-source-ledger.md)).

## When to use it

Use this service when a set of authorized, source-linked research excerpts may span patent strategy, IP-backed finance, credit risk, or related fields. It can help Theo and MindrianOS choose which research method or domain specialist to consider next.

Supply text segments with stable IDs, source references, and the room scope and snapshot. The service returns a classification for each segment and a rollup from the source algorithm. Results remain research signals; the service does not look up documents or experts, query the graph, or write to the room.

## CLI

Save a request such as `ip-finance-request.json`:

```json
{
  "scope_id": "room:research",
  "snapshot_id": "snapshot:research-1",
  "segments": [
    {
      "id": "paper:1",
      "source_ref": "room://paper/1",
      "text": "Patent-backed lending depends on IP collateral valuation and credit risk analysis."
    }
  ]
}
```

Run:

```sh
eureka-workflow research.classify_ip_finance_domain_signals ip-finance-request.json
```

The same request is available through `scout_run_workflow`, using the catalog capability ID and input schema.

## Reading the result

Each segment includes its stable ID, source reference, content hash, best matching domain, matched terms, and any secondary domains returned by the source algorithm. Short acronyms with common alternative meanings are surfaced as source-linked warnings. The result also includes a source-linked domain rollup, scope, snapshot, and deterministic input fingerprint.

The score is a keyword hit count scaled by the source heuristic. It is not a probability or an estimate of credit quality. Acronym matching is case-sensitive; ties follow the source lexicon order. In a biomedical catalog, for example, `PD` can mean Parkinson's disease or programmed death rather than probability of default; the result warns when a short ambiguous acronym fires. Verify consequential claims against evidence and use other methods for legal, financial, or opportunity assessment.

The adjacent LATEST `GenesisExpertPanel_IPFinance.js` remains unexposed: it generates canned persona responses, including unverified claims, and does not perform expert research. See the source ledger for that review boundary.
