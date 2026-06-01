import { useState, useEffect, useRef } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import { Brain, Radar, Users, TrendingUp, AlertTriangle, Zap } from 'lucide-react';

import { getAnomalies, getCascadeGraph, getSuppliers, runIntelligenceScan, QUERY_KEYS } from '../api/client';

const severityColors = {
  critical: '#EF4444',
  high: '#F59E0B',
  medium: '#3B82F6',
  low: '#10B981',
};

function IntelligencePage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3 mb-2">
        <Brain size={24} color="var(--ocean-teal)" />
        <div>
          <h1 className="text-xl font-bold text-[color:var(--text-primary)]">Intelligence Center</h1>
          <p className="text-xs text-[color:var(--text-muted)]">Anomaly detection · Cascade risk analysis · Supplier resilience scoring</p>
        </div>
      </div>

      <AnomalyRadar />
      <CascadeGraphSection />
      <SupplierScorecardsSection />
    </div>
  );
}


/* ────── ANOMALY RADAR ────── */
function AnomalyRadar() {
  const queryClient = useQueryClient();
  const { data, refetch, isFetching } = useQuery({
    queryKey: QUERY_KEYS.anomalies,
    queryFn: getAnomalies,
  });
  const scanMutation = useMutation({
    mutationFn: runIntelligenceScan,
    onSuccess: () => {
      [
        QUERY_KEYS.latestScan,
        QUERY_KEYS.anomalies,
        QUERY_KEYS.cascadeGraph,
        QUERY_KEYS.externalRisks,
        QUERY_KEYS.slaOverview,
      ].forEach((queryKey) => queryClient.invalidateQueries({ queryKey }));
      refetch();
    },
  });
  const summary = data?.data || {};
  const anomalies = summary.anomalies || [];

  return (
    <div className="glass-panel rounded-xl p-5">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Radar size={16} color="var(--ocean-teal)" />
          <span className="text-[10px] uppercase tracking-[0.2em] text-[color:var(--ocean-teal)]">Anomaly Radar</span>
          <span className="ml-2 px-2 py-0.5 rounded-full bg-[rgba(239,68,68,0.15)] text-[10px] font-bold text-[color:var(--status-critical)]">
            {summary.total_anomalies || 0} detected
          </span>
        </div>
        <button
          onClick={() => scanMutation.mutate()}
          disabled={isFetching || scanMutation.isPending}
          className="px-3 py-1 rounded-lg border border-[color:var(--ocean-teal)] text-[10px] font-semibold uppercase tracking-[0.1em] text-[color:var(--ocean-teal)] hover:bg-[rgba(0,200,224,0.1)] transition-all"
        >
          {isFetching || scanMutation.isPending ? 'Scanning...' : 'Scan Now'}
        </button>
      </div>
      {scanMutation.data?.data ? (
        <div className="mb-3 rounded-lg border border-[color:var(--glass-border)] bg-[color:var(--bg-card)] p-3 text-xs text-[color:var(--text-secondary)]">
          Scan complete: {scanMutation.data.data.anomalies_count} anomalies, {scanMutation.data.data.external_risks_count} external risks, {scanMutation.data.data.weather_risks_count} weather checks flagged.
        </div>
      ) : null}

      {/* Type counters */}
      <div className="flex gap-4 mb-4">
        {[
          { label: 'Risk Spikes', val: summary.by_type?.risk_spikes || 0, color: '#EF4444' },
          { label: 'Silent Delays', val: summary.by_type?.silent_delays || 0, color: '#F59E0B' },
          { label: 'Carrier Failures', val: summary.by_type?.carrier_failures || 0, color: '#A855F7' },
        ].map((t) => (
          <div
            key={t.label}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg border"
            style={{ borderColor: `${t.color}33`, background: `${t.color}0D` }}
          >
            <span className="w-2 h-2 rounded-full" style={{ background: t.color }} />
            <span className="text-xs font-semibold" style={{ color: t.color }}>{t.val}</span>
            <span className="text-[10px] text-[color:var(--text-muted)]">{t.label}</span>
          </div>
        ))}
      </div>

      {/* Anomaly list */}
      <div className="max-h-64 overflow-auto space-y-2">
        {anomalies.map((a, i) => (
          <motion.div
            key={`${a.type}-${a.shipment_id || a.carrier}-${i}`}
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.05 }}
            className="flex items-start gap-3 p-3 rounded-lg border-l-2 bg-[color:var(--bg-card)]"
            style={{ borderColor: severityColors[a.severity] || '#3B82F6' }}
          >
            <AlertTriangle size={14} color={severityColors[a.severity]} className="shrink-0 mt-0.5" />
            <div>
              <div className="flex items-center gap-2">
                <span
                  className="text-[9px] uppercase font-bold px-1.5 py-0.5 rounded-full"
                  style={{
                    background: `${severityColors[a.severity]}1A`,
                    color: severityColors[a.severity],
                  }}
                >
                  {a.type.replace(/_/g, ' ')}
                </span>
                {a.shipment_id && (
                  <span className="text-[10px] font-mono text-[color:var(--ocean-teal)]">{a.shipment_id}</span>
                )}
                {a.carrier && (
                  <span className="text-[10px] text-[color:var(--text-muted)]">{a.carrier}</span>
                )}
              </div>
              <p className="text-xs text-[color:var(--text-secondary)] mt-1">{a.description}</p>
            </div>
          </motion.div>
        ))}
        {anomalies.length === 0 && (
          <div className="text-center py-6 text-xs text-[color:var(--text-muted)]">
            No anomalies detected — fleet operating within normal parameters
          </div>
        )}
      </div>
    </div>
  );
}


