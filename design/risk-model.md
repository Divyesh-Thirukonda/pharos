# PharOS potential conflict model

PharOS reviews actual captured street footage alongside historical intersection context. YOLO detections can support short local image tracks; consistent observations can support conditional two-second image-plane projections. These projections are not future truth, calibrated road trajectories, or proof of a near miss. PharOS does not classify people as reckless or infer intent.

## Historical context and location

The map ranks injury-involved reported crashes. **When it happens** charts count all known-time reported crashes by local hour over the displayed historical period. These measures do not share a denominator with captured video: the charts are neither live incident counts nor exposure-adjusted risk. Missing hours remain separate, and Manhattan hourly totals include records excluded from map placement.

The selected Sixth Avenue / West 23rd Street demo focus has a public still camera and a matched historical profile when available. The five continuous West Street feeds are nearby locations with explicit distances; their observations are not transferred to the focus crossing. A camera marker, proximity, or street-name similarity does not establish coverage. The [source record](data-sources.md) gives exact locations and verification scope.

## Current video pipeline

The backend captures at most eight seconds from an allowlisted 511NY stream or a retrieved VSS recording, samples it at four frames per second, and limits width to 640 pixels. The exact saved MP4 and its hash identify the input sent to NVIDIA Cosmos and YOLO. Cosmos supplies fresh visual observations; W&B structures those observations against the user's question. Each verdict is `supported`, `uncertain`, or `not_observed`, with source-relative time ranges only when supplied by the observed evidence. Search relevance and the wording of a question do not establish that an event occurred.

Hosted direct-video jobs succeeded on both an eight-second Vestry Street capture and a five-second recorded New York segment. Each returned `not_observed` for its question; the analyzed archive copy also played in the browser with object boxes. These checks establish the flow from actual bytes through fresh inference, not near-miss accuracy. The [runtime record](runtime-verification.md) retains exact provenance and limits. Failed components remain visibly unavailable; an indexed description is not substituted for a failed fresh Cosmos request.

The **Sources & connections** panel separates configured credentials, authenticated service health, and recent successful operations. A model service responding to a health check cannot validate a track, event, or review. Interpret every video finding from the job's actual input and component results, not a general connection badge.

For recognized motion-event questions, a model `supported` verdict needs at least one bounded video-relative interval spanning a sample interval or longer. At four fps, that minimum is 0.25 seconds. An explicitly single-frame Cosmos account or missing temporal evidence downgrades the verdict to `uncertain`, preserves the original model verdict and raw observation, labels interpretations unverified, and clears interventions. This guard followed an actual unsupported single-frame claim; its purpose is to expose uncertainty rather than conceal the model's output. Bounded timestamps alone do not validate the described motion, so human review is still required. No-event results have no intervention suggestions, and copied generic guidance details are filtered.

## Observed tracks and conditional projections

[`backend/tracking.py`](../backend/tracking.py) consumes YOLO pixel boxes and normalizes geometry to the image. It associates adjacent detections using class, box overlap, footpoint distance, scale consistency, and a motion gate. The footpoint is the box's bottom-center, an image reference rather than a calibrated road contact point. IDs exist only inside one captured window; counts across frames are not unique people or event totals.

A projection needs at least four consistent adjacent observations. Missing frames or detections, time gaps, shape changes, large position jumps, class changes, and ambiguous associations end the track. The system does not interpolate through a disappearance or claim to resolve occluded identities. Direction changes, poor linear fit, or unstable box size suppress projection. These conservative rules reduce unsupported continuations; they are not a validated tracking benchmark.

For an eligible track, a least-squares fit over up to six recent observations estimates image velocity. The projection translates the latest box for at most two seconds and stops at the image boundary. Dashed paths and projected box envelopes mean **if this recent image motion continues**. Their widths are not calibrated physical footprints or statistical confidence intervals. Four-fps sampling can miss brief interactions, and camera movement, perspective, turns, low resolution, and occlusion can invalidate the motion model.

The candidate rule compares pairs of eligible projections. It flags newly overlapping boxes only when their image positions converge and neither already overlaps at the observation time. Its label is **Potential projected image overlap**. Different depths can produce the same image overlap; such a flag is neither a confirmed near miss nor a forecast collision. The reported offset is an extrapolation horizon in image space, not physical time to collision. No risk probability is generated.

