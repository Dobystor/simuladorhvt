import { NavLink, Outlet } from 'react-router-dom';
import ConnectionStatusBar from './ConnectionStatusBar';
import SessionHeader from './SessionHeader';

export default function AppShell() {
  return (
    <div className="app-shell">
      <div className="topbar">
        <div style={{ display: 'flex', alignItems: 'center', gap: 24 }}>
          <span className="header-brand">Haulage Simulator</span>
          <nav className="nav">
            <NavLink to="/summary" className={({ isActive }) => (isActive ? 'active' : '')}>
              Summary
            </NavLink>
          <NavLink to="/simulate" className={({ isActive }) => (isActive ? 'active' : '')}>
            Simulate
          </NavLink>
          <NavLink to="/history/log" className={({ isActive }) => (isActive ? 'active' : '')}>
            Event Log
          </NavLink>
            <NavLink to="/history/feed" className={({ isActive }) => (isActive ? 'active' : '')}>
              Live Feed
            </NavLink>
          </nav>
        </div>
        <div style={{ display: 'flex', gap: 16, alignItems: 'center' }}>
          <ConnectionStatusBar />
          <SessionHeader />
        </div>
      </div>
      <div className="content">
        <Outlet />
      </div>
    </div>
  );
}
