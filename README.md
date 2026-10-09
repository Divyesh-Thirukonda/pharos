# PharOS

PharOS is a Manhattan street-safety workspace built with React, TypeScript, MapLibre, and FastAPI. A 3D map and a right sidebar bring crash history, street cameras, and actual-video review together. The selected demo focus is Sixth Avenue and West 23rd Street. Its identity combines an emerald headdress, protective eye, and lighthouse with gold beams.

**Hosted app:** [Open PharOS](https://team-12-app.thecosmoslabs.com/app/?v=beacon). This versioned link avoids HTML retained by an older cached release.

## Run locally

Use Node.js 22.12+ and Python 3.10+. From the repository root:

```sh
npm install
python3 -m venv backend/.venv
backend/.venv/bin/pip install -r backend/requirements.txt
backend/.venv/bin/uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

In a second terminal:

```sh
npm run dev
```

Open the local URL printed by Vite, normally `http://127.0.0.1:5173`. Vite forwards `/api` requests to FastAPI on port 8000. Public map and camera data need network access; public-source reads work without workshop credentials.

See [backend setup](backend/README.md) and [.env.example](.env.example) for VSS, inference, and optional Weave configuration. Direct video analysis needs `COSMOS3_REASON_URL`, `YOLO_URL`, and `GPU_BEARER_TOKEN`; structured review also needs `WANDB_API_KEY`. Export these values into the backend process; `.env.example` is not loaded automatically. Keep credentials on the server. Missing connections produce an explicit unavailable state while public-data features remain usable.

## What is implemented

- A full-screen architectural map with a compact **City / Camera area / Review** sidebar, street search, crash heatmap, camera nodes, tilt control, and a three-stop walkthrough.
- A public DOT still image at the demo focus, its matched crash history, contributing factors, time-of-day chart, prevention guidance, and an optional AI-assisted historical review.
- Five nearby continuous 511NY feeds on West Street: West 14th, West 23rd, Houston, West 42nd, and Vestry Streets, ordered by distance from the demo focus. They show different intersections, not Sixth Avenue / West 23rd Street.
- **When it happens** charts of reported crashes by local hour, available for Manhattan and matched street-pair profiles.
- Recorded New York video search with a query-specific retrieval plan. Results are candidate footage; semantic similarity does not verify that the requested interaction occurred.
- Direct-video adapters that send an actual capture to NVIDIA Cosmos and YOLO, followed by a structured W&B review. A complete hosted Vestry Street job is verified; it returned `not_observed` for its eight-second window.
- Observed object boxes and window-local tracks, with optional two-second image-plane extrapolations after four consistent observations. No manual scenario supplies map findings.
- Public-source caching, stale/unavailable states, source links, configuration status, and optional assessment tracing.

Use **W** for walkthrough, **H** for the crash heatmap, **T** for tilt, and **/** for search. Sidebar tabs support arrow keys, Home, and End. On narrow screens the sidebar becomes a bottom panel. **Sources & connections** opens current service checks and source details without crowding the map.

## Read the map correctly

The heatmap and ranked list use **injury-involved crash counts**, not live near misses or crash probabilities. An injury crash is a distinct reported collision with at least one recorded injury. Intersections rank by `injuryCrashes`, then total crash count and name. The API returns the top 100 groups plus any matched Sixth Avenue / West 23rd Street profile separately in `metadata.focusIntersections`; showing the demo focus does not change its rank. Reported factors do not prove the cause of a future event.

The backend dynamically finds the latest Manhattan crash date in [NYC Open Data](https://data.cityofnewyork.us/Public-Safety/Motor-Vehicle-Collisions-Crashes/h9gi-nx95) and requests the preceding twelve months. The source window observed during development on **October 9, 2026 was June 12, 2025 through June 11, 2026**. These dates are not hardcoded: use the response and on-screen period for the current window. The retrieval time describes when PharOS fetched the records, not when the source last recorded a crash.

Street names are normalized and grouped as pairs; map positions use median reported coordinates. Records without a usable cross street or coordinate are excluded and duplicate collision IDs are removed. Collision data is cached for 24 hours; the camera directory for one hour. Failed refreshes preserve the original retrieval time and mark the cache stale.

Hourly bars count **all reported crashes with a known local `crash_time`**, not only injury crashes or camera events. The Manhattan chart includes deduplicated records excluded from map placement; an intersection chart uses only its matched group. Missing or invalid times are counted separately. Bars are time-of-day totals over the displayed historical period, not an hourly live incident timeline or exposure-adjusted risk.

Up to three [NYC DOT cameras](https://webcams.nyctmc.org/map) within **180 m** may be associated with an intersection. Proximity does not guarantee that the camera sees the crossing, and camera direction may change. The selected public image refreshes every **15 seconds while the page is visible**. “Image loaded” is the browser retrieval time; the provider supplies no capture timestamp. These are still images, not continuous video. Developer data-feed access is subject to NYC DOT's [subscriber agreement](https://webcams.nyctmc.org/subscribers).

The demo focus uses the official [6 Ave @ 23 St camera](https://webcams.nyctmc.org/map?cameras=fcc24aa5-4da0-48f2-aa43-e70e4677517c) at 40.7429026, −73.9927978. It supplies still images. The nearest verified continuous feeds are West Street / West 14th Street, about 1.34 km away, and West Street / West 23rd Street, about 1.38 km away. Neither provides exact coverage of the focus intersection.

The [official 511NY registry](https://api-511x-nysdot.carsprogram.org/cameras/map-features) supplies genuine continuous HLS video. Advancing playlists and H.264 decoding were verified on October 9, 2026. Vestry reports 640×352; the other four allowlisted feeds report 352×240. Playback can lag the street; the source clock is unverified. PharOS is testing public viewer streams from a closed allowlist. Formal approval under the [developer terms](https://511ny.org/help/24) has not been obtained; public reachability is not a license claim.

Analysis captures up to eight seconds at four frames per second and at most 640 pixels wide. The final hosted Vestry job completed with an eight-second 640×352 capture, 32 detection frames, and 43 window-local tracks in 14.533 seconds. It returned `not_observed`, no conflict claim, and no recommended interventions. The saved final response (local verification record) retains the exact video hash, model provenance, and timings. Local tracks are not unique people or event counts; one successful job is not a detection-accuracy benchmark.

Capture jobs have a 30-minute expiry target with cleanup on job requests and worker completion, plus storage limits; this is not a permanent video archive. Projected image overlap is a review candidate: perspective can make objects at different depths overlap. No calibrated road speed, physical TTC, or collision probability is reported. Recorded moving-camera jobs suppress projections, and headphones alone are excluded as risk evidence.

Motion-event claims need evidence across multiple sampled frames with a bounded interval. An unsupported single-frame claim is downgraded to `uncertain`, with the original model interpretation retained for review. A model-supported result is never automatically a confirmed near-miss count.

## Sponsor integration status

Runtime use is confirmed for three of the [event's four sponsor technologies](https://tokensand.com/vastnyc): VAST retrieval, fresh NVIDIA video inference, and W&B query planning and structured review. Cursor's review attempt stopped at authentication. See the [runtime verification record](design/runtime-verification.md) for exact results and limits.

| Sponsor | Runtime use | Observed result |
| --- | --- | --- |
| VAST Data | Search and source-media access through the existing workshop VSS | Two query-specific public searches returned 15 and 18 candidate clips, with event counts unknown; recorded MP4 playback also verified |
| NVIDIA | Fresh raw-video interpretation and workshop object detection | `nvidia/cosmos3-nano-reasoner` analyzed the final captured bytes in 4.494 seconds; YOLO returned 32 detection frames in 1.081 seconds |
| CoreWeave (Weights & Biases) | Query planning and structured review of fresh visual observations | `meta-llama/Llama-3.3-70B-Instruct` returned the final connected fresh-video review in 3.317 seconds at 18:46 UTC |
| SpaceXAI (Cursor) | Code-review attempt using the workshop VM's `agent` CLI | Returned “Authentication required”; no completed Cursor use is claimed |

The live job completed without component errors and its captured-media route returned HTTP 206 with an MP4 header. A separate recorded-video job (local verification record) completed on a five-second source segment in 14.821 seconds, also returning `not_observed`. Analyzed-copy playback with object boxes was verified before the current sidebar redesign. These checks establish the inference flows, not detection accuracy. Weave tracing remains optional and disabled; no trace delivery is claimed.

The status panel uses `/api/system/status`. Cosmos/YOLO statuses reflect authenticated model/health probes cached for 30 seconds; a health response does not prove video inference. VSS/W&B use actual operations in the current server process: configured-but-unused is **Not verified**, and a success older than 15 minutes is **Check needed**. A failed check is **Not connected**. Historical successful runs above remain distinct from current connection status.

## Demo in three steps

1. In **City**, open the **6th Ave & West 23rd St** focus card. **Camera area** shows its still image, matched history, hourly reports, factors, and next steps. **Copy general guidance** copies those general recommendations, not the generated assessment.
2. Return to **City** and choose a **Live nearby** feed. Monitoring starts bounded analyses while visible, at least 30 seconds apart after the previous job finishes. Compare the result with its analyzed footage and optional image-plane projections. Use **Monitor off** to pause new requests.
3. Open **Review**, search for an interaction, inspect **Search criteria**, and analyze a candidate's actual footage. Open **Sources & connections** to inspect service status. A search match is not a verified near miss.

## Build and checks

```sh
npm test
npm run build
backend/.venv/bin/python -m pytest backend/tests -q
```

The frontend build type-checks TypeScript and writes `dist/`. FastAPI serves that directory in production. `/health` reports server readiness, `/api/health` reports configuration, and `/api/system/status` distinguishes service checks from recorded inference operations. None returns credentials.

The current revision passes **76 tests: 60 backend and 16 frontend**, and the production frontend build succeeds. Checks include hourly-history semantics, focus-area inclusion, and runtime status states. The redesigned hosted app was verified on October 9, 2026: the focus camera image, real hourly data, sidebar navigation, and a fresh West 23rd Street video job all worked. That 8-second 352×240 job completed in 14.034 seconds using NVIDIA Cosmos, YOLO, and W&B, returned `not_observed`, and had no component errors. A fresh `distracted driver` search returned 15 archive candidates and source playback was verified; these are not event counts. The status panel confirmed VAST, NVIDIA, and W&B connections, with Cursor and Weave unavailable. Details and earlier historical-review results are recorded in the runtime verification document. Passing checks does not establish near-miss detection accuracy or trace delivery.

Workshop packaging, the `/app` route, and deployment steps are in the [deployment guide](deploy/README.md).

## Design and research

Read the [design and HCI rationale](design/README.md), [source comparison](design/data-sources.md), [risk model](design/risk-model.md), and [interface-copy guide](design/interface-copy.md). The [color logo](src/assets/pharos-mark.svg), [favicon](src/assets/pharos-favicon.svg), and [monochrome logo](design/pharos-mark-mono.svg) are included. Layout adaptation credits and the exact reference revision are in [third-party notices](THIRD_PARTY_NOTICES.md).
