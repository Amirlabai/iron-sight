# Multi-Origin Strategy: Combined Target Handling

This document outlines the proposed solution for scenarios where a single city or cluster is targeted by multiple launch origins (e.g., Lebanon and Iran) simultaneously.

## The Problem
Currently, the system clusters cities by proximity (10km) and then infers **one** origin based on the cluster's geographic centroid. If two different countries target the same location at the same time, only one trajectory line will be displayed.

## Proposed Solutions

### 1. Sub-Zone Segmentation
Instead of clustering the entire city, we can identify targeting patterns.
- **Method**: If a city like Tel Aviv receives multiple alerts across different neighborhoods (North vs South vs Center), we treat each sub-neighborhood as a potential distinct target.
- **Visual**: Multiple lines would converge on different points within the same metropolitan area.

### 2. Directional Probability Model
Use a probability score based on the "Alert Window" duration and frequency.
- **Method**: If the northern part of a cluster is expanding faster, increase the weight for Lebanon. If the center is hit repeatedly, trigger an "Iran/Yemen" probability line.
- **Visual**: Display multiple dashed lines representing the different potential origins with varying opacity (alpha) based on probability.

### 3. Iron Dome Intercept Logic (Heuristic)
If we can detect "Intercept" alerts (often a different category in some APIs), we can use the intercept location to calculate the rocket's vector more precisely.
- **Method**: Retro-calculate the vector from the intercept point and the target point to find the true origin angle.

### 4. Overlapping Origin Lines
When an alert hits a major city known to be a multi-origin target:
- **Method**: Always display all "likely" origins (e.g., for Tel Aviv, show a faint line from Gaza, Lebanon, and Iran) until the specific vector is confirmed by the hit pattern.

---
**Status**: Recommendation Only. Implementation deferred to Phase 3.
