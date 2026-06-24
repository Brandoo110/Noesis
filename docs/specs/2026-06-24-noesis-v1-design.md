# Noesis V1 设计 Spec

> **From signal to insight, made for one.**
> 状态：草案（待用户评审）· 日期：2026-06-24 · 适用范围：V1（冷启动深度调研 + 自动 thesis）

本文件是 Noesis V1 的**冻结设计**，驱动后续实现计划（plan）。北极星愿景另见 vault `Projects/active/Noesis/`（早期 README/EVALUATION，仅作参考，不代表当前定位）。

---

## 1. 产品定位与边界

**一句话**：Noesis 是一张以"你的持仓"为入口、可探索的**情报知识图谱**。输入你买的或在盯的标的（任意市场），Agent 自动调研这家公司 + 它背后的产业链 + 最近的情报/舆情/发展方向（每条带证据），并自动派生一版 thesis 给你确认。你可以沿产业链/产业图谱自由下钻探索。

**核心价值链**：抓得到 → 看得懂（证据化）→ 连得上（连回你的持仓）→ 留得住（变化追踪）。

### 红线（非协商）

- **不荐股**：不给出买/卖/加/减仓建议。
- **不预测股价**：不输出目标价、涨跌预测。
- **不自动交易**：不接任何下单/资金通道。
- **可信优先**：每条结论可溯源；LLM 推断的内容必须显式标注，与一手证据视觉区分。
- "投资建议"一律重构为**研究待办 / 关注点**（"你可能想自己去核实的问题"），永远小字、仅供参考，**不是核心卖点**。

产品交付的是"发生了什么、证据是什么、和你哪个持仓有关、还需要跟进什么"，不是"该买什么"。

---

## 2. 目标用户与心智模型

**用户**：自主决策的活跃个人投资者，持有数只到数十只标的，跨市场（美股/A 股/港股/加密均可）。

**统一心智模型**——全产品只有三种对象反复出现：

| 对象 | 是什么 | 用户能做什么 |
|---|---|---|
| **Position 持仓/关注** | 你买的或盯的标的 | 图谱入口 |
| **Entity 实体节点** | 公司 / 产业段 / 主题 | 点进、展开、收藏 |
| **Intel 情报（带证据）** | 发生在某实体上的事 + AI 解读 | 点开看原文 |

每到一个节点都回答同样四件事：**这是什么 · 最近发生了什么（带证据）· 和我的持仓什么关系 · 它下面有哪些代表性股票**。

---

## 3. V1 范围

**In（V1 做）**：
- 多持仓录入（手输/粘贴）+ 组合主页（轻量）
- 个股详情全套（见 §6）
- 产业链图谱**懒加载**展开 1–2 层（见 §4）
- 产业段 → 沿生长路径算出的代表性股
- 自动派生 thesis + 用户确认闸门
- 全程证据引用 + 信源可信度分级
- 同产业段重叠提示（组合风险的轻量版）

**Out（放 V1.5 / V2）**：
- 组合级隐藏风险完整版（共同供应链暴露/相关性矩阵）
- 持续监控 / 通知 / Daily Digest / Weekly Review 自动化
- 变化 diff 自动化（V1 存快照，手动对比）
- 券商同步、截图 OCR 录入
- GraphRAG / 图数据库（见 §10，短期不做）

---

## 4. 核心交互：从持仓生长的图谱（懒加载）

```
录入持仓 → 每个持仓建一个"种子节点"
你的图谱 = 持仓种子 + 已展开的邻居
点任一节点"展开" → 按需研究该节点的上游/下游/竞品 → 长出新节点（研究过即缓存）
点产业段节点 → 沿生长路径算出代表性股 → 可再点回个股详情
全程：节点高亮"它和你哪个持仓有关 + 路径"；面包屑防迷路
```

**两条工程铁律（地基，不是优化项）**：
1. **懒加载**：默认只展开持仓相关 1–2 层，其余节点点到才深入研究，结果缓存复用。控制成本/延迟/幻觉。
2. **每条边/每个"代表性股"可核验**：图结构由 LLM 生成，但每条边标注 `inferred`（脑补·未证实）vs `source_backed`（有出处）+ 置信度，用户可一键剪枝。这是"透明可信"卖点的落点。

---

## 5. 板块 / 界面

| 界面 | 核心内容 |
|---|---|
| **组合主页** | 持仓列表 + 图谱缩略 + 今日变化 + 同产业段重叠提示 |
| **个股详情** | §6 全套 |
| **图谱探索器**（主舞台） | 可点可展开的分层价值链，持仓节点高亮，懒加载，边标注 inferred/source_backed |
| **产业段详情** | 这段是什么 · 近期产业事件 · 沿路径算出的代表性股 |
| **证据抽屉**（全局） | 任意结论一点看原文/信源/抓取时间 |

