# PharOS backend

From the repository root:

```sh
python3 -m venv backend/.venv
backend/.venv/bin/pip install -r backend/requirements.txt
backend/.venv/bin/uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Vite proxies `/api` to port 8000 in development. A production frontend build in `dist/` is served by FastAPI. The workshop Ingress strips `/app`; the frontend must resolve requests/assets against its deployment base. `/health` is the deployment readiness path; `/api/health` reports configuration without returning credentials.

## Connections

Set these server-side environment variables; no credentials belong in frontend code, tracked files, query logs or screenshots:

| Variable | Purpose |
| --- | --- |
| `VSS_URL` | Existing team's VSS base URL (`INGRESS_URL` also supported) |
| `VSS_USERNAME` | Team login (`TEAM_USERNAME` also supported) |
| `VSS_PASSWORD` | Team password |
| `WANDB_API_KEY` | W&B/CoreWeave serverless inference key |
| `WANDB_TEAM`, `WANDB_PROJECT` | Optional usage attribution; project defaults to `pharos` |
| `WANDB_MODEL` | Optional model ID; otherwise an instruction model is preferred from `/models`, avoiding explicitly named reasoning models |
| `WEAVE_PROJECT` | Optional `team/project` to trace assessments; requires the optional Weave SDK |
| `WEAVE_ENABLED` | Alternative opt-in: `true` uses `WANDB_TEAM`/`WANDB_PROJECT` |
| `SOCRATA_APP_TOKEN` | Optional NYC Open Data application token |
| `PHAROS_CACHE_DIR` | Optional public cache directory; defaults to gitignored `backend/.cache/` |

Missing VSS/W&B credentials produce explicit unavailable states, not simulated evidence. The video source allowlist lives in memory, so search again after a process restart before playing a clip. A media proxy forwards byte ranges and keeps the VSS JWT server-side. Assessment output validates its schema, evidence IDs and official citation URLs. Inference failure returns distinctly labeled curated guidance.

To enable Weave tracing, install `backend/requirements-tracing.txt` and configure `WEAVE_PROJECT` plus `WANDB_API_KEY`. The traced operation includes assessment context, indexed evidence, query, output and latency; credentials are read inside the operation and are never function arguments. Tracing is optional and fails independently of inference. `tracingStatus: enabled` means instrumentation was initialized; it is not a claim that a trace has been externally verified. `.env.example` documents settings but is not loaded automatically; export values into the backend process or inject them through the deployment Secret.

## Public-source methodology

`GET /api/intersections` uses the latest 12 months present in [NYC collision records](https://data.cityofnewyork.us/Public-Safety/Motor-Vehicle-Collisions-Crashes/h9gi-nx95). Normalized street pairs are grouped across Manhattan and positioned at median reported coordinates. Missing cross streets, invalid coordinates and duplicate collision IDs are excluded. Important source-schema detail: `off_street_name` is the API field labeled **CROSS STREET NAME**; `cross_street_name` contains off-street addresses and is not used for intersection grouping. The source field descriptions are verified at `/api/views/h9gi-nx95.json`.

The response exposes crash counts, distinct injury-involved crash counts (`injuryCrashes`), injury/fatality totals and police-reported contributing factors. Groups rank by injury-involved crash count, then total crash count and name. The optional relative `riskScore` scales `injuryCrashes` against the highest group; it is not a probability or validated risk estimate. The UI should foreground raw counts. Markers and camera associations are approximate. Nearby cameras within 180 m are not guaranteed to view the intersection.

`GET /api/cameras` reads the [public NYC DOT camera directory](https://webcams.nyctmc.org/api/cameras) and retains Manhattan entries. Selected camera images can load directly from their source-provided `imageUrl`; the backend neither proxies nor archives them. Source capture time is unknown. The official viewer requests refreshed images every two seconds; this is not a guarantee of fresh content. Its [subscriber notice](https://webcams.nyctmc.org/subscribers) requires a data-sharing agreement for developer data-feed access. The application includes attribution, source links and that access note. Do not imply continuous video or derive temporal near-miss measurements from snapshots.

Public data is cached on disk (collisions 24 h, camera directory 1 h). Failed refreshes retain the original retrieval timestamp and return `mode: stale`; unavailable sources return empty collections with a source error. No fake records are inserted.

## Checks

```sh
backend/.venv/bin/python -m pytest backend/tests -q
```

Tests cover street normalization, source-field semantics, deduplication, missing coordinates, stale cache timestamps, JWT refresh, source allowlisting, Range playback, credential non-disclosure, and honest disconnected states. Workshop inference and video connections require real environment credentials for end-to-end verification.
