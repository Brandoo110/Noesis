import { WORKSPACE_VIEWS, type WorkspaceView } from "./shell-types";

interface SideRailProps {
  activeView: WorkspaceView;
  onViewChange: (view: WorkspaceView) => void;
}

export function SideRail({
  activeView,
  onViewChange
}: SideRailProps): JSX.Element {
  return (
    <nav aria-label="主导航" className="rail">
      <div className="rail-logo">N</div>
      {WORKSPACE_VIEWS.map((item) => (
        <button
          aria-label={item.label}
          aria-pressed={activeView === item.id}
          className="rail-button"
          key={item.id}
          onClick={() => onViewChange(item.id)}
          title={item.label}
          type="button"
        >
          <svg aria-hidden="true" viewBox="0 0 24 24">
            <path d={item.iconPath} />
          </svg>
        </button>
      ))}
      <div className="rail-spacer" />
      <div aria-label="本地用户" className="rail-user">JL</div>
    </nav>
  );
}