Overlay only the detections, trails, and projections belonging to the displayed frame of the saved analyzed window. Keep ongoing live-source playback separate. An analysis can be old relative to the street even when it has just finished; show acquisition and completion times. The camera's source clock and broadcast delay remain unknown. Monitoring starts for a selected live camera, captures four-second windows at eight fps, waits for the previous job to complete, then starts after one second, and pauses when the page is hidden. It preserves the previous timestamped result while processing; it does not imply uninterrupted analysis of every source frame.

## Evidence required for metric claims

Measured speed, physical clearance, and metric trajectory projections require continuous, correctly timed observations and reliable scene calibration. Perspective and scene scale affect the relation between image motion and road motion; [camera calibration research](https://arxiv.org/abs/1702.06451) explicitly treats scale inference as part of speed measurement. PharOS additionally requires camera-motion compensation for moving views. It rejects unsupported metric outputs rather than assigning plausible-looking values.

| Evidence | Permitted output |
| --- | --- |
| Single image or intermittent snapshots | Visible scene conditions and a review prompt; no measured speed, acceleration, TTC, or PET |
| Uncalibrated fixed-camera continuous video | Observed boxes, local image tracks, conditional image-space projections, and qualitative review; physical metrics unavailable |
| Moving-camera replay without verified pose and scale | Qualitative evidence only; no invented fixed-scene physics |
| Continuous calibrated tracks with validated timing | Conditional local trajectories and supported surrogate measurements, with quality flags |

The workshop's moving-camera New York clips remain qualitative replay. Unknown geolocation prevents attaching their observations to a specific intersection. Recorded-video jobs retain observed boxes and tracks but suppress forecasts and projected-overlap flags because camera-motion compensation is unavailable. Observed image trails still must not be interpreted as road trajectories. A meaningful physical forecast requires ground-plane calibration, verified timing, motion compensation when needed, and validation against measured ground truth.

Time to collision, or TTC, estimates when a collision would occur if the relevant motion assumptions continue. Post-encroachment time, or PET, describes the elapsed gap between one road user leaving a shared position and another reaching it. PET is retrospective. Neither is a collision probability. The [FHWA SSAM definitions](https://www.fhwa.dot.gov/publications/research/safety/08050/) supply the terminology, not validation of PharOS or universal thresholds. The current app reports neither calibrated TTC nor PET.

## Review priority

Prioritize the interaction in this order, while keeping evidence quality independent from severity. The current uncalibrated pipeline can describe visible interactions; the metric items below require a future validated measurement path:

1. Converging occupied areas, closing motion, and a short supported TTC.
2. Measured speed and available stopping margin, using explicit assumptions rather than a universal stopping-distance constant.
3. Turning or crossing conflicts, yielding behavior, and signal state when actually visible and time-aligned.
4. Observed hard braking, abrupt evasion, or a small supported retrospective PET.
5. Occlusion, lighting, glare, and scene visibility that affect detection or response.

A vehicle seen near a pedestrian is not enough to establish a near miss. A signal violation must not be inferred from a light facing another approach. A hidden object or interrupted track increases uncertainty; it does not automatically increase confidence in danger. Preserve candidate, reviewed, and rejected outcomes so a human can inspect both the event and the model's claim.

Low-contrast clothing matters only in relation to illumination and the surrounding scene. Describe “low subject contrast under low light” rather than blame the person. [NHTSA's conspicuity review](https://www.nhtsa.gov/book/countermeasures-that-work/pedestrian-safety/countermeasures/other-strategies-behavior-change-4) supports the relevance of visibility to detection; it does not supply an individual collision probability. Headphones alone are excluded as a risk input. Do not infer attention, hearing ability, intent, or fault from appearance.

## Validation before live use

Validate calibration and timestamps against measured ground truth before enabling physical units. Compare detections and track continuity with manually reviewed clips; report false positives and missed events across daylight, darkness, weather, occlusion, and road-user types. Evaluate forecast error at each advertised horizon on held-out scenes. Check threshold sensitivity rather than choosing an impressive-looking alert rate.

The tracking tests exercise normalization, minimum evidence, gaps, ambiguous overlap, class changes, jumps, reversals, convergence, and image boundaries. These checks establish behavior on controlled examples, not field accuracy. A supported model verdict still needs a human to inspect the same video before it becomes a reviewed near-miss finding.

Keep observation duration and exposure information beside aggregation. A busy camera may produce more candidates simply because it sees more interactions. Historical crash counts, image-overlap candidates, model-supported interactions, and human-reviewed near misses remain separate. Recommended next steps should identify the supporting observation and the review needed; they should never promise a quantified safety benefit without evaluation. No person or vehicle is tracked between cameras.