/* ────── CASCADE GRAPH (SVG) ────── */
function CascadeGraphSection() {
  const { data } = useQuery({
    queryKey: QUERY_KEYS.cascadeGraph,
    queryFn: getCascadeGraph,
  });
  const svgRef = useRef(null);
  const graph = data?.data || { nodes: [], edges: [] };

  useEffect(() => {
    if (!svgRef.current || graph.nodes.length === 0) return;

    const svg = svgRef.current;
    const width = svg.clientWidth || 800;
    const height = 400;

    // Simple force layout
    const nodes = graph.nodes.map((n, i) => ({
      ...n,
      x: 100 + (i % 10) * 70 + Math.random() * 30,
      y: 60 + Math.floor(i / 10) * 80 + Math.random() * 30,
    }));

    const nodeMap = {};
    nodes.forEach(n => { nodeMap[n.id] = n; });

    // Simple force iterations
    for (let iter = 0; iter < 50; iter++) {
      // Repulsion
      for (let i = 0; i < nodes.length; i++) {
        for (let j = i + 1; j < nodes.length; j++) {
          const dx = nodes[j].x - nodes[i].x;
          const dy = nodes[j].y - nodes[i].y;
          const dist = Math.sqrt(dx * dx + dy * dy) || 1;
          const force = 800 / (dist * dist);
          nodes[i].x -= (dx / dist) * force;
          nodes[i].y -= (dy / dist) * force;
          nodes[j].x += (dx / dist) * force;
          nodes[j].y += (dy / dist) * force;
        }
      }
      // Attraction
      graph.edges.forEach(e => {
        const src = nodeMap[e.source];
        const tgt = nodeMap[e.target];
        if (!src || !tgt) return;
        const dx = tgt.x - src.x;
        const dy = tgt.y - src.y;
        const dist = Math.sqrt(dx * dx + dy * dy) || 1;
        const force = dist * 0.01;
        src.x += (dx / dist) * force;
        src.y += (dy / dist) * force;
        tgt.x -= (dx / dist) * force;
        tgt.y -= (dy / dist) * force;
      });
      // Center constraint
      nodes.forEach(n => {
        n.x = Math.max(30, Math.min(width - 30, n.x));
        n.y = Math.max(30, Math.min(height - 30, n.y));
      });
    }

    // Render
    let svgContent = '';

    // Edges
    graph.edges.forEach(e => {
      const src = nodeMap[e.source];
      const tgt = nodeMap[e.target];
      if (!src || !tgt) return;
      const color = e.type === 'cascade' ? '#EF444466' : '#00C8E033';
      svgContent += `<line x1="${src.x}" y1="${src.y}" x2="${tgt.x}" y2="${tgt.y}" stroke="${color}" stroke-width="${e.type === 'cascade' ? 2 : 1}" />`;
    });

    // Nodes
    nodes.forEach(n => {
      const color = n.type === 'port' ? '#00C8E0' : severityColors[n.risk_level] || '#10B981';
      const r = n.type === 'port' ? 6 : Math.max(4, Math.min(12, (n.risk || 50) / 10));
      if (n.type === 'port') {
        svgContent += `<rect x="${n.x - r}" y="${n.y - r}" width="${r * 2}" height="${r * 2}" rx="2" fill="${color}" opacity="0.7" />`;
      } else {
        svgContent += `<circle cx="${n.x}" cy="${n.y}" r="${r}" fill="${color}" opacity="0.8" />`;
      }
      if (r > 7) {
        svgContent += `<text x="${n.x}" y="${n.y - r - 4}" fill="var(--text-muted)" font-size="8" text-anchor="middle">${n.label?.substring(0, 12) || ''}</text>`;
      }
    });

    svg.innerHTML = svgContent;
  }, [graph]);

  return (
    <div className="glass-panel rounded-xl p-5">
      <div className="flex items-center gap-2 mb-4">
        <Zap size={16} color="var(--ocean-teal)" />
        <span className="text-[10px] uppercase tracking-[0.2em] text-[color:var(--ocean-teal)]">Cascade Risk Network</span>
        <span className="ml-2 text-[10px] text-[color:var(--text-muted)]">
          {graph.nodes.length} nodes · {graph.edges.length} connections
        </span>
      </div>
      <div className="flex gap-3 mb-3">
        <span className="flex items-center gap-1 text-[10px] text-[color:var(--text-muted)]">
          <span className="w-2 h-2 rounded-full bg-[#EF4444]" /> High Risk
        </span>
        <span className="flex items-center gap-1 text-[10px] text-[color:var(--text-muted)]">
          <span className="w-2 h-2 rounded-full bg-[#F59E0B]" /> Medium Risk
        </span>
        <span className="flex items-center gap-1 text-[10px] text-[color:var(--text-muted)]">
          <span className="w-2 h-2 rounded bg-[#00C8E0]" /> Port Node
        </span>
      </div>
      <svg
        ref={svgRef}
        className="w-full rounded-lg"
        style={{ height: 400, background: 'rgba(0,0,0,0.2)' }}
      />
    </div>
  );
}


