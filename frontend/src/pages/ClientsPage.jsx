import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { AlertTriangle, Copy, ExternalLink, FileText, MessageCircle, Users } from 'lucide-react';

import {
  createClient,
  createShipment,
  getClientShipments,
  getClientWeeklyReport,
  getClientWhatsappAlert,
  getClients,
  QUERY_KEYS,
} from '../api/client';

const urgencyColor = {
  critical: '#EF4444',
  high: '#F59E0B',
  medium: '#EAB308',
  low: '#10B981',
};

const defaultWizard = {
  name: '',
  industry: 'Textiles',
  country: 'India',
  city: '',
  primary_contact: '',
  contact_phone: '+91',
  contact_email: '',
  sla_on_time_pct: 95,
  risk_tolerance: 'medium',
  annual_shipment_count: 12,
  cargo_type: 'Textiles',
  cargo_value_usd: 250000,
  weight_kg: 12000,
  hs_code: '620342',
  incoterm: 'FOB',
  po_number: '',
  bl_number: '',
  container_number: '',
  notes: '',
  carrier: 'Maersk',
  operator_name: 'Maersk',
  tracking_number: '',
  vessel_name: '',
  voyage_number: '',
  mode: 'sea',
  status: 'pending',
  origin_city: '',
  origin_country: '',
  origin_lat: '',
  origin_lon: '',
  origin_port_id: '',
  dest_city: '',
  dest_country: '',
  dest_lat: '',
  dest_lon: '',
  dest_port_id: '',
  route_distance_km: '',
  etd: '',
  eta: '',
  ata: '',
  dock_terminal: '',
  berth: '',
  customs_status: 'pending',
  priority: 'normal',
  lc_expiry_date: '',
  expected_transit_days: 14,
};

