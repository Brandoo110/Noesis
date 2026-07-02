import type { Basis, Relation } from "./types/api";

export type ViewMode = "home" | "graph" | "ops";
export type PositionRunState = "completed" | "awaiting" | "running" | "degraded" | null;
export type ThesisDecision = "confirmed" | "edited" | "rejected" | null;

export interface DemoPosition {
  id: string;
  symbol: string;
  name: string;
  market: "US" | "CN" | "HK";
  kind: "owned" | "watching";
  run: PositionRunState;
  runId: string | null;
}

export interface DemoEvidence {
  id: string;
  title: string;
  source: string;
  tier: 1 | 2 | 3;
  captured: string;
  published: string | null;
  snippet: string;
  url: string;
}

export interface GraphNodeDatum {
  id: string;
  symbol: string;
  name: string;
  relation: Relation;
  basis: Basis;
  conf: number;
  ev: string[];
  rationale: string;
  kind?: "segment";
  expandsTo?: GraphNodeDatum[];
}

export interface DetailItem {
  text: string;
  ev: string[];
}

export interface IntelDatum {
  title: string;
  type: string;
  dir: "+" | "-" | "0";
  tier: 1 | 2 | 3;
  content: string;
  ev: string[];
}

export interface DetailDatum {
  summary: string;
  reasons: DetailItem[];
  assumptions: DetailItem[];
  risks: DetailItem[];
  intel: IntelDatum[];
}

export interface OpsRunDatum {
  id: string;
  pos: string;
  status: "completed" | "awaiting_confirmation" | "failed";
  lat: string;
  tools: number;
  cache: string;
}

export interface TraceDatum {
  name: string;
  kind: "node" | "tool";
  status: "ok" | "retry" | "failed";
  lat: string;
  metas: string[];
}

export const INITIAL_POSITIONS: DemoPosition[] = [
  { id: "nvda", symbol: "NVDA", name: "英伟达", market: "US", kind: "owned", run: "completed", runId: "run_8f3a21" },
  { id: "tsm", symbol: "TSM", name: "台积电", market: "US", kind: "owned", run: "completed", runId: "run_7c11e0" },
  { id: "catl", symbol: "300750", name: "宁德时代", market: "CN", kind: "owned", run: "awaiting", runId: "run_6b42da" },
  { id: "tencent", symbol: "0700", name: "腾讯控股", market: "HK", kind: "owned", run: null, runId: null },
  { id: "asml", symbol: "ASML", name: "阿斯麦", market: "US", kind: "watching", run: null, runId: null }
];

export const INITIAL_THESIS_STATE: Record<string, ThesisDecision> = {
  nvda: "confirmed",
  tsm: "confirmed"
};

