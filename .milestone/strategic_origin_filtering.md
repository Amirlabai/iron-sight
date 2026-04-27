# Strategic Origin Filtering (MISSION: NEWSFLASH_GUARD)

Restrict automatic detection of long-range origins (Iran, Yemen) to only be considered when a `newsFlash` alert context is active, preventing false strategic alarms for regional salvos.

## Tactical Scope & Rationale
Currently, the `TrackingEngine` and `ThreatProcessor` automatically identify "Iran" or "Yemen" based on geographic polygons and large city counts. This mission implements a strict gate: these origins will only be validated if a `newsFlash` (Potential Threat Warning) is present in the current alert batch or already active in the theater.

## Proposed Technical Changes

### Backend Core
#### [MODIFY] [engine.py](file:///c:/Users/amirl/OneDrive/Documents/GitHub/iron-sight/backend/src/core/engine.py)
- **`get_origin` refactor**:
  - Add `allow_strategic: bool = True` parameter.
  - Guard the "Vector Projections Strategy" block (lines 289-294) with `if allow_strategic:`.
  - If `allow_strategic` is False, bypass Iran/Yemen polygon checks and fallback directly to Gaza/Lebanon distance analysis.

#### [MODIFY] [threat_processor.py](file:///c:/Users/amirl/OneDrive/Documents/GitHub/iron-sight/backend/src/core/threat_processor.py)
- **`process` signature update**:
  - Accept `active_events: dict` and `has_newsflash_in_batch: bool`.
- **`_process_missiles` logic**:
  - Calculate `allow_strategic` by checking if `has_newsflash_in_batch` is True OR if any event in `active_events` has `category == "newsFlash"` and `end_time is None`.
  - Guard `force_iran` threshold check (line 43) with `allow_strategic`.
  - Pass `allow_strategic` to `engine.get_origin`.

### Backend Service
#### [MODIFY] [main.py](file:///c:/Users/amirl/OneDrive/Documents/GitHub/iron-sight/backend/src/main.py)
- **Alert Ingestion Pre-scan**:
  - Before the `for alert_payload in alerts` loop (line 129), compute `has_newsflash_in_batch = any(a.get('type') == 'newsFlash' for a in alerts)`.
- **Processor Invocation**:
  - Update call to `processor.process(a_type, cities_raw, active_events, has_newsflash_in_batch)`.

## Verification & Hardening Plan

### Automated Validation
- **Simulator Stress Test**:
  - Trigger a 50-city missile alert without a newsFlash. Verify origin demotes to "Lebanon/Gaza".
  - Trigger a 50-city missile alert WITH a preceding or simultaneous newsFlash. Verify origin validates as "Iran".

### Manual Intelligence Check

---

## Implementation Record

Completed: 2026-04-27

### Changes Deployed

| File | Change |
|---|---|
| `engine.py` | Added `allow_strategic` flag to `get_origin` to gate long-range projections. |
| `threat_processor.py` | Updated `process` and `_process_missiles` to compute and pass `allow_strategic` context. |
| `main.py` | Implemented batch pre-scan for newsFlash alerts and propagated state to processor. |

### Summary

Successfully implemented the `NEWSFLASH_GUARD` logic. Long-range origin detection for Iran and Yemen is now strictly contingent on the presence of a `newsFlash` (Potential Threat Warning) within the current alert batch or an active theater event. This ensures high-fidelity regional classification for standard salvos while maintaining strategic readiness for confirmed escalations.

