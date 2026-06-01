import { useMemo, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { QUERY_KEYS, getClients, getShipments, simulateDisruption } from '../../api/client';

const titles = {
  '/': 'Dashboard',
  '/map': 'Operations Command Map',
  '/clients': 'Client Portfolio',
  '/shipments': 'Cargo Portfolio',
  '/alerts': 'Alerts',
  '/intelligence': 'Intelligence Center',
  '/simulation': 'Risk Scenario Studio',
};

const regionPresets = {
  suez: { label: 'Suez / Red Sea', region: 'Suez / Red Sea', lat: 30.4, lon: 32.3, radius_km: 1100 },
  south_china_sea: { label: 'South China Sea', region: 'South China Sea', lat: 18, lon: 115, radius_km: 900 },
  rotterdam: { label: 'Rotterdam / North Sea', region: 'Rotterdam / North Sea', lat: 51.9, lon: 4.5, radius_km: 500 },
  panama: { label: 'Panama Canal', region: 'Panama Canal', lat: 9.08, lon: -79.68, radius_km: 650 },
  manual: { label: 'Manual coordinates', region: 'Manual coordinates' },
};

const defaultForm = {
  type: 'weather',
  severity: 'high',
  preset: 'south_china_sea',
  region: 'South China Sea',
  lat: 18,
  lon: 115,
  radius_km: 900,
  duration_hours: 48,
  target_type: 'all',
  target_ref: '',
};

function TopBar({ sidebarWidth, height }) {
  const location = useLocation();
  const queryClient = useQueryClient();
  const [plannerOpen, setPlannerOpen] = useState(false);
  const [form, setForm] = useState(defaultForm);
  const [result, setResult] = useState(null);

  const title = useMemo(() => titles[location.pathname] || 'OculusIQ', [location.pathname]);

  const { data: clientsData } = useQuery({
    queryKey: QUERY_KEYS.clients,
    queryFn: getClients,
    enabled: plannerOpen,
  });
  const { data: shipmentsData } = useQuery({
    queryKey: [...QUERY_KEYS.shipments, 'planner'],
    queryFn: () => getShipments({ page: 1, page_size: 500 }),
    enabled: plannerOpen,
  });

  const clients = clientsData?.data || [];
  const shipments = shipmentsData?.data || [];
  const operators = useMemo(
    () => [...new Set(shipments.map((shipment) => shipment.operator_name || shipment.carrier).filter(Boolean))].sort(),
    [shipments]
  );

  const simulateMutation = useMutation({
    mutationFn: () => {
      const target = {};
      if (form.target_type === 'client') target.client_id = form.target_ref;
      if (form.target_type === 'shipment') target.shipment_id = form.target_ref;
      if (form.target_type === 'operator') target.operator_name = form.target_ref;
      return simulateDisruption({
        type: form.type,
        severity: form.severity,
        region: form.region,
        lat: Number(form.lat),
        lon: Number(form.lon),
        radius_km: Number(form.radius_km),
        duration_hours: Number(form.duration_hours),
        target_type: form.target_type,
        ...target,
      });
    },
    onSuccess: (payload) => {
      setResult(payload.data);
      [
        QUERY_KEYS.shipments,
        QUERY_KEYS.stats,
        QUERY_KEYS.disruptions,
        QUERY_KEYS.alerts,
        QUERY_KEYS.clients,
        QUERY_KEYS.slaOverview,
        QUERY_KEYS.financial,
        QUERY_KEYS.weatherRisks,
      ].forEach((queryKey) => queryClient.invalidateQueries({ queryKey }));
    },
  });

  const updatePreset = (presetKey) => {
    const preset = regionPresets[presetKey];
    setForm((prev) => ({
      ...prev,
      preset: presetKey,
      region: preset.region,
      lat: preset.lat ?? prev.lat,
      lon: preset.lon ?? prev.lon,
      radius_km: preset.radius_km ?? prev.radius_km,
    }));
  };

  return (
    <>
      <header
        className="topbar"
        style={{
          left: sidebarWidth,
          height,
        }}
      >
        <div>
          <h1 className="page-title">{title}</h1>
          <span className="last-updated">Last updated: {new Date().toLocaleTimeString()}</span>
        </div>
        <button type="button" onClick={() => setPlannerOpen(true)} className="simulate-btn">
          Scenario Planner
        </button>
      </header>

      {plannerOpen ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
          <div className="glass-panel max-h-[92vh] w-full max-w-3xl overflow-auto rounded-xl p-5">
            <div className="mb-4 flex items-center justify-between gap-3">
              <div>
                <div className="text-lg font-bold text-[color:var(--text-primary)]">Scenario Planner</div>
                <div className="text-xs text-[color:var(--text-muted)]">Create a disruption scenario and push the impact through cargo, clients, alerts, and SLA views.</div>
              </div>
              <button type="button" className="btn-outline" onClick={() => setPlannerOpen(false)}>Close</button>
            </div>

            <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
              <Field label="Type">
                <select className="search-input w-full" value={form.type} onChange={(event) => setForm((prev) => ({ ...prev, type: event.target.value }))}>
                  {['weather', 'congestion', 'geopolitical', 'operational'].map((type) => <option key={type} value={type}>{type}</option>)}
                </select>
              </Field>
              <Field label="Severity">
                <select className="search-input w-full" value={form.severity} onChange={(event) => setForm((prev) => ({ ...prev, severity: event.target.value }))}>
                  {['medium', 'high', 'critical'].map((severity) => <option key={severity} value={severity}>{severity}</option>)}
                </select>
              </Field>
              <Field label="Region">
                <select className="search-input w-full" value={form.preset} onChange={(event) => updatePreset(event.target.value)}>
                  {Object.entries(regionPresets).map(([key, preset]) => <option key={key} value={key}>{preset.label}</option>)}
                </select>
              </Field>
              <Field label="Duration">
                <input className="search-input w-full" type="number" min="1" value={form.duration_hours} onChange={(event) => setForm((prev) => ({ ...prev, duration_hours: event.target.value }))} />
              </Field>
              <Field label="Latitude">
                <input className="search-input w-full" type="number" step="0.01" value={form.lat} disabled={form.preset !== 'manual'} onChange={(event) => setForm((prev) => ({ ...prev, lat: event.target.value }))} />
              </Field>
              <Field label="Longitude">
                <input className="search-input w-full" type="number" step="0.01" value={form.lon} disabled={form.preset !== 'manual'} onChange={(event) => setForm((prev) => ({ ...prev, lon: event.target.value }))} />
              </Field>
              <Field label="Radius KM">
                <input className="search-input w-full" type="number" min="10" value={form.radius_km} onChange={(event) => setForm((prev) => ({ ...prev, radius_km: event.target.value }))} />
              </Field>
              <Field label="Target">
                <select className="search-input w-full" value={form.target_type} onChange={(event) => setForm((prev) => ({ ...prev, target_type: event.target.value, target_ref: '' }))}>
                  <option value="all">All cargo</option>
                  <option value="client">Client</option>
                  <option value="shipment">Shipment</option>
                  <option value="operator">Operator</option>
                </select>
              </Field>
              {form.target_type !== 'all' ? (
                <Field label="Target selection">
                  <select className="search-input w-full" value={form.target_ref} onChange={(event) => setForm((prev) => ({ ...prev, target_ref: event.target.value }))}>
                    <option value="">Select...</option>
                    {form.target_type === 'client' && clients.map((client) => <option key={client.id} value={client.id}>{client.name}</option>)}
                    {form.target_type === 'shipment' && shipments.map((shipment) => <option key={shipment.id} value={shipment.id}>{shipment.id} - {shipment.client_name || shipment.carrier}</option>)}
                    {form.target_type === 'operator' && operators.map((operator) => <option key={operator} value={operator}>{operator}</option>)}
                  </select>
                </Field>
              ) : null}
            </div>

            {result ? (
              <div className="mt-4 rounded-lg border border-[color:var(--glass-border)] bg-[color:var(--bg-card)] p-3 text-xs text-[color:var(--text-secondary)]">
                Scenario created: {result.disruption_id} affected {result.affected_shipments} cargo movement(s) and created {result.alerts_created} alert(s).
              </div>
            ) : null}
            {simulateMutation.error ? (
              <div className="mt-4 rounded-lg border border-red-500/40 bg-red-500/10 p-3 text-xs text-red-300">
                {simulateMutation.error.message}
              </div>
            ) : null}

            <div className="mt-5 flex justify-end gap-2">
              <button type="button" className="btn-outline" onClick={() => setPlannerOpen(false)}>Cancel</button>
              <button
                type="button"
                className="btn-solid"
                disabled={simulateMutation.isPending || (form.target_type !== 'all' && !form.target_ref)}
                onClick={() => simulateMutation.mutate()}
              >
                {simulateMutation.isPending ? 'Planning...' : 'Run Scenario Planner'}
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </>
  );
}

function Field({ label, children }) {
  return (
    <label className="space-y-1 text-xs text-[color:var(--text-muted)]">
      <span className="uppercase tracking-[0.14em]">{label}</span>
      {children}
    </label>
  );
}

export default TopBar;
