/**
 * IRON SIGHT: Geospatial Utilities (FE-GEO-U1)
 * Optimized for tactical hull generation and coordinate normalization.
 */

/**
 * Calculates the convex hull of a set of 2D points using the Monotone Chain algorithm.
 * @param {Array} points - Array of [lat, lng] coordinates.
 * @returns {Array} - The convex hull coordinates [lat, lng].
 */
export function getConvexHull(points) {
    if (!points || points.length < 3) return points;

    // Sort by latitude (x), then longitude (y)
    const sorted = [...points].sort((a, b) => a[0] !== b[0] ? a[0] - b[0] : a[1] - b[1]);

    const crossProduct = (a, b, c) => {
        return (b[1] - a[1]) * (c[0] - b[0]) - (b[0] - a[0]) * (c[1] - b[1]);
    };

    const lower = [];
    for (const p of sorted) {
        while (lower.length >= 2 && crossProduct(lower[lower.length - 2], lower[lower.length - 1], p) <= 0) {
            lower.pop();
        }
        lower.push(p);
    }

    const upper = [];
    for (let i = sorted.length - 1; i >= 0; i--) {
        const p = sorted[i];
        while (upper.length >= 2 && crossProduct(upper[upper.length - 2], upper[upper.length - 1], p) <= 0) {
            upper.pop();
        }
        upper.push(p);
    }

    upper.pop();
    lower.pop();
    return lower.concat(upper);
}

/** Shared haversine angular distance (radians along great circle). */
export function haversineCore(p1, p2) {
    const dLat = (p2[0] - p1[0]) * Math.PI / 180;
    const dLng = (p2[1] - p1[1]) * Math.PI / 180;
    const a =
        Math.sin(dLat / 2) * Math.sin(dLat / 2) +
        Math.cos(p1[0] * Math.PI / 180) * Math.cos(p2[0] * Math.PI / 180) *
        Math.sin(dLng / 2) * Math.sin(dLng / 2);
    return 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

/**
 * Calculates the Haversine distance between two [lat, lng] points in kilometers.
 */
export function getDistance(p1, p2) {
    return 6371 * haversineCore(p1, p2);
}

/**
 * Calculates the centroid of a set of coordinates.
 */
export function getCentroid(points) {
    if (!points || points.length === 0) return null;
    const sum = points.reduce((acc, p) => [acc[0] + p[0], acc[1] + p[1]], [0, 0]);
    return [sum[0] / points.length, sum[1] / points.length];
}
