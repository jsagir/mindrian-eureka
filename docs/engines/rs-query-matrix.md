# Reverse Salient Research Query Matrix

`research.generate_rs_query_matrix` turns an RS domain-analysis result into 60 deterministic research-query drafts.

## When to use it

Use after `research.analyze_rs_domain_projection` and before a MindrianOS-approved evidence-gathering pass:

```bash
eureka-workflow research.generate_rs_query_matrix rs-query-context.json --output rs-query-matrix.json
```

The output has 15 queries in each source category: shared-ground queries (`a_intersect_b`), A-leading-to-B, B-leading-to-A, and adjacent-domain exploration. The input carries `scope_id` and `snapshot_id` so the generated questions remain linked to the graph snapshot that informed the domain analysis.

## Host research boundary

This stage only creates drafts. It does not call a search provider or validate query quality. Review and authorize each external request in MindrianOS, and apply the host's canonical egress rules before sending query text. Eureka's local hygiene check is a supplementary filter, not an authorization boundary.

The source uses only the primary domain and the first adjacent domain when constructing the categories. The source is Mindrian BSL 1.1; distribution and attribution review remains pending. See the [engine source ledger](../engine-source-ledger.md).
