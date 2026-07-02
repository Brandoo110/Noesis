import { useEffect, useRef, useState } from "react";

interface TopBarProps {
  showFilter?: boolean;
  subtitle: string;
  title: string;
}

export function TopBar({
  showFilter = false,
  subtitle,
  title
}: TopBarProps): JSX.Element {
  const [filterOpen, setFilterOpen] = useState(false);
  const [healthOpen, setHealthOpen] = useState(false);
  const actionsRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    function closeFromOutside(event: MouseEvent): void {
      if (!actionsRef.current?.contains(event.target as Node)) {
        setFilterOpen(false);
        setHealthOpen(false);
      }
    }
    function closeFromEscape(event: KeyboardEvent): void {
      if (event.key === "Escape") {
        setFilterOpen(false);
        setHealthOpen(false);
      }
    }
    document.addEventListener("mousedown", closeFromOutside);
    document.addEventListener("keydown", closeFromEscape);
    return () => {
      document.removeEventListener("mousedown", closeFromOutside);
      document.removeEventListener("keydown", closeFromEscape);
    };
  }, []);

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
        <input aria-label="全局搜索" placeholder="搜索标的、主题或证据…" />
      </label>
      <div className="topbar-actions" ref={actionsRef}>
        {showFilter ? (
          <button
            aria-expanded={filterOpen}
            className="secondary-button"
            onClick={() => {
              setFilterOpen((current) => !current);
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
            setHealthOpen((current) => !current);
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
              <select aria-label="持仓类型筛选" defaultValue="all">
                <option value="all">全部</option>
                <option value="owned">持有</option>
                <option value="watching">观察</option>
              </select>
            </label>
            <label>
              研究状态
              <select aria-label="研究状态筛选" defaultValue="all">
                <option value="all">全部</option>
                <option value="researched">已研究</option>
                <option value="awaiting">待确认</option>
                <option value="unresearched">未研究</option>
              </select>
            </label>
            <button className="secondary-button" type="button">
              重置筛选
            </button>
          </section>
        ) : null}
        {healthOpen ? (
          <section aria-label="产品状态" className="popover health-popover">
            <p className="eyebrow">LAUNCH READINESS</p>
            <h2>产品状态</h2>
            <HealthRow label="本地优先" value="SQLite + 本地 Web，无交易通道。" />
            <HealthRow label="非荐股" value="只输出研究关注点和证据化情报。" />
            <HealthRow label="证据化" value="结论保留 evidence / source tier / basis 标记。" />
            <HealthRow label="门禁" value="前端测试与 production build 作为上线检查。" />
          </section>
        ) : null}
      </div>
    </header>
  );
}

function HealthRow({ label, value }: { label: string; value: string }): JSX.Element {
  return (
    <div className="health-row">
      <strong>{label}</strong>
      <span>{value}</span>
    </div>
  );
}
