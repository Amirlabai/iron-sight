# Israel boundary style mocks

Local-only comparison pages (not shipped in production builds). They require
`.incoming/il(2).json` and `.incoming/ps.json` on disk; CI does not run these HTML files.
Integrated geodata lives in `dashboard/src/assets/countries.json` and
`backend/src/data/countries.geojson` (regenerate via `scripts/merge_israel_boundary.py`).

Compare two map styles before integrating into Iron Sight.

| File | Style |
|------|--------|
| [israel-boundary-mock-outline.html](israel-boundary-mock-outline.html) | Israel fill + Gaza/WB as dashed interior outlines |
| [israel-boundary-mock-cutout.html](israel-boundary-mock-cutout.html) | Israel fill with Gaza/WB as polygon holes (cutout) |

Data: [.incoming/il(2).json](../.incoming/il(2).json), [.incoming/ps.json](../.incoming/ps.json)

## Run locally

From the **repo root** (so `fetch('../.incoming/...')` resolves):

```powershell
cd "c:\Users\amirl\OneDrive\Documents\GitHub\iron-sight"
python -m http.server 8765
```

Then open:

- http://localhost:8765/scratch/israel-boundary-mock-outline.html
- http://localhost:8765/scratch/israel-boundary-mock-cutout.html

Do not open the HTML files directly with `file://` — the browser will block loading the GeoJSON.
