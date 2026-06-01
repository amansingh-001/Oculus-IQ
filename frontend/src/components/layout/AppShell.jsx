import { Suspense, lazy, useEffect, useState } from 'react';

import TopBar from './TopBar';
import Sidebar from './Sidebar';

const OceanCanvas3D = lazy(() => import('../3d/OceanCanvas3D'));

const SIDEBAR_EXPANDED = 200;
const SIDEBAR_COLLAPSED = 60;
const TOPBAR_HEIGHT = 56;

function AppShell({ children }) {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    const media = window.matchMedia('(max-width: 1024px)');
    const handleChange = () => setIsMobile(media.matches);
    handleChange();

    if (media.addEventListener) {
      media.addEventListener('change', handleChange);
    } else {
      media.addListener(handleChange);
    }

    return () => {
      if (media.removeEventListener) {
        media.removeEventListener('change', handleChange);
      } else {
        media.removeListener(handleChange);
      }
    };
  }, []);

  useEffect(() => {
    if (isMobile) {
      setIsCollapsed(true);
      return;
    }

    const stored = window.localStorage.getItem('sidebar-collapsed');
    setIsCollapsed(stored === 'true');
  }, [isMobile]);

  const handleToggle = () => {
    setIsCollapsed((prev) => {
      const next = !prev;
      if (!isMobile) {
        window.localStorage.setItem('sidebar-collapsed', String(next));
      }
      return next;
    });
  };

  const sidebarWidth = isMobile ? 0 : isCollapsed ? SIDEBAR_COLLAPSED : SIDEBAR_EXPANDED;

  return (
    <div className="relative min-h-screen text-[color:var(--text-primary)]">
      <Suspense fallback={null}>
        <OceanCanvas3D />
      </Suspense>

      <Sidebar isCollapsed={isCollapsed} isMobile={isMobile} onToggle={handleToggle} />

      {isMobile && !isCollapsed ? (
        <button
          type="button"
          className="fixed inset-0 z-10 bg-black/40"
          onClick={() => setIsCollapsed(true)}
          aria-label="Close sidebar"
        />
      ) : null}

      <TopBar sidebarWidth={sidebarWidth} height={TOPBAR_HEIGHT} />

      <main
        className="relative z-10 min-h-screen px-6 py-6"
        style={{
          paddingLeft: sidebarWidth,
          paddingTop: TOPBAR_HEIGHT,
        }}
      >
        {children}
      </main>
    </div>
  );
}

export default AppShell;
