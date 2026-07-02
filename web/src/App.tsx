import {
  useEffect,
  useMemo,
  useRef,
  useState,
  type CSSProperties,
  type FormEvent,
  type KeyboardEvent
} from "react";

import { downloadMarkdown } from "./lib/markdown";
import {
  CORRELATION_SYMBOLS,
  CORRELATION_VALUES,
  DETAILS,
  EVIDENCE,
  GRAPH,
  INITIAL_POSITIONS,
  INITIAL_THESIS_STATE,
  METRIC_TILES,
  OPS_RUNS,
  OVERLAP_GROUPS,
  TRACES,
  type DemoEvidence,
  type DemoPosition,
  type DetailDatum,
  type DetailItem,
  type GraphNodeDatum,
  type IntelDatum,
  type OpsRunDatum,
  type PositionRunState,
  type ThesisDecision,
  type TraceDatum,
  type ViewMode
} from "./redesign-data";
import type { Basis, Relation } from "./types/api";

const RUN_STEPS = ["intake_resolve", "expand", "intel_synth", "thesis_draft"];

const STATUS_META = {
  confirmed: { text: "已确认 thesis", color: "var(--brand-700)", bg: "var(--brand-100)", dot: "var(--brand-700)" },
  awaiting: { text: "待确认", color: "var(--amber-700)", bg: "var(--amber-100)", dot: "var(--amber-600)" },
  running: { text: "研究中", color: "var(--blue-700)", bg: "var(--blue-100)", dot: "var(--blue-700)" },
  degraded: { text: "完成 · 无 thesis", color: "var(--red-700)", bg: "var(--red-100)", dot: "#C4756B" },
  none: { text: "未研究", color: "#6B756F", bg: "#F0F3EF", dot: "#B7C0BA" }
} as const;

const RUN_STATUS_META = {
  completed: { label: "已完成", bg: "var(--brand-100)", color: "var(--brand-700)" },
  awaiting_confirmation: { label: "待确认", bg: "var(--amber-100)", color: "var(--amber-700)" },
  failed: { label: "失败", bg: "var(--red-100)", color: "var(--red-700)" }
} as const;

const RELATION_LABELS: Record<Relation, string> = {
  supplier: "供应商",
  customer: "客户",
  competitor: "竞争",
  belongs_to: "归属"
};

const VIEW_META: Record<ViewMode, { title: string; sub: string }> = {
  home: { title: "组合工作台", sub: "持仓 · 研究状态 · 组合洞察" },
  graph: { title: "图谱探索", sub: "产业链懒加载 · 证据追踪" },
  ops: { title: "AgentOps", sub: "Run 监控 · 追踪 · 质量门禁" }
};

const EMPTY_FORM = {
  symbol: "",
  market: "US" as DemoPosition["market"],
  name: "",
  kind: "owned" as DemoPosition["kind"]
};

