/** Shared event fixtures for Vitest utils tests */

export const squareHull = [
  [31.9, 33.9],
  [31.9, 34.1],
  [32.1, 34.1],
  [32.1, 33.9],
];

export const missileEventNear = {
  id: 'evt-near',
  category: 'missiles',
  all_cities: [{ name: 'Tel Aviv', coords: [32.0853, 34.7818] }],
};

export const missileEventWithHull = {
  id: 'evt-hull',
  category: 'missiles',
  clusters: [{ hull: squareHull, cities: [] }],
  all_cities: [],
};

export const newsFlashEvent = {
  id: 'evt-nf',
  category: 'newsFlash',
  all_cities: [],
};
