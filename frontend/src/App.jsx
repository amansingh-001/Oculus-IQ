import { Navigate, Route, Routes } from 'react-router-dom';
import AppShell from './components/layout/AppShell';

import Dashboard from './pages/Dashboard';
import MapPage from './pages/MapPage';
import ShipmentsPage from './pages/ShipmentsPage';
import AlertsPage from './pages/AlertsPage';
import SimulationPage from './pages/SimulationPage';
import IntelligencePage from './pages/IntelligencePage';
import ClientsPage from './pages/ClientsPage';

function App() {
  return (
    <AppShell>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/map" element={<MapPage />} />
        <Route path="/ports" element={<Navigate to="/map" replace />} />
        <Route path="/clients" element={<ClientsPage />} />
        <Route path="/shipments" element={<ShipmentsPage />} />
        <Route path="/alerts" element={<AlertsPage />} />
        <Route path="/intelligence" element={<IntelligencePage />} />
        <Route path="/simulation" element={<SimulationPage />} />
        <Route path="/copilot" element={<Navigate to="/" replace />} />
        <Route path="/settings" element={<Navigate to="/" replace />} />
      </Routes>
    </AppShell>
  );
}

export default App;
