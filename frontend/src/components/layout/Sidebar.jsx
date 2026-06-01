import { Bell, Brain, ChevronLeft, ChevronRight, FlaskConical, Globe, LayoutDashboard, Package, Users } from 'lucide-react';
import { NavLink } from 'react-router-dom';
import clsx from 'clsx';

const navItems = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/map', label: 'Operations Map', icon: Globe },
  { to: '/clients', label: 'Clients', icon: Users },
  { to: '/shipments', label: 'Cargo Portfolio', icon: Package },
  { to: '/alerts', label: 'Alerts', icon: Bell },
  { to: '/intelligence', label: 'Intelligence', icon: Brain },
  { to: '/simulation', label: 'Risk Scenario Studio', icon: FlaskConical },
];

function Sidebar({ isCollapsed, isMobile, onToggle }) {
  const width = isMobile ? 200 : isCollapsed ? 60 : 200;
  const hiddenOnMobile = isMobile && isCollapsed;
  const ToggleIcon = isCollapsed ? ChevronRight : ChevronLeft;

  return (
    <aside
      className={clsx('sidebar', hiddenOnMobile && 'sidebar-hidden', isCollapsed && 'sidebar-collapsed')}
      style={{ width }}
    >
      <div className="sidebar-top">
        <div className="brand">
          <svg viewBox="0 0 40 40" className="logo-icon" aria-hidden="true">
            <circle cx="20" cy="20" r="18" stroke="#00C8E0" strokeWidth="0.5" fill="none" opacity="0.3" />
            <circle cx="20" cy="20" r="12" stroke="#00C8E0" strokeWidth="0.8" fill="none" opacity="0.5" />
            <circle cx="20" cy="20" r="6" stroke="#00C8E0" strokeWidth="1.2" fill="none" opacity="0.8" />
            <line
              x1="20" y1="20" x2="20" y2="2"
              stroke="#00C8E0" strokeWidth="1" opacity="0.9"
              className="radar-sweep"
            />
            <circle cx="20" cy="20" r="2" fill="#00C8E0" />
          </svg>
          {!isCollapsed ? (
            <div>
              <span className="brand-name">OculusIQ</span>
              <span className="brand-sub">Predictive Intelligence</span>
            </div>
          ) : null}
        </div>
        <button type="button" className="sidebar-toggle" onClick={onToggle} aria-label="Toggle sidebar">
          <ToggleIcon size={16} />
        </button>
      </div>

      <nav className="sidebar-nav">
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) => clsx('nav-item', isActive && 'nav-item-active')}
              title={isCollapsed ? item.label : undefined}
            >
              <Icon size={16} className="nav-item-icon" />
              {!isCollapsed ? <span className="nav-item-text">{item.label}</span> : null}
            </NavLink>
          );
        })}
      </nav>

      <div className="ai-status">
        <span className="pulse-dot" />
        {!isCollapsed ? <span>OculusIQ Intelligence Active</span> : null}
      </div>
    </aside>
  );
}

export default Sidebar;
