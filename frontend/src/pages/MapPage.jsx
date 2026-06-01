import { useMemo, useState } from 'react';
import L from 'leaflet';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { CircleMarker, MapContainer, Marker, Popup, TileLayer, Polyline, Circle } from 'react-leaflet';

import {
  createPort,
  createRoute,
  createShipment,
  getChokepoints,
  getClients,
  getDisruptions,
  getExternalRisks,
  getPortCongestion,
  getRouteNetwork,
  getShipments,
  QUERY_KEYS,
} from '../api/client';
import SourceBadge from '../components/SourceBadge';

function colorForRisk(level) {
  if (level === 'critical') return '#EF4444';
  if (level === 'high') return '#F59E0B';
  if (level === 'medium') return '#EAB308';
  return '#10B981';
}

function radiusForRisk(level) {
  if (level === 'critical') return 10;
  if (level === 'high') return 8;
  if (level === 'medium') return 6;
  return 5;
}

function congestionColor(score) {
  if (score > 80) return '#EF4444';
  if (score > 60) return '#F59E0B';
  if (score > 40) return '#EAB308';
  return '#10B981';
}

function disasterColor(risk) {
  if (risk.source_event_type === 'EQ' || risk.source_event_type === 'VO') return 'purple';
  if (risk.severity === 'critical') return 'red';
  return 'orange';
}

function disasterIcon(risk) {
  const color = disasterColor(risk);
  return L.divIcon({
    className: '',
    iconSize: [34, 34],
    iconAnchor: [17, 17],
    html: `<div class="disaster-marker disaster-${color}"><span class="disaster-pulse-ring"></span><span class="disaster-core"></span></div>`,
  });
}

const defaultCargo = {
  client_id: '',
  origin_city: 'Mumbai',
  origin_country: 'India',
  origin_lat: 19.1,
  origin_lon: 72.9,
  dest_city: 'Hamburg',
  dest_country: 'Germany',
  dest_lat: 53.5,
  dest_lon: 10,
  cargo_type: 'Textiles',
  cargo_value_usd: 250000,
  weight_kg: 12000,
  carrier: 'Maersk',
  operator_name: 'Maersk',
  mode: 'sea',
  status: 'pending',
  tracking_number: '',
  origin_port_id: 'INNSAV',
  dest_port_id: 'DEHAM',
  priority: 'normal',
};

const defaultPort = {
  id: '',
  name: '',
  city: '',
  country: '',
  lat: '',
  lon: '',
  type: 'sea_port',
  capacity_teu: '',
};

const defaultRoute = {
  from_port_id: '',
  to_port_id: '',
  mode: 'sea',
  distance_km: 1000,
  base_transit_hours: 48,
  base_cost_usd_per_teu: 900,
  reliability_score: 85,
};

