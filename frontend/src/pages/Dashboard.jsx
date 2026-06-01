import { useEffect, useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import { AlertOctagon, AlertTriangle, Ship, TrendingUp, Zap, DollarSign, Brain, Activity, FlaskConical, Users, MessageCircle } from 'lucide-react';
import { Area, AreaChart, CartesianGrid, ComposedChart, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import gsap from 'gsap';

import {
  getDisruptions, getFeedHealth, getShipmentStats, getShipmentTimeline, getFinancialSummary,
  getAnomalies, getClientSlaOverview, getLatestIntelligenceScan, runIntelligenceScan, QUERY_KEYS,
} from '../api/client';
import SourceBadge from '../components/SourceBadge';

const severityConfig = {
  critical: { color: 'var(--status-critical)', label: 'Critical', icon: AlertOctagon },
  high: { color: 'var(--status-high)', label: 'High', icon: AlertTriangle },
  medium: { color: 'var(--status-medium)', label: 'Medium', icon: AlertTriangle },
};

function Dashboard() {
  const queryClient = useQueryClient();
  const { data: stats } = useQuery({ queryKey: QUERY_KEYS.stats, queryFn: getShipmentStats });
  const { data: disruptions } = useQuery({
    queryKey: QUERY_KEYS.disruptions,
    queryFn: getDisruptions,
    refetchInterval: 30000,
  });
  const { data: timeline } = useQuery({
    queryKey: QUERY_KEYS.timeline,
    queryFn: getShipmentTimeline,
    refetchInterval: 60000,
  });
  const { data: financial } = useQuery({
    queryKey: QUERY_KEYS.financial,
    queryFn: getFinancialSummary,
    refetchInterval: 60000,
  });
  const { data: anomalyData } = useQuery({
    queryKey: QUERY_KEYS.anomalies,
    queryFn: getAnomalies,
    refetchInterval: 120000,
  });
  const { data: feedHealth } = useQuery({
    queryKey: QUERY_KEYS.feeds,
    queryFn: getFeedHealth,
    refetchInterval: 60000,
  });
  const { data: slaOverview } = useQuery({
    queryKey: QUERY_KEYS.slaOverview,
    queryFn: getClientSlaOverview,
    refetchInterval: 60000,
  });
  const { data: latestScan } = useQuery({
    queryKey: QUERY_KEYS.latestScan,
    queryFn: getLatestIntelligenceScan,
    refetchInterval: 60000,
  });

  const scanMutation = useMutation({
    mutationFn: runIntelligenceScan,
    onSuccess: () => {
      [
        QUERY_KEYS.latestScan,
        QUERY_KEYS.anomalies,
        QUERY_KEYS.cascadeGraph,
        QUERY_KEYS.externalRisks,
        QUERY_KEYS.weatherRisks,
        QUERY_KEYS.slaOverview,
        QUERY_KEYS.disruptions,
      ].forEach((queryKey) => queryClient.invalidateQueries({ queryKey }));
    },
  });

  const totalShipments = stats?.data?.total ?? 0;
  const criticalHigh = (stats?.data?.critical ?? 0) + (stats?.data?.high ?? 0);
  const disruptionCount = disruptions?.meta?.total ?? 0;
  const onTimeRate = stats?.data?.on_time_rate ?? 0;
  const totalCargoValue = stats?.data?.total_cargo_value ?? 0;
  const anomalyCount = anomalyData?.data?.total_anomalies ?? 0;
  const cargoAtRisk = financial?.data?.cargo_at_risk_usd ?? 0;
  const clients = slaOverview?.data || [];
  const slaRiskClients = clients.filter((client) => ['critical', 'high'].includes(client.urgency)).length;
  const cargoUnderManagement = clients.reduce((sum, client) => sum + (client.active_cargo_value_usd || 0), 0) || totalCargoValue;

  const feeds = feedHealth?.data?.feeds || {};
  const scan = scanMutation.data?.data || latestScan?.data;

  const timelineData = timeline?.data || [];

  // Ticker items
  const tickerItems = useMemo(() => [
    `💰 Total cargo at risk: $${(cargoAtRisk / 1e6).toFixed(0)}M`,
    `⚡ Disruptions today: ${disruptionCount}`,
    `📦 Shipments at elevated risk: ${criticalHigh}`,
    `🔴 Anomalies detected: ${anomalyCount}`,
    `📊 Fleet on-time rate: ${onTimeRate.toFixed(1)}%`,
    `🌐 Total fleet value: $${(totalCargoValue / 1e6).toFixed(0)}M`,
  ], [cargoAtRisk, disruptionCount, criticalHigh, anomalyCount, onTimeRate, totalCargoValue]);

  return (
    <div className="space-y-5">
      {/* Financial Ticker */}
      <div className="overflow-hidden rounded-xl border border-[color:var(--glass-border)] bg-[rgba(0,0,0,0.3)]">
        <div className="ticker-wrapper">
          <div className="ticker-content">
            {[...tickerItems, ...tickerItems].map((item, i) => (
              <span key={i} className="ticker-item">{item}</span>
            ))}
          </div>
        </div>
      </div>

      {/* KPI Cards — Row 1 */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-4">
        <StatCard
          label="Clients Active"
          value={clients.length}
          accent="var(--ocean-teal)"
          icon={Users}
          sub={`${totalShipments} cargo movements monitored`}
        />
        <StatCard
          label="Shipments Monitored"
          value={totalShipments}
          accent="var(--ocean-teal)"
          icon={Ship}
          sub="Across all forwarder clients"
        />
        <StatCard
          label="SLA Clients at Risk"
          value={slaRiskClients}
          accent="var(--status-high)"
          icon={AlertTriangle}
          sub={`${criticalHigh} cargo movements at elevated risk`}
        />
        <StatCard
          label="Cargo Under Management"
          value={cargoUnderManagement / 1e6}
          accent="var(--status-critical)"
          icon={DollarSign}
          sub={`${disruptionCount} active disruptions watched`}
          suffix="M"
          decimals={1}
          stripe
        />
      </div>

      {/* Data feed status */}
      <div className="glass-panel rounded-xl p-4">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
          <div className="text-[10px] uppercase tracking-[0.2em] text-[color:var(--text-muted)]">Data Feed Health</div>
          <button type="button" className="btn-outline" disabled={scanMutation.isPending} onClick={() => scanMutation.mutate()}>
            <Brain size={13} /> {scanMutation.isPending ? 'Scanning...' : 'Scan Now'}
          </button>
        </div>
        <div className="flex flex-wrap items-center gap-4">
          <SourceBadge source="weather" updatedAt={feeds.weather?.last_updated} showUpdated />
          <SourceBadge source="gdelt" updatedAt={feeds.disruptions?.last_updated} showUpdated />
          <div className="text-[10px] text-[color:var(--text-muted)]">
            Shipments: {feeds.shipments?.csv_count || 0} imported · {feeds.shipments?.synthetic_count || 0} synthetic
          </div>
          <div className="text-[10px] text-[color:var(--text-muted)]">
            Gemini: {feeds.gemini?.key_configured ? 'configured' : 'not configured'}
          </div>
        </div>
        {scan ? (
          <div className="mt-3 grid grid-cols-2 gap-2 md:grid-cols-5">
            <MiniKPI label="Last Scan" value={new Date(scan.created_at).toLocaleTimeString()} icon={Activity} />
            <MiniKPI label="Scan Anomalies" value={scan.anomalies_count ?? 0} icon={Brain} />
            <MiniKPI label="SLA Clients" value={scan.sla_clients_at_risk ?? 0} icon={AlertTriangle} />
            <MiniKPI label="External Risks" value={scan.external_risks_count ?? 0} icon={Zap} />
            <MiniKPI label="Weather Checks" value={scan.weather_risks_count ?? 0} icon={Activity} />
          </div>
        ) : null}
      </div>

      {/* KPI Cards — Row 2 (Smaller) */}
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <MiniKPI label="On-Time vs SLA Target" value={`${onTimeRate.toFixed(1)}%`} icon={TrendingUp} />
        <MiniKPI label="Anomalies Detected" value={anomalyCount} icon={Brain} />
        <MiniKPI
          label="Avg Disruption Risk Index"
          value={totalShipments > 0 ? ((stats?.data?.critical * 90 + stats?.data?.high * 75 + stats?.data?.medium * 50 + stats?.data?.low * 20) / totalShipments).toFixed(1) : '0'}
          icon={Activity}
        />
        <MiniKPI label="Financial Exposure" value={`$${((financial?.data?.total_exposure_usd || 0) / 1e6).toFixed(1)}M`} icon={FlaskConical} />
      </div>

      {clients.length > 0 && (
        <section className="glass-panel rounded-xl p-5">
          <div className="mb-4 flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-[0.12em] text-[color:var(--ocean-teal)]">
              Clients Needing Attention
            </span>
            <span className="text-[10px] text-[color:var(--text-muted)]">{slaRiskClients} SLA risk clients</span>
          </div>
          <div className="space-y-2">
            {clients.slice(0, 5).map((client) => {
              const color = client.urgency === 'critical' ? '#EF4444' : client.urgency === 'high' ? '#F59E0B' : '#10B981';
              return (
                <div key={client.client_id} className="flex flex-wrap items-center justify-between gap-3 rounded-lg bg-[color:var(--bg-card)] p-4">
                  <div>
                    <div className="text-sm font-semibold text-[color:var(--text-primary)]">{client.client_name}</div>
                    <div className="text-xs text-[color:var(--text-muted)]">
                      {client.status} · {client.at_risk_shipments || 0} at-risk cargo movements · SLA gap {client.sla_gap ?? 0}%
                    </div>
                  </div>
                  <button type="button" className="btn-outline" style={{ borderColor: color, color }}>
                    <MessageCircle size={13} /> Notify Client
                  </button>
                </div>
              );
            })}
          </div>
        </section>
      )}

      {/* Risk Timeline Chart */}
      {timelineData.length > 0 && (
        <section className="glass-panel rounded-xl p-5">
          <div className="mb-4 flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-[0.12em] text-[color:var(--ocean-teal)]">
              24-Hour Disruption Risk Timeline
            </span>
            <span className="text-[10px] text-[color:var(--text-muted)]">{timelineData.length} data points</span>
          </div>
          <ResponsiveContainer width="100%" height={200}>
            <ComposedChart data={timelineData}>
              <defs>
                <linearGradient id="critGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#EF4444" stopOpacity={0.4} />
                  <stop offset="95%" stopColor="#EF4444" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="highGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#F59E0B" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#F59E0B" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="medGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#EAB308" stopOpacity={0.2} />
                  <stop offset="95%" stopColor="#EAB308" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
              <XAxis dataKey="hour" tick={{ fill: 'var(--text-muted)', fontSize: 10 }} />
              <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 10 }} />
              <Tooltip
                contentStyle={{
                  background: 'var(--bg-card)',
                  border: '1px solid var(--glass-border)',
                  borderRadius: '8px',
                  color: 'var(--text-primary)',
                  fontSize: '11px',
                }}
              />
              <Area type="monotone" dataKey="critical" stackId="1" stroke="#EF4444" fill="url(#critGrad)" />
              <Area type="monotone" dataKey="high" stackId="1" stroke="#F59E0B" fill="url(#highGrad)" />
              <Area type="monotone" dataKey="medium" stackId="1" stroke="#EAB308" fill="url(#medGrad)" />
              <Line type="monotone" dataKey="low" stroke="var(--ocean-teal)" strokeDasharray="5 5" dot={false} />
            </ComposedChart>
          </ResponsiveContainer>
        </section>
      )}

      {/* Live Disruption Feed */}
      <section className="glass-panel rounded-xl p-5">
        <div className="mb-4 flex items-center justify-between">
          <span className="text-xs font-semibold uppercase tracking-[0.12em] text-[color:var(--ocean-teal)]">
            Live Disruption Feed
          </span>
          <SourceBadge source="gdelt" updatedAt={feeds.disruptions?.last_updated} showUpdated />
        </div>
        <div className="max-h-96 space-y-2 overflow-auto pr-2">
          {(disruptions?.data || []).map((item, index) => {
            const severity = severityConfig[item.severity] || severityConfig.medium;
            const SeverityIcon = severity.icon;

            return (
              <motion.div
                key={item.id}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.3, delay: index * 0.04 }}
                className="flex items-center justify-between rounded-lg border-l-2 bg-[color:var(--bg-card)] p-4"
                style={{ borderColor: severity.color }}
              >
                <div>
                  <div className="flex items-center gap-2">
                    <div className="text-sm font-semibold text-[color:var(--text-primary)]">{item.title}</div>
                    <span
                      className="rounded-full px-1.5 py-0.5 text-[8px] uppercase font-bold"
                      style={{ background: `${severity.color}1A`, color: severity.color }}
                    >
                      {item.type}
                    </span>
                  </div>
                  <div className="text-xs text-[color:var(--text-muted)] mt-1">
                    {severity.label} severity · {item.affected_shipment_count} shipments affected
                    {item.estimated_financial_impact_usd > 0 && (
                      <span className="ml-2 text-[color:var(--status-high)]">
                        · ${(item.estimated_financial_impact_usd / 1e6).toFixed(1)}M at risk
                      </span>
                    )}
                  </div>
                  <div className="mt-2">
                    <SourceBadge source={item.source} updatedAt={item.last_updated || item.detected_at} showUpdated />
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <span
                    className="rounded-full border px-2 py-1 text-[10px] font-semibold uppercase tracking-[0.08em]"
                    style={{ color: severity.color, borderColor: severity.color, background: `${severity.color}1A` }}
                  >
                    {severity.label}
                  </span>
                  <SeverityIcon size={16} color={severity.color} />
                </div>
              </motion.div>
            );
          })}
        </div>
      </section>
    </div>
  );
}

