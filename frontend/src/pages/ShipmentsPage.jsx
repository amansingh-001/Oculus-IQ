import { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { FileUp, Pencil } from 'lucide-react';

import {
  getClients,
  getCsvTemplate,
  getShipments,
  importShipmentsCsv,
  QUERY_KEYS,
  updateShipment,
} from '../api/client';
import SourceBadge from '../components/SourceBadge';

const filterOptions = ['All', 'Sea', 'Delayed', 'Critical'];

function ShipmentsPage() {
  const queryClient = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: QUERY_KEYS.shipments,
    queryFn: () => getShipments({ page: 1, page_size: 500 }),
  });
  const { data: clientsData } = useQuery({ queryKey: QUERY_KEYS.clients, queryFn: getClients });
  const [search, setSearch] = useState('');
  const [activeFilter, setActiveFilter] = useState('All');
  const [clientFilter, setClientFilter] = useState('');
  const [showTariffs, setShowTariffs] = useState(false);
  const [editShipment, setEditShipment] = useState(null);
  const [editForm, setEditForm] = useState({ status: '', eta: '', notes: '' });
  const [csvModalOpen, setCsvModalOpen] = useState(false);
  const [csvText, setCsvText] = useState('');

  const updateMutation = useMutation({
    mutationFn: ({ id, payload }) => updateShipment(id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.shipments });
    },
  });

  const importMutation = useMutation({
    mutationFn: ({ text }) => importShipmentsCsv(text, true),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.shipments });
    },
  });

  const templateMutation = useMutation({
    mutationFn: getCsvTemplate,
    onSuccess: (payload) => {
      const columns = payload?.data?.columns?.map((col) => col.name) || [];
      const example = payload?.data?.example_row || {};
      if (!columns.length) return;
      const header = columns.join(',');
      const row = columns.map((col) => example[col] || '').join(',');
      setCsvText(`${header}\n${row}`);
    },
  });

  const shipments = data?.data || [];
  const clients = clientsData?.data || [];

  const filteredShipments = useMemo(() => {
    const query = search.trim().toLowerCase();

    return shipments.filter((shipment) => {
      const matchesQuery = !query
        || shipment.id.toLowerCase().includes(query)
        || shipment.carrier.toLowerCase().includes(query)
        || shipment.origin.city.toLowerCase().includes(query)
        || shipment.destination.city.toLowerCase().includes(query);

      if (!matchesQuery) return false;
      if (clientFilter && shipment.client_id !== clientFilter) return false;

      if (activeFilter === 'Sea') return shipment.mode === 'sea';
      if (activeFilter === 'Delayed') return shipment.status === 'delayed';
      if (activeFilter === 'Critical') return shipment.risk_score >= 85 || shipment.risk_level === 'critical';

      return true;
    });
  }, [shipments, search, activeFilter, clientFilter]);

  if (isLoading) {
    return <div className="text-[color:var(--text-secondary)]">Loading shipments...</div>;
  }

  return (
    <div className="space-y-4">
      <div className="table-controls">
        <input
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          placeholder="Search routes, carriers, cargo IDs, clients..."
          className="search-input"
        />
        <select value={clientFilter} onChange={(event) => setClientFilter(event.target.value)} className="search-input max-w-xs">
          <option value="">All clients</option>
          {clients.map((client) => (
            <option key={client.id} value={client.id}>{client.name}</option>
          ))}
        </select>
        <label className="flex items-center gap-2 text-xs text-[color:var(--text-secondary)]">
          <input type="checkbox" checked={showTariffs} onChange={(event) => setShowTariffs(event.target.checked)} />
          Show tariff details
        </label>
        <button type="button" className="btn-outline" onClick={() => setCsvModalOpen(true)}>
          <FileUp size={13} /> Import CSV
        </button>
        <div className="filter-chips">
          {filterOptions.map((option) => (
            <button
              key={option}
              type="button"
              className={`chip ${activeFilter === option ? 'active' : ''}`}
              onClick={() => setActiveFilter(option)}
            >
              {option}
            </button>
          ))}
        </div>
      </div>

      <div className="glass-panel overflow-hidden rounded-xl">
        <table className="w-full text-left text-sm">
          <thead className="table-head">
            <tr>
              <th className="px-5 py-3">ID</th>
              <th className="px-5 py-3">Client</th>
              <th className="px-5 py-3">Route</th>
              <th className="px-5 py-3">Carrier</th>
              <th className="px-5 py-3">Mode</th>
              <th className="px-5 py-3">Status</th>
              <th className="px-5 py-3">Disruption Risk Index</th>
              <th className="px-5 py-3">Source</th>
              {showTariffs ? <th className="px-5 py-3">Tariff</th> : null}
              {showTariffs ? <th className="px-5 py-3">Landed Cost</th> : null}
              <th className="px-5 py-3">Actions</th>
            </tr>
          </thead>
          <tbody>
            {filteredShipments.map((shipment) => {
              const riskColor = shipment.risk_score >= 85
                ? 'var(--status-critical)'
                : shipment.risk_score >= 70
                ? 'var(--status-high)'
                : 'var(--status-ok)';
              const borderColor = shipment.risk_score >= 70 ? riskColor : 'transparent';
              const tariffFlag = (shipment.tariff_rate_pct || 0) > 20;

              return (
                <tr
                  key={shipment.id}
                  className="table-row"
                  style={{
                    borderLeftColor: tariffFlag ? '#F97316' : borderColor,
                    background: tariffFlag && showTariffs ? 'rgba(249,115,22,0.06)' : undefined,
                  }}
                >
                  <td className="px-5 py-3 font-semibold text-[color:var(--ocean-teal)]">{shipment.id}</td>
                  <td className="px-5 py-3 text-[color:var(--text-secondary)]">{shipment.client_name || 'Unassigned'}</td>
                  <td className="px-5 py-3 text-[color:var(--text-secondary)]">
                    <span className="route-from">{shipment.origin.city}</span>
                      <span className="route-arrow"> → </span>
                    <span className="route-to">{shipment.destination.city}</span>
                  </td>
                  <td className="px-5 py-3 text-[color:var(--text-secondary)]">{shipment.carrier}</td>
                  <td className="px-5 py-3">
                    <span className={`mode-pill mode-${shipment.mode}`}>{shipment.mode}</span>
                  </td>
                  <td className="px-5 py-3" style={{ color: statusColor(shipment.status) }}>
                    {shipment.status}
                  </td>
                  <td className="px-5 py-3 font-semibold" style={{ color: riskColor }}>
                    {shipment.risk_score}
                  </td>
                  <td className="px-5 py-3">
                    <SourceBadge source={shipment.source} updatedAt={shipment.last_updated} showUpdated={false} />
                  </td>
                  {showTariffs ? (
                    <td className="px-5 py-3 font-semibold" style={{ color: tariffFlag ? '#F97316' : 'var(--text-secondary)' }}>
                      {shipment.tariff_rate_pct ?? 0}%
                    </td>
                  ) : null}
                  {showTariffs ? (
                    <td className="px-5 py-3 text-[color:var(--text-secondary)]">
                      ${((shipment.tariff_adjusted_cost_usd || shipment.cargo_value_usd || 0) / 1000).toFixed(0)}K
                    </td>
                  ) : null}
                  <td className="px-5 py-3">
                    <button
                      type="button"
                      className="btn-outline"
                      onClick={() => {
                        setEditShipment(shipment);
                        setEditForm({
                          status: shipment.status || '',
                          eta: shipment.eta ? shipment.eta.slice(0, 10) : '',
                          notes: shipment.notes || '',
                        });
                      }}
                    >
                      <Pencil size={13} /> Edit
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {editShipment ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
          <div className="glass-panel w-full max-w-lg rounded-xl p-5 space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm font-bold text-[color:var(--text-primary)]">Update Shipment</div>
                <div className="text-xs text-[color:var(--text-muted)]">{editShipment.id} · {editShipment.client_name}</div>
              </div>
              <button type="button" className="btn-outline" onClick={() => setEditShipment(null)}>Close</button>
            </div>
            <div className="grid grid-cols-1 gap-3">
              <label className="text-xs text-[color:var(--text-muted)]">Status</label>
              <select
                value={editForm.status}
                onChange={(event) => setEditForm((prev) => ({ ...prev, status: event.target.value }))}
                className="search-input"
              >
                {['pending', 'in_transit', 'delayed', 'delivered'].map((status) => (
                  <option key={status} value={status}>{status}</option>
                ))}
              </select>
              <label className="text-xs text-[color:var(--text-muted)]">ETA</label>
              <input
                type="date"
                value={editForm.eta}
                onChange={(event) => setEditForm((prev) => ({ ...prev, eta: event.target.value }))}
                className="search-input"
              />
              <label className="text-xs text-[color:var(--text-muted)]">Notes</label>
              <textarea
                value={editForm.notes}
                onChange={(event) => setEditForm((prev) => ({ ...prev, notes: event.target.value }))}
                className="min-h-28 rounded-lg border border-[color:var(--glass-border)] bg-[color:var(--bg-card)] p-3 text-xs text-[color:var(--text-secondary)]"
              />
            </div>
            <div className="flex items-center justify-end gap-2">
              <button type="button" className="btn-outline" onClick={() => setEditShipment(null)}>Cancel</button>
              <button
                type="button"
                className="btn-solid"
                onClick={() => {
                  updateMutation.mutate({
                    id: editShipment.id,
                    payload: {
                      status: editForm.status,
                      eta: editForm.eta || null,
                      notes: editForm.notes,
                    },
                  });
                  setEditShipment(null);
                }}
              >
                Save Updates
              </button>
            </div>
          </div>
        </div>
      ) : null}

      {csvModalOpen ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
          <div className="glass-panel w-full max-w-2xl rounded-xl p-5 space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm font-bold text-[color:var(--text-primary)]">Import or Update Shipments</div>
                <div className="text-xs text-[color:var(--text-muted)]">Paste CSV text or insert the template.</div>
              </div>
              <button type="button" className="btn-outline" onClick={() => setCsvModalOpen(false)}>Close</button>
            </div>
            <textarea
              value={csvText}
              onChange={(event) => setCsvText(event.target.value)}
              placeholder="Paste CSV data here"
              className="min-h-56 w-full rounded-lg border border-[color:var(--glass-border)] bg-[color:var(--bg-card)] p-3 text-xs text-[color:var(--text-secondary)]"
            />
            {importMutation.data?.meta?.error ? (
              <div className="rounded-lg border border-[color:var(--glass-border)] bg-[color:var(--bg-card)] p-3 text-xs text-[color:var(--status-high)]">
                {importMutation.data.meta.error}
              </div>
            ) : null}
            {importMutation.data?.data ? (
              <div className="space-y-2">
                <div className="text-xs text-[color:var(--text-muted)]">
                  Imported: {importMutation.data.data.inserted || 0} · Updated: {importMutation.data.data.updated || 0} · Errors: {importMutation.data.data.errors?.length || 0}
                </div>
                {importMutation.data.data.errors?.length ? (
                  <div className="rounded-lg border border-[color:var(--glass-border)] bg-[color:var(--bg-card)] p-3">
                    <div className="text-[10px] uppercase tracking-[0.2em] text-[color:var(--text-muted)]">CSV Validation Report</div>
                    <div className="mt-2 max-h-40 space-y-1 overflow-auto text-xs text-[color:var(--text-secondary)]">
                      {importMutation.data.data.errors.slice(0, 20).map((error, index) => (
                        <div key={`${error.row}-${index}`}>
                          Row {error.row}: {error.error}
                        </div>
                      ))}
                    </div>
                    {importMutation.data.data.errors.length > 20 ? (
                      <div className="mt-2 text-[10px] text-[color:var(--text-muted)]">
                        Showing first 20 errors.
                      </div>
                    ) : null}
                  </div>
                ) : null}
              </div>
            ) : null}
            <div className="flex flex-wrap items-center justify-end gap-2">
              <button type="button" className="btn-outline" onClick={() => templateMutation.mutate()}>
                Insert Template
              </button>
              <button
                type="button"
                className="btn-solid"
                onClick={() => importMutation.mutate({ text: csvText })}
              >
                Import CSV
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}

function statusColor(status) {
  if (status === 'delayed') return 'var(--status-high)';
  if (status === 'delivered') return 'var(--status-ok)';
  if (status === 'in_transit') return 'var(--status-info)';
  return 'var(--text-muted)';
}

export default ShipmentsPage;
