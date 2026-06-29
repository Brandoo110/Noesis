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
    <div className="drawer-layer">
      <div
        aria-hidden="true"
        className="drawer-backdrop"
        onClick={close}
      />
      <aside
        aria-labelledby="evidence-drawer-title"
        aria-modal="true"
        className="evidence-drawer"
        onKeyDown={handleKeyDown}
        ref={drawerRef}
        role="dialog"
        tabIndex={-1}
      >
        <header className="drawer-header">
          <span className="drawer-symbol" aria-hidden="true">E</span>
          <div>
            <p className="eyebrow">Evidence Viewer</p>
            <h2 id="evidence-drawer-title">证据抽屉</h2>
          </div>
          <button aria-label="关闭" onClick={close} type="button">
            Close
          </button>
        </header>
        {evidence.isLoading ? <p className="drawer-loading">加载证据...</p> : null}
        {evidence.evidences.length === 0 &&
        !evidence.isLoading &&
        Object.keys(evidence.errors).length === 0 ? (
          <p className="empty-note">暂无可展示证据。</p>
        ) : null}
        <ul className="evidence-list">
          {evidence.evidences.map((item) => (
            <li className="evidence-card" key={item.id}>
              <div className="evidence-card-header">
                <span className="evidence-id">{item.id}</span>
                <span className="evidence-tier">{`tier ${item.source_tier}`}</span>
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
              <p className="evidence-snippet">{item.snippet}</p>
              {item.url ? (
                <p>
                  <a className="source-link" href={item.url} rel="noreferrer" target="_blank">
                    打开来源
                  </a>
                </p>
              ) : null}
            </li>
          ))}
        </ul>
        {Object.entries(evidence.errors).map(([id, message]) => (
          <div className="alert evidence-error" key={id} role="alert">
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