export const EVIDENCE: Record<string, DemoEvidence> = {
  "ev-101": {
    id: "ev-101",
    title: "NVIDIA FY2026 Q1 10-Q：供应承诺与采购义务",
    source: "SEC EDGAR · 10-Q",
    tier: 1,
    captured: "2026-06-12",
    published: "2026-05-28",
    snippet: "公司披露与 HBM 及先进封装相关的长期采购承诺显著增加，供应商集中度风险在风险因素一节中被再次强调。",
    url: "https://example.com/ev-101"
  },
  "ev-102": {
    id: "ev-102",
    title: "台积电 2026 Q1 法说会纪要：CoWoS 产能翻倍计划",
    source: "TSMC IR · 法说会",
    tier: 1,
    captured: "2026-06-10",
    published: "2026-04-17",
    snippet: "管理层确认 2026 年底前 CoWoS 月产能较 2025 年翻倍，AI 相关收入占比持续提升，先进制程产能已被主要客户预订至 2027。",
    url: "https://example.com/ev-102"
  },
  "ev-103": {
    id: "ev-103",
    title: "Reuters：云厂商集体上调 AI 资本开支指引",
    source: "Reuters",
    tier: 2,
    captured: "2026-06-20",
    published: "2026-06-19",
    snippet: "微软、Meta 与谷歌在最新财报电话会中均上调全年资本开支指引，主要投向 AI 数据中心与加速计算集群。",
    url: "https://example.com/ev-103"
  },
  "ev-104": {
    id: "ev-104",
    title: "BIS 出口管制新规征求意见稿",
    source: "美国商务部 BIS",
    tier: 1,
    captured: "2026-06-25",
    published: "2026-06-24",
    snippet: "新一轮征求意见稿拟将部分高带宽存储与先进封装设备纳入管制清单，行业评论期至 2026 年 8 月。",
    url: "https://example.com/ev-104"
  },
  "ev-105": {
    id: "ev-105",
    title: "行业博客：CoWoS 与 AI 服务器供应链追踪（6 月）",
    source: "行业博客（三级来源）",
    tier: 3,
    captured: "2026-06-18",
    published: "2026-06-15",
    snippet: "博主根据供应链调研推断 ODM 订单流向与 GPU 云厂商扩张节奏；该来源为三级来源，相关结论标记为推断。",
    url: "https://example.com/ev-105"
  },
  "ev-106": {
    id: "ev-106",
    title: "公司公告：与台积电签订长期产能保障协议",
    source: "公司公告",
    tier: 1,
    captured: "2026-06-05",
    published: "2026-05-30",
    snippet: "公告披露预付款项用于锁定先进制程与先进封装产能，期限覆盖 2026-2028 年。",
    url: "https://example.com/ev-106"
  },
  "ev-107": {
    id: "ev-107",
    title: "财新：宁德时代神行电池产线爬坡情况",
    source: "财新",
    tier: 2,
    captured: "2026-06-22",
    published: "2026-06-21",
    snippet: "报道称神行超充电池产线利用率回升，海外基地建设进度符合指引；储能订单增速高于动力电池。",
    url: "https://example.com/ev-107"
  },
  "ev-108": {
    id: "ev-108",
    title: "Meta 财报电话会：GPU 集群扩建计划",
    source: "Meta IR",
    tier: 1,
    captured: "2026-06-11",
    published: "2026-04-30",
    snippet: "管理层披露年内新增两个十万卡级训练集群，推理侧算力采购同步增长。",
    url: "https://example.com/ev-108"
  },
  "ev-109": {
    id: "ev-109",
    title: "国家新闻出版署：6 月游戏版号名单",
    source: "NPPA",
    tier: 1,
    captured: "2026-06-28",
    published: "2026-06-26",
    snippet: "6 月共发放国产网络游戏版号 104 个，发放节奏与上半年均值持平。",
    url: "https://example.com/ev-109"
  }
};

