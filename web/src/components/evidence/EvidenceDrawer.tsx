import { useEffect, useRef, type KeyboardEvent } from "react";

import { useEvidenceDrawer } from "../../context/evidence-drawer";
import { useEvidence } from "../../hooks/use-evidence";

export function EvidenceDrawer(): JSX.Element | null {
  const { close, ids, isOpen, knownEvidences, remember } = useEvidenceDrawer();
  const evidence = useEvidence(ids, knownEvidences);
  const drawerRef = useRef<HTMLElement | null>(null);
  const previousFocusRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    if (evidence.evidences.length > 0) {
      remember(evidence.evidences);
    }
  }, [evidence.evidences, remember]);

  useEffect(() => {
    if (!isOpen || typeof document === "undefined") {
      return undefined;
    }

    previousFocusRef.current =
      document.activeElement instanceof HTMLElement
        ? document.activeElement
        : null;
    drawerRef.current?.focus({ preventScroll: true });

    return () => {
      previousFocusRef.current?.focus({ preventScroll: true });
      previousFocusRef.current = null;
    };
  }, [isOpen]);

  if (!isOpen) {
    return null;
  }

  function handleKeyDown(event: KeyboardEvent<HTMLElement>): void {
    if (event.key === "Escape") {
      event.preventDefault();
      close();
    }
  }

  return (
    <div className="evidence-layer">
      <div
        aria-hidden="true"
        className="drawer-backdrop"
        onClick={close}
      />
      <aside
        aria-labelledby="evidence-drawer-title"
        aria-modal="true"
        className="evidence-panel"
        onKeyDown={handleKeyDown}
        ref={drawerRef}
        role="dialog"
        tabIndex={-1}
      >
        <header className="drawer-header">
          <div>
            <p className="eyebrow">EVIDENCE VIEWER</p>
            <h2 id="evidence-drawer-title">证据抽屉</h2>
          </div>
          <span className="count-pill" aria-hidden="true">
            {`${evidence.evidences.length} 条`}
          </span>
          <button aria-label="关闭" onClick={close} type="button">
            ×
          </button>
        </header>
        {evidence.isLoading ? <p className="empty-note">加载证据...</p> : null}
        {evidence.evidences.length === 0 &&
        !evidence.isLoading &&
        Object.keys(evidence.errors).length === 0 ? (
          <p className="empty-note">暂无可展示证据。</p>
        ) : null}
        <ul>
          {evidence.evidences.map((item) => (
            <li className="evidence-card" key={item.id}>
              <div>
                <span className="mono">{item.id}</span>
                <span className={tierClassName(item.source_tier)}>{`tier ${item.source_tier}`}</span>
              </div>
              <h3>{item.title ?? item.id}</h3>
              <dl className="evidence-meta">
                <div>
                  <dt>Source</dt>
                  <dd>{item.source}</dd>
                </div>
                <div>
                  <dt>Captured</dt>
                  <dd>
                    <time dateTime={item.captured_at}>{item.captured_at}</time>
                  </dd>
                </div>
                <div>
                  <dt>Published</dt>
                  <dd>{item.published_at ?? "unknown"}</dd>
                </div>
              </dl>
              <blockquote>{item.snippet}</blockquote>
              {item.url ? (
                <p>
                  <a href={item.url} rel="noreferrer" target="_blank">
                    打开来源
                  </a>
                </p>
              ) : null}
            </li>
          ))}
        </ul>
        {Object.entries(evidence.errors).map(([id, message]) => (
          <div className="compact-alert" key={id} role="alert">
            <span>{id}:{message}</span>
            <button
              aria-label={`重新加载证据 ${id}`}
              onClick={() => evidence.retry(id)}
              type="button"
            >
              重新加载
            </button>
          </div>
        ))}
      </aside>
    </div>
  );
}

function tierClassName(tier: number): string {
  if (tier === 1) return "tier-badge tier-1";
  if (tier === 2) return "tier-badge tier-2";
  return "tier-badge tier-3";
}
