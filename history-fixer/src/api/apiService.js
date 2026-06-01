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

export const fetchHistory = async (category = 'all') => {
  const params = new URLSearchParams();
  if (category !== 'all') params.set('category', category);
  params.set('limit', String(HISTORY_FETCH_LIMIT));
  const qs = params.toString();
  const url = `${TACTICAL_API_URL}/api/history${qs ? `?${qs}` : ''}`;
  const res = await fetch(url);
  const data = await parseJsonResponse(res, 'History fetch');
  return Array.isArray(data) ? data : [];
};

export const updateAlertOrigin = async (id, category, origin_name, origin_coords, origin_ml_scores = null) => {
  const body = { id, category, origin_name, origin_coords };
  if (origin_ml_scores) body.origin_ml_scores = origin_ml_scores;
  const res = await fetch(`${TACTICAL_API_URL}/api/history/update`, {
    method: 'POST',
    headers,
    body: JSON.stringify(body),
  });
  return parseJsonResponse(res, 'Update');
};

export const suggestOrigin = async (payload) => {
  const res = await fetch(`${TACTICAL_API_URL}/api/history/suggest-origin`, {
    method: 'POST',
    headers,
    body: JSON.stringify(payload),
  });
  return parseJsonResponse(res, 'Suggest origin');
};

export const projectEntry = async (payload) => {
  const res = await fetch(`${TACTICAL_API_URL}/api/history/project-entry`, {
    method: 'POST',
    headers,
    body: JSON.stringify(payload),
  });
  return parseJsonResponse(res, 'Project entry');
};

export const fetchTrainingExport = async (category = 'missiles', format = 'json') => {
  const res = await fetch(
    `${TACTICAL_API_URL}/api/history/training-export?category=${category}&format=${format}`,
    { headers: { 'X-Mission-Key': MISSION_KEY } },
  );
  if (format === 'csv') {
    if (!res.ok) throw new Error(`Export failed: ${res.status}`);
    return res.text();
  }
  return parseJsonResponse(res, 'Training export');
};

export const splitAlert = async (id, category) => {
  const res = await fetch(`${TACTICAL_API_URL}/api/history/split`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ id, category }),
  });
  return parseJsonResponse(res, 'Split');
};

export const mergeAlerts = async (ids, category) => {
  const res = await fetch(`${TACTICAL_API_URL}/api/history/merge`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ ids, category }),
  });
  return parseJsonResponse(res, 'Merge');
};

export const fetchCities = async () => {
  const res = await fetch(`${TACTICAL_API_URL}/api/cities`);
  return parseJsonResponse(res, 'Cities');
};

export const fetchHealth = async () => {
  const res = await fetch(`${TACTICAL_API_URL}/api/history?limit=1`);
  const data = await parseJsonResponse(res, 'Health');
  return Array.isArray(data) ? { status: 'OPERATIONAL', rows: data.length } : data;
};