export const GRAPH: Record<string, { neighbors: GraphNodeDatum[] }> = {
  nvda: {
    neighbors: [
      {
        id: "n-tsm",
        symbol: "TSM",
        name: "台积电",
        relation: "supplier",
        basis: "source_backed",
        conf: 0.93,
        ev: ["ev-102", "ev-106"],
        rationale: "4nm 与 CoWoS 独家代工，法说会与供应协议双重印证",
        expandsTo: [
          { id: "n-asml", symbol: "ASML", name: "阿斯麦", relation: "supplier", basis: "source_backed", conf: 0.95, ev: ["ev-102"], rationale: "EUV 光刻机唯一供应商" },
          { id: "n-shinetsu", symbol: "4063.T", name: "信越化学", relation: "supplier", basis: "inferred", conf: 0.62, ev: ["ev-105"], rationale: "硅片供应，推断自行业格局" }
        ]
      },
      { id: "n-hynix", symbol: "000660", name: "SK 海力士", relation: "supplier", basis: "source_backed", conf: 0.88, ev: ["ev-101"], rationale: "HBM3E 主力供应商，10-Q 供应承诺印证" },
      { id: "n-fii", symbol: "601138", name: "工业富联", relation: "supplier", basis: "inferred", conf: 0.64, ev: ["ev-105"], rationale: "AI 服务器整机组装，推断边" },
      { id: "n-msft", symbol: "MSFT", name: "微软", relation: "customer", basis: "source_backed", conf: 0.9, ev: ["ev-103"], rationale: "Azure 资本开支指引上调" },
      { id: "n-meta", symbol: "META", name: "Meta", relation: "customer", basis: "source_backed", conf: 0.85, ev: ["ev-108"], rationale: "财报电话会披露 GPU 集群扩建" },
      { id: "n-crwv", symbol: "CRWV", name: "CoreWeave", relation: "customer", basis: "inferred", conf: 0.7, ev: ["ev-105"], rationale: "GPU 云租赁规模推断" },
      { id: "n-amd", symbol: "AMD", name: "超威半导体", relation: "competitor", basis: "source_backed", conf: 0.95, ev: ["ev-101"], rationale: "10-K 风险因素互列" },
      { id: "n-segai", symbol: "", name: "AI 加速计算", relation: "belongs_to", basis: "source_backed", conf: 0.97, ev: ["ev-101"], rationale: "数据中心收入占比 87%", kind: "segment" },
      { id: "n-segcapex", symbol: "", name: "数据中心资本开支", relation: "belongs_to", basis: "inferred", conf: 0.74, ev: ["ev-103"], rationale: "主题暴露为推断", kind: "segment" }
    ]
  },
  tsm: {
    neighbors: [
      { id: "t-asml", symbol: "ASML", name: "阿斯麦", relation: "supplier", basis: "source_backed", conf: 0.95, ev: ["ev-102"], rationale: "EUV 光刻机唯一供应商" },
      { id: "t-amat", symbol: "AMAT", name: "应用材料", relation: "supplier", basis: "source_backed", conf: 0.86, ev: ["ev-102"], rationale: "沉积与刻蚀设备主力供应商" },
      { id: "t-nvda", symbol: "NVDA", name: "英伟达", relation: "customer", basis: "source_backed", conf: 0.93, ev: ["ev-106"], rationale: "长期产能保障协议" },
      { id: "t-aapl", symbol: "AAPL", name: "苹果", relation: "customer", basis: "source_backed", conf: 0.91, ev: ["ev-102"], rationale: "先进制程最大单一客户" },
      { id: "t-samsung", symbol: "005930", name: "三星代工", relation: "competitor", basis: "source_backed", conf: 0.9, ev: ["ev-102"], rationale: "先进制程代工直接竞争" },
      { id: "t-segfab", symbol: "", name: "先进制程代工", relation: "belongs_to", basis: "source_backed", conf: 0.96, ev: ["ev-102"], rationale: "核心业务归属", kind: "segment" },
      { id: "t-segai", symbol: "", name: "AI 加速计算", relation: "belongs_to", basis: "source_backed", conf: 0.88, ev: ["ev-102"], rationale: "AI 相关收入占比提升", kind: "segment" }
    ]
  },
  catl: {
    neighbors: [
      { id: "c-tianqi", symbol: "002466", name: "天齐锂业", relation: "supplier", basis: "inferred", conf: 0.66, ev: ["ev-107"], rationale: "锂盐供应，推断自采购结构" },
      { id: "c-xianDao", symbol: "300450", name: "先导智能", relation: "supplier", basis: "source_backed", conf: 0.84, ev: ["ev-107"], rationale: "产线设备供应商，扩产伴随订单" },
      { id: "c-tesla", symbol: "TSLA", name: "特斯拉", relation: "customer", basis: "source_backed", conf: 0.9, ev: ["ev-107"], rationale: "长期供货协议公开披露" },
      { id: "c-nio", symbol: "9866", name: "蔚来", relation: "customer", basis: "source_backed", conf: 0.82, ev: ["ev-107"], rationale: "车型配套关系" },
      { id: "c-byd", symbol: "002594", name: "比亚迪", relation: "competitor", basis: "source_backed", conf: 0.93, ev: ["ev-107"], rationale: "动力电池份额直接竞争" },
      { id: "c-segbat", symbol: "", name: "动力电池", relation: "belongs_to", basis: "source_backed", conf: 0.97, ev: ["ev-107"], rationale: "核心业务归属", kind: "segment" },
      { id: "c-seges", symbol: "", name: "储能系统", relation: "belongs_to", basis: "inferred", conf: 0.78, ev: ["ev-107"], rationale: "第二增长曲线，推断权重", kind: "segment" }
    ]
  },
  tencent: {
    neighbors: [
      { id: "x-nvda", symbol: "NVDA", name: "英伟达", relation: "supplier", basis: "inferred", conf: 0.72, ev: ["ev-105"], rationale: "AI 算力采购，推断自行业格局" },
      { id: "x-odm", symbol: "", name: "服务器 ODM", relation: "supplier", basis: "inferred", conf: 0.6, ev: ["ev-105"], rationale: "数据中心硬件采购推断", kind: "segment" },
      { id: "x-baba", symbol: "9988", name: "阿里巴巴", relation: "competitor", basis: "source_backed", conf: 0.88, ev: ["ev-109"], rationale: "云与广告业务竞争" },
      { id: "x-seggame", symbol: "", name: "游戏发行", relation: "belongs_to", basis: "source_backed", conf: 0.95, ev: ["ev-109"], rationale: "版号发放直接相关", kind: "segment" },
      { id: "x-segnet", symbol: "", name: "互联网平台", relation: "belongs_to", basis: "source_backed", conf: 0.96, ev: ["ev-109"], rationale: "核心业务归属", kind: "segment" }
    ]
  },
  asml: {
    neighbors: [
      { id: "a-zeiss", symbol: "", name: "蔡司光学", relation: "supplier", basis: "source_backed", conf: 0.92, ev: ["ev-102"], rationale: "EUV 光学系统独家供应", kind: "segment" },
      { id: "a-tsm", symbol: "TSM", name: "台积电", relation: "customer", basis: "source_backed", conf: 0.94, ev: ["ev-102"], rationale: "EUV 最大客户之一" },
      { id: "a-samsung", symbol: "005930", name: "三星电子", relation: "customer", basis: "source_backed", conf: 0.87, ev: ["ev-102"], rationale: "存储与代工双线采购" },
      { id: "a-segequip", symbol: "", name: "半导体设备", relation: "belongs_to", basis: "source_backed", conf: 0.97, ev: ["ev-102"], rationale: "核心业务归属", kind: "segment" }
    ]
  }
};

