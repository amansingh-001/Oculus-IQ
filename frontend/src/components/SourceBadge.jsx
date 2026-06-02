const SOURCE_STYLES = {
  gdelt: { label: 'LIVE - GDELT', color: '#10B981', bg: 'rgba(16,185,129,0.15)' },
  weather: { label: 'LIVE - Open-Meteo', color: '#3B82F6', bg: 'rgba(59,130,246,0.15)' },
  csv: { label: 'IMPORTED', color: '#14B8A6', bg: 'rgba(20,184,166,0.15)' },
  seed: { label: 'SYNTHETIC', color: '#9CA3AF', bg: 'rgba(156,163,175,0.15)' },
};

function formatRelativeTime(updatedAt) {
  if (!updatedAt) return null;
  const updated = new Date(updatedAt);
  if (Number.isNaN(updated.getTime())) return null;
  const diffMs = Date.now() - updated.getTime();
  const minutes = Math.max(Math.floor(diffMs / 60000), 0);
  if (minutes < 1) return 'just now';
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

function SourceBadge({ source, updatedAt, showUpdated = true }) {
  const style = SOURCE_STYLES[source] || SOURCE_STYLES.seed;
  const relative = formatRelativeTime(updatedAt);

  return (
    <div className="flex items-center gap-2">
      <span
        className="rounded-full px-2 py-0.5 text-[9px] font-semibold uppercase tracking-[0.12em]"
        style={{ color: style.color, background: style.bg, border: `1px solid ${style.color}33` }}
      >
        {style.label}
      </span>
      {showUpdated && relative ? (
        <span className="text-[10px] text-[color:var(--text-muted)]">Updated {relative}</span>
      ) : null}
    </div>
  );
}

export default SourceBadge;
