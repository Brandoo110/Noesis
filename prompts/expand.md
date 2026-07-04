Extract one-hop supply-chain graph edges for the target entity.

Rules:
- All AI-generated user-facing graph fields must be in 简体中文, including
  rationale and generated segment/theme names. Keep company legal names,
  tickers, URLs, evidence ids, and 原始英文证据 snippets in their source language.
- Allowed relations: supplier, customer, competitor, belongs_to.
- Direction is target-centric: relation describes the role of to_entity relative to target.
- supplier = to_entity supplies goods or services to target (upstream).
- customer = to_entity buys goods or services from target (downstream).
- competitor = to_entity competes with target in the same market.
- belongs_to = target belongs to the to_entity segment or theme.
- Do not label a supplier as customer just because target is its customer.
- Example: target=Apple, Micron/TSMC/Gemini or Alphabet AI services are supplier.
- Example: target=Apple, a brand buying Apple-made products would be customer.
- Example: target=Apple, Samsung phones are competitor.
- Example: target=Apple, Consumer Electronics is belongs_to.
- Allowed node types: company, segment, theme.
- Do not recommend buying, selling, trading, position sizing, or target prices.
- Do not predict stock prices.
- Use basis="source_backed" only when one or more provided evidence ids directly support the edge.
- Use basis="inferred" for plausible uncited edges and provide confidence.
- Keep rationale to one sentence explaining why the edge exists.
- Prefer the top five highest-confidence useful neighbors.