function useCountUp(value, decimals = 0) {
  const [displayValue, setDisplayValue] = useState(value);

  useEffect(() => {
    const state = { val: 0 };
    const tween = gsap.to(state, {
      val: value,
      duration: 1.2,
      ease: 'power3.out',
      onUpdate: () => {
        const factor = 10 ** decimals;
        setDisplayValue(Math.round(state.val * factor) / factor);
      },
    });
    return () => tween.kill();
  }, [value, decimals]);

  return displayValue;
}

function StatCard({ label, value, accent, icon: Icon, sub, suffix = '', decimals = 0, stripe = false, sparkline = false }) {
  const displayValue = useCountUp(value, decimals);
  const glowStyle = useMemo(
    () => ({
      background: `radial-gradient(circle, ${accent} 0%, transparent 70%)`,
    }),
    [accent]
  );

  return (
    <div className="glass-panel relative overflow-hidden rounded-xl p-5">
      <div className="absolute right-0 top-0 h-20 w-20 opacity-20" style={glowStyle} />
      {stripe ? <div className="absolute inset-0 bg-[linear-gradient(135deg,transparent_0%,rgba(255,61,61,0.08)_50%,transparent_100%)]" /> : null}
      <div className="relative z-10 flex items-start justify-between">
        <div>
          <div className="text-[10px] uppercase tracking-[0.2em] text-[color:var(--text-muted)]">{label}</div>
          <div className="mt-2 text-4xl font-extrabold" style={{ color: accent }}>
            {displayValue}{suffix}
          </div>
          <div className="mt-1 text-xs text-[color:var(--text-muted)]">{sub}</div>
        </div>
        <Icon size={22} color={accent} style={{ opacity: 0.4 }} />
      </div>
      {sparkline ? (
        <div className="relative z-10 mt-3 flex items-end gap-1">
          {[6, 10, 7, 12, 9, 14].map((bar, index) => (
            <span
              key={`spark-${index}`}
              className="w-2 rounded"
              style={{ height: `${bar}px`, background: accent, opacity: 0.5 }}
            />
          ))}
        </div>
      ) : null}
    </div>
  );
}

function MiniKPI({ label, value, icon: Icon }) {
  return (
    <div className="glass-panel rounded-xl p-3 flex items-center gap-3">
      <Icon size={16} color="var(--ocean-teal)" style={{ opacity: 0.5 }} />
      <div>
        <div className="text-xs font-bold text-[color:var(--text-primary)]">{value}</div>
        <div className="text-[9px] text-[color:var(--text-muted)]">{label}</div>
      </div>
    </div>
  );
}

export default Dashboard;
