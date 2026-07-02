export type WorkspaceView = "home" | "graph" | "ops";

export interface WorkspaceViewMeta {
  id: WorkspaceView;
  label: string;
  title: string;
  subtitle: string;
  iconPath: string;
}

export const WORKSPACE_VIEWS: WorkspaceViewMeta[] = [
  {
    id: "home",
    label: "组合工作台",
    title: "组合工作台",
    subtitle: "持仓 · 研究状态 · 组合洞察",
    iconPath: "M3 4h7v8H3zM14 4h7v5h-7zM14 13h7v7h-7zM3 16h7v4H3z"
  },
  {
    id: "graph",
    label: "图谱探索",
    title: "图谱探索",
    subtitle: "产业链懒加载 · 证据追踪",
    iconPath: "M5 12h4m6-6h4m-4 12h4M8.5 10.5 15 6.8M8.5 13.5 15 17.2"
  },
  {
    id: "ops",
    label: "AgentOps",
    title: "AgentOps",
    subtitle: "Run 监控 · 追踪 · 质量门禁",
    iconPath: "M3 12h4l3-8 4 16 3-8h4"
  }
];
