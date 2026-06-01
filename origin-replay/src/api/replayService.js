import { TACTICAL_API_URL, MISSION_KEY, HISTORY_FETCH_LIMIT } from '../utils/constants';

const headers = {
  'Content-Type': 'application/json',
  'X-Mission-Key': MISSION_KEY,
};

async function parseJsonResponse(res, label) {
  const text = await res.text();
  let data;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    throw new Error(`${label}: invalid JSON (${res.status})`);
  }
  if (!res.ok) {
    const msg = data?.error || data?.message || res.statusText || String(res.status);
    throw new Error(`${label}: ${msg}`);
  }
  return data;
}

export async function fetchHistory(category = 'missiles') {
  const params = new URLSearchParams();
  params.set('category', category);
  params.set('limit', String(HISTORY_FETCH_LIMIT));
  const url = `${TACTICAL_API_URL}/api/history?${params.toString()}`;
  const res = await fetch(url);
  const data = await parseJsonResponse(res, 'History fetch');
  return Array.isArray(data) ? data : [];
}

export async function fetchOriginReplay({ id, category = 'missiles', allowStrategic = true }) {
  const res = await fetch(`${TACTICAL_API_URL}/api/origin/replay`, {
    method: 'POST',
    headers,
    body: JSON.stringify({
      id,
      category,
      allow_strategic: allowStrategic,
    }),
  });
  return parseJsonResponse(res, 'Origin replay');
}

export async function fetchHealth() {
  const res = await fetch(`${TACTICAL_API_URL}/api/history?limit=1`);
  const data = await parseJsonResponse(res, 'Health');
  return Array.isArray(data) ? { status: 'OPERATIONAL', rows: data.length } : data;
}
