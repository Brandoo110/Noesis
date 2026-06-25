# Noesis — Codex 编码契约

本文件只定义代码落地规则。产品红线、Do-NOT、协作角色、上下文入口以 `CLAUDE.md` 为准；V1 业务设计以 `/Users/junjieli/obsidian/Brain/Projects/active/Noesis/docs/2026-06-24-noesis-v1-design.md` 为准。冲突时：用户指令 > `CLAUDE.md` > V1 spec > 本文件。

## 1. 技术栈与版本

- Python：`3.11+`，新代码必须可在 3.11 运行；禁止使用只在 3.12+ 可用的语法，除非同步升级版本约束。
- 后端：`FastAPI` + `Pydantic` + `LangGraph`；依赖版本必须写入锁文件或明确约束文件。
- 存储：`SQLite` 为主库；本地向量用 `Chroma`，关键词检索用 SQLite `FTS5`。
- 前端：`React` + `TypeScript` + 图谱库；图库在开放项中实现时定。
- 测试：`pytest` 为后端默认测试入口；前端建立后使用 `npm test` 和 `npm run build` 作为门禁。
- 本地优先：不得引入 Kafka、Flink、ClickHouse、Elasticsearch、K8s、Neo4j/图数据库、GraphRAG。

## 2. Repo 目录职责

- `graph/`：LangGraph state、节点、子图装配、run orchestration。只放研究流逻辑，不写 HTTP handler。
- `db/`：SQLite schema/migrations、thin repositories、事务 helper。不得放 LLM prompt 或 API 路由。
- `api/`：FastAPI app、routers、request/response DTO、依赖注入、错误映射。
- `web/`：React 前端、图谱探索器、证据抽屉、报告/详情视图。不得复制后端领域规则。
- `prompts/`：按节点拆分 prompt 模板和 JSON schema 说明；prompt 文件名必须和节点名对齐。
- `tools/`：采集器、SEC/web/manual URL adapter、本地模型 wrapper、脚本化工具。
- `evaluation/`：eval case、golden fixture、pytest harness、人工评审样本。
- `docs/`：spec、ADR、运行手册、验收记录；实现细节优先写到代码测试，不堆进 docs。

## 3. 命名、大小与类型

- Python 文件、函数、变量：`snake_case`；类和 Pydantic model：`PascalCase`；常量：`UPPER_SNAKE_CASE`。
- TypeScript 文件：React component 用 `PascalCase.tsx`，普通模块用 `kebab-case.ts`。
- TypeScript 导出：默认用 named export；禁止新增 `default export`，除非框架入口强制要求。
- 单个 Python 源文件不超过 `350` 行；单个 React component 文件不超过 `250` 行；超过先拆模块。
- 单个函数不超过 `70` 行；超过必须拆出纯函数或 adapter。
- Python 新函数必须写参数和返回类型；禁止新代码使用裸 `dict`/`list` 作为公共接口，需用 `TypedDict`、`dataclass` 或 Pydantic model。
- `Any` 只能用于第三方 SDK 边界；使用处必须在同文件内尽快转换成项目类型。
- 时间字段统一存 UTC ISO 字符串或 `datetime`；落库字段名用 `_at` 后缀。
- ID 字段命名：表内主键用 `id`；跨表引用用 `<entity>_id`，例如 `run_id`、`entity_id`。

## 4. 错误处理

- 禁止裸 `except:`；捕获异常必须指定类型。
- 外部采集、LLM、向量库、SEC/API 调用失败必须返回可降级结果，不得让整条研究流无条件中断。
- 领域错误用项目异常类表达，例如 `EntityResolveError`、`GroundingError`、`ResearchNodeError`。
- `api/` 只做错误映射：领域异常转稳定 HTTP status + JSON body；不得在 router 中拼接业务补救逻辑。
- 降级结果必须进入 trace，字段至少包含 `node_name`、`status="degraded"`、`reason`、`fallback_used`。
- 禁止 `print` 调试；使用结构化 logger，日志不得包含 API key、cookie、完整原文版权内容。

## 5. LangGraph 节点新增规则

- 每个节点一个文件：`graph/nodes/<node_name>.py`；prompt 放 `prompts/<node_name>.md`。
- 节点函数签名固定：`def <node_name>(state: ResearchState, deps: GraphDeps) -> ResearchStateUpdate`。
- 节点只读写自己的 state slice；跨节点共享字段必须先在 `ResearchState` 中声明。
- 输入必须显式列在节点文件顶部的 `REQUIRED_STATE_KEYS`；输出列在 `OUTPUT_STATE_KEYS`。
- 节点返回增量 update，不直接 mutate 传入的 `state`。
- 每个节点必须写 trace：开始、成功、降级、失败都记录到 `node_traces`。
- trace 字段至少包含：`run_id`、`node_name`、`entity_id?`、`inputs_ref`、`outputs_ref`、`status`、`started_at`、`ended_at`、`model_id?`、`evidence_ids?`。
- LLM 节点输出必须先通过 Pydantic schema 校验，再写 state 或落库。
- 研究流新增节点时，同步新增 happy-path 测试和一个降级路径测试。
- 禁止节点内直接打开 SQLite 连接；通过 `deps` 注入 repo 或 service。

