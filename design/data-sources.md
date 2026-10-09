# PharOS data sources and coverage

PharOS combines place, footage, and evidence without treating them as interchangeable. Continuous, calibrated video can support trajectory analysis. A current snapshot supports visual inspection. Historical crashes and environmental context support prioritization, but neither establishes a near miss happening now.

## Continuous Manhattan video

The current [511NY site](https://511ny.org/) uses this public [camera registry](https://api-511x-nysdot.carsprogram.org/cameras/map-features). Its camera views include HLS video URLs as well as still images. On October 9, 2026, the Houston, West 42nd, and West 14th Street master playlists returned HTTP 200 with cross-origin access enabled. Houston's media sequence advanced from 50172 to 50178 with five-second segments and no end marker; `ffprobe` decoded H.264 at 352×240 and reported 15 fps. This establishes an advancing video source, not a guarantee that every listed camera is available or sees a useful crossing.

The registry supplied eight West Street locations. PharOS currently allowlists the five marked **Yes**; the others are researched alternatives. Coordinates describe the camera location, not the bounds of its view. Resolution comes from the fetched HLS master manifest unless marked unverified.

| Official camera | Latitude, longitude | Stream path | Resolution | App allowlist |
| --- | --- | --- | --- | --- |
| [32998 · Vestry Street](https://511ny.org/camera/32998) | 40.7228915, −74.0114845 | `R11_277` | 640×352 | Yes |
| [32991 · West Houston Street](https://511ny.org/camera/32991) | 40.7292424, −74.0105167 | `R11_271` | 352×240 | Yes |
| [32995 · West 42nd Street](https://511ny.org/camera/32995) | 40.7620712, −74.0009178 | `R11_274` | 352×240 | Yes |
| [32997 · West 14th Street](https://511ny.org/camera/32997) | 40.7422765, −74.0087175 | `R11_276` | 352×240 | Yes |
| [32992 · West 34th Street](https://511ny.org/camera/32992) | 40.7571131, −74.0047018 | `R11_272` | 352×240 | No |
| [32994 · West 57th Street](https://511ny.org/camera/32994) | 40.7714757, −73.9941676 | `R11_273` | Unverified | No |
| [32996 · West 23rd Street](https://511ny.org/camera/32996) | 40.7482608, −74.0076232 | `R11_275` | 352×240 | Yes |
| [32999 · Spring Street](https://511ny.org/camera/32999) | 40.7258881, −74.0109027 | `R11_278` | 352×240 | No |

Each stream follows `https://s9.nysdot.skyvdn.com/rtplive/{stream path}/playlist.m3u8`; for example, [Vestry Street HLS](https://s9.nysdot.skyvdn.com/rtplive/R11_277/playlist.m3u8). These are provider-controlled endpoints and may change. The source capture clock and broadcast delay are unverified. Most views are low resolution; continuous video alone does not establish useful pedestrian visibility or adequate track quality.

PharOS is testing publicly reachable viewer streams from a closed allowlist. The current [511NY developer agreement](https://511ny.org/help/24), updated September 18, 2026, describes approved feed access, a request process reviewed weekly, and conditions for reuse and redistribution. The same content is available from the site's [public help API](https://api-511x-nysdot.carsprogram.org/cms/helpPages/24). No agreement has been accepted or formal feed approval obtained for PharOS. HTTP access and permissive CORS do not establish a reuse license. A continuing deployment must resolve the applicable access and redistribution terms.

## Sixth Avenue and West 23rd Street focus

The selected demo focus uses the official NYC DOT camera **6 Ave @ 23 St**, ID `fcc24aa5-4da0-48f2-aa43-e70e4677517c`, at 40.7429025573452, −73.992797766009. The [DOT directory](https://webcams.nyctmc.org/api/cameras) supplies its coordinates and [image endpoint](https://webcams.nyctmc.org/api/cameras/fcc24aa5-4da0-48f2-aa43-e70e4677517c/image). The matching 511NY entry, 21158, is a still-image view. No continuous video endpoint for this exact crossing was verified.

The official registry fetched at **18:55:05 UTC on October 9, 2026** contained 2,715 camera features and 1,746 HLS views. Ranking continuous views by straight-line distance from the exact DOT coordinates found West Street / West 14th Street closest at **1,343 m**, followed by West Street / West 23rd Street at **1,384 m**. No closer continuous midtown or east-side view appeared in that registry. These are nearby feeds, not views of the focus crossing.

At **18:55:44 UTC**, both nearest feeds decoded H.264 at 352×240 and 15 fps. West 14th's media sequence advanced from 51189 to 51191; West 23rd's advanced from 51172 to 51173. Neither playlist had an end marker, and both passed a three-frame FFmpeg decode. This confirms advancing video at the time of the check; it does not verify pedestrian visibility, scene calibration, or continued availability.

## Captured footage and inference

The pipeline captures up to eight seconds of source video, transcodes to four frames per second at no more than 640 pixels wide, and retains the exact analyzed MP4 with its SHA-256 hash. It sends those bytes to NVIDIA Cosmos for fresh visual interpretation and the workshop YOLO service for detections. W&B structures the fresh observations against the user's question and approved guidance. Hosted checks succeeded for an eight-second 640×352 Vestry capture and a five-second 640×360 archive segment; both returned `not_observed` for their questions. The analyzed archive copy played in the browser with object boxes. The [runtime record](runtime-verification.md) preserves timings, hashes, screenshots, and the limits of these functional checks.

The capture has server acquisition start/end times and video-relative frame times. These are not the camera's original capture timestamps. Keep live-source playback separate from the saved analyzed window: a completed review applies to that window, even if the player is already showing a later scene. Monitoring requests successive bounded windows and can leave temporal gaps.

Capture jobs target 30 minutes of retention from creation. Cleanup occurs on job creation/list/detail requests and worker completion; completed or failed jobs may be removed sooner to maintain the 24-job and 150 MiB limits. It is not an exact wall-clock deletion service. Files left by a prior process are removed during cleanup, and job metadata is held in memory. Temporary downloaded archive originals are removed after transcoding. This is a short-lived review cache, not a permanent archive; downloaded or externally traced copies would need their own policy.

## Recorded workshop evidence

The [hosted PharOS app](https://team-12-app.thecosmoslabs.com/app/) also connects to the existing workshop VSS. On October 9, 2026, two query-specific searches returned 15 and 18 candidates with unknown event counts. Recorded source media returned HTTP 206 and played in the browser. Earlier indexed descriptions and the fresh-video model both identify `nvidia/cosmos3-nano-reasoner`; they are different evidence paths. An earlier catalog showed 168 `new_york` clips associated with `nyc_bike_gopro-1`; that is not a stable total or proof of exact location.

The replay collection has unverified intersection coordinates and calibration. Search finds candidate footage; similarity is not evidence that a requested near miss occurred. The new direct-video action analyzes actual bytes against the question. Keep the source available for human review, preserve negation and uncertainty, and do not attach a replay to a real map node merely because it was retrieved. Recording time may be unknown even when an upload date or dated filename exists. The [Cosmos Labs builders challenge](https://workshop.thecosmoslabs.com/labs/builders-challenge) is the workshop entry point.

## Real time camera options

| Source | Appropriate role | Access and evidence boundary |
| --- | --- | --- |
| [NYC TMC camera map](https://webcams.nyctmc.org/map) | Broad NYC location discovery and current visual inspection | The public directory supplies image URLs; the public viewer retrieves JPEG snapshots. Its [subscriber agreement](https://webcams.nyctmc.org/api/cameras/subscriber-api-agreement) explicitly contemplates usable video signals, but does not expose a verified HLS/RTSP endpoint or cadence. Do not generalize the public still-only API to every approved subscriber service. [DOT feed guidance](https://www.nyc.gov/html/dot/html/about/datafeeds.shtml#realtime) |
| [511NY developer feeds](https://511ny.org/help/24) | Selected continuous Manhattan views and agency context | Public HLS access is verified for selected views above; formal developer feed approval and applicable reuse terms remain distinct. The current registry supersedes the legacy developer/API links found in older search results. |
| [EarthCam Times Square](https://www.earthcam.com/usa/newyork/timessquare/) | Licensed focused coverage of a few locations | Offers streaming views and still presets. Its [FAQ](https://www.earthcam.com/faq.php) and [link policy](https://www.earthcam.com/site/linktous.php) distinguish linking from embedding/rebroadcasting; the [EULA](https://cc8.earthcam.net/eula/web) restricts capture and recording without permission. No EarthCam ingestion or reuse rights are established here. |
| Authorized fixed camera or sensor pilot | Best candidate for an actual calibrated near-miss pipeline | Arrange an intersection view with continuous timestamps, known geometry, sufficient resolution, and documented retention and access. This is an acquisition option, not a feed already connected to PharOS. |
| Consented fleet or bicycle video | Replay review and potential future mobile-camera analysis | Camera pose, ego-motion, time synchronization, and scene scale must be solved before metric trajectory claims. The current workshop replay remains qualitative. |

Prefer one well-observed intersection over broad but intermittent images when validating detection. Check real capture cadence, repeated frames, dropped intervals, camera movement, resolution, occlusion, and clock offsets. Distinguish the time an image was captured from the time PharOS fetched it.

## Context and basemap sources

The implemented map uses NYC crash records, the public camera directory, and OpenFreeMap/OpenStreetMap building massing. Other sources below are researched extensions rather than connected feeds. The observed crash window on October 9, 2026 was June 12, 2025–June 11, 2026; the backend derives that period dynamically from the latest available record. It ranks normalized street pairs by injury-involved crash count, then total reports and name. The top 100 groups are returned alongside a separately matched focus profile in `metadata.focusIntersections`; displaying the focus does not change its rank. Nearby DOT camera matches within 180 m are approximate; their images refresh every 15 seconds while visible, with retrieval time distinct from unknown capture time.

The **When it happens** chart bins police reports by their local `crash_time` hour, labeled `America/New_York` in the API. It counts all known-time crashes over the displayed period, not only injury crashes. Collision IDs are deduplicated before aggregation. Manhattan bins include records excluded from map placement because of unusable streets or coordinates; an intersection's bins include only that matched group. Missing or invalid hours are reported separately. A zero bar means no known-time reports in that bin, not proof that no event happened. These bars are time-of-day history, not a continuous incident timeline or exposure-adjusted risk.

| Source | Use in PharOS | Limitation |
| --- | --- | --- |
| [NYC DOT traffic speeds](https://www.nyc.gov/html/dot/html/about/datafeeds.shtml#realtime) | Corridor congestion context | Sensors are concentrated on major arterials and highways; aggregate link speeds do not establish an individual vehicle's motion. |
| [NYPD Motor Vehicle Collisions](https://data.cityofnewyork.us/Public-Safety/Motor-Vehicle-Collisions-Crashes/h9gi-nx95) | Historical reported-crash layer | Police-reported collisions are not near-miss observations. Inspect the actual maximum event date and update metadata before showing freshness. The [federal catalog](https://catalog.data.gov/dataset/motor-vehicle-collisions-crashes) currently carries a notice about a disrupted update process, so a nominal update schedule is insufficient. |
| [NYC311 service requests](https://data.cityofnewyork.us/Social-Services/311-Service-Requests-from-2010-to-Present/erm2-nwe9/data) | Reports of lighting, visibility, street, or signal problems | Reports are leads for review, not verified current scene conditions. The [current dataset guidance](https://www.nyc.gov/opendata/news/all-news/311-Service-Requests-Updates) separates newer records from the 2010–2019 archive. |
| [National Weather Service API](https://www.weather.gov/documentation/services-web-api) | Nearby observations, forecasts, and weather alerts | Keep station/time metadata. A nearby station does not measure the light or traction at a particular crossing. NWS notes that observations may be delayed by up to 20 minutes. |
| [NYC building footprint metadata](https://github.com/CityOfNewYork/nyc-geo-metadata/blob/main/Metadata/Metadata_BuildingFootprints.md) | Building outlines and height-aware city massing | Roof height above ground and ground elevation are distinct fields. Geometry describes the built environment rather than current camera visibility. |
| [MapLibre examples](https://maplibre.org/maplibre-gl-js/docs/examples/) | Rendering geographic buildings and map layers | Rendering capability is not a data license or evidence of photographic accuracy. Keep the selected basemap's attribution visible. |

## Evidence record and display rules

Keep source identity, source type, capture interval, fetch time, geographic certainty, camera motion, calibration status, observation quality, and review status with each analysis. Use UTC internally and an explicitly labeled New York time display. A failed fetch must not refresh the capture timestamp.

**Sources & connections** reads `/api/system/status`. Cosmos and YOLO use authenticated model/health probes cached for 30 seconds, with last inference recorded separately. VSS and W&B use actual operation results from the current process: configured without use is `unverified`, a recent success is `connected`, a success older than 15 minutes is `stale`, and a failed operation is `unavailable`. Process restarts clear that operation history. Optional Weave configuration does not establish trace delivery, and Cursor is not a runtime service. A green health check is not evidence that a particular video was analyzed.

Actual node panels should show their own source footage and insights, or a clear unavailable state. Do not substitute unrelated footage. If coordinates are unknown, keep the clip outside the location-linked layer. A risk metric that cannot be computed is unavailable, not zero.

For a published deployment, follow the source's applicable access and redistribution terms and carry NYC DOT's [stated attribution and disclaimer](https://www.nyc.gov/html/dot/html/about/datafeeds.shtml#disclaimer) where its data is used. Keep camera and basemap source links available from the interface. Never label the full city “live” when only selected cameras or a replay collection are available.
