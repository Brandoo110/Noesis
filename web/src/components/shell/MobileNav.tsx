import { WORKSPACE_VIEWS, type WorkspaceView } from "./shell-types";

interface MobileNavProps {
  activeView: WorkspaceView;
  onViewChange: (view: WorkspaceView) => void;
}

export function MobileNav({
  activeView,
  onViewChange
}: MobileNavProps): JSX.Element {
  return (
    <nav aria-label="移动端导航" className="mobile-nav">
      {WORKSPACE_VIEWS.map((item) => (
        <button
          aria-label={item.label}
          aria-pressed={activeView === item.id}
          key={item.id}
          onClick={() => onViewChange(item.id)}
          type="button"
        >
          <svg aria-hidden="true" viewBox="0 0 24 24">
            <path d={item.iconPath} />
          </svg>
          {item.label}
        </button>
      ))}
    </nav>
  );
}
