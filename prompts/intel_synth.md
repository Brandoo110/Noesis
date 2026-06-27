Extract evidence-grounded intelligence items from cited evidence snippets.

Rules:
- Only extract intelligence whose PRIMARY SUBJECT is the target company:
  {name} (symbol {symbol}, aliases {aliases}).
- If an evidence snippet's main subject is a DIFFERENT company, even one
  mentioned alongside the target, DISCARD it.
- Prefer the target's fundamentals, products, supply chain, partnerships, and
  material events over generic share-price movements of other firms.
- Every item must cite one or more provided evidence ids.
- Sentiment dir is expected price-impact direction: up, down, or neutral.
- Do not invent facts beyond the cited snippets.
- Do not recommend buying or selling and do not predict prices.
