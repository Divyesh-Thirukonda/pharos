# PharOS runtime verification

Public app: [Open PharOS](https://team-12-app.thecosmoslabs.com/app/). Checks below are from October 9, 2026; timestamps are UTC. No credentials are included. Named files under `artifacts/` are local verification records excluded from the published repository; screenshot descriptions below are historical records, not current interface previews.

**Verified inference result:** the deployment tested at **18:46 UTC** completed a fresh Vestry Street video job with all three model stages connected, no errors, `not_observed`, and no recommended interventions. A recorded-video job also completed earlier, with browser playback and visible object boxes. That deployment added temporal evidence requirements after a prior model made an unsupported single-frame conflict claim. These are functional checks, not detection-accuracy measurements or confirmed near-miss findings.

**Current interface revision:** the map and right sidebar now use **City / Camera area / Review**, a Sixth Avenue / West 23rd Street demo focus, five nearby continuous feeds, hourly crash-history charts, the lighthouse identity, and **Sources & connections**. The frontend production build succeeds and **76 tests pass: 60 backend and 16 frontend**. The video jobs and screenshots below predate this layout revision; they establish the named inference paths, not a new deployment or a visual check of the current interface.

## Hosted raw-video verification

The final deployed job record (`artifacts/final-deployed-verification.json`, local only) preserves job `60b31c16e83e400dbd7a6a606f991673`, source `511ny-32998` at West Street / Vestry Street, and all observations. It finished with `status: completed`, `stage: Fresh video analysis complete`, and no errors.

| Measurement | Observed result |
| --- | --- |
| Server acquisition interval | 18:46:27.203732–18:46:33.908113; analysis completed 18:46:41.736493 |
| Actual analyzed MP4 | 8.0 seconds, 4 fps, 640×352, 919,069 bytes |
| Video identity | SHA-256 `f89072677f8a4019023b70b453f58e1623515a85d5d9c44379b746dd2542b3b8` |
| Fresh NVIDIA Cosmos | `nvidia/cosmos3-nano-reasoner`; 4.494 seconds; `inputType: actual_video_bytes`, matching video hash, `reusedIndexedDescription: false` |
| YOLO | `YOLO11 (workshop detector)`; 1.081 seconds; detections across 32 sampled frames |
| Fresh W&B assessment | `meta-llama/Llama-3.3-70B-Instruct`; 3.317 seconds; `source: fresh_video_inference`, `assessmentStatus: connected` |
| Total job duration | 14.533 seconds, including 6.704 seconds acquiring/transcoding source video; Cosmos and YOLO ran concurrently |
| Tracking output | 43 window-local tracks, 71 per-frame projections, zero projected-overlap flags |
| Event result | `not_observed`; three qualitative scene observations with unknown timing; `nextSteps: []` |

Both GPU adapters received the same captured MP4 bytes. Cosmos provenance explicitly records the matching hash; YOLO supplies frame detections from that job input. The server acquisition interval is shorter than the clip duration because HLS can supply already buffered segments. It does not establish the source's original capture clock, broadcast delay, or a street-to-alert latency benchmark.

The 43 tracks are fragmented local associations, not 43 unique vehicles or people. Repeated per-frame projections are not separate incidents. A `not_observed` result makes zero event claims for this question and window; it is not proof that no risk existed or that the detector has zero false negatives. Qualitative scene observations remain model interpretations, even when no event is claimed.

The packaged Linux FFmpeg initially crashed on HLS. The successful hosted jobs used the system-decoder fix. The earlier 18:10 live proof (`artifacts/live-video-verification.json`, local only) records a separate successful run in 13.149 seconds; its media route returned HTTP 206 with an MP4 header. These measurements describe different captured windows.

The earlier live-analysis screenshot (`artifacts/pharos-live-final.jpg`, local only) shows a later Vestry monitoring window playing with observed car boxes and the `not_observed` result. Native playback reported 640×352, `readyState: 4`, `paused: false`, and `currentTime: 0.018`. Its visible receipt interval is 14:48:58–14:49:05 ET, with analysis completed at 14:49:13 ET; it is a different window from the 18:46 UTC API proof above. This verifies analyzed-video presentation and playback in the preceding layout, not the current sidebar design, box accuracy, or event-detection performance.

## Temporal evidence guard and monitoring

The pre-guard monitoring responses (`artifacts/final-monitoring-verification.json`, local only) preserve an important failure case: job `2c1a8161c773445f94a5dd90c452ada2` returned a model `supported` verdict despite unknown event intervals and a single-frame limitation. **That result is an unverified model claim, not a confirmed near miss.** The artifact is retained to make the failure visible; it must not be included in verified-event counts.

For recognized motion-event questions, the final backend requires a bounded observation interval spanning at least one sample interval—0.25 seconds at 4 fps—and rejects an explicitly single-frame Cosmos account. A supported claim lacking this evidence becomes `uncertain`; `modelVerdict` preserves the original claim, observations are labeled unverified interpretations, and intervention suggestions are cleared. Copied generic guidance details are filtered. These rules cannot prove that model-supplied times or descriptions are correct; human video review remains necessary.

The final 18:46 job verifies connected inference, richer scene observations, and an empty recommendation list for `not_observed`. It does not exercise a positive claim being downgraded; that branch is covered by controlled tests. Monitoring defaults on for a selected live camera, begins windows at least 30 seconds apart after the previous job completes, and pauses when the page is hidden. It retains the previous timestamped result while a new window processes. The earlier monitoring record shows repeated jobs, not uninterrupted analysis of every source frame.

## Recorded video and browser verification

The recorded-job response (`artifacts/recorded-video-verification.json`, local only) preserves job `91444006ae2d49cd9d71cd86629303c8`, completed at **18:15:30.850860**, for the question `near miss pedestrian on phone`. The source was VSS candidate `debc2610c447d40d3056fa6e`, filename `20261008_070736_VID_20261006_174811_003_chunk_0023_segment_004_of_006.mp4`. Its exact intersection and recording time remain unknown.

| Measurement | Observed result |
| --- | --- |
| Prepared analyzed copy | 5.0 seconds, 4 fps, 640×360, 540,945 bytes; server preparation 18:15:16.029737–18:15:22.322771 |
| Video identity | SHA-256 `7b355aceb2956ebf0162187623934bdfe60f688cde4ec4a37c3f1dd37733456f`; Cosmos provenance records the same hash and actual video bytes |
| Fresh inference | Cosmos 1.037 seconds, YOLO 2.739 seconds, W&B 5.715 seconds; the same model IDs as the live job |
| Total job duration | 14.821 seconds; completed without component errors |
| Detection and tracking output | 20 frames, 73 local track fragments, zero projections or projected-overlap flags because recorded-camera motion is uncompensated |
| Event result | `not_observed`; no positive evidence of the requested near miss, with unknown event timestamps |
| Browser check | Analyzed copy played with `readyState: 4`, 640×360, `paused: false`; visible boxes over pedestrians and bicycles |

The earlier mobile analyzed-video screenshot (`artifacts/recorded-analysis-mobile.jpg`, local only) shows the saved footage, observed boxes, excerpt-preparation times, and zero verified matches in the preceding layout. It verifies rendering and playback of this analyzed copy, not the current sidebar design, bounding-box precision, identity continuity, phone use, or a near-miss false-negative rate. Detector class labels such as `cell phone` are model hypotheses; a class appearing somewhere in a frame does not establish the full queried interaction.

This 18:15 archive response predates the final temporal guard and no-event recommendation refinement. Its generic next-step links are historical output, not current proof that interventions were warranted. The final live job above verifies the later empty-action behavior for `not_observed`.

## Current source and search checks

| Check | Observed result | What it establishes |
| --- | --- | --- |
| Official 511NY HLS | Public master playlists returned HTTP 200. Houston's media sequence advanced from 50172 to 50178 with five-second segments; H.264 decoding reported 352×240 and 15 fps. | An advancing continuous source, rather than an updating JPEG or static recording. |
| Hosted live player | Native live-video playback reached `readyState: 4`. | Browser playback worked in the tested session; no claim about inference latency or source capture time. |
| Public search at 17:53:22 | `distracted driver`: HTTP 200, connected, 15 unique candidates, `eventCount: null`, every candidate `not_analyzed`; 5.7 seconds. | W&B query planning and VSS candidate retrieval worked. No distracted-driver event was verified. |
| Public search at 17:53:22 | `near miss pedestrian on phone`: HTTP 200, connected, 18 unique candidates, `eventCount: null`, every candidate `not_analyzed`; 11.6 seconds. | Query-specific evidence requirements and retrieval worked. No near miss or phone-related distraction was verified. |

The sanitized search response record (`artifacts/search-verification.json`, local only) preserves both public requests, timings, candidate counts, and their distinct retrieval plans. Both plans used `meta-llama/Llama-3.3-70B-Instruct`; each retained the original question and identified attention or intent as unobservable. A retrieval requirement is not an observation. Similarity scores and result counts do not measure event prevalence or accuracy.

The current live-video allowlist covers West Street at Vestry, Houston, West 42nd, West 14th, and West 23rd Streets. The [official registry](https://api-511x-nysdot.carsprogram.org/cameras/map-features) supplies the stream links. Vestry's manifest reports 640×352; the other four report 352×240. At 18:55:44 UTC, West 14th and West 23rd both passed an advancing-playlist and H.264 decode check. They are about 1.34 km and 1.38 km from the demo focus, whose exact DOT camera supplies still images. See the [source comparison](data-sources.md) for IDs and check details. Source timestamps, stream delay, and camera-view coverage remain unverified. PharOS is testing publicly reachable viewer streams; formal approval under the [511NY developer agreement](https://511ny.org/help/24) has not been obtained.

The tracker requires four consistent adjacent observations, uses window-local IDs, and breaks ambiguous or missing associations. Its optional two-second projections describe image motion. They cannot establish road speed, physical TTC, or a collision. Recorded moving-camera jobs retain observed tracks but suppress projections and projected-overlap flags. Full behavior and validation limits are in the [risk model](risk-model.md).

## Historical source checks retained from the earlier build

These checks were performed at approximately 16:52–17:08 and remain evidence of their named data paths. They do not verify fresh raw-video analysis.

| Check | Observed result |
| --- | --- |
| Manhattan crash aggregation | Connected; 12,907 source records, 5,084 excluded, 2,587 normalized street-pair groups. Latest available twelve-month period: June 12, 2025–June 11, 2026. |
| First ranked street pair | Chrystie Street / Delancey Street: 24 crashes, 17 injury-involved crashes, 19 injured people, zero fatalities. Positions use median reported coordinates. |
| NYC DOT directory and image | 377 Manhattan cameras. A Central Park West / 86 Street image returned HTTP 200 JPEG, 21,781 bytes, `Cache-Control: no-store`; capture time unknown. This endpoint supplies a still image. |
| Recorded source media | A `bytes=0-1023` range request returned HTTP 206 and an MP4 header. Browser playback reached `readyState: 4`, 1920×1080, duration 5.005 seconds, and advancing time with `paused: false`. |

At **17:05:40**, a historical-only POST to `/app/api/assessments` returned HTTP 200 in 17.9 seconds with connected W&B inference. Three factors matched supplied reports: driver inattention/distraction (7), failure to yield (4), and traffic control disregarded (3); three recommendations used approved source URLs. These counts are police-report history, not visual detections.

At approximately **17:08**, the earlier **Review this moment** flow reviewed the indexed description for `20261008_073828_GX010001_chunk_0004_segment_001_of_006.mp4` and displayed an AI-assisted review with three approved references. The older review screenshot (`artifacts/pharos-evidence-review.jpg`, local only) records that interface. That action is superseded by the direct-video workflow. Its success established text review of indexed evidence, not new NVIDIA analysis of raw footage, a verified near miss, or attachment to a map intersection.

Historical assessment output used strict JSON schema and independent checks on evidence IDs, approved URLs, and unsupported motion claims. Earlier public failures returned labeled curated guidance. These positive requests are functional examples, not a reliability benchmark.

## Deployment and measurement boundaries

- At 17:05, obsolete HTML cache validators returned HTTP 200 with `Cache-Control: no-store, max-age=0` and no ETag/Last-Modified. Hashed asset caching remained available.
- Current local checks: **76 tests passed**—60 backend and 16 frontend—and the production frontend build succeeded. Controlled tests establish expected behavior, not field detection accuracy.
- The deployment used by the 18:46 proof passed 70 tests and used an 822,491-byte bundle, SHA-256 `459d72ef3d2cb563c5b688fb654ead173d4871cff46ead456c31b5692e60b203`; rollout completed for pod `pharos-6d85f9b78f-99npt`. This bundle predates the current map/sidebar revision.
- Capture jobs target 30-minute retention from creation, with cleanup on job requests/worker completion and caps of 24 jobs and 150 MiB. This is opportunistic expiry, not guaranteed deletion at an exact time.
- Historical crash counts, retrieved candidates, repeated frame detections, window-local tracks, projected image overlaps, model-supported observations, and human-reviewed near misses are distinct quantities. Missing or uncomputed evidence is unknown, not zero.
- Continuous source playback does not imply continuous inference: monitoring analyzes successive bounded windows and can leave gaps. Acquisition and completion timestamps do not reveal the camera's original clock or broadcast delay.
- Three sponsor integrations have runtime evidence: VAST retrieval, fresh NVIDIA raw-video inference, and W&B planning/review. Cursor's VM review attempt required authentication; no successful Cursor use or Weave trace delivery is claimed.
- `/api/system/status` distinguishes current-process operation results from authenticated GPU health probes. Configuration alone is unverified; a health response does not establish successful inference on a video. Previously successful jobs do not guarantee a current connection after restart.

No manual trajectory lab is part of the current observation workflow. Historical map counts come from [NYC collision records](https://data.cityofnewyork.us/Public-Safety/Motor-Vehicle-Collisions-Crashes/h9gi-nx95); direct camera observations must remain tied to their actual source footage and capture window.

## Sidebar release verification — October 9, 2026, 19:18 UTC

The redesigned app is deployed at https://team-12-app.thecosmoslabs.com/app/. Release bundle SHA-256: `3311c3947cdb50eb9428b453b02a147b833f0cf9c932b878e13ef246cbfd59b8`. Frontend entry: `index-DXpbwjoM.js`. The release exposes actual hourly bins, the focus street pair outside the top 100, five sorted continuous feeds, and service health/operation status. Local checks passed 60 backend and 16 frontend tests plus the production build.

A browser-triggered live job `7fd8969f40f947968bf02141462239e6` used West Street at West 23rd Street at 19:17:56 UTC. It captured eight seconds at 352×240 and four frames per second. Capture took 6.157 s, YOLO 0.799 s, Cosmos 2.597 s, and W&B assessment 5.279 s; total 14.034 s. Its video hash was `a14ddf5a14fb318c88e85ae8eadc1b2442ae516fa3f6cd43b451259efddfc11e`; Cosmos recorded the same hash and actual-video-bytes input. The result was `not_observed`, with no next steps or component errors. This is successful inference on real footage, not a near-miss accuracy claim.

The focus image loaded at its actual 352-pixel width. Focus history contains ten reported crashes and four injury crashes in the displayed source period, with the busiest recorded hour 18:00–19:00 (four reports). Desktop and narrow layouts, camera navigation, Review query persistence, and connection disclosures were inspected through the browser. Private local verification JSON and screenshots are intentionally excluded from the public repository.

At 19:21–19:24 UTC, a browser search for `distracted driver` returned 15 VAST candidate clips through the W&B query planner. One initial media attempt failed transiently; selecting another candidate and retrying the first restored playback at 1920-pixel video width. A direct range probe on the first candidate returned HTTP 206. The status panel returned connected for Cosmos, YOLO, W&B, and VAST; Weave and Cursor remained unavailable. The UI displayed candidate counts rather than asserting distracted-driving events.

## Logo cache correction

The initial sidebar release served current application code, but Cloudflare still cached the old unversioned `/app/pharos-mark.svg` (smile) asset. A cache-busted request confirmed the lighthouse bytes were already deployed. The canonical logo and favicon now live under `src/assets` and are processed by Vite into content-hashed URLs. The application and HTML favicon reference those generated files, so future logo edits change their URLs automatically. This fixes the stale logo without requiring visitors to clear their cache.

## Main URL and heatmap toggle

The main URL is https://team-12-app.thecosmoslabs.com/app/ with no version query. Legacy `v` query parameters are removed by the frontend while preserving other query parameters and the hash. The heatmap control previously hid only the density layer, leaving crash markers visible; H now toggles density, halos, markers, and their hit targets together. The control displays On/Off, repeated keydown events are ignored, and shortcuts do not run while the connections dialog is open or a text field is active. Heat rendering remains visible at close zoom and the crash glow is stronger in the 3D view. The production build succeeds.


## Playback and demo query revision — October 9, 2026

The DOT still-image client now checks every second while visible, with an in-flight guard. Nearby HLS playback remains continuous and now uses a smaller live-edge buffer, automatic preloading, and player-module preload on camera hover/focus. Archive and captured MP4s preload automatically. Detection overlays follow decoded video frames through `requestVideoFrameCallback`. Live analysis captures four-second windows at eight fps; it starts another window one second after the preceding review completes. GPU detection results can appear before Cosmos/assessment finish. These are serial video-window jobs, not uninterrupted one-second inference on every broadcast frame.

Search candidate ordering now checks requested actor/action conditions in the indexed descriptions, then uses fused retrieval rank. Phone use by a stationary cyclist or an unrelated actor does not outrank walking phone use. This ordering is retrieval relevance, never verification. The selected archive candidate starts actual NVIDIA review automatically. No demo query shortcut or preset was added.

The exact query `distracted walker almost hit` returned 18 candidates. Three promising phone/walking/traffic candidates were analyzed on the hosted service: `706c3a4bf735431dbe63390e61bdc6e1`, `98d2b43bb8d94926adb205522deb998e`, and `bdf75b6940864299963e413f2a61df52`. All returned `not_observed`. The first shows a phone user with an SUV passing behind, without clear evasive action; the other two do not resolve the requested conjunction. A genuine distracted-walker near miss has **not** been established from this archive. Do not pitch the demo query as a verified successful match.

Production build and 79 tests passed (63 backend, 16 frontend), including the actor-specific ranking regression and bounded four-second/eight-fps live capture.


The user replaced the almost-hit criterion with two short observable-risk demos: `Pedestrian phone crossing` and `Obstructed crosswalk`. The assessment instruction now explicitly prohibits adding an unrequested near-miss or vehicle-conflict requirement to a simpler behavior/obstruction question. A matching, completed archive review can promote a retrieved clip, serve its actual prepared MP4, and reuse the review for the exact query/source while its capture remains available (30-minute bounded cache). This never applies to completed live-camera jobs. Nothing pins source IDs or demo answers in the frontend or backend. The actor/action and requested-obstruction-location ranking regressions, plus exact-query cached-review isolation, are covered by backend tests.


### Verified two-prompt demos

- **Pedestrian phone crossing** — source `c0a94d1895faab1b850918d8`, job `4a7405c09d204ccc8a5e62353ddba3dd`; `supported`. The pedestrian is clearly using his phone while crossing the street. Analyzed MP4 SHA256 `eeb9f39b3ac0a1aa83b746fdbc124e1898fd9f3ce34c43e34ab094a465441676`; 5.0 seconds, 8.0 fps. Total inference pipeline 11.033 seconds. Models: NVIDIA Cosmos3 Nano Reasoner, YOLO11, W&B Llama 3.3 70B.
- **Obstructed crosswalk** — source `2fe3bd2df3ce7669576b6de2`, job `8804af8510b048408d6ca28319dc97a5`; `supported`. The crosswalk is partially obstructed by a red construction barrier and orange traffic cones. Pedestrians are crossing the street despite the obstruction. A traffic controller is present and holding an orange flag. The white van is stopped at the intersection. Analyzed MP4 SHA256 `4a31bbb06ea83896bdd53062af6d79fbfb8680ace45067fbabe133085f09942f`; 5.0 seconds, 8.0 fps. Total inference pipeline 11.703 seconds. Models: NVIDIA Cosmos3 Nano Reasoner, YOLO11, W&B Llama 3.3 70B.

Both exact prompts were entered into the hosted Review UI, each selected its actual reviewed clip as candidate 01, and both MP4s reached `readyState=4` with the full five seconds buffered. Native video playback was checked visually: the phone user is visible crossing, and the barrier/barrels are visibly within the crossing. No collision or near miss was claimed. The later single-player refinement removes the initial source player once the analyzed capture is available and collapses repeated observations under **Observed signals**.

The new live capture was 4.0 seconds at 8.0 fps, 352×240, 144,236 bytes. Full job took 7.895 seconds with no component errors. This establishes working faster window inference, **not one-second streaming inference or all-broadcast-frame coverage**.
