import { useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useMutation, useQuery } from '@tanstack/react-query';
import { motion, AnimatePresence } from 'framer-motion';
import { FlaskConical, AlertTriangle, Clock, DollarSign, Shield, Brain, Activity } from 'lucide-react';

import { getClientShipments, getClients, getShipments, getSimulationScenarios, runSimulation, getSimulationHistory, QUERY_KEYS } from '../api/client';

const severityColors = {
  critical: '#EF4444',
  high: '#F59E0B',
  medium: '#3B82F6',
};

const scenarioIcons = {
  suez_closure: '🚢',
  typhoon_south_china_sea: '🌊',
  shanghai_lockdown: '🏗️',
  rotterdam_strike: '⚡',
  global_fuel_shortage: '⛽',
  cyber_attack_logistics: '🔒',
};

const durationLabels = [12, 24, 48, 96, 168, 720];

function SimulationPage() {
  const [searchParams] = useSearchParams();
  const [selectedScenario, setSelectedScenario] = useState(null);
  const [duration, setDuration] = useState(48);
  const [result, setResult] = useState(null);
  const [targetType, setTargetType] = useState('all');
  const [targetRef, setTargetRef] = useState('');
  const clientId = searchParams.get('client');

  const { data: scenariosData } = useQuery({
    queryKey: QUERY_KEYS.scenarios,
    queryFn: getSimulationScenarios,
  });

  const { data: historyData } = useQuery({
    queryKey: QUERY_KEYS.simulationHistory,
    queryFn: getSimulationHistory,
  });
  const { data: clientShipmentsData } = useQuery({
    queryKey: ['simulation', 'client-shipments', clientId],
    queryFn: () => getClientShipments(clientId),
    enabled: Boolean(clientId),
  });
  const { data: clientsData } = useQuery({ queryKey: QUERY_KEYS.clients, queryFn: getClients });
  const { data: shipmentsData } = useQuery({
    queryKey: [...QUERY_KEYS.shipments, 'simulation-targets'],
    queryFn: () => getShipments({ page: 1, page_size: 500 }),
  });

  useEffect(() => {
    if (clientId) {
      setTargetType('client');
      setTargetRef(clientId);
    }
  }, [clientId]);

  const runMutation = useMutation({
    mutationFn: () => {
      const payload = { target_type: targetType };
      if (targetType === 'client') payload.client_id = targetRef;
      if (targetType === 'shipment') payload.shipment_id = targetRef;
      if (targetType === 'operator') payload.operator_name = targetRef;
      return runSimulation(selectedScenario, duration, payload);
    },
    onSuccess: (payload) => setResult(payload.data),
  });

  const scenarios = scenariosData?.data || [];
  const history = historyData?.data || [];
  const clientShipments = clientShipmentsData?.data || [];
  const clients = clientsData?.data || [];
  const shipments = shipmentsData?.data || [];
  const operators = useMemo(
    () => [...new Set(shipments.map((shipment) => shipment.operator_name || shipment.carrier).filter(Boolean))].sort(),
    [shipments]
  );

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3 mb-2">
        <FlaskConical size={24} color="var(--ocean-teal)" />
        <div>
          <h1 className="text-xl font-bold text-[color:var(--text-primary)]">Risk Scenario Studio</h1>
          <p className="text-xs text-[color:var(--text-muted)]">Scenario planning for client risk briefings before disruptions cascade</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
        {/* LEFT PANEL */}
        <div className="lg:col-span-2 space-y-4">
          {/* Scenario Cards */}
          <div className="glass-panel rounded-xl p-4">
            <div className="text-[10px] uppercase tracking-[0.2em] text-[color:var(--text-muted)] mb-3">Select Scenario</div>
            <div className="grid grid-cols-2 gap-2">
              {scenarios.map((s) => (
                <button
                  key={s.key}
                  type="button"
                  onClick={() => setSelectedScenario(s.key)}
                  className="text-left rounded-lg p-3 border transition-all duration-200"
                  style={{
                    background: selectedScenario === s.key ? 'rgba(0,200,224,0.1)' : 'var(--bg-card)',
                    borderColor: selectedScenario === s.key ? 'var(--ocean-teal)' : 'var(--glass-border)',
                  }}
                >
                  <div className="text-lg mb-1">{scenarioIcons[s.key] || '🌐'}</div>
                  <div className="text-xs font-semibold text-[color:var(--text-primary)] leading-tight">{s.name}</div>
                  <div className="mt-1 flex items-center gap-1">
                    <span
                      className="inline-block w-1.5 h-1.5 rounded-full"
                      style={{ background: severityColors[s.severity] || '#3B82F6' }}
                    />
                    <span className="text-[9px] uppercase tracking-[0.1em] text-[color:var(--text-muted)]">
                      {s.severity}
                    </span>
                  </div>
                  {s.historical_precedent && (
                    <div className="mt-1 text-[9px] text-[color:var(--text-muted)] opacity-60">
                      📋 {s.historical_precedent}
                    </div>
                  )}
                </button>
              ))}
            </div>
          </div>

          <div className="glass-panel rounded-xl p-4">
            <div className="text-[10px] uppercase tracking-[0.2em] text-[color:var(--text-muted)] mb-3">Target Planning</div>
            <div className="grid grid-cols-1 gap-3">
              <label className="space-y-1 text-xs text-[color:var(--text-muted)]">
                <span className="uppercase tracking-[0.12em]">Target type</span>
                <select
                  className="search-input w-full"
                  value={targetType}
                  onChange={(event) => {
                    setTargetType(event.target.value);
                    setTargetRef('');
                  }}
                >
                  <option value="all">All cargo</option>
                  <option value="client">Client</option>
                  <option value="shipment">Shipment</option>
                  <option value="operator">Operator</option>
                </select>
              </label>
              {targetType !== 'all' ? (
                <label className="space-y-1 text-xs text-[color:var(--text-muted)]">
                  <span className="uppercase tracking-[0.12em]">Target</span>
                  <select className="search-input w-full" value={targetRef} onChange={(event) => setTargetRef(event.target.value)}>
                    <option value="">Select target</option>
                    {targetType === 'client' && clients.map((client) => <option key={client.id} value={client.id}>{client.name}</option>)}
                    {targetType === 'shipment' && shipments.map((shipment) => <option key={shipment.id} value={shipment.id}>{shipment.id} - {shipment.client_name || shipment.carrier}</option>)}
                    {targetType === 'operator' && operators.map((operator) => <option key={operator} value={operator}>{operator}</option>)}
                  </select>
                </label>
              ) : null}
            </div>
          </div>

          {/* Duration Slider */}
          <div className="glass-panel rounded-xl p-4">
            <div className="text-[10px] uppercase tracking-[0.2em] text-[color:var(--text-muted)] mb-3">Duration</div>
            <div className="flex items-center gap-2 flex-wrap">
              {durationLabels.map((d) => (
                <button
                  key={d}
                  type="button"
                  onClick={() => setDuration(d)}
                  className="px-3 py-1.5 rounded-full text-xs font-semibold transition-all"
                  style={{
                    background: duration === d ? 'var(--ocean-teal)' : 'transparent',
                    color: duration === d ? '#000' : 'var(--text-secondary)',
                    border: `1px solid ${duration === d ? 'var(--ocean-teal)' : 'var(--glass-border)'}`,
                  }}
                >
                  {d < 72 ? `${d}h` : `${Math.round(d / 24)}d`}
                </button>
              ))}
            </div>
          </div>

          {/* RUN BUTTON */}
          <button
            type="button"
            disabled={!selectedScenario || runMutation.isPending || (targetType !== 'all' && !targetRef)}
            onClick={() => runMutation.mutate()}
            className="w-full py-4 rounded-xl text-sm font-bold uppercase tracking-[0.15em] transition-all duration-300"
            style={{
              background: selectedScenario ? 'linear-gradient(135deg, rgba(239,68,68,0.15), rgba(239,68,68,0.05))' : 'var(--bg-card)',
              border: selectedScenario ? '1.5px solid rgba(239,68,68,0.5)' : '1.5px solid var(--glass-border)',
              color: selectedScenario ? '#EF4444' : 'var(--text-muted)',
              cursor: selectedScenario && (targetType === 'all' || targetRef) ? 'pointer' : 'not-allowed',
              animation: selectedScenario && !runMutation.isPending ? 'pulse 2s infinite' : 'none',
            }}
          >
            {runMutation.isPending ? 'Running Scenario...' : 'Run Scenario Planner'}
          </button>

          {/* History */}
          {history.length > 0 && (
            <div className="glass-panel rounded-xl p-4">
              <div className="text-[10px] uppercase tracking-[0.2em] text-[color:var(--text-muted)] mb-3">Past Simulations</div>
              <div className="space-y-2 max-h-40 overflow-auto">
                {history.slice(0, 5).map((h) => (
                  <button
                    key={h.simulation_id}
                    type="button"
                    onClick={() => setResult(h)}
                    className="w-full text-left rounded-lg p-2 bg-[color:var(--bg-card)] border border-[color:var(--glass-border)] hover:border-[color:var(--ocean-teal)] transition-all"
                  >
                    <div className="text-xs font-semibold text-[color:var(--text-primary)]">{h.scenario_name}</div>
                    <div className="text-[10px] text-[color:var(--text-muted)]">
                      {h.affected_shipments} ships · ${((h.total_impact_usd || 0) / 1e6).toFixed(1)}M
                    </div>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* RIGHT PANEL */}
        <div className="lg:col-span-3">
          <AnimatePresence mode="wait">
            {!result ? (
              <motion.div
                key="empty"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="glass-panel rounded-xl p-8 flex flex-col items-center justify-center min-h-[500px]"
              >
                <div className="relative w-32 h-32 mb-6">
                  <div className="absolute inset-0 rounded-full border border-[color:var(--ocean-teal)] opacity-20 animate-ping" />
                  <div className="absolute inset-4 rounded-full border border-[color:var(--ocean-teal)] opacity-40 animate-ping" style={{ animationDelay: '0.5s' }} />
                  <div className="absolute inset-8 rounded-full border-2 border-[color:var(--ocean-teal)] opacity-60" />
                  <div className="absolute inset-0 flex items-center justify-center">
                    <FlaskConical size={32} color="var(--ocean-teal)" />
                  </div>
                </div>
                <h2 className="text-lg font-semibold text-[color:var(--text-primary)]">Select a Scenario</h2>
                <p className="text-xs text-[color:var(--text-muted)] mt-2 text-center max-w-xs">
                  Choose a disruption scenario, set duration, and run the simulation to see cascade impact analysis.
                </p>
              </motion.div>
            ) : (
              <motion.div
                key="result"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                className="space-y-4"
              >
                {/* Primary Impact */}
                <div className="glass-panel rounded-xl p-5">
                  <div className="flex items-center gap-2 mb-3">
                    <AlertTriangle size={16} color="#EF4444" />
                    <span className="text-[10px] uppercase tracking-[0.2em] text-[color:var(--status-critical)]">Primary Impact</span>
                  </div>
                  <div className="grid grid-cols-3 gap-4">
                    <div>
                      <div className="text-3xl font-extrabold text-[color:var(--status-critical)]">
                        {result.primary_impact?.shipments_directly_affected || result.affected_shipments || 0}
                      </div>
                      <div className="text-[10px] text-[color:var(--text-muted)]">Ships Affected</div>
                    </div>
                    <div>
                      <div className="text-3xl font-extrabold text-[color:var(--status-high)]">
                        {result.primary_impact?.total_teu_affected || '—'}
                      </div>
                      <div className="text-[10px] text-[color:var(--text-muted)]">TEU Impacted</div>
                    </div>
                    <div>
                      <div className="text-3xl font-extrabold text-[color:var(--ocean-teal)]">
                        {result.primary_impact?.avg_delay_hours || result.delay_hours_avg || 0}h
                      </div>
                      <div className="text-[10px] text-[color:var(--text-muted)]">Avg Delay</div>
                    </div>
                  </div>
                </div>

                {result.target_impact ? (
                  <div className="glass-panel rounded-xl p-5">
                    <div className="flex items-center gap-2 mb-3">
                      <Shield size={16} color="var(--ocean-teal)" />
                      <span className="text-[10px] uppercase tracking-[0.2em] text-[color:var(--ocean-teal)]">Target Impact</span>
                    </div>
                    <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
                      <InfoBlock label="Target" value={result.target_impact.target_ref} />
                      <InfoBlock label="Target Cargo" value={result.target_impact.target_shipments} />
                      <InfoBlock label="Affected" value={result.target_impact.affected_target_shipments} />
                      <InfoBlock label="SLA Impact" value={result.target_impact.sla_impact} />
                    </div>
                    <div className="mt-3 text-xs text-[color:var(--text-muted)]">
                      Target cargo at risk: ${(result.target_impact.target_cargo_value_at_risk_usd / 1e6).toFixed(2)}M
                    </div>
                  </div>
                ) : null}

                {/* Cascade */}
                <div className="glass-panel rounded-xl p-5">
                  <div className="flex items-center gap-2 mb-3">
                    <Activity size={16} color="var(--ocean-teal)" />
                    <span className="text-[10px] uppercase tracking-[0.2em] text-[color:var(--ocean-teal)]">Cascade Effect</span>
                  </div>
                  <div className="flex items-center justify-center gap-6 py-4">
                    {[
                      { label: 'Primary', val: result.primary_impact?.shipments_directly_affected || result.affected_shipments || 0, color: '#EF4444' },
                      { label: 'Secondary', val: result.cascade_impact?.secondary_shipments_affected || 0, color: '#F59E0B' },
                      { label: 'Tertiary', val: result.cascade_impact?.tertiary_ripple_count || 0, color: '#3B82F6' },
                    ].map((item, i) => (
                      <div key={item.label} className="flex items-center gap-3">
                        <div className="text-center">
                          <div
                            className="w-16 h-16 rounded-full flex items-center justify-center text-lg font-bold border-2"
                            style={{
                              borderColor: item.color,
                              color: item.color,
                              boxShadow: `0 0 20px ${item.color}33`,
                            }}
                          >
                            {item.val}
                          </div>
                          <div className="text-[9px] text-[color:var(--text-muted)] mt-1">{item.label}</div>
                        </div>
                        {i < 2 && <span className="text-[color:var(--text-muted)]">→</span>}
                      </div>
                    ))}
                  </div>
                </div>

                {/* Financial */}
                <div className="glass-panel rounded-xl p-5">
                  <div className="flex items-center gap-2 mb-3">
                    <DollarSign size={16} color="#10B981" />
                    <span className="text-[10px] uppercase tracking-[0.2em] text-[color:var(--status-ok)]">Financial Impact</span>
                  </div>
                  <div className="text-4xl font-extrabold text-[color:var(--status-critical)] mb-3">
                    {result.financial_impact?.total_display || `$${((result.total_impact_usd || 0) / 1e6).toFixed(1)}M`}
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    {result.financial_impact && Object.entries({
                      'Delay Cost': result.financial_impact.delay_cost_usd,
                      'Rerouting': result.financial_impact.rerouting_cost_usd,
                      'Insurance': result.financial_impact.insurance_spike_usd,
                      'Penalties': result.financial_impact.penalty_clauses_usd,
                    }).map(([label, val]) => (
                      <div key={label} className="flex justify-between text-xs">
                        <span className="text-[color:var(--text-muted)]">{label}</span>
                        <span className="text-[color:var(--text-secondary)] font-semibold">${((val || 0) / 1000).toFixed(0)}K</span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Strategic Options */}
                {result.strategic_options && (
                  <div className="glass-panel rounded-xl p-5">
                    <div className="flex items-center gap-2 mb-3">
                      <Shield size={16} color="var(--ocean-teal)" />
                      <span className="text-[10px] uppercase tracking-[0.2em] text-[color:var(--ocean-teal)]">Strategic Options</span>
                    </div>
                    <div className="space-y-2">
                      {result.strategic_options.map((opt, i) => (
                        <div key={i} className="flex items-start gap-2 p-2 rounded-lg bg-[color:var(--bg-card)]">
                          <span
                            className="shrink-0 mt-0.5 rounded-full px-1.5 py-0.5 text-[9px] uppercase font-bold"
                            style={{
                              background: opt.priority === 'urgent' ? 'rgba(239,68,68,0.15)' : opt.priority === 'high' ? 'rgba(245,158,11,0.15)' : 'rgba(59,130,246,0.15)',
                              color: opt.priority === 'urgent' ? '#EF4444' : opt.priority === 'high' ? '#F59E0B' : '#3B82F6',
                            }}
                          >
                            {opt.priority}
                          </span>
                          <div>
                            <div className="text-xs text-[color:var(--text-primary)]">{opt.action}</div>
                            <div className="text-[10px] text-[color:var(--text-muted)]">{opt.impact}</div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {clientId && clientShipments.length > 0 && (
                  <div className="glass-panel rounded-xl p-5">
                    <div className="flex items-center gap-2 mb-3">
                      <AlertTriangle size={16} color="#F59E0B" />
                      <span className="text-[10px] uppercase tracking-[0.2em] text-[color:var(--status-high)]">Client Impact Breakdown</span>
                    </div>
                    <div className="overflow-auto">
                      <table className="w-full text-left text-xs">
                        <thead className="table-head">
                          <tr>
                            <th className="px-3 py-2">Client</th>
                            <th className="px-3 py-2">Shipments Hit</th>
                            <th className="px-3 py-2">Cargo at Risk</th>
                            <th className="px-3 py-2">SLA Impact</th>
                            <th className="px-3 py-2">Action</th>
                          </tr>
                        </thead>
                        <tbody>
                          <tr className="table-row">
                            <td className="px-3 py-2">{clientShipments[0]?.client_name || clientId}</td>
                            <td className="px-3 py-2">{clientShipments.filter((s) => s.risk_score >= 60).length} of {clientShipments.length}</td>
                            <td className="px-3 py-2">${(clientShipments.reduce((sum, s) => sum + (s.risk_score >= 60 ? s.cargo_value_usd || 0 : 0), 0) / 1e6).toFixed(1)}M</td>
                            <td className="px-3 py-2">Review critical lanes</td>
                            <td className="px-3 py-2">Notify</td>
                          </tr>
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}

                {/* Gemini Analysis */}
                {result.gemini_analysis && (
                  <div className="glass-panel rounded-xl p-5">
                    <div className="flex items-center gap-2 mb-3">
                      <Brain size={16} color="#A855F7" />
                      <span className="text-[10px] uppercase tracking-[0.2em] text-purple-400">AI Strategic Analysis</span>
                    </div>
                    <p className="text-sm text-[color:var(--text-secondary)] leading-relaxed whitespace-pre-line">
                      {result.gemini_analysis}
                    </p>
                  </div>
                )}
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}

function InfoBlock({ label, value }) {
  return (
    <div className="rounded-lg bg-[color:var(--bg-card)] p-3">
      <div className="text-[9px] uppercase tracking-[0.12em] text-[color:var(--text-muted)]">{label}</div>
      <div className="mt-1 text-xs font-semibold text-[color:var(--text-primary)]">{value}</div>
    </div>
  );
}

export default SimulationPage;