export const DETAILS: Record<string, DetailDatum> = {
  nvda: {
    summary: "英伟达由数据中心训练与推理需求双轮驱动，短期供给瓶颈在 HBM 与 CoWoS 产能；研究重点在大客户自研芯片进度与出口管制边界。",
    reasons: [
      { text: "数据中心收入占比 87%，云厂商资本开支指引持续上调", ev: ["ev-101", "ev-103"] },
      { text: "CUDA 生态与整机柜方案构成切换成本", ev: ["ev-101"] }
    ],
    assumptions: [
      { text: "HBM 与 CoWoS 供给在 2026H2 逐步缓解", ev: ["ev-102"] },
      { text: "推理需求接棒训练需求，支撑 2027 年采购量", ev: ["ev-103", "ev-108"] }
    ],
    risks: [
      { text: "大客户自研 ASIC 分流高端 GPU 需求", ev: ["ev-105"] },
      { text: "出口管制范围扩大影响可服务市场", ev: ["ev-104"] }
    ],
    intel: [
      { title: "云厂商资本开支指引上调", type: "需求", dir: "+", tier: 1, content: "三大云厂商上调 2026 年资本开支指引，AI 数据中心为主要投向。", ev: ["ev-103"] },
      { title: "CoWoS 产能扩张进度确认", type: "供应链", dir: "+", tier: 1, content: "台积电确认年底前 CoWoS 月产能翻倍，先进封装瓶颈边际缓解。", ev: ["ev-102"] },
      { title: "出口管制新规征求意见", type: "监管", dir: "-", tier: 1, content: "BIS 拟扩大 HBM 与先进封装设备管制范围，评论期至 8 月。", ev: ["ev-104"] },
      { title: "GPU 云厂商扩张节奏（推断）", type: "产业链", dir: "0", tier: 3, content: "三级来源推断 GPU 云持续扩张，需一手证据进一步验证。", ev: ["ev-105"] }
    ]
  },
  tsm: {
    summary: "台积电先进制程与先进封装双紧张，AI 相关收入占比提升；研究重点在 CoWoS 扩产兑现节奏与地缘政策变量。",
    reasons: [{ text: "先进制程产能被主要客户预订至 2027 年", ev: ["ev-102"] }],
    assumptions: [{ text: "CoWoS 扩产按计划于 2026 年底翻倍", ev: ["ev-102"] }],
    risks: [{ text: "出口管制与地缘政策的不确定性", ev: ["ev-104"] }],
    intel: [{ title: "CoWoS 月产能翻倍计划", type: "产能", dir: "+", tier: 1, content: "法说会确认扩产节奏，先进封装收入占比提升。", ev: ["ev-102"] }]
  },
  catl: {
    summary: "宁德时代动力电池份额稳定，边际变化来自神行超充产线爬坡与储能业务放量；研究重点为海外基地进度与上游锂价传导。",
    reasons: [{ text: "全球动力电池份额第一，客户结构多元", ev: ["ev-107"] }],
    assumptions: [{ text: "储能业务 2026 年增速高于动力电池", ev: ["ev-107"] }],
    risks: [
      { text: "上游锂价波动向盈利端传导", ev: ["ev-107"] },
      { text: "海外基地投产进度不及指引", ev: ["ev-107"] }
    ],
    intel: [{ title: "神行电池产线利用率回升", type: "产能", dir: "+", tier: 2, content: "财新报道产线爬坡符合指引，储能订单增速更高。", ev: ["ev-107"] }]
  },
  asml: {
    summary: "阿斯麦 EUV 订单能见度延伸至 2027 年，逻辑与存储客户扩产节奏是核心变量。",
    reasons: [{ text: "EUV 光刻机独家供应地位", ev: ["ev-102"] }],
    assumptions: [{ text: "2026 年存储客户重启扩产", ev: ["ev-105"] }],
    risks: [{ text: "对华出口许可政策变化", ev: ["ev-104"] }],
    intel: []
  },
  tencent: {
    summary: "腾讯本次研究完成但未生成 thesis；分类情报与证据可查看，可重新研究以生成可确认的 thesis。",
    reasons: [],
    assumptions: [],
    risks: [],
    intel: [{ title: "游戏版号发放节奏平稳", type: "监管", dir: "0", tier: 1, content: "6 月版号数量维持高位，新游储备充足。", ev: ["ev-109"] }]
  }
};

