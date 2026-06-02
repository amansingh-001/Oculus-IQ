import { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import { AlertOctagon, AlertTriangle, Copy, ExternalLink, Info, MessageCircle } from 'lucide-react';

import { acknowledgeAlert, getAlerts, getAlertDraft, getClientWhatsappAlert, getShipmentById, QUERY_KEYS } from '../api/client';
import SourceBadge from '../components/SourceBadge';

const priorityConfig = {
  critical: { color: 'var(--status-critical)', label: 'Critical Risk', icon: AlertOctagon },
  high: { color: 'var(--status-high)', label: 'High Risk', icon: AlertTriangle },
  medium: { color: 'var(--status-medium)', label: 'Medium Risk', icon: Info },
};

function AlertsPage() {
  const queryClient = useQueryClient();
  const [whatsappDraft, setWhatsappDraft] = useState(null);
  const { data } = useQuery({ queryKey: QUERY_KEYS.alerts, queryFn: () => getAlerts({ acknowledged: false }) });

  const ackMutation = useMutation({
    mutationFn: acknowledgeAlert,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.alerts });
    },
  });

  const draftMutation = useMutation({ mutationFn: getAlertDraft });
  const whatsappMutation = useMutation({
    mutationFn: async (alert) => {
      const shipment = await getShipmentById(alert.shipment_id);
      const clientId = shipment.data?.client_id;
      if (!clientId) return { data: { message: 'No client linked to this alert.', phone: '' } };
      return getClientWhatsappAlert(clientId);
    },
    onSuccess: (payload) => setWhatsappDraft(payload.data),
  });

  const alerts = data?.data || [];
  const counts = useMemo(() => {
    return alerts.reduce(
      (acc, alert) => {
        acc[alert.priority] = (acc[alert.priority] || 0) + 1;
        return acc;
      },
      { critical: 0, high: 0, medium: 0 }
    );
  }, [alerts]);

  return (
    <div className="space-y-4">
      <div className="alerts-header">
        <div className="alert-counts">
          <span className="count critical">
            <AlertOctagon size={14} /> {counts.critical} Critical
          </span>
          <span className="count high">
            <AlertTriangle size={14} /> {counts.high} High
          </span>
          <span className="count medium">
            <Info size={14} /> {counts.medium} Medium
          </span>
        </div>
      </div>

      {alerts.map((alert, index) => {
        const config = priorityConfig[alert.priority] || priorityConfig.medium;
        const HighlightIcon = config.icon;

        return (
          <motion.div
            key={alert.id}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.05, duration: 0.3 }}
            className="alert-card"
            style={{ borderColor: config.color, borderLeftColor: config.color }}
          >
            <div className="alert-left">
              <span
                className="alert-badge"
                style={{ color: config.color, borderColor: config.color, background: `${config.color}1A` }}
              >
                {config.label}
              </span>
              <div className="alert-title">
                {alert.title}
                <HighlightIcon size={14} color={config.color} />
              </div>
              <div className="alert-sub">Shipment {alert.shipment_id} · {alert.priority.toUpperCase()}</div>
              <div className="mt-2">
                <SourceBadge source={alert.source || 'seed'} updatedAt={alert.last_updated} showUpdated />
              </div>
              <p className="alert-desc">{highlightRoute(alert.ai_summary)}</p>
              {draftMutation.isSuccess && draftMutation.variables === alert.id ? (
                <div className="alert-draft">
                  <div className="font-semibold">{draftMutation.data?.data?.subject}</div>
                  <div className="mt-2 text-[color:var(--text-secondary)]">{draftMutation.data?.data?.body}</div>
                </div>
              ) : null}
            </div>
            <div className="alert-actions">
              <button className="btn-outline" onClick={() => whatsappMutation.mutate(alert)}>
                <MessageCircle size={13} /> Notify Client
              </button>
              <button className="btn-outline" onClick={() => draftMutation.mutate(alert.id)}>
                View Draft
              </button>
              <button className="btn-solid" onClick={() => ackMutation.mutate(alert.id)}>
                Acknowledge
              </button>
            </div>
          </motion.div>
        );
      })}
      {whatsappDraft ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
          <div className="glass-panel w-full max-w-xl rounded-xl p-5">
            <div className="mb-3 flex items-center justify-between">
              <div className="text-sm font-bold text-[color:var(--text-primary)]">WhatsApp Alert Composer</div>
              <button type="button" className="btn-outline" onClick={() => setWhatsappDraft(null)}>Close</button>
            </div>
            <textarea
              readOnly
              value={whatsappDraft.message || ''}
              className="min-h-56 w-full rounded-lg border border-[color:var(--glass-border)] bg-[color:var(--bg-card)] p-3 text-xs text-[color:var(--text-secondary)]"
            />
            <div className="mt-3 flex flex-wrap gap-2">
              <button type="button" className="btn-solid" onClick={() => navigator.clipboard?.writeText(whatsappDraft.message || '')}>
                <Copy size={13} /> Copy Message
              </button>
              {whatsappDraft.phone ? (
                <button
                  type="button"
                  className="btn-outline"
                  onClick={() => {
                    const phone = whatsappDraft.phone.replace(/[^\d+]/g, '').replace('+', '');
                    window.open(`https://wa.me/${phone}?text=${encodeURIComponent(whatsappDraft.message || '')}`, '_blank', 'noopener,noreferrer');
                  }}
                >
                  <ExternalLink size={13} /> Open WhatsApp
                </button>
              ) : null}
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}

function highlightRoute(summary) {
  if (!summary) return summary;
  return summary;
}

export default AlertsPage;