function MapPage() {
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState('Cargo');
  const [selectedPort, setSelectedPort] = useState(null);
  const [modal, setModal] = useState(null);
  const [cargoForm, setCargoForm] = useState(defaultCargo);
  const [portForm, setPortForm] = useState(defaultPort);
  const [routeForm, setRouteForm] = useState(defaultRoute);
  const [layers, setLayers] = useState({
    shipments: true,
    ports: true,
    routes: true,
    disruptions: true,
    chokepoints: true,
    externalRisks: true,
  });

  const { data } = useQuery({
    queryKey: [...QUERY_KEYS.shipments, 'map'],
    queryFn: () => getShipments({ page: 1, page_size: 500 }),
  });
  const { data: clientsData } = useQuery({ queryKey: QUERY_KEYS.clients, queryFn: getClients });
  const { data: networkData } = useQuery({ queryKey: QUERY_KEYS.portNetwork, queryFn: getRouteNetwork });
  const { data: disruptionData } = useQuery({
    queryKey: QUERY_KEYS.disruptions,
    queryFn: getDisruptions,
    refetchInterval: 30000,
  });
  const { data: chokepointData } = useQuery({ queryKey: QUERY_KEYS.chokepoints, queryFn: getChokepoints });
  const { data: congestionData } = useQuery({
    queryKey: QUERY_KEYS.portCongestion,
    queryFn: getPortCongestion,
    refetchInterval: 60000,
  });
  const { data: externalRiskData } = useQuery({
    queryKey: QUERY_KEYS.externalRisks,
    queryFn: getExternalRisks,
    refetchInterval: 300000,
  });

  const shipments = data?.data || [];
  const clients = clientsData?.data || [];
  const network = networkData?.data || {};
  const disruptions = disruptionData?.data || [];
  const chokepoints = chokepointData?.data || [];
  const ports = congestionData?.data || [];
  const externalRisks = externalRiskData?.data || [];
  const atRiskCount = shipments.filter((s) => ['high', 'critical'].includes(s.risk_level)).length;

  const portFeatures = (network.features || []).filter((f) => f.geometry?.type === 'Point');
  const routeFeatures = (network.features || []).filter((f) => f.geometry?.type === 'LineString');
  const portById = useMemo(() => Object.fromEntries(ports.map((port) => [port.port_id || port.id, port])), [ports]);

  const shipmentSourceCounts = useMemo(() => shipments.reduce((acc, shipment) => {
    const key = shipment.source || 'seed';
    acc[key] = (acc[key] || 0) + 1;
    return acc;
  }, {}), [shipments]);

  const latestShipmentUpdate = useMemo(() => {
    const timestamps = shipments
      .map((shipment) => shipment.last_updated)
      .filter(Boolean)
      .map((value) => new Date(value))
      .filter((value) => !Number.isNaN(value.getTime()));
    if (!timestamps.length) return null;
    return new Date(Math.max(...timestamps.map((date) => date.getTime()))).toISOString();
  }, [shipments]);

  const invalidateCargo = (clientId) => {
    [
      QUERY_KEYS.shipments,
      [...QUERY_KEYS.shipments, 'map'],
      QUERY_KEYS.stats,
      QUERY_KEYS.financial,
      QUERY_KEYS.clients,
      QUERY_KEYS.slaOverview,
      clientId ? ['clients', clientId] : null,
    ].filter(Boolean).forEach((queryKey) => queryClient.invalidateQueries({ queryKey }));
  };

  const cargoMutation = useMutation({
    mutationFn: () => createShipment({
      ...cargoForm,
      client_id: cargoForm.client_id || null,
      origin_lat: Number(cargoForm.origin_lat),
      origin_lon: Number(cargoForm.origin_lon),
      dest_lat: Number(cargoForm.dest_lat),
      dest_lon: Number(cargoForm.dest_lon),
      cargo_value_usd: Number(cargoForm.cargo_value_usd),
      weight_kg: Number(cargoForm.weight_kg || 0) || null,
    }),
    onSuccess: () => {
      invalidateCargo(cargoForm.client_id);
      setModal(null);
      setCargoForm(defaultCargo);
    },
  });

  const portMutation = useMutation({
    mutationFn: () => createPort({
      ...portForm,
      id: portForm.id || null,
      lat: Number(portForm.lat),
      lon: Number(portForm.lon),
      capacity_teu: Number(portForm.capacity_teu || 0) || null,
    }),
    onSuccess: () => {
      [QUERY_KEYS.portCongestion, QUERY_KEYS.portNetwork].forEach((queryKey) => queryClient.invalidateQueries({ queryKey }));
      setModal(null);
      setPortForm(defaultPort);
    },
  });

  const routeMutation = useMutation({
    mutationFn: () => createRoute({
      ...routeForm,
      distance_km: Number(routeForm.distance_km),
      base_transit_hours: Number(routeForm.base_transit_hours),
      base_cost_usd_per_teu: Number(routeForm.base_cost_usd_per_teu),
      reliability_score: Number(routeForm.reliability_score),
    }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.portNetwork });
      setModal(null);
      setRouteForm(defaultRoute);
    },
  });

  const toggleLayer = (key) => setLayers((prev) => ({ ...prev, [key]: !prev[key] }));

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold text-[color:var(--text-primary)]">Operations Command Map</h1>
          <p className="text-xs text-[color:var(--text-muted)]">Cargo, ports, routes, chokepoints, disruptions, and external risk events in one live workspace.</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button type="button" className="btn-solid" onClick={() => setModal('cargo')}>+ Add Cargo</button>
          <button type="button" className="btn-outline" onClick={() => setModal('port')}>+ Add Port</button>
          <button type="button" className="btn-outline" onClick={() => setModal('route')}>+ Add Route</button>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-3 xl:grid-cols-[1fr_360px]">
        <div className="relative h-[78vh] overflow-hidden rounded-xl border border-[color:var(--glass-border)] shadow-[0_0_60px_rgba(0,200,224,0.08),inset_0_0_30px_rgba(0,0,0,0.3)]">
          <div className="map-hud">
            <div className="hud-stat">
              <span className="hud-label">Tracked Cargo</span>
              <span className="hud-value">{shipments.length}</span>
            </div>
            <div className="hud-divider" />
            <div className="hud-stat">
              <span className="hud-label">At Risk</span>
              <span className="hud-value risk">{atRiskCount}</span>
            </div>
            <div className="hud-divider" />
            <div className="hud-stat">
              <span className="hud-label">Ports</span>
              <span className="hud-value">{portFeatures.length || ports.length}</span>
            </div>
            <div className="hud-divider" />
            <div className="hud-stat">
              <SourceBadge source={shipmentSourceCounts.csv ? 'csv' : 'seed'} updatedAt={latestShipmentUpdate} showUpdated={false} />
              <div className="text-[9px] text-[color:var(--text-muted)]">
                Imported: {shipmentSourceCounts.csv || 0} / Synthetic: {shipmentSourceCounts.seed || 0}
              </div>
            </div>
          </div>

          <div className="map-controls">
            {Object.entries(layers).map(([key, active]) => (
              <label key={key} className="layer-toggle">
                <input type="checkbox" checked={active} onChange={() => toggleLayer(key)} />
                <span className="text-[10px] capitalize">{key.replace(/([A-Z])/g, ' $1')}</span>
              </label>
            ))}
          </div>

          <div className="map-legend">
            <span className="legend-dot green" /> On Time
            <span className="legend-dot amber" /> Delayed
            <span className="legend-dot red" /> Critical
            <span className="legend-dot purple" /> Chokepoint / External
          </div>

          <MapContainer center={[20, 20]} zoom={2} className="h-full w-full">
            <TileLayer
              url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
              attribution="&copy; OpenStreetMap contributors &copy; CARTO"
            />

            {layers.routes && routeFeatures.map((f, i) => (
              <Polyline
                key={`route-${i}`}
                positions={f.geometry.coordinates.map(([lng, lat]) => [lat, lng])}
                pathOptions={{
                  color: f.properties?.delay_factor > 1.4 ? '#EF444466' : f.properties?.mode === 'air' ? '#A855F766' : '#00C8E033',
                  weight: f.properties?.mode === 'air' ? 1 : 1.5,
                  dashArray: f.properties?.mode === 'air' ? '4,8' : undefined,
                }}
              />
            ))}

            {layers.disruptions && disruptions.map((d) => d.affected_region && (
              <Circle
                key={`disruption-${d.id}`}
                center={[d.affected_region.lat, d.affected_region.lon]}
                radius={(d.affected_region.radius_km || 500) * 1000}
                pathOptions={{
                  color: d.severity === 'critical' ? '#EF444466' : '#F59E0B44',
                  fillColor: d.severity === 'critical' ? '#EF444422' : '#F59E0B11',
                  fillOpacity: 0.3,
                  weight: 1,
                }}
              />
            ))}

            {layers.externalRisks && externalRisks.map((risk) => (
              <Marker key={risk.id} position={[risk.lat, risk.lon]} icon={disasterIcon(risk)}>
                <Popup>
                  <div className="text-sm">
                    <div className="font-semibold">{risk.title}</div>
                    <div>{risk.source_event_type} / {risk.severity}</div>
                    {risk.url ? <a href={risk.url} target="_blank" rel="noreferrer">GDACS detail</a> : null}
                  </div>
                </Popup>
              </Marker>
            ))}

            {layers.ports && portFeatures.map((f) => {
              const [lng, lat] = f.geometry.coordinates;
              const props = f.properties || {};
              const livePort = portById[props.id] || {};
              const congestion = livePort.congestion_score ?? props.congestion_score ?? 0;
              const color = props.type === 'chokepoint' ? '#A855F7' : congestionColor(congestion);
              return (
                <CircleMarker
                  key={`port-${props.id}`}
                  center={[lat, lng]}
                  radius={props.type === 'chokepoint' ? 7 : Math.max(4, Math.min(12, (props.capacity_teu || 1_000_000) / 3_500_000))}
                  pathOptions={{
                    color,
                    fillColor: color,
                    fillOpacity: 0.7,
                    weight: 1.5,
                    className: congestion > 80 ? 'vessel-critical' : '',
                  }}
                  eventHandlers={{ click: () => setSelectedPort({ ...props, ...livePort, port_id: props.id }) }}
                >
                  <Popup>
                    <div className="text-sm">
                      <div className="font-semibold">{props.name}</div>
                      <div>{props.type?.replace('_', ' ')} / {props.city}</div>
                      <div>Congestion: {Math.round(congestion)}%</div>
                    </div>
                  </Popup>
                </CircleMarker>
              );
            })}

            {layers.chokepoints && chokepoints.map((cp) => (
              <CircleMarker
                key={`cp-${cp.id}`}
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
                    <div>Status: {cp.status?.toUpperCase()}</div>
                    <div>Congestion: {cp.congestion_score}%</div>
                  </div>
                </Popup>
              </CircleMarker>
            ))}

            {layers.shipments && shipments.map((shipment) => (
              <CircleMarker
                key={shipment.id}
                center={[shipment.current_location.lat, shipment.current_location.lon]}
                radius={radiusForRisk(shipment.risk_level)}
                pathOptions={{
                  color: colorForRisk(shipment.risk_level),
                  fillOpacity: 0.8,
                  className: shipment.risk_level === 'critical' ? 'vessel-critical' : '',
                }}
              >
                <Popup>
                  <div className="text-sm">
                    <div className="font-semibold">{shipment.id}</div>
                    <div>{shipment.origin.city} -&gt; {shipment.destination.city}</div>
                    <div>Risk: {shipment.risk_score} ({shipment.risk_level})</div>
                    <div>Operator: {shipment.operator_name || shipment.carrier}</div>
                  </div>
                </Popup>
              </CircleMarker>
            ))}
          </MapContainer>
        </div>

        <OperationsPanel
          activeTab={activeTab}
          setActiveTab={setActiveTab}
          shipments={shipments}
          ports={ports}
          routes={routeFeatures}
          chokepoints={chokepoints}
          disruptions={disruptions}
          externalRisks={externalRisks}
          selectedPort={selectedPort}
          onClearPort={() => setSelectedPort(null)}
        />
      </div>

      {modal ? (
        <MapCreateModal
          type={modal}
          clients={clients}
          ports={portFeatures}
          cargoForm={cargoForm}
          setCargoForm={setCargoForm}
          portForm={portForm}
          setPortForm={setPortForm}
          routeForm={routeForm}
          setRouteForm={setRouteForm}
          onClose={() => setModal(null)}
          onSubmit={() => {
            if (modal === 'cargo') cargoMutation.mutate();
            if (modal === 'port') portMutation.mutate();
            if (modal === 'route') routeMutation.mutate();
          }}
          isSaving={cargoMutation.isPending || portMutation.isPending || routeMutation.isPending}
          error={cargoMutation.error || portMutation.error || routeMutation.error}
        />
      ) : null}
    </div>
  );
}

