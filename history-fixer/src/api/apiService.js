import { TACTICAL_API_URL, MISSION_KEY } from '../utils/constants';

const headers = {
  'Content-Type': 'application/json',
  'X-Mission-Key': MISSION_KEY
};

export const fetchHistory = async (category = 'all') => {
  const url = category === 'all' 
    ? `${TACTICAL_API_URL}/api/history` 
    : `${TACTICAL_API_URL}/api/history?category=${category}`;
  const res = await fetch(url);
  return res.json();
};

export const updateAlertOrigin = async (id, category, origin_name, origin_coords) => {
  const res = await fetch(`${TACTICAL_API_URL}/api/history/update`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ id, category, origin_name, origin_coords })
  });
  return res.json();
};

export const splitAlert = async (id, category) => {
  const res = await fetch(`${TACTICAL_API_URL}/api/history/split`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ id, category })
  });
  return res.json();
};

export const mergeAlerts = async (ids, category) => {
  const res = await fetch(`${TACTICAL_API_URL}/api/history/merge`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ ids, category })
  });
  return res.json();
};

export const fetchCities = async () => {
  const res = await fetch(`${TACTICAL_API_URL}/api/cities`);
  return res.json();
};
