import { Search } from 'lucide-react';

function cityCount(ev) {
  return (ev.all_cities || []).length;
}

function storedOrigin(ev) {
  const t = ev.trajectories?.[0];
  return t?.origin || '—';
}

export default function EventPicker({
  events,
  selectedId,
  onSelect,
  loading,
  search,
  onSearchChange,
}) {
  const q = search.trim().toLowerCase();
  const filtered = events.filter((ev) => {
    if (!q) return true;
    const id = String(ev.id || '').toLowerCase();
    const origin = storedOrigin(ev).toLowerCase();
    const n = String(cityCount(ev));
    return id.includes(q) || origin.includes(q) || n.includes(q);
  });

  return (
    <aside className="event-picker">
      <div className="picker-header">
        <h2>Archive</h2>
        <span className="picker-count">{filtered.length} events</span>
      </div>
      <div className="search-box">
        <Search size={14} />
        <input
          type="text"
          placeholder="Search ID, origin, city count…"
          value={search}
          onChange={(e) => onSearchChange(e.target.value)}
        />
      </div>
      <div className="event-list">
        {loading && <p className="muted">Loading archive…</p>}
        {!loading && filtered.length === 0 && (
          <p className="muted">No events match.</p>
        )}
        {filtered.map((ev) => (
          <button
            key={ev.id}
            type="button"
            className={`event-card${selectedId === ev.id ? ' selected' : ''}`}
            onClick={() => onSelect(ev)}
          >
            <span className="event-id">#{ev.id}</span>
            <span className="event-meta">
              {storedOrigin(ev)} · {cityCount(ev)} cities
            </span>
            {ev.title && <span className="event-title">{ev.title}</span>}
          </button>
        ))}
      </div>
    </aside>
  );
}