/* ────── SUPPLIER SCORECARDS ────── */
function SupplierScorecardsSection() {
  const { data } = useQuery({
    queryKey: QUERY_KEYS.suppliers,
    queryFn: getSuppliers,
  });
  const suppliers = data?.data || [];

  const countryFlags = {
    'Taiwan': '🇹🇼', 'South Korea': '🇰🇷', 'China': '🇨🇳', 'India': '🇮🇳',
    'Switzerland': '🇨🇭', 'Germany': '🇩🇪', 'Japan': '🇯🇵', 'USA': '🇺🇸',
    'Hong Kong': '🇭🇰',
  };

  return (
    <div className="glass-panel rounded-xl p-5">
      <div className="flex items-center gap-2 mb-4">
        <Users size={16} color="var(--ocean-teal)" />
        <span className="text-[10px] uppercase tracking-[0.2em] text-[color:var(--ocean-teal)]">Supplier Resilience</span>
        <span className="ml-2 text-[10px] text-[color:var(--text-muted)]">{suppliers.length} suppliers</span>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
        {suppliers.map((s) => {
          const scoreColor = s.risk_score >= 70 ? '#10B981' : s.risk_score >= 40 ? '#F59E0B' : '#EF4444';
          return (
            <motion.div
              key={s.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="rounded-xl p-4 border bg-[color:var(--bg-card)]"
              style={{ borderColor: `${scoreColor}33` }}
            >
              <div className="flex items-start justify-between mb-3">
                <div>
                  <div className="text-sm font-semibold text-[color:var(--text-primary)]">
                    {countryFlags[s.country] || '🌐'} {s.name}
                  </div>
                  <div className="text-[10px] text-[color:var(--text-muted)]">{s.industry} · {s.country}</div>
                </div>
                {/* Circular score */}
                <div className="relative w-12 h-12 flex items-center justify-center">
                  <svg viewBox="0 0 36 36" className="w-full h-full -rotate-90">
                    <circle cx="18" cy="18" r="15.9" fill="none" stroke="rgba(255,255,255,0.05)" strokeWidth="3" />
                    <circle
                      cx="18" cy="18" r="15.9"
                      fill="none"
                      stroke={scoreColor}
                      strokeWidth="3"
                      strokeDasharray={`${s.risk_score} 100`}
                      strokeLinecap="round"
                    />
                  </svg>
                  <span className="absolute text-xs font-bold" style={{ color: scoreColor }}>
                    {Math.round(s.risk_score)}
                  </span>
                </div>
              </div>
              <div className="grid grid-cols-3 gap-2 text-center">
                <div>
                  <div className="text-xs font-semibold text-[color:var(--text-primary)]">{s.on_time_rate}%</div>
                  <div className="text-[9px] text-[color:var(--text-muted)]">On-time</div>
                </div>
                <div>
                  <div className="text-xs font-semibold text-[color:var(--text-primary)]">{s.active_shipments_count}</div>
                  <div className="text-[9px] text-[color:var(--text-muted)]">Shipments</div>
                </div>
                <div>
                  <div className="text-xs font-semibold" style={{ color: s.geopolitical_risk >= 60 ? '#EF4444' : s.geopolitical_risk >= 40 ? '#F59E0B' : '#10B981' }}>
                    {s.geopolitical_risk}
                  </div>
                  <div className="text-[9px] text-[color:var(--text-muted)]">Geo Risk</div>
                </div>
              </div>
              {(s.alternative_supplier_ids || []).length > 0 && (
                <div className="mt-2 text-[9px] text-[color:var(--text-muted)]">
                  🔄 {s.alternative_supplier_ids.length} alternative{s.alternative_supplier_ids.length > 1 ? 's' : ''} available
                </div>
              )}
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}

export default IntelligencePage;
