import type { PropsWithChildren, ReactNode } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { humanizeState, stateTone } from "./utils";

export function BrandMark({ compact = false }: { compact?: boolean }) {
  return (
    <div className={`brand ${compact ? "brand--compact" : ""}`} aria-label="CER Test Portal">
      <span className="brand__mark" aria-hidden="true">C</span>
      {!compact && <span><strong>CER</strong><small>TEST PORTAL</small></span>}
    </div>
  );
}

const iconPaths: Record<string, ReactNode> = {
  stations: <><path d="M4 11.5 12 4l8 7.5"/><path d="M6.5 10.5V20h11v-9.5M10 20v-6h4v6"/></>,
  devices: <><rect x="5" y="3" width="14" height="18" rx="3"/><path d="M9 7h6M9 11h6M9 15h3"/></>,
  alarms: <><path d="M6 9a6 6 0 0 1 12 0v5l2 3H4l2-3Z"/><path d="M10 21h4"/></>,
  search: <><circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 4 4"/></>,
  refresh: <><path d="M20 7v5h-5"/><path d="M18.3 16a8 8 0 1 1 .7-9l1 5"/></>,
  controls: <><path d="M5 12h14M8 7h8M9 17h6"/><circle cx="8" cy="12" r="2"/></>,
  close: <><path d="m6 6 12 12M18 6 6 18"/></>,
  arrow: <><path d="m9 18 6-6-6-6"/></>,
  bolt: <><path d="m13 2-7 11h6l-1 9 7-12h-6Z"/></>,
};

export function Icon({ name, size = 20 }: { name: string; size?: number }) {
  return (
    <svg className="icon" width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      {iconPaths[name] ?? iconPaths.bolt}
    </svg>
  );
}

export function AppShell() {
  const navigate = useNavigate();
  const logout = () => {
    localStorage.removeItem("cer-session");
    navigate("/login");
  };
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <BrandMark compact />
        <nav aria-label="Main navigation">
          <NavLink to="/stations" title="Station List" data-testid="nav-stations"><Icon name="stations"/><span>Stations</span></NavLink>
          <NavLink to="/devices" title="Device List" data-testid="nav-devices"><Icon name="devices"/><span>Devices</span></NavLink>
          <NavLink to="/alarms" title="Alarm Center" data-testid="nav-alarms"><Icon name="alarms"/><span>Alarms</span></NavLink>
        </nav>
        <button className="sidebar__logout" onClick={logout} aria-label="Log out">↪</button>
      </aside>
      <div className="app-frame">
        <header className="topbar">
          <span className="offline-chip"><i /> Offline simulator</span>
          <div className="topbar__right"><span>Research workspace</span><button onClick={logout} className="avatar" aria-label="Account menu">CR</button></div>
        </header>
        <main><Outlet /></main>
      </div>
    </div>
  );
}

export function PageHeader({ eyebrow, title, actions }: { eyebrow?: string; title: string; actions?: ReactNode }) {
  return <div className="page-header"><div>{eyebrow && <p>{eyebrow}</p>}<h1>{title}</h1></div>{actions}</div>;
}

export function StatusPill({ status, testId }: { status: string; testId?: string }) {
  return <span className={`status status--${stateTone(status)}`} data-testid={testId}><i />{humanizeState(status)}</span>;
}

export function Panel({ children, className = "" }: PropsWithChildren<{ className?: string }>) {
  return <section className={`panel ${className}`}>{children}</section>;
}

export function SearchBox({ value, onChange, placeholder, testId }: { value: string; onChange: (value: string) => void; placeholder: string; testId?: string }) {
  return <label className="search-box"><Icon name="search" size={17}/><input value={value} onChange={(event) => onChange(event.target.value)} placeholder={placeholder} data-testid={testId}/></label>;
}

export function RefreshButton({ onClick, loading }: { onClick: () => void; loading?: boolean }) {
  return <button className="icon-button" onClick={onClick} aria-label="Refresh" disabled={loading}><Icon name="refresh"/></button>;
}

export function LoadingState() {
  return <div className="loading" role="status"><span /><span /><span /> Loading synthetic data</div>;
}

export function ErrorBanner({ message }: { message: string }) {
  return <div className="error-banner" role="alert">{message}</div>;
}

export function EmptyState({ title, detail }: { title: string; detail: string }) {
  return <div className="empty-state"><div className="empty-state__icon">◇</div><strong>{title}</strong><p>{detail}</p></div>;
}