## 6. 新增领域表与 thin repo

- 每张领域表必须有 schema/migration、Pydantic row model、repository、测试 fixture。
- 表名用复数 snake_case；字段名不得使用缩写，除通用 `id`、`url`、`qty`。
- 所有领域表默认包含 `created_at`；可变记录包含 `updated_at`。
- JSON 字段必须以 `_json` 或复数语义命名，并在 row model 中转换成明确类型。
- thin repo 只做 SQL 与 row mapping：允许 CRUD、按索引查询、批量 upsert；禁止写 LLM 调用、prompt、图遍历业务策略。
- 事务边界放在 graph/service 层；repo 方法不得隐式 commit，除非方法名明确含 `commit`。
- SQL 必须使用参数绑定；禁止 f-string 拼接用户输入。
- 新表必须补至少一个索引，或在 PR/commit 说明中写明为什么不需要。

## 7. Grounding 硬性要求

- 任何对用户展示的结论必须带 `evidence_ids`；空 evidence 的结论不得进入 report/intel/thesis。
- `intel_items`、`thesis_assumptions`、`intelligence_reports` 中的 claim 必须能追到 `evidences.id`。
- 产业链边 `graph_edges.basis` 只能是 `inferred` 或 `source_backed`。
- `basis="source_backed"` 时 `evidence_ids` 不能为空，且至少一个 evidence 的 source tier 已知。
- `basis="inferred"` 时必须写 `confidence`，并在前端/API payload 中保留该标记，不得渲染成已证实事实。
- risk review 必须检查：无 evidence claim、错误 `basis`、source-backed 空证据、thesis 无假设证据。
- 检索只返回可引用片段和 metadata；禁止把无来源摘要当作 evidence。

## 8. API 与 Web 约定

- API route 文件按资源命名：`api/routes/entities.py`、`positions.py`、`reports.py`。
- FastAPI response model 必须显式声明；不得直接返回数据库 row dict。
- API payload 对 inferred/source_backed、source tier、evidence ids 不做字段省略。
- Web 类型从 API contract 手写或生成到 `web/src/types/`；组件不得直接假设后端内部表结构。
- 图谱节点/边组件必须视觉区分：持仓节点、产业段、theme、`inferred` 边、`source_backed` 边。
- Web 触发展开时只请求当前节点 expansion；禁止一次性请求全图预研。

## 9. 测试规范

- 后端测试默认目录：`tests/`；文件名 `test_<module>.py`。
- 研究流测试沿用 PulseRadar 范式：fixture DB + fake LLM/search adapters + trace 断言。
- 每个 LangGraph 节点至少两个测试：happy-path 和降级路径。
- 每个 repo 至少测试 insert/get/upsert 或核心查询；必须覆盖空结果。
- Grounding 测试必须包含：无 evidence claim 被拦、inferred 边保留标记、source_backed 空证据失败。
- 测试禁止真实网络调用；外部 API 必须 fake 或录制最小 fixture。
- 新增依赖、schema 或 graph wiring 后，至少跑相关 `pytest`；前端改动至少跑相关 test/build。
- 不能运行测试时，提交说明必须写明原因和未验证风险。

## 10. Commit message

- 使用 Conventional Commits：`type(scope): summary`。
- `type` 只用：`feat`、`fix`、`test`、`docs`、`refactor`、`chore`。
- `scope` 使用目录或能力名：`graph`、`db`、`api`、`web`、`grounding`、`eval`、`docs`。
- summary 用英文小写祈使句，不超过 `72` 字符。
- 同一 commit 不混无关主题；schema 变更必须和对应 repo/test 同 commit。
- 每个 Phase 完成、相关 commit 落地后，由 Codex 负责 git push 同步到 `origin/main`，不需等主控指示。

## 11. 开放项（实现时定）

- 前端图库：`react-flow` vs `cytoscape`。
- 云模型 ID：轻量结构化模型、强综合模型、异构 risk review 模型。
- 默认懒加载深度和每层 top-N。
- Chroma collection 命名、embedding 模型和本地 Qwen 运行方式。
- migration 工具选型：裸 SQL 文件或轻量 migration runner。