export function App(): JSX.Element {
  const [view, setView] = useState<ViewMode>("home");
  const [positions, setPositions] = useState<DemoPosition[]>(() =>
    INITIAL_POSITIONS.map((position) => ({ ...position }))
  );
  const [thesisState, setThesisState] = useState<Record<string, ThesisDecision>>(
    () => ({ ...INITIAL_THESIS_STATE })
  );
  const [search, setSearch] = useState("");
  const [filterKind, setFilterKind] = useState<"all" | DemoPosition["kind"]>("all");
  const [filterResearch, setFilterResearch] = useState<"all" | "researched" | "awaiting" | "unresearched">("all");
  const [filterOpen, setFilterOpen] = useState(false);
  const [healthOpen, setHealthOpen] = useState(false);
  const [addOpen, setAddOpen] = useState(false);
  const [form, setForm] = useState(EMPTY_FORM);
  const [runningId, setRunningId] = useState<string | null>(null);
  const [runStep, setRunStep] = useState("");
  const [graphSeedId, setGraphSeedId] = useState("nvda");
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});
  const [selectedNodeId, setSelectedNodeId] = useState("nvda");
  const [basisFilter, setBasisFilter] = useState<"all" | Basis>("all");
  const [detailOpen, setDetailOpen] = useState(false);
  const [drawerIds, setDrawerIds] = useState<string[] | null>(null);
  const [opsRunId, setOpsRunId] = useState("run_8f3a21");
  const [toast, setToast] = useState<string | null>(null);
  const timersRef = useRef<number[]>([]);
  const toastTimerRef = useRef<number | null>(null);

  useEffect(
    () => () => {
      timersRef.current.forEach((timer) => window.clearTimeout(timer));
      if (toastTimerRef.current !== null) {
        window.clearTimeout(toastTimerRef.current);
      }
    },
    []
  );

  useEffect(() => {
    function onKeyDown(event: globalThis.KeyboardEvent): void {
      if (event.key === "Escape") {
        if (drawerIds) {
          setDrawerIds(null);
        } else if (detailOpen) {
          setDetailOpen(false);
        }
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [detailOpen, drawerIds]);

  const seedPosition =
    positions.find((position) => position.id === graphSeedId) ?? positions[0];
  const viewMeta =
    view === "graph"
      ? {
          title: VIEW_META.graph.title,
          sub: `${seedPosition.symbol} · ${seedPosition.name} 产业链`
        }
      : VIEW_META[view];

  const filteredPositions = useMemo(
    () =>
      positions.filter((position) => {
        const query = search.trim().toLowerCase();
        const okQuery =
          !query ||
          `${position.symbol} ${position.name} ${position.market}`
            .toLowerCase()
            .includes(query);
        const okKind = filterKind === "all" || position.kind === filterKind;
        const status = positionStatus(position, thesisState);
        const okResearch =
          filterResearch === "all" ||
          (filterResearch === "researched" && status !== "none") ||
          (filterResearch === "awaiting" && status === "awaiting") ||
          (filterResearch === "unresearched" && status === "none");
        return okQuery && okKind && okResearch;
      }),
    [filterKind, filterResearch, positions, search, thesisState]
  );

  const graphModel = useMemo(
    () => buildGraphModel(seedPosition, expanded, basisFilter),
    [basisFilter, expanded, seedPosition]
  );

  const detail = DETAILS[seedPosition.id] ?? emptyDetail(seedPosition);
  const evidenceIds = useMemo(
    () => collectEvidenceIds(detail, GRAPH[seedPosition.id]?.neighbors ?? []),
    [detail, seedPosition.id]
  );
  const evidenceCards = (drawerIds ?? [])
    .map((id) => EVIDENCE[id])
    .filter((item): item is DemoEvidence => Boolean(item));
  const selectedOpsRun =
    OPS_RUNS.find((run) => run.id === opsRunId) ?? OPS_RUNS[0];

  function showToast(message: string): void {
    if (toastTimerRef.current !== null) {
      window.clearTimeout(toastTimerRef.current);
    }
    setToast(message);
    toastTimerRef.current = window.setTimeout(() => setToast(null), 3000);
  }

  function submitAdd(event: FormEvent<HTMLFormElement>): void {
    event.preventDefault();
    const symbol = form.symbol.trim().toUpperCase();
    const name = form.name.trim();
    if (!symbol && !name) {
      showToast("请输入 Symbol 或公司名称");
      return;
    }
    setPositions((current) =>
      current.concat({
        id: `p-${Date.now()}`,
        symbol: symbol || "—",
        name: name || "待解析",
        market: form.market,
        kind: form.kind,
        run: null,
        runId: null
      })
    );
    setForm(EMPTY_FORM);
    setAddOpen(false);
    showToast("已添加持仓 · 点击「开始研究」触发调研");
  }

  function startRun(positionId: string): void {
    if (runningId) {
      return;
    }
    timersRef.current.forEach((timer) => window.clearTimeout(timer));
    timersRef.current = [];
    setRunningId(positionId);
    setRunStep(RUN_STEPS[0]);
    setPositions((current) =>
      current.map((position) =>
        position.id === positionId ? { ...position, run: "running" } : position
      )
    );
    RUN_STEPS.slice(1).forEach((step, index) => {
      timersRef.current.push(
        window.setTimeout(() => setRunStep(step), 1100 * (index + 1))
      );
    });
    timersRef.current.push(window.setTimeout(() => finishRun(positionId), 4400));
  }

  function finishRun(positionId: string): void {
    const degraded = positionId === "tencent";
    setRunningId(null);
    setRunStep("");
    setThesisState((current) =>
      degraded ? current : { ...current, [positionId]: null }
    );
    setPositions((current) =>
      current.map((position) =>
        position.id === positionId
          ? {
              ...position,
              run: degraded ? "degraded" : "awaiting",
              runId: `run_${Math.random().toString(16).slice(2, 8)}`
            }
          : position
      )
    );
    showToast(
      degraded
        ? "研究完成，但未生成 thesis（降级路径）· 可在详情中重新研究"
        : "研究完成 · thesis 待确认，点击「查看图谱」下钻"
    );
  }

  function openGraph(positionId: string): void {
    setGraphSeedId(positionId);
    setExpanded({});
    setSelectedNodeId(positionId);
    setBasisFilter("all");
    setDetailOpen(false);
    setView("graph");
  }

  function handleNodeClick(node: GraphNodeView): void {
    if (node.id === graphSeedId) {
      setDetailOpen(true);
      return;
    }
    if (node.source.expandsTo && !expanded[node.id]) {
      setExpanded((current) => ({ ...current, [node.id]: true }));
      setSelectedNodeId(node.id);
      showToast(
        `已展开 ${node.source.name} · 新增 ${node.source.expandsTo.length} 个节点 · 缓存未命中，结果已缓存`
      );
      return;
    }
    setSelectedNodeId(node.id);
  }

  function confirmThesis(next: Exclude<ThesisDecision, null>): void {
    setThesisState((current) => ({ ...current, [graphSeedId]: next }));
    if (next === "confirmed") {
      setPositions((current) =>
        current.map((position) =>
          position.id === graphSeedId ? { ...position, run: "completed" } : position
        )
      );
    }
    showToast(
      next === "confirmed"
        ? "已确认 thesis 假设，纳入跟踪基线"
        : next === "edited"
          ? "已标记需修改，待补充证据后重新确认"
          : "已拒绝 thesis，退回重新起草"
    );
  }

  function retryFromDetail(): void {
    setDetailOpen(false);
    setView("home");
    startRun(graphSeedId);
  }

  return (
    <div className="noesis-app">
      <Rail view={view} setView={setView} />
      <div className="main-column">
        <Topbar
          filterKind={filterKind}
          filterOpen={filterOpen}
          filterResearch={filterResearch}
          healthOpen={healthOpen}
          isHome={view === "home"}
          resetFilters={() => {
            setFilterKind("all");
            setFilterResearch("all");
            setSearch("");
          }}
          search={search}
          setFilterKind={setFilterKind}
          setFilterOpen={setFilterOpen}
          setFilterResearch={setFilterResearch}
          setHealthOpen={setHealthOpen}
          setSearch={setSearch}
          subtitle={viewMeta.sub}
          title={viewMeta.title}
        />
        <main className="page-body">
          {view === "home" ? (
            <HomeView
              addOpen={addOpen}
              exportBrief={() => {
                downloadMarkdown("portfolio-brief.md", portfolioMarkdown(positions, thesisState));
                showToast("已生成 portfolio-brief.md · 保留证据与推断标记");
              }}
              filteredPositions={filteredPositions}
              form={form}
              graphSeedId={graphSeedId}
              positions={positions}
              runStep={runStep}
              runningId={runningId}
              setAddOpen={setAddOpen}
              setForm={setForm}
              startRun={startRun}
              submitAdd={submitAdd}
              thesisState={thesisState}
              viewGraph={openGraph}
            />
          ) : null}
          {view === "graph" ? (
            <GraphView
              basisFilter={basisFilter}
              detail={detail}
              evidenceIds={evidenceIds}
              graphModel={graphModel}
              graphSeedId={graphSeedId}
              onNodeClick={handleNodeClick}
              openDetail={() => setDetailOpen(true)}
              openEvidence={(ids) => setDrawerIds(ids)}
              resetGraph={() => {
                setExpanded({});
                setSelectedNodeId(graphSeedId);
                setBasisFilter("all");
                showToast("图谱已重置为种子第一圈");
              }}
              selectedNodeId={selectedNodeId}
              seedPosition={seedPosition}
              setBasisFilter={setBasisFilter}
            />
          ) : null}
          {view === "ops" ? (
            <AgentOpsView
              opsRunId={opsRunId}
              refresh={() => showToast("已刷新 AgentOps 指标")}
              selectedOpsRun={selectedOpsRun}
              setOpsRunId={setOpsRunId}
            />
          ) : null}
        </main>
      </div>
      <MobileNav setView={setView} view={view} />
      {detailOpen ? (
        <StockDetailDrawer
          confirmThesis={confirmThesis}
          decision={thesisState[graphSeedId] ?? null}
          detail={detail}
          evidenceCount={evidenceIds.length}
          isDegraded={seedPosition.run === "degraded"}
          onClose={() => setDetailOpen(false)}
          openEvidence={(ids) => setDrawerIds(ids)}
          position={seedPosition}
          retryDisabled={runningId !== null}
          retryFromDetail={retryFromDetail}
          status={positionStatus(seedPosition, thesisState)}
          exportReport={() => {
            downloadMarkdown(
              `${seedPosition.symbol.toLowerCase()}-report.md`,
              stockMarkdown(seedPosition, detail, evidenceIds)
            );
            showToast(`已生成 ${seedPosition.symbol.toLowerCase()}-report.md`);
          }}
        />
      ) : null}
      {drawerIds ? (
        <EvidenceDrawer
          evidences={evidenceCards}
          onClose={() => setDrawerIds(null)}
        />
      ) : null}
      {toast ? <div className="toast" role="status">{toast}</div> : null}
    </div>
  );
}

function Rail({
  setView,
  view
}: {
  setView: (view: ViewMode) => void;
  view: ViewMode;
}): JSX.Element {
  return (
    <nav aria-label="主导航" className="rail">
      <div className="rail-logo">N</div>
      <RailButton
        active={view === "home"}
        label="组合工作台"
        onClick={() => setView("home")}
        path="M3 4h7v8H3zM14 4h7v5h-7zM14 13h7v7h-7zM3 16h7v4H3z"
      />
      <RailButton
        active={view === "graph"}
        label="图谱探索"
        onClick={() => setView("graph")}
        path="M5 12h4m6-6h4m-4 12h4M8.5 10.5 15 6.8M8.5 13.5 15 17.2"
      />
      <RailButton
        active={view === "ops"}
        label="AgentOps"
        onClick={() => setView("ops")}
        path="M3 12h4l3-8 4 16 3-8h4"
      />
      <div className="rail-spacer" />
      <div aria-label="本地用户" className="rail-user">JL</div>
    </nav>
  );
}

function RailButton({
  active,
  label,
  onClick,
  path
}: {
  active: boolean;
  label: string;
  onClick: () => void;
  path: string;
}): JSX.Element {
  return (
    <button
      aria-label={label}
      aria-pressed={active}
      className="rail-button"
      onClick={onClick}
      title={label}
      type="button"
    >
      <svg aria-hidden="true" viewBox="0 0 24 24">
        <path d={path} />
      </svg>
    </button>
  );
}

function Topbar({
  filterKind,
  filterOpen,
  filterResearch,
  healthOpen,
  isHome,
  resetFilters,
  search,
  setFilterKind,
  setFilterOpen,
  setFilterResearch,
  setHealthOpen,
  setSearch,
  subtitle,
  title
}: {
  filterKind: "all" | DemoPosition["kind"];
  filterOpen: boolean;
  filterResearch: "all" | "researched" | "awaiting" | "unresearched";
  healthOpen: boolean;
  isHome: boolean;
  resetFilters: () => void;
  search: string;
  setFilterKind: (value: "all" | DemoPosition["kind"]) => void;
  setFilterOpen: (value: boolean) => void;
  setFilterResearch: (value: "all" | "researched" | "awaiting" | "unresearched") => void;
  setHealthOpen: (value: boolean) => void;
  setSearch: (value: string) => void;
  subtitle: string;
  title: string;
}): JSX.Element {
  return (
    <header className="topbar">
      <div className="topbar-title">
        <h1>{title}</h1>
        <p>{subtitle}</p>
      </div>
      <label className="topbar-search">
        <span className="sr-only">全局搜索</span>
        <svg aria-hidden="true" viewBox="0 0 24 24">
          <circle cx="11" cy="11" r="7" />
          <path d="m20 20-3.5-3.5" />
        </svg>
        <input
          aria-label="全局搜索"
          onChange={(event) => setSearch(event.target.value)}
          placeholder="搜索标的、主题或证据…"
          value={search}
        />
      </label>
      <div className="topbar-actions">
        {isHome ? (
          <button
            aria-expanded={filterOpen}
            className="secondary-button"
            onClick={() => {
              setFilterOpen(!filterOpen);
              setHealthOpen(false);
            }}
            type="button"
          >
            筛选
          </button>
        ) : null}
        <button
          aria-expanded={healthOpen}
          className="secondary-button health-button"
          onClick={() => {
            setHealthOpen(!healthOpen);
            setFilterOpen(false);
          }}
          type="button"
        >
          <i />Health
        </button>
        {filterOpen ? (
          <section aria-label="筛选面板" className="popover filter-popover">
            <label>
              持仓类型
              <select
                onChange={(event) =>
                  setFilterKind(event.target.value as "all" | DemoPosition["kind"])
                }
                value={filterKind}
              >
                <option value="all">全部</option>
                <option value="owned">持有</option>
                <option value="watching">观察</option>
              </select>
            </label>
            <label>
              研究状态
              <select
                onChange={(event) =>
                  setFilterResearch(
                    event.target.value as "all" | "researched" | "awaiting" | "unresearched"
                  )
                }
                value={filterResearch}
              >
                <option value="all">全部</option>
                <option value="researched">已研究</option>
                <option value="awaiting">待确认</option>
                <option value="unresearched">未研究</option>
              </select>
            </label>
            <button className="secondary-button" onClick={resetFilters} type="button">
              重置筛选
            </button>
          </section>
        ) : null}
        {healthOpen ? (
          <section aria-label="产品状态" className="popover health-popover">
            <p className="eyebrow">LAUNCH READINESS</p>
            <h2>产品状态</h2>
            {[
              ["本地优先", "SQLite + 本地 Web，无交易通道。"],
              ["非荐股", "只输出研究关注点和证据化情报。"],
              ["证据化", "结论保留 evidence / source tier / basis 标记。"],
              ["门禁", "前端测试与 production build 作为上线检查。"]
            ].map(([label, value]) => (
              <div className="health-row" key={label}>
                <strong>{label}</strong>
                <span>{value}</span>
              </div>
            ))}
          </section>
        ) : null}
      </div>
    </header>
  );
}

function HomeView({
  addOpen,
  exportBrief,
  filteredPositions,
  form,
  graphSeedId,
  positions,
  runningId,
  runStep,
  setAddOpen,
  setForm,
  startRun,
  submitAdd,
  thesisState,
  viewGraph
}: {
  addOpen: boolean;
  exportBrief: () => void;
  filteredPositions: DemoPosition[];
  form: typeof EMPTY_FORM;
  graphSeedId: string;
  positions: DemoPosition[];
  runningId: string | null;
  runStep: string;
  setAddOpen: (value: boolean) => void;
  setForm: (value: typeof EMPTY_FORM) => void;
  startRun: (id: string) => void;
  submitAdd: (event: FormEvent<HTMLFormElement>) => void;
  thesisState: Record<string, ThesisDecision>;
  viewGraph: (id: string) => void;
}): JSX.Element {
  return (
    <div className="home-grid">
      <section aria-label="持仓卡" className="card positions-card">
        <header className="card-header">
          <div>
            <p className="eyebrow">PORTFOLIO</p>
            <h2>持仓</h2>
          </div>
          <span className="count-pill">{filteredPositions.length} ITEMS</span>
          <button
            className="primary-button"
            onClick={() => setAddOpen(!addOpen)}
            type="button"
          >
            + 添加持仓
          </button>
        </header>
        {addOpen ? (
          <form aria-label="添加持仓" className="add-form" onSubmit={submitAdd}>
            <label>
              Symbol
              <input
                onChange={(event) => setForm({ ...form, symbol: event.target.value })}
                placeholder="如 NVDA / 300750"
                value={form.symbol}
              />
            </label>
            <label>
              市场
              <select
                onChange={(event) =>
                  setForm({ ...form, market: event.target.value as DemoPosition["market"] })
                }
                value={form.market}
              >
                <option value="US">US</option>
                <option value="CN">CN</option>
                <option value="HK">HK</option>
              </select>
            </label>
            <label>
              公司名称
              <input
                onChange={(event) => setForm({ ...form, name: event.target.value })}
                placeholder="可选，Symbol 与名称至少填一项"
                value={form.name}
              />
            </label>
            <label>
              类型
              <select
                onChange={(event) =>
                  setForm({ ...form, kind: event.target.value as DemoPosition["kind"] })
                }
                value={form.kind}
              >
                <option value="owned">持有</option>
                <option value="watching">观察</option>
              </select>
            </label>
            <button className="primary-button" type="submit">添加</button>
          </form>
        ) : null}
        {filteredPositions.length === 0 ? (
          <div className="empty-box">
            <strong>{positions.length === 0 ? "暂无持仓" : "没有匹配的持仓"}</strong>
            <span>
              {positions.length === 0
                ? "添加第一个标的，AI 将调研公司、产业链与情报，并派生待确认的 thesis。"
                : "试试清空搜索词或重置筛选。"}
            </span>
          </div>
        ) : (
          <PositionTable
            graphSeedId={graphSeedId}
            positions={filteredPositions}
            runningId={runningId}
            runStep={runStep}
            startRun={startRun}
            thesisState={thesisState}
            viewGraph={viewGraph}
          />
        )}
      </section>
      <aside className="side-stack">
        <PortfolioBrief
          exportBrief={exportBrief}
          positions={positions}
          thesisState={thesisState}
        />
        <CorrelationMatrix />
      </aside>
    </div>
  );
}

function PositionTable({
  graphSeedId,
  positions,
  runningId,
  runStep,
  startRun,
  thesisState,
  viewGraph
}: {
  graphSeedId: string;
  positions: DemoPosition[];
  runningId: string | null;
  runStep: string;
  startRun: (id: string) => void;
  thesisState: Record<string, ThesisDecision>;
  viewGraph: (id: string) => void;
}): JSX.Element {
  return (
    <>
      <div className="pos-head" aria-hidden="true">
        <span>标的</span>
        <span className="pos-cell-market">市场</span>
        <span className="pos-cell-kind">类型</span>
        <span>研究状态</span>
        <span>操作</span>
      </div>
      {positions.map((position) => {
        const status = positionStatus(position, thesisState);
        const meta = STATUS_META[status];
        const isRunningThis = runningId === position.id;
        const hasGraph = Boolean(GRAPH[position.id]) && position.run !== null && position.run !== "running";
        return (
          <div
            className={position.id === graphSeedId ? "pos-row pos-row-active" : "pos-row"}
            key={position.id}
          >
            <div className="symbol-cell">
              <span>{position.symbol.slice(0, 1)}</span>
              <div>
                <strong>{position.symbol}</strong>
                <small>{position.name}</small>
              </div>
            </div>
            <span className="market-chip pos-cell-market">{position.market}</span>
            <span className="pos-cell-kind">{position.kind === "owned" ? "持有" : "观察"}</span>
            <span className="status-pill" style={{ color: meta.color, background: meta.bg }}>
              <i
                className={status === "running" ? "pulse-dot" : ""}
                style={{ background: meta.dot }}
              />
              {isRunningThis && runStep ? `研究中 · ${runStep}` : meta.text}
            </span>
            <div className="row-actions">
              <button
                aria-label={`${position.runId ? "重新研究" : "开始研究"} ${position.symbol}`}
                className="secondary-button"
                disabled={runningId !== null}
                onClick={() => startRun(position.id)}
                type="button"
              >
                {status === "running" ? "研究中…" : position.runId ? "重新研究" : "开始研究"}
              </button>
              {hasGraph ? (
                <button
                  aria-label={`查看图谱 ${position.symbol}`}
                  className="graph-button"
                  onClick={() => viewGraph(position.id)}
                  type="button"
                >
                  查看图谱
                </button>
              ) : null}
            </div>
          </div>
        );
      })}
      <footer className="table-footer">
        <span>显示 1-{positions.length} · 共 {positions.length} 项</span>
        <span>非荐股 · 每条结论均挂证据</span>
      </footer>
    </>
  );
}

function PortfolioBrief({
  exportBrief,
  positions,
  thesisState
}: {
  exportBrief: () => void;
  positions: DemoPosition[];
  thesisState: Record<string, ThesisDecision>;
}): JSX.Element {
  const completedN = positions.filter((position) =>
    ["confirmed", "awaiting"].includes(positionStatus(position, thesisState))
  ).length;
  const degradedN = positions.filter((position) => position.run === "degraded").length;
  const failedN = 1;
  return (
    <section aria-label="组合 Brief" className="card portfolio-brief">
      <header className="card-header compact">
        <div>
          <p className="eyebrow">PORTFOLIO BRIEF</p>
          <h2>组合 Brief</h2>
        </div>
        <button className="secondary-button small" onClick={exportBrief} type="button">
          导出 Markdown
        </button>
      </header>
      <div className="brief-stats">
        <StatTile label="持仓数量" value={String(positions.length)} />
        <StatTile label="重叠主题" value={String(OVERLAP_GROUPS.length)} />
        <StatTile
          label="thesis ready"
          value={String(Object.values(thesisState).filter((state) => state === "confirmed").length)}
        />
      </div>
      <div className="run-health">
        <div className="run-health-top">
          <strong>Run Health</strong>
          <span>{completedN + degradedN + failedN} latest runs · {failedN} failed</span>
        </div>
        <div className="health-bar" aria-hidden="true">
          <i style={{ flexGrow: Math.max(completedN, 0.2), background: "var(--brand-700)" }} />
          <i style={{ flexGrow: Math.max(degradedN, 0.2), background: "var(--amber-600)" }} />
          <i style={{ flexGrow: failedN, background: "var(--red-700)" }} />
        </div>
        <p><strong>run_3fa908</strong> TSM · rate_limit（历史失败，已被 run_7c11e0 取代）</p>
      </div>
      <div className="brief-lines">
        {positions.map((position) => (
          <div key={position.id}>
            <span>{position.symbol}</span>
            <p>{briefSummary(position, thesisState)}</p>
          </div>
        ))}
      </div>
      <div className="overlap-list">
        {OVERLAP_GROUPS.map((group) => (
          <article key={group.name}>
            <strong>{group.name}</strong>
            <span>{group.symbols}</span>
            <BasisBadge basis={group.basis} label={group.basis === "source_backed" ? "有出处" : "基于推断"} />
          </article>
        ))}
      </div>
      <p className="redline-note">仅供参考 · 用于研究跟踪，不构成交易依据</p>
    </section>
  );
}

function StatTile({ label, value }: { label: string; value: string }): JSX.Element {
  return (
    <div>
      <strong>{value}</strong>
      <small>{label}</small>
    </div>
  );
}

function CorrelationMatrix(): JSX.Element {
  return (
    <section aria-label="相关性矩阵" className="card correlation-card">
      <header>
        <p className="eyebrow">CORRELATION</p>
        <h2>相关性矩阵</h2>
      </header>
      <div className="matrix">
        <span />
        {CORRELATION_SYMBOLS.map((symbol) => <b key={symbol}>{symbol}</b>)}
        {CORRELATION_SYMBOLS.map((row) => (
          <MatrixRow key={row} row={row} />
        ))}
      </div>
      <p>基于产业链重叠估算 · 仅供参考</p>
    </section>
  );
}

function MatrixRow({ row }: { row: string }): JSX.Element {
  return (
    <>
      <b>{row}</b>
      {CORRELATION_SYMBOLS.map((col) => {
        const value =
          row === col
            ? 1
            : CORRELATION_VALUES[`${row}|${col}`] ?? CORRELATION_VALUES[`${col}|${row}`] ?? 0;
        const text = row === col ? "1.0" : value.toFixed(2).replace("0.", ".");
        return (
          <span
            key={`${row}-${col}`}
            style={{
              background:
                row === col
                  ? "var(--brand-900)"
                  : `rgba(10, 92, 87, ${(value * 0.8).toFixed(2)})`,
              color: value > 0.55 || row === col ? "#FFFFFF" : "var(--ink-2)"
            }}
          >
            {text}
          </span>
        );
      })}
    </>
  );
}

function GraphView({
  basisFilter,
  detail,
  evidenceIds,
  graphModel,
  graphSeedId,
  onNodeClick,
  openDetail,
  openEvidence,
  resetGraph,
  selectedNodeId,
  seedPosition,
  setBasisFilter
}: {
  basisFilter: "all" | Basis;
  detail: DetailDatum;
  evidenceIds: string[];
  graphModel: GraphModel;
  graphSeedId: string;
  onNodeClick: (node: GraphNodeView) => void;
  openDetail: () => void;
  openEvidence: (ids: string[]) => void;
  resetGraph: () => void;
  selectedNodeId: string;
  seedPosition: DemoPosition;
  setBasisFilter: (basis: "all" | Basis) => void;
}): JSX.Element {
  return (
    <div className="graph-view">
      <section className="graph-card card">
        <header className="graph-header">
          <div>
            <p className="eyebrow">RESEARCH GRAPH · LAZY EXPAND</p>
            <h2>{`Research Graph — ${seedPosition.symbol}`}</h2>
            <p>{seedPosition.symbol} · {seedPosition.name} · 懒加载展开，节点点到才研究</p>
          </div>
          <div className="graph-controls">
            <div aria-label="basis 筛选" className="segmented" role="group">
              {(["all", "source_backed", "inferred"] as const).map((basis) => (
                <button
                  aria-pressed={basisFilter === basis}
                  key={basis}
                  onClick={() => setBasisFilter(basis)}
                  type="button"
                >
                  {basis === "all" ? "全部" : basis}
                </button>
              ))}
            </div>
            <button className="primary-button" onClick={openDetail} type="button">
              个股详情
            </button>
            <button className="secondary-button" onClick={resetGraph} type="button">
              重置图谱
            </button>
          </div>
        </header>
        <div className="graph-legend">
          <span><i className="legend-line source" />source_backed</span>
          <span><i className="legend-line inferred" />inferred</span>
          <span><i className="legend-node seed" />持仓种子</span>
          <span><i className="legend-node company" />公司</span>
          <span><i className="legend-node segment" />产业 / 主题</span>
          <strong>lazy expand · {seedPosition.runId ?? "no run"}</strong>
        </div>
        <div className="graph-canvas">
          <div className="graph-stage">
            <svg aria-hidden="true" height="560" viewBox="0 0 1240 560" width="1240">
              {graphModel.edges.map((edge) => (
                <g key={edge.id}>
                  <line
                    stroke={edge.source.basis === "source_backed" ? "var(--brand-600)" : "var(--amber-600)"}
                    strokeDasharray={edge.source.basis === "inferred" ? "6 5" : undefined}
                    strokeWidth="1.6"
                    x1={edge.from.x}
                    x2={edge.to.x}
                    y1={edge.from.y}
                    y2={edge.to.y}
                  />
                  <text
                    className="edge-label"
                    x={(edge.from.x + edge.to.x) / 2}
                    y={(edge.from.y + edge.to.y) / 2 - 6}
                  >
                    {RELATION_LABELS[edge.source.relation]}
                  </text>
                </g>
              ))}
            </svg>
            <button
              className={selectedNodeId === graphSeedId ? "graph-node seed-node selected" : "graph-node seed-node"}
              onClick={() =>
                onNodeClick({
                  id: graphSeedId,
                  source: seedAsNode(seedPosition),
                  x: 620,
                  y: 280
                })
              }
              style={{ "--x": "534px", "--y": "249px", "--w": "172px", "--h": "62px" } as CSSProperties}
              type="button"
            >
              <strong>{seedPosition.symbol}</strong>
              <span>{seedPosition.name}</span>
            </button>
            {graphModel.nodes.map((node) => (
              <button
                className={graphNodeClass(node, selectedNodeId)}
                key={node.id}
                onClick={() => onNodeClick(node)}
                style={graphNodeStyle(node)}
                title={node.source.expandsTo && !node.expanded ? "点击展开产业链（懒加载）" : node.source.name}
                type="button"
              >
                {node.source.symbol ? <strong>{node.source.symbol}</strong> : null}
                <span>{node.source.name}</span>
                {node.source.expandsTo && !node.expanded ? (
                  <i>{`+${node.source.expandsTo.length}`}</i>
                ) : null}
              </button>
            ))}
          </div>
        </div>
      </section>
      <section aria-label="关系清单" className="card relationships-card">
        <header className="relationship-head">
          <div>
            <p className="eyebrow">RELATIONSHIP EVIDENCE</p>
            <h2>关系清单</h2>
          </div>
          <span className="count-pill">{graphModel.edges.length}</span>
        </header>
        <div className="relationship-table-head" aria-hidden="true">
          <span>FROM→TO</span>
          <span>关系</span>
          <span>BASIS</span>
          <span>置信</span>
          <span>证据</span>
          <span>说明</span>
        </div>
        {graphModel.edges.map((edge) => (
          <div className="relationship-row" key={edge.id}>
            <strong>{edge.fromLabel} → {edge.toLabel}</strong>
            <span>{RELATION_LABELS[edge.source.relation]}</span>
            <BasisBadge basis={edge.source.basis} label={edge.source.basis === "source_backed" ? "source" : "inferred"} />
            <span className="mono">{Math.round(edge.source.conf * 100)}%</span>
            <span className="evidence-cell">
              <b>{edge.source.ev.length}</b>
              {edge.source.ev.length > 0 ? (
                <button onClick={() => openEvidence(edge.source.ev)} type="button">
                  查看证据
                </button>
              ) : null}
            </span>
            <p>{edge.source.rationale}</p>
          </div>
        ))}
        {graphModel.edges.length === 0 ? (
          <p className="empty-note">当前 basis 筛选下没有关系。</p>
        ) : null}
      </section>
      <section className="card graph-summary">
        <p className="eyebrow">THESIS SNAPSHOT</p>
        <h2>{seedPosition.symbol} 研究摘要</h2>
        <p>{detail.summary}</p>
        <button onClick={() => openEvidence(evidenceIds)} type="button">
          证据 {evidenceIds.length}
        </button>
      </section>
    </div>
  );
}

function StockDetailDrawer({
  confirmThesis,
  decision,
  detail,
  evidenceCount,
  exportReport,
  isDegraded,
  onClose,
  openEvidence,
  position,
  retryDisabled,
  retryFromDetail,
  status
}: {
  confirmThesis: (decision: Exclude<ThesisDecision, null>) => void;
  decision: ThesisDecision;
  detail: DetailDatum;
  evidenceCount: number;
  exportReport: () => void;
  isDegraded: boolean;
  onClose: () => void;
  openEvidence: (ids: string[]) => void;
  position: DemoPosition;
  retryDisabled: boolean;
  retryFromDetail: () => void;
  status: keyof typeof STATUS_META;
}): JSX.Element {
  const meta = STATUS_META[status];
  return (
    <div className="detail-layer">
      <button aria-label="关闭个股详情遮罩" className="drawer-backdrop" onClick={onClose} type="button" />
      <aside
        aria-label="个股详情"
        aria-modal="true"
        className="detail-panel"
        onKeyDown={(event: KeyboardEvent<HTMLElement>) => {
          if (event.key === "Escape") {
            onClose();
          }
        }}
        role="dialog"
        tabIndex={-1}
      >
        <header className="drawer-header">
          <div>
            <p className="eyebrow">STOCK DETAIL / THESIS</p>
            <h2><span>{position.symbol}</span> {position.name}</h2>
            <div className="detail-chips">
              <span>{position.market}</span>
              <span>{position.runId ?? "no run"}</span>
              <span style={{ color: meta.color, background: meta.bg }}>{meta.text}</span>
              <span>evidence {evidenceCount}</span>
            </div>
          </div>
          <button aria-label="关闭" onClick={onClose} type="button">×</button>
        </header>
        {isDegraded ? (
          <div className="degraded-banner">
            <strong>本次研究已完成，但没有生成 thesis</strong>
            <button disabled={retryDisabled} onClick={retryFromDetail} type="button">
              重新研究
            </button>
          </div>
        ) : null}
        <section className="summary-card">
          <p className="eyebrow">现状一句话</p>
          <p>{detail.summary}</p>
        </section>
        {detail.reasons.length + detail.assumptions.length + detail.risks.length > 0 ? (
          <section className="thesis-groups">
            <p className="eyebrow">THESIS 假设</p>
            <ThesisGroup color="green" items={detail.reasons} openEvidence={openEvidence} title="持有理由" />
            <ThesisGroup color="blue" items={detail.assumptions} openEvidence={openEvidence} title="关键假设" />
            <ThesisGroup color="amber" items={detail.risks} openEvidence={openEvidence} title="风险" />
          </section>
        ) : (
          <p className="empty-note">暂无可确认 thesis，可重新研究补齐假设。</p>
        )}
        {!isDegraded ? (
          <section className="confirm-row">
            <button className="primary-button" onClick={() => confirmThesis("confirmed")} type="button">
              确认 thesis 假设
            </button>
            <button className="secondary-button" onClick={() => confirmThesis("edited")} type="button">
              标记需修改
            </button>
            <button className="danger-button" onClick={() => confirmThesis("rejected")} type="button">
              拒绝
            </button>
            {decision ? <p>{decisionText(decision)}</p> : null}
          </section>
        ) : null}
        <section className="intel-list">
          <p className="eyebrow">分类情报流</p>
          {detail.intel.length === 0 ? (
            <p className="empty-note">暂无分类情报。</p>
          ) : (
            detail.intel.map((item) => (
              <IntelCard item={item} key={item.title} openEvidence={openEvidence} />
            ))
          )}
        </section>
        <section className="watch-card">
          <div>
            <strong>关注点</strong>
            <span>仅供参考</span>
          </div>
          {detail.risks.length > 0 ? (
            detail.risks.map((risk) => <p key={risk.text}>{risk.text}</p>)
          ) : (
            <p>暂无额外关注点。</p>
          )}
          <small>研究待办与关注点，不构成交易依据。</small>
        </section>
        <button className="secondary-button export-report" onClick={exportReport} type="button">
          导出报告 Markdown
        </button>
      </aside>
    </div>
  );
}

function ThesisGroup({
  color,
  items,
  openEvidence,
  title
}: {
  color: "green" | "blue" | "amber";
  items: DetailItem[];
  openEvidence: (ids: string[]) => void;
  title: string;
}): JSX.Element | null {
  if (items.length === 0) {
    return null;
  }
  return (
    <div className={`thesis-group ${color}`}>
      <h3>{title}</h3>
      {items.map((item) => (
        <article key={item.text}>
          <p>{item.text}</p>
          <button onClick={() => openEvidence(item.ev)} type="button">
            证据 {item.ev.length}
          </button>
        </article>
      ))}
    </div>
  );
}

function IntelCard({
  item,
  openEvidence
}: {
  item: IntelDatum;
  openEvidence: (ids: string[]) => void;
}): JSX.Element {
  const direction =
    item.dir === "+" ? ["↑ 正向", "pos"] : item.dir === "-" ? ["↓ 负向", "neg"] : ["→ 中性", "neu"];
  return (
    <article className="intel-card">
      <header>
        <h3>{item.title}</h3>
        <span>{item.type}</span>
        <b className={direction[1]}>{direction[0]}</b>
        <small>tier {item.tier}</small>
      </header>
      <p>{item.content}</p>
      <button onClick={() => openEvidence(item.ev)} type="button">
        查看证据
      </button>
    </article>
  );
}

function EvidenceDrawer({
  evidences,
  onClose
}: {
  evidences: DemoEvidence[];
  onClose: () => void;
}): JSX.Element {
  return (
    <div className="evidence-layer">
      <button aria-label="关闭证据遮罩" className="drawer-backdrop evidence-backdrop" onClick={onClose} type="button" />
      <aside
        aria-label="证据抽屉"
        aria-modal="true"
        className="evidence-panel"
        onKeyDown={(event: KeyboardEvent<HTMLElement>) => {
          if (event.key === "Escape") {
            onClose();
          }
        }}
        role="dialog"
        tabIndex={-1}
      >
        <header className="drawer-header evidence-title-row">
          <div>
            <p className="eyebrow">EVIDENCE VIEWER</p>
            <h2>证据抽屉</h2>
          </div>
          <span className="count-pill">{evidences.length} 条</span>
          <button aria-label="关闭" onClick={onClose} type="button">×</button>
        </header>
        {evidences.map((item) => (
          <article className="evidence-card" key={item.id}>
            <header>
              <span className="mono">{item.id}</span>
              <TierBadge tier={item.tier} />
            </header>
            <h3>{item.title}</h3>
            <p className="evidence-meta">{item.source} · 抓取 {item.captured} · 发布 {item.published ?? "unknown"}</p>
            <blockquote>{item.snippet}</blockquote>
            <a href={item.url} rel="noreferrer" target="_blank">打开来源 ↗</a>
          </article>
        ))}
      </aside>
    </div>
  );
}

function AgentOpsView({
  opsRunId,
  refresh,
  selectedOpsRun,
  setOpsRunId
}: {
  opsRunId: string;
  refresh: () => void;
  selectedOpsRun: OpsRunDatum;
  setOpsRunId: (id: string) => void;
}): JSX.Element {
  const selectedMeta = RUN_STATUS_META[selectedOpsRun.status];
  const trace = TRACES[selectedOpsRun.id] ?? [];
  return (
    <div className="ops-view">
      <section className="ops-metrics">
        {METRIC_TILES.map((tile) => (
          <article key={tile.label}>
            <strong>{tile.value}</strong>
            <span>{tile.label}</span>
          </article>
        ))}
      </section>
      <div className="ops-grid">
        <section className="card ops-runs">
          <header className="card-header compact">
            <div>
              <p className="eyebrow">RECENT RUNS</p>
              <h2>最近 Runs</h2>
            </div>
            <button className="secondary-button small" onClick={refresh} type="button">
              刷新
            </button>
          </header>
          {OPS_RUNS.map((run) => {
            const meta = RUN_STATUS_META[run.status];
            return (
              <button
                aria-pressed={run.id === opsRunId}
                className="run-card"
                key={run.id}
                onClick={() => setOpsRunId(run.id)}
                type="button"
              >
                <strong>{run.id}</strong>
                <span style={{ color: meta.color, background: meta.bg }}>{meta.label}</span>
                <small>{run.pos} · {run.lat} · {run.tools} tools · cache {run.cache}</small>
              </button>
            );
          })}
        </section>
        <section aria-label="Run trace" className="card run-trace">
          <header className="trace-header">
            <div>
              <p className="eyebrow">RUN TRACE</p>
              <h2>Run Trace</h2>
            </div>
            <span style={{ color: selectedMeta.color, background: selectedMeta.bg }}>
              {selectedMeta.label}
            </span>
          </header>
          <ol>
            {trace.map((step, index) => (
              <TraceStep hasLine={index < trace.length - 1} key={`${step.name}-${index}`} step={step} />
            ))}
          </ol>
        </section>
      </div>
    </div>
  );
}

function TraceStep({ hasLine, step }: { hasLine: boolean; step: TraceDatum }): JSX.Element {
  return (
    <li className={`trace-step ${step.status}`}>
      <i />
      {hasLine ? <b aria-hidden="true" /> : null}
      <div>
        <header>
          <strong>{step.name}</strong>
          <span>{step.kind}</span>
          <em>{step.status}</em>
          <small>{step.lat}</small>
        </header>
        <p>
          {step.metas.map((meta) => <small key={meta}>{meta}</small>)}
        </p>
      </div>
    </li>
  );
}

function MobileNav({
  setView,
  view
}: {
  setView: (view: ViewMode) => void;
  view: ViewMode;
}): JSX.Element {
  const items: Array<[ViewMode, string]> = [
    ["home", "工作台"],
    ["graph", "图谱"],
    ["ops", "AgentOps"]
  ];
  return (
    <nav aria-label="移动端导航" className="mobile-nav">
      {items.map(([target, label]) => (
        <button
          aria-pressed={view === target}
          key={target}
          onClick={() => setView(target)}
          type="button"
        >
          {label}
        </button>
      ))}
    </nav>
  );
}

function BasisBadge({ basis, label }: { basis: Basis; label: string }): JSX.Element {
  return <span className={`basis-badge ${basis}`}>{label}</span>;
}

function TierBadge({ tier }: { tier: 1 | 2 | 3 }): JSX.Element {
  return <span className={`tier-badge tier-${tier}`}>tier {tier}</span>;
}

function positionStatus(
  position: DemoPosition,
  thesisState: Record<string, ThesisDecision>
): keyof typeof STATUS_META {
  if (position.run === "running") {
    return "running";
  }
  if (position.run === "degraded") {
    return "degraded";
  }
  if (position.run === "awaiting") {
    return "awaiting";
  }
  if (position.run === "completed") {
    return thesisState[position.id] === "confirmed" ? "confirmed" : "awaiting";
  }
  return "none";
}

function briefSummary(
  position: DemoPosition,
  thesisState: Record<string, ThesisDecision>
): string {
  const status = positionStatus(position, thesisState);
  if (status === "running") {
    return "研究中…";
  }
  if (status === "confirmed" && DETAILS[position.id]) {
    return DETAILS[position.id].summary;
  }
  if (status === "awaiting") {
    return "待确认 thesis";
  }
  if (status === "degraded") {
    return "研究完成但无 thesis，可重新研究";
  }
  return "尚未研究";
}

function emptyDetail(position: DemoPosition): DetailDatum {
  return {
    summary: `${position.name} 暂无综合 thesis。`,
    reasons: [],
    assumptions: [],
    risks: [],
    intel: []
  };
}

function collectEvidenceIds(
  detail: DetailDatum,
  neighbors: GraphNodeDatum[]
): string[] {
  const ids = new Set<string>();
  [...detail.reasons, ...detail.assumptions, ...detail.risks].forEach((item) =>
    item.ev.forEach((id) => ids.add(id))
  );
  detail.intel.forEach((item) => item.ev.forEach((id) => ids.add(id)));
  neighbors.forEach((node) => node.ev.forEach((id) => ids.add(id)));
  return Array.from(ids);
}

interface Point {
  x: number;
  y: number;
}

interface GraphNodeView {
  id: string;
  source: GraphNodeDatum;
  x: number;
  y: number;
  expanded?: boolean;
}

interface GraphEdgeView {
  id: string;
  source: GraphNodeDatum;
  from: Point;
  to: Point;
  fromLabel: string;
  toLabel: string;
}

interface GraphModel {
  nodes: GraphNodeView[];
  edges: GraphEdgeView[];
}

function buildGraphModel(
  seed: DemoPosition,
  expanded: Record<string, boolean>,
  basisFilter: "all" | Basis
): GraphModel {
  const seedPoint = { x: 620, y: 280 };
  const graphData = GRAPH[seed.id] ?? { neighbors: [] };
  const grouped: Record<Relation, GraphNodeDatum[]> = {
    supplier: [],
    customer: [],
    competitor: [],
    belongs_to: []
  };
  graphData.neighbors.forEach((node) => grouped[node.relation].push(node));
  const allNodes: GraphNodeView[] = [];
  const allEdges: GraphEdgeView[] = [];
  const placeGroup = (
    list: GraphNodeDatum[],
    xFor: (index: number, count: number) => number,
    yFor: (index: number, count: number) => number
  ) => {
    list.forEach((node, index) => {
      const count = list.length;
      const placed = {
        id: node.id,
        source: node,
        x: clampX(xFor(index, count)),
        y: yFor(index, count),
        expanded: expanded[node.id]
      };
      allNodes.push(placed);
      allEdges.push({
        id: `seed-${node.id}`,
        source: node,
        from: seedPoint,
        to: placed,
        fromLabel: seed.symbol,
        toLabel: labelNode(node)
      });
      if (node.expandsTo && expanded[node.id]) {
        node.expandsTo.forEach((child, childIndex) => {
          const childNode = {
            id: child.id,
            source: child,
            x: clampX(placed.x - 236),
            y: placed.y + (childIndex - (node.expandsTo!.length - 1) / 2) * 118
          };
          allNodes.push(childNode);
          allEdges.push({
            id: `${node.id}-${child.id}`,
            source: child,
            from: placed,
            to: childNode,
            fromLabel: labelNode(node),
            toLabel: labelNode(child)
          });
        });
      }
    });
  };
  placeGroup(grouped.supplier, () => 300, (index, count) => 280 + (index - (count - 1) / 2) * 140);
  placeGroup(grouped.customer, () => 940, (index, count) => 280 + (index - (count - 1) / 2) * 140);
  placeGroup(grouped.competitor, (index, count) => 620 + (index - (count - 1) / 2) * 240, () => 88);
  placeGroup(grouped.belongs_to, (index, count) => 620 + (index - (count - 1) / 2) * 300, () => 488);

  const edges =
    basisFilter === "all"
      ? allEdges
      : allEdges.filter((edge) => edge.source.basis === basisFilter);
  const visibleNodeIds = new Set(edges.flatMap((edge) => [edge.source.id]));
  const nodes =
    basisFilter === "all"
      ? uniqueNodes(allNodes)
      : uniqueNodes(allNodes.filter((node) => visibleNodeIds.has(node.id)));
  return { nodes, edges };
}

function uniqueNodes(nodes: GraphNodeView[]): GraphNodeView[] {
  const seen = new Set<string>();
  return nodes.filter((node) => {
    if (seen.has(node.id)) {
      return false;
    }
    seen.add(node.id);
    return true;
  });
}

function clampX(x: number): number {
  return Math.max(90, Math.min(1150, x));
}

function labelNode(node: GraphNodeDatum): string {
  return node.symbol || node.name;
}

function seedAsNode(position: DemoPosition): GraphNodeDatum {
  return {
    id: position.id,
    symbol: position.symbol,
    name: position.name,
    relation: "belongs_to",
    basis: "source_backed",
    conf: 1,
    ev: [],
    rationale: "持仓种子"
  };
}

function graphNodeClass(node: GraphNodeView, selectedNodeId: string): string {
  const classes = ["graph-node"];
  classes.push(node.source.kind === "segment" ? "segment-node" : "company-node");
  if (node.source.basis === "inferred") {
    classes.push("inferred-node");
  }
  if (node.id === selectedNodeId) {
    classes.push("selected");
  }
  return classes.join(" ");
}

function graphNodeStyle(node: GraphNodeView): CSSProperties {
  const width = node.source.kind === "segment" ? 190 : 150;
  const height = node.source.kind === "segment" ? 42 : 54;
  return {
    "--x": `${node.x - width / 2}px`,
    "--y": `${node.y - height / 2}px`,
    "--w": `${width}px`,
    "--h": `${height}px`
  } as CSSProperties;
}

function decisionText(decision: Exclude<ThesisDecision, null>): string {
  if (decision === "confirmed") {
    return "✓ 已确认：假设已纳入跟踪基线";
  }
  if (decision === "edited") {
    return "已标记需修改：待补充证据后重新确认";
  }
  return "已拒绝：thesis 退回重新起草";
}

function portfolioMarkdown(
  positions: DemoPosition[],
  thesisState: Record<string, ThesisDecision>
): string {
  return [
    "# 组合 Brief",
    "仅供参考：以下内容用于研究跟踪，保留来源与推断标记。",
    "",
    "## 持仓一句话",
    ...positions.map((position) => `- **${position.symbol}**: ${briefSummary(position, thesisState)}`),
    "",
    "## 产业段重叠",
    ...OVERLAP_GROUPS.map((group) =>
      `- ${group.name}: ${group.symbols}（${group.basis === "source_backed" ? "有出处" : "基于推断"}）`
    )
  ].join("\n");
}

function stockMarkdown(
  position: DemoPosition,
  detail: DetailDatum,
  evidenceIds: string[]
): string {
  return [
    `# ${position.symbol} 深度报告`,
    "",
    "## 摘要",
    detail.summary,
    "",
    "## Thesis",
    ...detail.reasons.map((item) => `- 持有理由：${item.text}`),
    ...detail.assumptions.map((item) => `- 关键假设：${item.text}`),
    ...detail.risks.map((item) => `- 风险：${item.text}`),
    "",
    "## 来源清单",
    ...evidenceIds.map((id) => {
      const evidence = EVIDENCE[id];
      return evidence ? `- ${evidence.title} - ${evidence.url} - tier ${evidence.tier}` : `- ${id}`;
    })
  ].join("\n");
}
