// Read-only. Node snapshot for the relationship agent. Parameters: $labels (list of labels).
MATCH (n)
WHERE any(l IN labels(n) WHERE l IN $labels)
RETURN coalesce(toString(n.id), toString(n.uuid), elementId(n)) AS id,
       labels(n) AS labels,
       coalesce(n.name, n.label, n.term, n.id) AS name,
       n.problem_type AS problem_type,
       n.discipline AS discipline,
       n.domain AS domain,
       n.jtbd_anchor AS jtbd_anchor,
       coalesce(n.source_ref, n.url, n.uri) AS source_ref,
       left(coalesce(n.definition, n.description, n.core_principles, n.key_insight, n.lesson, n.pws_definition, ''), 600) AS text
LIMIT 10001
