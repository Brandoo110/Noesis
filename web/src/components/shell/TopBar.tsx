interface TopBarProps {
  subtitle: string;
  title: string;
}

export function TopBar({ subtitle, title }: TopBarProps): JSX.Element {
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
      <div className="topbar-actions">
        <button
          aria-expanded="false"
          className="secondary-button health-button"
          type="button"
        >
          <i />Health
        </button>
      </div>
    </header>
  );
}