形态决策：**交互图谱优先（app-like）**；报告是图谱的可导出快照，不是主体验。

---

## 6. 个股详情 / AI 能力 / 报告

### 个股详情看什么（先结论、后证据、可下钻）
1. 现状一句话 + 自上次的变化
2. 它在产业链的位置（mini 图：上游/下游/竞品，可点）
3. 分类情报流（财报/监管/产品/供应链/高管/资本运作…），每条带【情绪方向】【信源 tier】【证据】
4. 舆情（分信源等级聚合，不混为一谈）
5. 发展方向/叙事（AI 综合，每句挂证据）
6. 和你其他持仓的关系（重叠/相关）
7. thesis（自动派生：持有理由/关键假设/风险，可确认）
8. 关注点（非建议·小字）

### AI 能调研/分析什么
实体解析（跨市场/语言）· 产业链扩展（标注 inferred/source_backed）· 多源采集→去重→聚类→分类 · 情绪=**对价格的预期影响方向**（非语义情绪）· 重要度打分 · 综合叙事 · thesis 派生 + 防幻觉审查 · 同段重叠（组合轻量）。

### 报告
两层：组合级 Brief（关键变化→重叠提示→每持仓一句话）+ 个股深度调研报告（摘要→变化→可点产业链地图→分类情报→发展方向→thesis→关注点→来源清单）。产品内交互可下钻，导出（PDF/MD）是快照。

---

## 7. 架构总览

本地优先、单人可建。新 repo `Noesis`，**移植 PulseRadar 已跑通的 backbone**，丢弃 brand 业务域。

```
FastAPI ── LangGraph 研究子图 ── SQLite(thin repo) ── 证据引用式检索(本地向量+FTS)
                 │
          node trace · eval harness · 确认闸门 · 报告模板
                 │
          Web 前端（图谱优先：react-flow/cytoscape 类 + 个股/报告视图）
```

---

## 8. 领域模型（SQLite）

| 表 | 关键字段 |
|---|---|
| `positions` | user_id, symbol, market, name, kind(owned/watching), qty?, cost_basis? |
| `entities` | id, **node_type(company/segment/theme)**, name, aliases, identifiers{symbol,cik,isin}, market |
| `graph_edges` | from_entity, to_entity, relation(supplier/customer/competitor/belongs_to), **basis(inferred/source_backed)**, confidence, evidence_ids |
| `node_expansion` | entity_id, 是否已研究, researched_at, cached_run_id（懒加载状态） |
| `intel_items` | entity_id, run_id, source, **source_tier(1-4)**, title, content, url, published_at, sentiment{dir,conf}, event_type |
| `theses` | position_id, run_id, summary, status(draft/confirmed/edited) |
| `thesis_assumptions` | thesis_id, text, kind(reason/assumption/risk), **evidence_ids**, status |
| `holding_relevance` | entity_id, position_id, path（"为什么和我有关"） |
| `intelligence_reports` | run_id, entity_id, payload, created_at |
| **复用（通用控制面）** | `run_registry` · `node_traces` · `audit_logs` · `approvals`(泛化 object_id) · `evidences` · `config*` |

---

## 9. 研究流（LangGraph 子图，每次"展开一个节点" = 一次小 run，进 trace）

```
1 intake/resolve  解析输入或定位节点实体（别名→实体→代码）
2 expand          LLM 提产业链边（标 inferred/source_backed + 置信度）
3 ingest          多源采集（web/Tavily 通用 + SEC 美股 + 手动 URL），并行
4 filter          本地 Qwen 降噪压缩（复用 PulseRadar filter）
5 evidence_build  去重、聚类、每条挂 evidence + 信源 tier
6 intel_synth     结构化：分类情报 / 情绪 / 发展方向
7 thesis_draft    （持仓种子节点）派生 thesis，假设挂证据
8 risk_review     防幻觉审查（复用 risk_reviewer 改造）：查无证据断言 + 校验 inferred 标注
9 human_confirm   确认闸门：用户确认/修改 thesis（复用 approval gate）
10 finalize       落库 + 缓存 + 生成报告
```

---

## 10. 产业链 grounding + 技术决策：为什么不用 GraphRAG

把三件常被混淆的事分开：

| | 是什么 | Noesis 取舍 |
|---|---|---|
| **产品域图**（domain graph） | 实体 + 有类型的边 | ✅ 要，但轻：SQLite 邻接表 + LLM 按需生成 + 前端图库 |
| **GraphRAG** | 从大语料抽实体关系建 KG + 社区摘要做检索 | ❌ V1 不做，短期大概率不需要 |
| **实体解析** | 别名归一（宁王→宁德时代→300750） | ✅ 轻量实体表 + 模糊匹配 + LLM 消歧 |