function ClientsPage() {
  const queryClient = useQueryClient();
  const [selectedClient, setSelectedClient] = useState(null);
  const [notice, setNotice] = useState('');
  const [wizardOpen, setWizardOpen] = useState(false);
  const [wizardStep, setWizardStep] = useState(1);
  const [wizard, setWizard] = useState(defaultWizard);
  const { data } = useQuery({ queryKey: QUERY_KEYS.clients, queryFn: getClients });
  const { data: shipmentsData } = useQuery({
    queryKey: ['clients', selectedClient?.id, 'shipments'],
    queryFn: () => getClientShipments(selectedClient.id),
    enabled: Boolean(selectedClient?.id),
  });
  const { data: reportData, refetch: refetchReport } = useQuery({
    queryKey: ['clients', selectedClient?.id, 'weekly-report'],
    queryFn: () => getClientWeeklyReport(selectedClient.id),
    enabled: false,
  });
  const { data: whatsappData, refetch: refetchWhatsapp } = useQuery({
    queryKey: ['clients', selectedClient?.id, 'whatsapp-alert'],
    queryFn: () => getClientWhatsappAlert(selectedClient.id),
    enabled: false,
  });

  const clients = data?.data || [];
  const shipments = shipmentsData?.data || [];
  const createMutation = useMutation({
    mutationFn: async () => {
      const clientResult = await createClient({
        name: wizard.name,
        industry: wizard.industry,
        country: wizard.country,
        city: wizard.city,
        primary_contact: wizard.primary_contact || null,
        contact_phone: wizard.contact_phone || null,
        contact_email: wizard.contact_email || null,
        sla_on_time_pct: Number(wizard.sla_on_time_pct),
        risk_tolerance: wizard.risk_tolerance,
        annual_shipment_count: Number(wizard.annual_shipment_count || 0),
        total_cargo_value_annual_usd: Number(wizard.cargo_value_usd || 0),
        notes: wizard.notes || null,
      });
      const client = clientResult.data;
      const shipmentResult = await createShipment({
        client_id: client.id,
        client_name: client.name,
        origin_city: wizard.origin_city,
        origin_country: wizard.origin_country,
        origin_lat: Number(wizard.origin_lat),
        origin_lon: Number(wizard.origin_lon),
        dest_city: wizard.dest_city,
        dest_country: wizard.dest_country,
        dest_lat: Number(wizard.dest_lat),
        dest_lon: Number(wizard.dest_lon),
        carrier: wizard.carrier,
        operator_name: wizard.operator_name || wizard.carrier,
        mode: wizard.mode,
        status: wizard.status,
        eta: wizard.eta || null,
        etd: wizard.etd || null,
        ata: wizard.ata || null,
        cargo_value_usd: Number(wizard.cargo_value_usd),
        cargo_type: wizard.cargo_type,
        container_number: wizard.container_number || null,
        tracking_number: wizard.tracking_number || null,
        vessel_name: wizard.vessel_name || null,
        voyage_number: wizard.voyage_number || null,
        origin_port_id: wizard.origin_port_id || null,
        dest_port_id: wizard.dest_port_id || null,
        dock_terminal: wizard.dock_terminal || null,
        berth: wizard.berth || null,
        customs_status: wizard.customs_status,
        priority: wizard.priority,
        incoterm: wizard.incoterm || null,
        hs_code: wizard.hs_code || null,
        po_number: wizard.po_number || null,
        bl_number: wizard.bl_number || null,
        lc_expiry_date: wizard.lc_expiry_date ? `${wizard.lc_expiry_date}T00:00:00` : null,
        expected_transit_days: Number(wizard.expected_transit_days || 0) || null,
        weight_kg: Number(wizard.weight_kg || 0) || null,
        route_distance_km: Number(wizard.route_distance_km || 0) || null,
        notes: wizard.notes || null,
      });
      return { client, shipment: shipmentResult.data };
    },
    onSuccess: ({ client }) => {
      [
        QUERY_KEYS.clients,
        QUERY_KEYS.slaOverview,
        QUERY_KEYS.stats,
        QUERY_KEYS.financial,
        QUERY_KEYS.shipments,
        [...QUERY_KEYS.shipments, 'map'],
        QUERY_KEYS.portNetwork,
        ['clients', client.id],
      ].forEach((queryKey) => queryClient.invalidateQueries({ queryKey }));
      setSelectedClient(client);
      setNotice('Client and cargo registered.');
      setWizardOpen(false);
      setWizardStep(1);
      setWizard(defaultWizard);
    },
  });
  const summary = useMemo(() => {
    const atRisk = clients.filter((client) => ['critical', 'high'].includes(client.sla_status?.urgency)).length;
    const cargo = clients.reduce((sum, client) => sum + (client.active_cargo_value_usd || 0), 0);
    return { atRisk, cargo };
  }, [clients]);

  const copyWhatsapp = async () => {
    const result = await refetchWhatsapp();
    const message = result.data?.data?.message;
    if (message) {
      await navigator.clipboard?.writeText(message);
      setNotice('WhatsApp message copied.');
    }
  };

  const openWhatsapp = async () => {
    const result = await refetchWhatsapp();
    const payload = result.data?.data;
    if (!payload?.message || !payload?.phone) return;
    const phone = payload.phone.replace(/[^\d+]/g, '').replace('+', '');
    window.open(`https://wa.me/${phone}?text=${encodeURIComponent(payload.message)}`, '_blank', 'noopener,noreferrer');
  };

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold text-[color:var(--text-primary)]">Client Portfolio</h1>
          <p className="text-xs text-[color:var(--text-muted)]">Multi-client freight intelligence for forwarders.</p>
        </div>
        <button type="button" className="btn-solid" onClick={() => setWizardOpen(true)}>+ Add Client</button>
      </div>

      <div className="grid grid-cols-1 gap-3 lg:grid-cols-3">
        <SummaryCard label="Total Clients" value={clients.length} icon={Users} color="var(--ocean-teal)" />
        <SummaryCard label="SLA Risk Clients" value={summary.atRisk} icon={AlertTriangle} color="#EF4444" />
        <SummaryCard label="Cargo Under Management" value={`$${(summary.cargo / 1e6).toFixed(1)}M`} icon={FileText} color="#10B981" />
      </div>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-[1fr_380px]">
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
          {clients.map((client) => {
            const sla = client.sla_status || {};
            const color = urgencyColor[sla.urgency] || '#10B981';
            return (
              <button
                key={client.id}
                type="button"
                onClick={() => setSelectedClient(client)}
                className="glass-panel rounded-xl p-4 text-left transition-all hover:border-[color:var(--ocean-teal)]"
                style={{ borderColor: selectedClient?.id === client.id ? 'var(--ocean-teal)' : undefined }}
              >
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <div className="text-sm font-bold text-[color:var(--text-primary)]">{client.name}</div>
                    <div className="mt-1 text-[10px] text-[color:var(--text-muted)]">{client.city}, {client.country}</div>
                  </div>
                  <span className="rounded-full border px-2 py-1 text-[9px]" style={{ color, borderColor: color }}>
                    {sla.status || 'no_data'}
                  </span>
                </div>
                <div className="mt-3 grid grid-cols-2 gap-2 text-xs">
                  <Info label="Industry" value={client.industry} />
                  <Info label="SLA" value={`${client.sla_on_time_pct}%`} />
                  <Info label="Active" value={client.active_shipments_count || 0} />
                  <Info label="At Risk" value={sla.at_risk_shipments || 0} color={color} />
                </div>
                <div className="mt-3 h-1.5 rounded-full bg-[rgba(255,255,255,0.08)]">
                  <div
                    className="h-full rounded-full"
                    style={{ width: `${Math.max(8, Math.min(100, sla.current_on_time_pct || client.current_sla_performance || 0))}%`, background: color }}
                  />
                </div>
                <div className="mt-2 text-[10px] text-[color:var(--text-muted)]">
                  ${(client.active_cargo_value_usd / 1e6 || 0).toFixed(1)}M active cargo
                </div>
              </button>
            );
          })}
        </div>

        <aside className="glass-panel rounded-xl p-4">
          {selectedClient ? (
            <div className="space-y-4">
              <div>
                <div className="text-lg font-bold text-[color:var(--text-primary)]">{selectedClient.name}</div>
                <div className="text-xs text-[color:var(--text-muted)]">{selectedClient.primary_contact} · {selectedClient.contact_phone}</div>
              </div>
              <div className="grid grid-cols-2 gap-2">
                <Info label="SLA Target" value={`${selectedClient.sla_on_time_pct}%`} />
                <Info label="SLA Status" value={selectedClient.sla_status?.status || 'no_data'} color={urgencyColor[selectedClient.sla_status?.urgency]} />
              </div>
              <div className="flex flex-wrap gap-2">
                <button type="button" className="btn-outline" onClick={copyWhatsapp}><Copy size={13} /> Copy WhatsApp</button>
                <button type="button" className="btn-outline" onClick={openWhatsapp}><MessageCircle size={13} /> Open WhatsApp</button>
                <button type="button" className="btn-outline" onClick={() => refetchReport()}><FileText size={13} /> Weekly Report</button>
                <Link className="btn-outline" to={`/simulation?client=${selectedClient.id}`}><ExternalLink size={13} /> Scenario</Link>
              </div>
              {notice ? <div className="text-xs text-[color:var(--status-ok)]">{notice}</div> : null}
              {reportData?.data ? (
                <div className="rounded-lg border border-[color:var(--glass-border)] bg-[color:var(--bg-card)] p-3 text-xs text-[color:var(--text-secondary)]">
                  Weekly report: {reportData.data.on_time_rate}% on-time, {reportData.data.at_risk_count} at risk, ${(reportData.data.total_cargo_value_monitored / 1e6).toFixed(1)}M monitored.
                </div>
              ) : null}
              <div>
                <div className="mb-2 text-[10px] uppercase tracking-[0.18em] text-[color:var(--text-muted)]">Risk-ranked cargo</div>
                <div className="max-h-80 space-y-2 overflow-auto">
                  {shipments.slice(0, 8).map((shipment) => (
                    <div key={shipment.id} className="rounded-lg bg-[color:var(--bg-card)] p-3 text-xs">
                      <div className="flex justify-between">
                        <span className="font-semibold text-[color:var(--ocean-teal)]">{shipment.id}</span>
                        <span style={{ color: shipment.risk_score >= 75 ? '#EF4444' : '#F59E0B' }}>{shipment.risk_score}</span>
                      </div>
                      <div className="mt-1 text-[color:var(--text-muted)]">{shipment.origin.city} {'->'} {shipment.destination.city}</div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <div className="flex min-h-[320px] items-center justify-center text-center text-sm text-[color:var(--text-muted)]">
              Select a client to inspect shipments, SLA risk, and notification actions.
            </div>
          )}
        </aside>
      </div>

      {wizardOpen ? (
        <ClientCargoWizard
          form={wizard}
          setForm={setWizard}
          step={wizardStep}
          setStep={setWizardStep}
          onClose={() => setWizardOpen(false)}
          onSubmit={() => createMutation.mutate()}
          isSaving={createMutation.isPending}
          error={createMutation.error}
        />
      ) : null}
    </div>
  );
}

function ClientCargoWizard({ form, setForm, step, setStep, onClose, onSubmit, isSaving, error }) {
  const update = (key, value) => setForm((prev) => ({ ...prev, [key]: value }));
  const requiredReady = form.name && form.city && form.origin_city && form.origin_country && form.origin_lat
    && form.origin_lon && form.dest_city && form.dest_country && form.dest_lat && form.dest_lon && form.cargo_value_usd;
  const steps = ['Company', 'Cargo', 'Tracking', 'Ports', 'Timing', 'Review'];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
      <div className="glass-panel max-h-[92vh] w-full max-w-5xl overflow-auto rounded-xl p-5">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div>
            <div className="text-lg font-bold text-[color:var(--text-primary)]">Register Client And Cargo</div>
            <div className="text-xs text-[color:var(--text-muted)]">New records are saved to SQLite and reflected across dashboard, map, clients, cargo, SLA, and financial views.</div>
          </div>
          <button type="button" className="btn-outline" onClick={onClose}>Close</button>
        </div>

        <div className="mb-4 flex flex-wrap gap-2">
          {steps.map((label, index) => (
            <button
              key={label}
              type="button"
              onClick={() => setStep(index + 1)}
              className={`chip ${step === index + 1 ? 'active' : ''}`}
            >
              {index + 1}. {label}
            </button>
          ))}
        </div>

        {step === 1 ? (
          <WizardGrid>
            <WizardInput label="Company name" value={form.name} onChange={(v) => update('name', v)} />
            <WizardInput label="Industry" value={form.industry} onChange={(v) => update('industry', v)} />
            <WizardInput label="City" value={form.city} onChange={(v) => update('city', v)} />
            <WizardInput label="Country" value={form.country} onChange={(v) => update('country', v)} />
            <WizardInput label="Primary contact" value={form.primary_contact} onChange={(v) => update('primary_contact', v)} />
            <WizardInput label="WhatsApp phone" value={form.contact_phone} onChange={(v) => update('contact_phone', v)} />
            <WizardInput label="Email" value={form.contact_email} onChange={(v) => update('contact_email', v)} />
            <WizardInput label="SLA on-time %" type="number" value={form.sla_on_time_pct} onChange={(v) => update('sla_on_time_pct', v)} />
            <WizardSelect label="Risk tolerance" value={form.risk_tolerance} onChange={(v) => update('risk_tolerance', v)} options={['low', 'medium', 'high']} />
            <WizardInput label="Annual shipments" type="number" value={form.annual_shipment_count} onChange={(v) => update('annual_shipment_count', v)} />
          </WizardGrid>
        ) : null}

        {step === 2 ? (
          <WizardGrid>
            <WizardInput label="Cargo type" value={form.cargo_type} onChange={(v) => update('cargo_type', v)} />
            <WizardInput label="Cargo value USD" type="number" value={form.cargo_value_usd} onChange={(v) => update('cargo_value_usd', v)} />
            <WizardInput label="Weight KG" type="number" value={form.weight_kg} onChange={(v) => update('weight_kg', v)} />
            <WizardInput label="HS code" value={form.hs_code} onChange={(v) => update('hs_code', v)} />
            <WizardSelect label="Incoterm" value={form.incoterm} onChange={(v) => update('incoterm', v)} options={['FOB', 'CIF', 'EXW', 'DDP']} />
            <WizardInput label="PO number" value={form.po_number} onChange={(v) => update('po_number', v)} />
            <WizardInput label="B/L number" value={form.bl_number} onChange={(v) => update('bl_number', v)} />
            <WizardInput label="Container" value={form.container_number} onChange={(v) => update('container_number', v)} />
            <label className="space-y-1 md:col-span-2 text-xs text-[color:var(--text-muted)]">
              <span className="uppercase tracking-[0.12em]">Cargo notes</span>
              <textarea className="min-h-24 w-full rounded-lg border border-[color:var(--glass-border)] bg-[color:var(--bg-card)] p-3 text-xs text-[color:var(--text-secondary)]" value={form.notes} onChange={(event) => update('notes', event.target.value)} />
            </label>
          </WizardGrid>
        ) : null}

        {step === 3 ? (
          <WizardGrid>
            <WizardInput label="Carrier" value={form.carrier} onChange={(v) => update('carrier', v)} />
            <WizardInput label="Operator" value={form.operator_name} onChange={(v) => update('operator_name', v)} />
            <WizardInput label="Tracking number" value={form.tracking_number} onChange={(v) => update('tracking_number', v)} />
            <WizardInput label="Vessel" value={form.vessel_name} onChange={(v) => update('vessel_name', v)} />
            <WizardInput label="Voyage" value={form.voyage_number} onChange={(v) => update('voyage_number', v)} />
            <WizardSelect label="Mode" value={form.mode} onChange={(v) => update('mode', v)} options={['sea', 'air', 'rail', 'road', 'multimodal']} />
            <WizardSelect label="Status" value={form.status} onChange={(v) => update('status', v)} options={['pending', 'in_transit', 'delayed', 'delivered']} />
          </WizardGrid>
        ) : null}

        {step === 4 ? (
          <WizardGrid>
            <WizardInput label="Origin city" value={form.origin_city} onChange={(v) => update('origin_city', v)} />
            <WizardInput label="Origin country" value={form.origin_country} onChange={(v) => update('origin_country', v)} />
            <WizardInput label="Origin lat" type="number" value={form.origin_lat} onChange={(v) => update('origin_lat', v)} />
            <WizardInput label="Origin lon" type="number" value={form.origin_lon} onChange={(v) => update('origin_lon', v)} />
            <WizardInput label="Origin port ID" value={form.origin_port_id} onChange={(v) => update('origin_port_id', v)} />
            <WizardInput label="Destination city" value={form.dest_city} onChange={(v) => update('dest_city', v)} />
            <WizardInput label="Destination country" value={form.dest_country} onChange={(v) => update('dest_country', v)} />
            <WizardInput label="Destination lat" type="number" value={form.dest_lat} onChange={(v) => update('dest_lat', v)} />
            <WizardInput label="Destination lon" type="number" value={form.dest_lon} onChange={(v) => update('dest_lon', v)} />
            <WizardInput label="Destination port ID" value={form.dest_port_id} onChange={(v) => update('dest_port_id', v)} />
            <WizardInput label="Route distance KM" type="number" value={form.route_distance_km} onChange={(v) => update('route_distance_km', v)} />
          </WizardGrid>
        ) : null}

        {step === 5 ? (
          <WizardGrid>
            <WizardInput label="ETD" type="datetime-local" value={form.etd} onChange={(v) => update('etd', v)} />
            <WizardInput label="ETA" type="datetime-local" value={form.eta} onChange={(v) => update('eta', v)} />
            <WizardInput label="ATA" type="datetime-local" value={form.ata} onChange={(v) => update('ata', v)} />
            <WizardInput label="Expected transit days" type="number" value={form.expected_transit_days} onChange={(v) => update('expected_transit_days', v)} />
            <WizardInput label="Dock terminal" value={form.dock_terminal} onChange={(v) => update('dock_terminal', v)} />
            <WizardInput label="Berth" value={form.berth} onChange={(v) => update('berth', v)} />
            <WizardSelect label="Customs status" value={form.customs_status} onChange={(v) => update('customs_status', v)} options={['pending', 'cleared', 'inspection', 'hold', 'blocked']} />
            <WizardSelect label="Priority" value={form.priority} onChange={(v) => update('priority', v)} options={['normal', 'high', 'urgent']} />
            <WizardInput label="LC expiry" type="date" value={form.lc_expiry_date} onChange={(v) => update('lc_expiry_date', v)} />
          </WizardGrid>
        ) : null}

        {step === 6 ? (
          <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
            <Review label="Client" value={`${form.name || 'Missing'} - ${form.city || 'City missing'}, ${form.country}`} />
            <Review label="Cargo" value={`${form.cargo_type} / $${Number(form.cargo_value_usd || 0).toLocaleString()} / ${form.weight_kg || 0}kg`} />
            <Review label="Tracking" value={`${form.operator_name || form.carrier} / ${form.tracking_number || 'tracking pending'}`} />
            <Review label="Route" value={`${form.origin_city || 'Origin'} -> ${form.dest_city || 'Destination'}`} />
            <Review label="Timing" value={`ETD ${form.etd || 'now'} / ETA ${form.eta || `${form.expected_transit_days}d`}`} />
            <Review label="Operations" value={`${form.dock_terminal || 'terminal pending'} / ${form.customs_status} / ${form.priority}`} />
          </div>
        ) : null}

        {error ? (
          <div className="mt-4 rounded-lg border border-red-500/40 bg-red-500/10 p-3 text-xs text-red-300">{error.message}</div>
        ) : null}

        <div className="mt-5 flex flex-wrap justify-end gap-2">
          <button type="button" className="btn-outline" disabled={step === 1} onClick={() => setStep(Math.max(1, step - 1))}>Back</button>
          {step < 6 ? (
            <button type="button" className="btn-solid" onClick={() => setStep(Math.min(6, step + 1))}>Next</button>
          ) : (
            <button type="button" className="btn-solid" disabled={isSaving || !requiredReady} onClick={onSubmit}>
              {isSaving ? 'Saving...' : 'Create Client And Cargo'}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

function WizardGrid({ children }) {
  return <div className="grid grid-cols-1 gap-3 md:grid-cols-2">{children}</div>;
}

function WizardInput({ label, value, onChange, type = 'text' }) {
  return (
    <label className="space-y-1 text-xs text-[color:var(--text-muted)]">
      <span className="uppercase tracking-[0.12em]">{label}</span>
      <input className="search-input w-full" type={type} value={value} onChange={(event) => onChange(event.target.value)} />
    </label>
  );
}

function WizardSelect({ label, value, onChange, options }) {
  return (
    <label className="space-y-1 text-xs text-[color:var(--text-muted)]">
      <span className="uppercase tracking-[0.12em]">{label}</span>
      <select className="search-input w-full" value={value} onChange={(event) => onChange(event.target.value)}>
        {options.map((option) => <option key={option} value={option}>{option}</option>)}
      </select>
    </label>
  );
}

function Review({ label, value }) {
  return (
    <div className="rounded-lg border border-[color:var(--glass-border)] bg-[color:var(--bg-card)] p-3">
      <div className="text-[9px] uppercase tracking-[0.12em] text-[color:var(--text-muted)]">{label}</div>
      <div className="mt-1 text-xs font-semibold text-[color:var(--text-primary)]">{value}</div>
    </div>
  );
}

function SummaryCard({ label, value, icon: Icon, color }) {
  return (
    <div className="glass-panel rounded-xl p-4">
      <Icon size={18} color={color} />
      <div className="mt-2 text-2xl font-extrabold" style={{ color }}>{value}</div>
      <div className="text-[10px] uppercase tracking-[0.14em] text-[color:var(--text-muted)]">{label}</div>
    </div>
  );
}

function Info({ label, value, color = 'var(--text-primary)' }) {
  return (
    <div>
      <div className="text-[9px] uppercase tracking-[0.12em] text-[color:var(--text-muted)]">{label}</div>
      <div className="truncate text-xs font-semibold" style={{ color }}>{value}</div>
    </div>
  );
}

export default ClientsPage;