function OperationsPanel({ activeTab, setActiveTab, shipments, ports, routes, chokepoints, disruptions, externalRisks, selectedPort, onClearPort }) {
  const tabs = ['Cargo', 'Ports', 'Routes', 'Risks'];
  return (
    <aside className="glass-panel h-[78vh] overflow-auto rounded-xl p-4">
      <div className="mb-3 flex flex-wrap gap-2">
        {tabs.map((tab) => (
          <button key={tab} type="button" className={`chip ${activeTab === tab ? 'active' : ''}`} onClick={() => setActiveTab(tab)}>
            {tab}
          </button>
        ))}
      </div>

      {selectedPort ? (
        <div className="mb-4 rounded-lg border border-[color:var(--glass-border)] bg-[color:var(--bg-card)] p-3">
          <div className="flex items-center justify-between">
            <div className="text-sm font-bold text-[color:var(--text-primary)]">{selectedPort.name}</div>
            <button type="button" className="text-xs text-[color:var(--text-muted)]" onClick={onClearPort}>clear</button>
          </div>
          <div className="mt-1 text-xs text-[color:var(--text-muted)]">{selectedPort.city}, {selectedPort.country}</div>
          <div className="mt-2 grid grid-cols-2 gap-2">
            <PanelStat label="Congestion" value={`${Math.round(selectedPort.congestion_score || 0)}%`} />
            <PanelStat label="Wait" value={`${selectedPort.wait_hours_estimated || selectedPort.avg_wait_hours || 0}h`} />
          </div>
        </div>
      ) : null}

      {activeTab === 'Cargo' ? (
        <PanelList
          title="Highest Risk Cargo"
          items={shipments.slice().sort((a, b) => b.risk_score - a.risk_score).slice(0, 12)}
          render={(shipment) => (
            <>
              <div className="text-xs font-semibold text-[color:var(--ocean-teal)]">{shipment.id}</div>
              <div className="text-[10px] text-[color:var(--text-muted)]">{shipment.client_name || 'Unassigned'} / {shipment.origin.city} to {shipment.destination.city}</div>
              <div className="text-[10px]" style={{ color: colorForRisk(shipment.risk_level) }}>Risk {shipment.risk_score} / {shipment.priority || 'normal'}</div>
            </>
          )}
        />
      ) : null}

      {activeTab === 'Ports' ? (
        <PanelList
          title="Port Congestion"
          items={ports.slice().sort((a, b) => b.congestion_score - a.congestion_score).slice(0, 14)}
          render={(port) => (
            <>
              <div className="text-xs font-semibold text-[color:var(--text-primary)]">{port.name}</div>
              <div className="text-[10px] text-[color:var(--text-muted)]">{port.city}, {port.country}</div>
              <div className="mt-1 h-1.5 rounded-full bg-[rgba(255,255,255,0.08)]">
                <div className="h-full rounded-full" style={{ width: `${port.congestion_score}%`, background: congestionColor(port.congestion_score) }} />
              </div>
            </>
          )}
        />
      ) : null}

      {activeTab === 'Routes' ? (
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-2">
            <PanelStat label="Route corridors" value={routes.length} />
            <PanelStat label="Chokepoints" value={chokepoints.length} />
          </div>
          <PanelList
            title="Chokepoints"
            items={chokepoints}
            render={(cp) => (
              <>
                <div className="text-xs font-semibold text-[color:var(--text-primary)]">{cp.name}</div>
                <div className="text-[10px] text-[color:var(--text-muted)]">{cp.status} / congestion {cp.congestion_score}%</div>
              </>
            )}
          />
        </div>
      ) : null}

      {activeTab === 'Risks' ? (
        <div className="space-y-3">
          <PanelList
            title="External Risks"
            items={externalRisks}
            render={(risk) => (
              <>
                <div className="text-xs font-semibold text-[color:var(--text-primary)]">{risk.title}</div>
                <div className="text-[10px] text-[color:var(--text-muted)]">{risk.source_event_type} / {risk.severity}</div>
              </>
            )}
          />
          <PanelList
            title="Active Disruptions"
            items={disruptions.slice(0, 8)}
            render={(risk) => (
              <>
                <div className="text-xs font-semibold text-[color:var(--text-primary)]">{risk.title}</div>
                <div className="text-[10px] text-[color:var(--text-muted)]">{risk.affected_shipment_count} cargo affected / {risk.severity}</div>
              </>
            )}
          />
        </div>
      ) : null}
    </aside>
  );
}