**理由**：
- "图"的高价值功能（共同供应链暴露、"为什么和我有关"路径）= **对边表做图遍历**，几行 SQL / 内存 BFS 即可，与 GraphRAG 无关。V1 规模（单用户、几百节点）用 SQLite 邻接表足够，**不上 Neo4j**。
- GraphRAG 为"大量静态语料的全局意义建构"设计，建图巨贵、擅长模糊全局问题；而 Noesis 的数据是**新鲜、按节点现采、要可溯源**——对的工具是**证据引用式检索**（retrieve + cite），复用 PulseRadar 现有本地向量(Chroma)+FTS。
- GraphRAG 只在 Phase 2+ 出现"读完所有持仓+产业链+数月历史，总结跨持仓跨时间共性主题"这种真实需求时才回头评估。现在做 = 提前还用不上的债。

---

## 11. 数据源策略（V1）

- **通用主力**：web / Tavily 类搜索（跨市场，全球可用）
- **美股加分**：SEC EDGAR API（10-K/10-Q/8-K，干净、免费、可引用）
- **手动兜底**：用户粘贴 URL / Markdown ingest
- **信源分级**：Tier 1 一手（监管/交易所/IR）> Tier 2 专业媒体 > Tier 3 综合媒体 > Tier 4 社交/UGC；tier 影响重要度加权与告警门槛。
- 合规：只抓公开信息、遵守 robots/ToS、版权内容只做"标题+一句话摘要+原文链接"。

---

## 12. LLM 路由（复用 PulseRadar 分层思路）

| 阶段 | 模型（默认） | 用途 |
|---|---|---|
| 过滤降噪 | 本地 Qwen | 压缩原始文本，省 token |
| 结构化抽取/分类/情绪 | 云端轻量（如 Gemini Flash Lite 类） | JSON 提取 |
| 综合叙事/报告/thesis | 云端强模型（Claude） | 长文综合 |
| 防幻觉审查 | 异构模型 | 独立审查，避免自审盲点 |

缺 key 时部分降级运行；具体模型 ID 以实现时配置为准。

---

## 13. 复用 vs 新建

- **移植**：LangGraph 编排骨架 · SQLite+thin repo · node trace · 证据引用式检索(RAG grounding) · risk_reviewer（改造成防幻觉/无证据断言检查）· eval harness · 确认闸门 · 报告模板。
- **新建**：图谱模型与懒加载 · 图谱前端 · 采集工具(web/Tavily+SEC+手动URL) · 实体解析 · prompts · 全部业务界面。

---

## 14. Eval / 测试策略

- **实体解析**：别名归一抽样人工评审（宁王→宁德时代类）。
- **产业链边质量**：抽样核验 inferred 标注是否诚实、source_backed 是否真有出处。
- **情报 grounding**：每条结论可溯源率、无证据断言被 risk_review 拦截率。
- **情绪（=价格影响方向）**：历史回测方向准确率（可后置）。
- **流程**：研究流 happy-path + 降级路径的 pytest（移植 PulseRadar 测试范式）。

---

## 15. 风险与缓解

| 风险 | 缓解 |
|---|---|
| 产业链图谱幻觉 | 懒加载 + 每条边 inferred/source_backed 标注 + 用户剪枝 + risk_review |
| 跨市场数据质量参差 | 信源分级；Tier 4 不单独触发；缺源降级 |
| 成本/延迟 | 懒加载（不预研全图）+ 缓存 + 本地模型主力 |
| 越界成投顾 | 非建议红线做成 UX 模式（标签+免责），"建议"重构为"研究待办" |

---

## 16. 阶段路线

- **V1**：本 spec 范围（冷启动深度调研 + 自动 thesis + 懒加载图谱）。
- **V1.5**：组合级隐藏风险完整版、变化 diff 自动化。
- **V2**：持续监控 + 通知 + Digest/Weekly Review、watchlist、券商同步。
- **Phase 2+（可选）**：在累积历史语料上评估 GraphRAG / 分层摘要。

---

## 17. 开放问题（待实现前确认）

- 前端图库选型（react-flow vs cytoscape）：实现时定。
- 默认懒加载展开深度与每层 top-N 节点数：实现时给默认值 + 可配。
- 具体云模型 ID：实现时配置。
- 代码作者角色（Claude Code / Codex）→ 决定 CLAUDE.md / AGENTS.md 分工，见项目根文档。
