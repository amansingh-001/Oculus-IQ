import { useQuery } from '@tanstack/react-query';
import { KeyRound, ServerCog } from 'lucide-react';

import { getFeedHealth, QUERY_KEYS } from '../api/client';

function SettingsPage() {
  const { data } = useQuery({ queryKey: QUERY_KEYS.feeds, queryFn: getFeedHealth, refetchInterval: 60000 });
  const feeds = data?.data?.feeds || {};
  const geminiConfigured = Boolean(feeds.gemini?.key_configured);

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <ServerCog size={22} color="var(--ocean-teal)" />
        <div>
          <div className="text-xl font-bold text-[color:var(--text-primary)]">Settings</div>
          <div className="text-xs text-[color:var(--text-muted)]">Read-only environment status and keys</div>
        </div>
      </div>

      <div className="glass-panel rounded-xl p-5 space-y-4">
        <div className="flex items-center gap-2">
          <KeyRound size={14} color="var(--ocean-teal)" />
          <div className="text-sm font-semibold text-[color:var(--text-primary)]">Gemini API Key</div>
        </div>
        <div className="text-xs text-[color:var(--text-secondary)]">
          {geminiConfigured ? 'Configured' : 'Not configured'}
        </div>
        <div className="text-[11px] text-[color:var(--text-muted)]">
          To change the key, edit backend/.env and restart the backend. Keys are never stored in the database.
        </div>
      </div>
    </div>
  );
}

export default SettingsPage;
