import { useEffect } from "react";

import { useEvidenceDrawer } from "../../context/evidence-drawer";
import { useEvidence } from "../../hooks/use-evidence";

export function EvidenceDrawer(): JSX.Element | null {
  const { close, ids, isOpen, knownEvidences, remember } = useEvidenceDrawer();
  const evidence = useEvidence(ids, knownEvidences);

  useEffect(() => {
    if (evidence.evidences.length > 0) {
      remember(evidence.evidences);
    }
  }, [evidence.evidences, remember]);

  if (!isOpen) {
    return null;
  }

  return (
    <aside aria-label="证据抽屉" role="dialog">
      <header>
        <h2>证据抽屉</h2>
        <button onClick={close} type="button">
          关闭
        </button>
      </header>
      {evidence.isLoading ? <p>加载证据...</p> : null}
      {evidence.evidences.length === 0 && !evidence.isLoading ? (
        <p>暂无可展示证据。</p>
      ) : null}
      <ul>
        {evidence.evidences.map((item) => (
          <li key={item.id}>
            <h3>{item.title ?? item.id}</h3>
            <p>{item.snippet}</p>
            <p>{`tier ${item.source_tier}`}</p>
            <time dateTime={item.captured_at}>{item.captured_at}</time>
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
        <p key={id} role="alert">
          {id}:{message}
        </p>
      ))}
    </aside>
  );
}
