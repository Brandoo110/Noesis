import { describe, expect, it } from "vitest";

import { REDLINE_PATTERN } from "./redline";

describe("REDLINE_PATTERN", () => {
  it("matches Chinese and English investment redline wording", () => {
    expect("这里出现目标价").toMatch(REDLINE_PATTERN);
    expect("This includes a strong buy rating").toMatch(REDLINE_PATTERN);
    expect("The report repeats a buy rating").toMatch(REDLINE_PATTERN);
    expect("The note repeats a sell rating").toMatch(REDLINE_PATTERN);
    expect("Analysts discuss a price target").toMatch(REDLINE_PATTERN);
    expect("The note uses an overweight label").toMatch(REDLINE_PATTERN);
  });

  it("does not match normal research wording", () => {
    expect("Revenue grew due to product demand").not.toMatch(REDLINE_PATTERN);
    expect("仅供参考的研究关注点").not.toMatch(REDLINE_PATTERN);
    expect("Best Buy sells Sony televisions.").not.toMatch(REDLINE_PATTERN);
    expect("https://example.com/best-buy-sale").not.toMatch(REDLINE_PATTERN);
    expect("The board approved a buyback program.").not.toMatch(REDLINE_PATTERN);
  });
});