function PanelStat({ label, value }) {
  return (
    <div className="rounded-lg bg-[color:var(--bg-card)] p-2">
      <div className="text-lg font-bold text-[color:var(--ocean-teal)]">{value}</div>
      <div className="text-[9px] uppercase tracking-[0.12em] text-[color:var(--text-muted)]">{label}</div>
    </div>
  );
}

function PanelList({ title, items, render }) {
  return (
    <div>
      <div className="mb-2 text-[10px] uppercase tracking-[0.18em] text-[color:var(--text-muted)]">{title}</div>
      <div className="space-y-2">
        {items.length ? items.map((item, index) => (
          <div key={item.id || item.port_id || item.name || index} className="rounded-lg border border-[color:var(--glass-border)] bg-[color:var(--bg-card)] p-3">
            {render(item)}
          </div>
        )) : (
          <div className="rounded-lg border border-[color:var(--glass-border)] bg-[color:var(--bg-card)] p-3 text-xs text-[color:var(--text-muted)]">No records found.</div>
        )}
      </div>
    </div>
  );
}

function MapCreateModal({
  type,
  clients,
  ports,
  cargoForm,
  setCargoForm,
  portForm,
  setPortForm,
  routeForm,
  setRouteForm,
  onClose,
  onSubmit,
  isSaving,
  error,
}) {
  const title = type === 'cargo' ? 'Add Cargo Movement' : type === 'port' ? 'Add Port' : 'Add Route Corridor';
  const portOptions = ports.map((feature) => feature.properties).filter(Boolean);
  const setCargo = (key, value) => setCargoForm((prev) => ({ ...prev, [key]: value }));
  const setPort = (key, value) => setPortForm((prev) => ({ ...prev, [key]: value }));
  const setRoute = (key, value) => setRouteForm((prev) => ({ ...prev, [key]: value }));

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
      <div className="glass-panel max-h-[90vh] w-full max-w-3xl overflow-auto rounded-xl p-5">
        <div className="mb-4 flex items-center justify-between">
          <div className="text-lg font-bold text-[color:var(--text-primary)]">{title}</div>
          <button type="button" className="btn-outline" onClick={onClose}>Close</button>
        </div>

        {type === 'cargo' ? (
          <ModalGrid>
            <ModalSelect label="Client" value={cargoForm.client_id} onChange={(v) => setCargo('client_id', v)} options={[['', 'Unassigned'], ...clients.map((client) => [client.id, client.name])]} />
            <ModalInput label="Cargo type" value={cargoForm.cargo_type} onChange={(v) => setCargo('cargo_type', v)} />
            <ModalInput label="Cargo value USD" type="number" value={cargoForm.cargo_value_usd} onChange={(v) => setCargo('cargo_value_usd', v)} />
            <ModalInput label="Weight KG" type="number" value={cargoForm.weight_kg} onChange={(v) => setCargo('weight_kg', v)} />
            <ModalInput label="Origin city" value={cargoForm.origin_city} onChange={(v) => setCargo('origin_city', v)} />
            <ModalInput label="Origin country" value={cargoForm.origin_country} onChange={(v) => setCargo('origin_country', v)} />
            <ModalInput label="Origin lat" type="number" value={cargoForm.origin_lat} onChange={(v) => setCargo('origin_lat', v)} />
            <ModalInput label="Origin lon" type="number" value={cargoForm.origin_lon} onChange={(v) => setCargo('origin_lon', v)} />
            <ModalInput label="Destination city" value={cargoForm.dest_city} onChange={(v) => setCargo('dest_city', v)} />
            <ModalInput label="Destination country" value={cargoForm.dest_country} onChange={(v) => setCargo('dest_country', v)} />
            <ModalInput label="Destination lat" type="number" value={cargoForm.dest_lat} onChange={(v) => setCargo('dest_lat', v)} />
            <ModalInput label="Destination lon" type="number" value={cargoForm.dest_lon} onChange={(v) => setCargo('dest_lon', v)} />
            <ModalInput label="Carrier" value={cargoForm.carrier} onChange={(v) => setCargo('carrier', v)} />
            <ModalInput label="Operator" value={cargoForm.operator_name} onChange={(v) => setCargo('operator_name', v)} />
            <ModalInput label="Tracking number" value={cargoForm.tracking_number} onChange={(v) => setCargo('tracking_number', v)} />
            <ModalSelect label="Priority" value={cargoForm.priority} onChange={(v) => setCargo('priority', v)} options={['normal', 'high', 'urgent'].map((v) => [v, v])} />
          </ModalGrid>
        ) : null}

        {type === 'port' ? (
          <ModalGrid>
            <ModalInput label="Port ID" value={portForm.id} onChange={(v) => setPort('id', v)} />
            <ModalInput label="Name" value={portForm.name} onChange={(v) => setPort('name', v)} />
            <ModalInput label="City" value={portForm.city} onChange={(v) => setPort('city', v)} />
            <ModalInput label="Country" value={portForm.country} onChange={(v) => setPort('country', v)} />
            <ModalInput label="Latitude" type="number" value={portForm.lat} onChange={(v) => setPort('lat', v)} />
            <ModalInput label="Longitude" type="number" value={portForm.lon} onChange={(v) => setPort('lon', v)} />
            <ModalSelect label="Type" value={portForm.type} onChange={(v) => setPort('type', v)} options={['sea_port', 'air_hub', 'chokepoint'].map((v) => [v, v])} />
            <ModalInput label="Capacity TEU" type="number" value={portForm.capacity_teu} onChange={(v) => setPort('capacity_teu', v)} />
          </ModalGrid>
        ) : null}

        {type === 'route' ? (
          <ModalGrid>
            <ModalSelect label="From port" value={routeForm.from_port_id} onChange={(v) => setRoute('from_port_id', v)} options={[['', 'Select'], ...portOptions.map((port) => [port.id, port.name])]} />
            <ModalSelect label="To port" value={routeForm.to_port_id} onChange={(v) => setRoute('to_port_id', v)} options={[['', 'Select'], ...portOptions.map((port) => [port.id, port.name])]} />
            <ModalSelect label="Mode" value={routeForm.mode} onChange={(v) => setRoute('mode', v)} options={['sea', 'air', 'rail', 'road', 'multimodal'].map((v) => [v, v])} />
            <ModalInput label="Distance KM" type="number" value={routeForm.distance_km} onChange={(v) => setRoute('distance_km', v)} />
            <ModalInput label="Transit hours" type="number" value={routeForm.base_transit_hours} onChange={(v) => setRoute('base_transit_hours', v)} />
            <ModalInput label="Cost per TEU" type="number" value={routeForm.base_cost_usd_per_teu} onChange={(v) => setRoute('base_cost_usd_per_teu', v)} />
            <ModalInput label="Reliability" type="number" value={routeForm.reliability_score} onChange={(v) => setRoute('reliability_score', v)} />
          </ModalGrid>
        ) : null}

        {error ? <div className="mt-4 rounded-lg border border-red-500/40 bg-red-500/10 p-3 text-xs text-red-300">{error.message}</div> : null}

        <div className="mt-5 flex justify-end gap-2">
          <button type="button" className="btn-outline" onClick={onClose}>Cancel</button>
          <button type="button" className="btn-solid" disabled={isSaving} onClick={onSubmit}>
            {isSaving ? 'Saving...' : 'Save'}
          </button>
        </div>
      </div>
    </div>
  );
}

function ModalGrid({ children }) {
  return <div className="grid grid-cols-1 gap-3 md:grid-cols-2">{children}</div>;
}

function ModalInput({ label, value, onChange, type = 'text' }) {
  return (
    <label className="space-y-1 text-xs text-[color:var(--text-muted)]">
      <span className="uppercase tracking-[0.12em]">{label}</span>
      <input className="search-input w-full" type={type} value={value} onChange={(event) => onChange(event.target.value)} />
    </label>
  );
}

function ModalSelect({ label, value, onChange, options }) {
  return (
    <label className="space-y-1 text-xs text-[color:var(--text-muted)]">
      <span className="uppercase tracking-[0.12em]">{label}</span>
      <select className="search-input w-full" value={value} onChange={(event) => onChange(event.target.value)}>
        {options.map(([optionValue, optionLabel]) => <option key={optionValue || optionLabel} value={optionValue}>{optionLabel}</option>)}
      </select>
    </label>
  );
}

export default MapPage;