export const OVERLAP_GROUPS = [
  { name: "AI 加速计算", symbols: "NVDA / TSM / ASML", basis: "source_backed" as Basis },
  { name: "半导体设备", symbols: "TSM / ASML", basis: "source_backed" as Basis },
  { name: "数据中心资本开支", symbols: "NVDA / TSM", basis: "inferred" as Basis }
];

export const CORRELATION_SYMBOLS = ["NVDA", "TSM", "300750", "0700", "ASML"];

export const CORRELATION_VALUES: Record<string, number> = {
  "NVDA|TSM": 0.72,
  "NVDA|300750": 0.18,
  "NVDA|0700": 0.22,
  "NVDA|ASML": 0.58,
  "TSM|300750": 0.15,
  "TSM|0700": 0.2,
  "TSM|ASML": 0.66,
  "300750|0700": 0.12,
  "300750|ASML": 0.1,
  "0700|ASML": 0.14
};

export const OPS_RUNS: OpsRunDatum[] = [
  { id: "run_8f3a21", pos: "NVDA", status: "completed", lat: "42.6s", tools: 9, cache: "38%" },
  { id: "run_6b42da", pos: "300750", status: "awaiting_confirmation", lat: "51.2s", tools: 11, cache: "27%" },
  { id: "run_7c11e0", pos: "TSM", status: "completed", lat: "39.8s", tools: 8, cache: "55%" },
  { id: "run_3fa908", pos: "TSM", status: "failed", lat: "12.4s", tools: 3, cache: "12%" }
];

