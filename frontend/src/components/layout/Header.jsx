import { useMemo } from 'react';
import { useLocation } from 'react-router-dom';
import { useMutation, useQueryClient } from '@tanstack/react-query';

import { QUERY_KEYS, simulateDisruption } from '../../api/client';

const titles = {
  '/': 'Dashboard',
  '/map': 'Live Map',
  '/ports': 'Port Network',
  '/clients': 'Client Portfolio',
  '/shipments': 'Cargo Portfolio',
  '/alerts': 'Alerts',
  '/intelligence': 'Intelligence Center',
  '/simulation': 'Risk Scenario Studio',
  '/copilot': 'Intelligence Officer',
};

function Header() {
  const location = useLocation();
  const queryClient = useQueryClient();

  const title = useMemo(() => titles[location.pathname] || 'OculusIQ', [location.pathname]);

  const simulateMutation = useMutation({
    mutationFn: () => simulateDisruption({}),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.shipments });
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.stats });
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.disruptions });
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.alerts });
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.weatherRisks });
    },
  });

  return (
    <header className="flex items-center justify-between border-b border-slate-700 bg-slate-900 px-6 py-3">
      <div>
        <h1 className="text-lg font-semibold">{title}</h1>
        <p className="text-xs text-slate-400">Last updated: {new Date().toLocaleTimeString()}</p>
      </div>
      <button
        type="button"
        onClick={() => simulateMutation.mutate()}
        disabled={simulateMutation.isPending}
        className="rounded-md bg-danger px-4 py-2 text-sm font-medium text-white hover:bg-red-600 disabled:opacity-60"
      >
        {simulateMutation.isPending ? 'Planning...' : 'Scenario Planner'}
      </button>
    </header>
  );
}

export default Header;
