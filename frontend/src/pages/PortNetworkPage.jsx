import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { MapContainer, TileLayer, CircleMarker, Polyline, Popup } from 'react-leaflet';
import { Anchor, Activity } from 'lucide-react';

import { getPortCongestion, getChokepoints, getRouteNetwork, QUERY_KEYS } from '../api/client';

function congestionColor(score) {
  if (score > 80) return '#EF4444';
  if (score > 60) return '#F59E0B';
  if (score > 40) return '#EAB308';
  return '#10B981';
}

function portRadius(capacityTeu) {
  if (!capacityTeu) return 5;
  if (capacityTeu > 20000000) return 12;
  if (capacityTeu > 10000000) return 10;
  if (capacityTeu > 5000000) return 8;
  return 6;
}

function PortNetworkPage() {
  const [selectedPort, setSelectedPort] = useState(null);

  const { data: congestionData } = useQuery({
    queryKey: QUERY_KEYS.portCongestion,
    queryFn: getPortCongestion,
    refetchInterval: 60000,
  });

  const { data: chokepointData } = useQuery({
    queryKey: QUERY_KEYS.chokepoints,
    queryFn: getChokepoints,
  });

  const { data: networkData } = useQuery({
    queryKey: QUERY_KEYS.portNetwork,
    queryFn: getRouteNetwork,
  });

  const ports = congestionData?.data || [];
  const chokepoints = chokepointData?.data || [];
  const network = networkData?.data || {};

  // Extract route edges from GeoJSON
  const routeLines = (network.features || [])
    .filter((f) => f.geometry?.type === 'LineString')
    .map((f) => ({
      positions: f.geometry.coordinates.map(([lng, lat]) => [lat, lng]),
      mode: f.properties?.mode || 'sea',
      reliability: f.properties?.reliability || 85,
      delayFactor: f.properties?.delay_factor || 1.0,
    }));

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <Anchor size={24} color="var(--ocean-teal)" />
        <div>
          <h1 className="text-xl font-bold text-[color:var(--text-primary)]">Port Network</h1>
          <p className="text-xs text-[color:var(--text-muted)]">Simulated port congestion · Chokepoint analysis · Route corridors</p>
        </div>
        <span className="rounded-full px-2 py-0.5 text-[9px] font-semibold uppercase tracking-[0.12em] text-[color:var(--text-muted)] border border-[color:var(--glass-border)]">
          Simulated
        </span>
      </div>

      {/* Legend */}
      <div className="flex gap-4 text-[10px] text-[color:var(--text-muted)]">
        <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-[#10B981]" /> Normal</span>
        <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-[#EAB308]" /> Elevated</span>
        <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-[#F59E0B]" /> High</span>
        <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-[#EF4444]" /> Critical</span>
        <span className="flex items-center gap-1"><span className="w-2 h-2 bg-[#A855F7] rotate-45" /> Chokepoint</span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
        {/* MAP */}
        <div className="lg:col-span-3 relative h-[75vh] overflow-hidden rounded-xl border border-[color:var(--glass-border)] shadow-[0_0_60px_rgba(0,200,224,0.08)]">
          <MapContainer center={[20, 40]} zoom={2} className="h-full w-full" style={{ background: '#0a0f1a' }}>
            <TileLayer
              url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
              attribution="&copy; OpenStreetMap &copy; CARTO"
            />

            {/* Route corridors */}
            {routeLines.map((route, i) => (
              <Polyline
                key={`route-${i}`}
                positions={route.positions}
                pathOptions={{
                  color: route.delayFactor > 1.5 ? '#EF4444' : route.mode === 'air' ? '#A855F7' : '#00C8E033',
                  weight: route.mode === 'air' ? 1 : 1.5,
                  dashArray: route.mode === 'air' ? '5,8' : undefined,
                  opacity: 0.5,
                }}
              />
            ))}

            {/* Port nodes */}
            {ports.filter(p => p.type !== 'chokepoint').map((port) => (
              <CircleMarker
                key={port.port_id}
                center={[port.lat, port.lon]}
                radius={portRadius(port.capacity_teu)}
                pathOptions={{
                  color: congestionColor(port.congestion_score),
                  fillColor: congestionColor(port.congestion_score),
                  fillOpacity: 0.7,
                  weight: 2,
                  className: port.congestion_score > 80 ? 'vessel-critical' : '',
                }}
                eventHandlers={{
                  click: () => setSelectedPort(port),
                }}
              >
                <Popup>
                  <div className="text-sm">
                    <div className="font-semibold">{port.name}</div>
                    <div>Congestion: {port.congestion_score}% (Simulated)</div>
                    <div>Wait: ~{port.wait_hours_estimated}h</div>
                  </div>
                </Popup>
              </CircleMarker>
            ))}

            {/* Chokepoints as diamond markers (using SVG-like small circles with different style) */}
            {chokepoints.map((cp) => (
              <CircleMarker
                key={cp.id}
                center={[cp.lat, cp.lon]}
                radius={8}
                pathOptions={{
                  color: '#A855F7',
                  fillColor: cp.status === 'critical' ? '#EF4444' : '#A855F7',
                  fillOpacity: 0.8,
                  weight: 2,
                }}
              >
                <Popup>
                  <div className="text-sm">
                    <div className="font-semibold">{cp.name}</div>
                    <div>Status: {cp.status.toUpperCase()}</div>
                    <div>Congestion: {cp.congestion_score}% (Simulated)</div>
                    <div>Connections: {cp.connections}</div>
                  </div>
                </Popup>
              </CircleMarker>
            ))}
          </MapContainer>
        </div>

        {/* SIDE PANEL */}
        <div className="space-y-3">
          {selectedPort ? (
            <PortDetailPanel port={selectedPort} onClose={() => setSelectedPort(null)} />
          ) : (
            <div className="glass-panel rounded-xl p-4">
              <div className="text-[10px] uppercase tracking-[0.2em] text-[color:var(--text-muted)] mb-3">Port Summary</div>
              <div className="grid grid-cols-2 gap-2 mb-4">
                <StatBox label="Total Ports" value={ports.length} color="var(--ocean-teal)" />
                <StatBox label="Chokepoints" value={chokepoints.length} color="#A855F7" />
                <StatBox label="Critical" value={ports.filter(p => p.congestion_score > 80).length} color="#EF4444" />
                <StatBox label="Normal" value={ports.filter(p => p.congestion_score <= 40).length} color="#10B981" />
              </div>

              {/* Top congested */}
              <div className="text-[10px] uppercase tracking-[0.15em] text-[color:var(--text-muted)] mb-2">Top Congested</div>
              <div className="space-y-1.5 max-h-80 overflow-auto">
                {ports
                  .sort((a, b) => b.congestion_score - a.congestion_score)
                  .slice(0, 10)
                  .map((p) => (
                    <button
                      key={p.port_id}
                      type="button"
                      onClick={() => setSelectedPort(p)}
                      className="w-full text-left flex items-center justify-between rounded-lg p-2 bg-[color:var(--bg-card)] border border-[color:var(--glass-border)] hover:border-[color:var(--ocean-teal)] transition-all"
                    >
                      <div>
                        <div className="text-xs font-semibold text-[color:var(--text-primary)]">{p.name}</div>
                        <div className="text-[10px] text-[color:var(--text-muted)]">{p.city}, {p.country}</div>
                      </div>
                      <div className="flex items-center gap-2">
                        <div className="w-12 h-1.5 rounded-full bg-[rgba(255,255,255,0.05)] overflow-hidden">
                          <div
                            className="h-full rounded-full"
                            style={{
                              width: `${p.congestion_score}%`,
                              background: congestionColor(p.congestion_score),
                            }}
                          />
                        </div>
                        <span className="text-xs font-semibold" style={{ color: congestionColor(p.congestion_score) }}>
                          {Math.round(p.congestion_score)}%
                        </span>
                      </div>
                    </button>
                  ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function PortDetailPanel({ port, onClose }) {
  const score = port.congestion_score || 0;
  const color = congestionColor(score);

  const statusLabel = score > 80 ? 'CRITICAL' : score > 60 ? 'HIGH' : score > 40 ? 'ELEVATED' : 'NORMAL';

  return (
    <div className="glass-panel rounded-xl p-4 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <div className="text-sm font-bold text-[color:var(--text-primary)]">{port.name}</div>
          <div className="text-[10px] text-[color:var(--text-muted)]">{port.city}, {port.country}</div>
        </div>
        <button onClick={onClose} className="text-[color:var(--text-muted)] hover:text-[color:var(--text-primary)] text-lg">✕</button>
      </div>
      <div className="text-[10px] uppercase tracking-[0.12em] text-[color:var(--text-muted)]">Simulated congestion feed</div>

      {/* Congestion gauge */}
      <div className="flex flex-col items-center py-4">
        <div className="relative w-28 h-14 overflow-hidden">
          <svg viewBox="0 0 120 60" className="w-full">
            <path d="M10 55 A50 50 0 0 1 110 55" fill="none" stroke="rgba(255,255,255,0.05)" strokeWidth="8" strokeLinecap="round" />
            <path
              d="M10 55 A50 50 0 0 1 110 55"
              fill="none"
              stroke={color}
              strokeWidth="8"
              strokeLinecap="round"
              strokeDasharray={`${score * 1.57} 157`}
            />
          </svg>
          <div className="absolute bottom-0 left-1/2 -translate-x-1/2 text-2xl font-extrabold" style={{ color }}>
            {Math.round(score)}%
          </div>
        </div>
        <span
          className="mt-2 px-3 py-1 rounded-full text-[10px] font-bold uppercase tracking-[0.1em]"
          style={{ background: `${color}1A`, color }}
        >
          {statusLabel}
        </span>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <InfoBlock label="Wait Time" value={`~${port.wait_hours_estimated || 0}h`} />
        <InfoBlock label="Trend" value={port.trend || 'stable'} />
        <InfoBlock label="Type" value={port.type?.replace('_', ' ')} />
        <InfoBlock label="Port ID" value={port.port_id} />
      </div>

      {port.capacity_teu && (
        <div className="text-center text-[10px] text-[color:var(--text-muted)]">
          Annual Capacity: {(port.capacity_teu / 1e6).toFixed(0)}M TEU
        </div>
      )}
    </div>
  );
}

function StatBox({ label, value, color }) {
  return (
    <div className="text-center rounded-lg p-2 bg-[color:var(--bg-card)]">
      <div className="text-lg font-bold" style={{ color }}>{value}</div>
      <div className="text-[9px] text-[color:var(--text-muted)]">{label}</div>
    </div>
  );
}

function InfoBlock({ label, value }) {
  return (
    <div className="rounded-lg p-2 bg-[color:var(--bg-card)]">
      <div className="text-[9px] text-[color:var(--text-muted)] uppercase tracking-[0.1em]">{label}</div>
      <div className="text-xs font-semibold text-[color:var(--text-primary)] capitalize">{value}</div>
    </div>
  );
}

export default PortNetworkPage;
