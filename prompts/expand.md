Extract one-hop supply-chain graph edges for the target entity.

Rules:
- Allowed relations: supplier, customer, competitor, belongs_to.
- Allowed node types: company, segment, theme.
- Do not recommend buying, selling, trading, position sizing, or target prices.
- Do not predict stock prices.
- Use basis="source_backed" only when one or more provided evidence ids directly support the edge.
- Use basis="inferred" for plausible uncited edges and provide confidence.
- Keep rationale to one sentence explaining why the edge exists.
- Prefer the top five highest-confidence useful neighbors.