export const TRACES: Record<string, TraceDatum[]> = {
  run_8f3a21: [
    { name: "intake_resolve", kind: "node", status: "ok", lat: "1.2s", metas: ["输入 NVDA / US", "输出 entity: nvda"] },
    { name: "web_search", kind: "tool", status: "ok", lat: "3.4s", metas: ["cache miss", "query: NVDA supply chain"] },
    { name: "expand_chain", kind: "node", status: "ok", lat: "8.9s", metas: ["新增 9 条边", "2 条标记 inferred"] },
    { name: "fetch_filings", kind: "tool", status: "ok", lat: "5.1s", metas: ["cache hit", "10-Q / 法说会纪要"] },
    { name: "intel_synth", kind: "node", status: "ok", lat: "12.3s", metas: ["4 条情报", "evidence 8 条"] },
    { name: "risk_reviewer", kind: "node", status: "ok", lat: "2.2s", metas: ["红线检查通过", "0 无证据断言"] },
    { name: "thesis_draft", kind: "node", status: "retry", lat: "9.5s", metas: ["retry 1", "3 组假设"] }
  ],
  run_6b42da: [
    { name: "intake_resolve", kind: "node", status: "ok", lat: "1.1s", metas: ["输入 300750 / CN", "输出 entity: catl"] },
    { name: "web_search", kind: "tool", status: "ok", lat: "4.2s", metas: ["cache miss"] },
    { name: "expand_chain", kind: "node", status: "ok", lat: "10.4s", metas: ["新增 7 条边", "2 条标记 inferred"] },
    { name: "intel_synth", kind: "node", status: "ok", lat: "14.8s", metas: ["1 条情报", "evidence 3 条"] },
    { name: "risk_reviewer", kind: "node", status: "ok", lat: "2.0s", metas: ["红线检查通过"] },
    { name: "thesis_draft", kind: "node", status: "ok", lat: "11.6s", metas: ["3 组假设", "待人工确认"] }
  ],
  run_7c11e0: [
    { name: "intake_resolve", kind: "node", status: "ok", lat: "0.9s", metas: ["输入 TSM / US"] },
    { name: "fetch_filings", kind: "tool", status: "ok", lat: "4.7s", metas: ["cache hit", "法说会纪要"] },
    { name: "expand_chain", kind: "node", status: "ok", lat: "9.7s", metas: ["新增 7 条边"] },
    { name: "intel_synth", kind: "node", status: "ok", lat: "13.1s", metas: ["1 条情报", "evidence 4 条"] },
    { name: "thesis_draft", kind: "node", status: "ok", lat: "10.2s", metas: ["3 组假设"] }
  ],
  run_3fa908: [
    { name: "intake_resolve", kind: "node", status: "ok", lat: "1.0s", metas: ["输入 TSM / US"] },
    { name: "web_search", kind: "tool", status: "failed", lat: "11.4s", metas: ["rate_limit", "重试 3 次后终止"] },
    { name: "run_abort", kind: "node", status: "failed", lat: "0.1s", metas: ["降级：保留已抓取证据"] }
  ]
};

export const METRIC_TILES = [
  { value: "24", label: "总 runs" },
  { value: "88%", label: "任务完成率" },
  { value: "38.2s", label: "平均时延" },
  { value: "71.4s", label: "P95 时延" },
  { value: "96%", label: "工具成功率" },
  { value: "41%", label: "缓存命中" },
  { value: "5", label: "重试次数" },
  { value: "18.4k", label: "tokens / run" },
  { value: "$0.023", label: "成本 / run" },
  { value: "93%", label: "证据覆盖率" }
];
