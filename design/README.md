# PharOS design and interaction

PharOS helps a street safety analyst move from a Manhattan overview to a specific interaction, inspect its evidence, and identify a practical next step. A full-screen architectural map establishes place; a persistent right sidebar holds the evidence. The selected demo focus is Sixth Avenue and West 23rd Street.

## Name, protective eye and lighthouse

PharOS is pronounced like “pharaoh,” following the chosen name. The identity combines a geometric headdress, an abstract protective eye, and a small lighthouse beneath it. The eye represents attention to a place; the lighthouse makes that attention useful by showing a direction for review. Neither symbol implies complete coverage or a guarantee of safety. The product concerns observable street interactions, not identities followed across the city.

The visual reference supplies an architectural vocabulary: pale surfaces, precise outlines, a measured isometric view, and transparent layers that reveal how a place works. PharOS carries that clarity from building to block to intersection. The headdress bands also read as parallel avenues interrupted by cross streets. These are contemporary design interpretations, not claims about the historical meaning of an Egyptian symbol. The added lighthouse is a deliberate visual metaphor for guidance. “OS” remains part of the name; no acronym is invented.

## Logo construction

The vector mark uses a 64 by 64 coordinate system and bilateral symmetry around x = 32. A 26-unit top edge widens into a 34-unit cap. Two tapered side wings create the headdress silhouette. Three sage bands cross each wing, establishing a street-grid rhythm. A centered almond eye spans x = 20.5 to x = 43.5 with a seven-unit gold pupil.

The lower chevron has been replaced by a lighthouse: a triangular roof, rectangular gold lantern, flat balcony, tapered emerald tower, and grounded plinth. Two gold beam wedges spread sideways from the lantern. The straight edges and central doorway make the element read as architecture rather than a smile. Sage wings recede while the gold pupil and light form one vertical focal line. No motion or rotating beam is needed.

The eye outline and tower remain recognizable without gold. The monochrome version uses negative-space bands and `currentColor`. Keep at least six grid units of surrounding clear space. Use the full mark at 32px or larger; the small icon removes wing bands and the doorway to preserve its silhouette. Do not stretch, rotate, animate the pupil, or give the eye a gaze that follows a visitor.

Assets: [color mark](../public/pharos-mark.svg), [small icon and favicon](../public/pharos-favicon.svg), and [monochrome mark](pharos-mark-mono.svg). The [React lockup](../src/BrandMark.tsx) exports `Logo` by default and a named `PharosMark`. The lockup contains only the icon and the text “PharOS”; the icon is decorative when the wordmark already names the product. A standalone mark has an accessible name.

## Material and color

The palette is an architectural model in daylight: ivory buildings, quiet mint water, sage open space, and deep ink labels. It deliberately avoids the visual language of an alarm console. Teal indicates interaction and selection; hazard colors indicate observations requiring attention. Gold is an identity accent, not a severity code.

| Role | Color | Application |
| --- | --- | --- |
| Surface | `#F7F8F4` | Page and panels |
| Deep ink | `#142D34` | Primary text and fine geometry |
| Teal | `#176C68` | Active controls and selected locations |
| Sage | `#B6C7A8` | Headdress bands and quiet natural accents |
| Muted text | `#5B7275` | Secondary information |
| Gold | `#D5AC54` | Logo pupil, lantern and light beams |
| Amber | `#E5B55C` | Lower historical crash intensity |
| Rust | `#C6553D` | Higher historical crash intensity |
| Plum | `#753B56` | Highest historical crash intensity |

Calculated contrast for these brand colors on the ivory surface is 13.53:1 for ink, 5.82:1 for teal, and 4.79:1 for muted text. Gold and rust do not meet 4.5:1 there and are not small-text colors. The current workspace uses related tonal colors for its surfaces and controls; these brand calculations are not a complete interface contrast audit. The heatmap has a textual measure and corresponding list. Unknown coverage is neutral and explicitly labeled; it never appears green or “safe.”

DM Sans carries controls and prose; Manrope gives headings and the wordmark a geometric structure. Time and measurements use tabular numerals. Compact uppercase text is reserved for short metadata labels. Panels use fine borders, shallow shadows, and modest corner radii so the geometry feels intentional without competing with the city.

## City to evidence

The opening view is an oblique Manhattan architectural model centered on the demo focus. Real geography gives the analyst familiar streets, parks, water, and building mass. Compact map controls offer a three-stop walkthrough, crash heatmap, tilt, camera nodes, and a return to 23rd & 6th. Buildings provide context rather than measured traffic conditions; there are no decorative “live” agents.

The right sidebar has three stable tabs. **City** introduces the focus intersection, distance-sorted **Live nearby** cameras, Manhattan history, the hourly chart, and street search. **Camera area** preserves the selected location while showing its footage and available evidence. **Review** searches recorded footage against a question and analyzes a selected clip. This map-and-sidebar organization adapts the reference workspace credited in [third-party notices](../THIRD_PARTY_NOTICES.md), while keeping PharOS's palette and identity.

The focus camera supplies a public still, refreshed while visible and labeled with retrieval time. Its matched historical street-pair profile remains available even if it falls outside the top 100 ranked intersections. Continuous cameras along West Street are listed separately with distance: West 14th and West 23rd are roughly 1.34 km and 1.38 km away. Their video is not assigned to the Sixth Avenue crossing. Historical contributing factors and prevention guidance follow the image in the same panel. “Copy general guidance” copies the general recommendations, not the generated historical assessment.

**When it happens** answers a different question from the heatmap: how reported crashes are distributed across the local hour of day over the displayed historical period. Each bar exposes its count on hover or keyboard focus. The Manhattan chart includes all deduplicated records with usable times, including records excluded from map placement; a location chart uses its own matched street pair. Missing times are counted separately. The highlighted busiest hour is not a live warning or a risk probability.

**Review** retrieves candidate footage, then analyzes its actual bytes through NVIDIA Cosmos and object detection. The fresh review stays attached to that source segment without assigning it to the selected map node. Search criteria, source details, and indexed descriptions are expandable. Model observations require verification against the footage; search similarity and object labels alone cannot establish the requested interaction. Keep potential conflicts distinct from confirmed events and avoid assigning blame.

The implemented heatmap names its measure, injury-involved historical crashes, and its observation window. It remains separate from video observations and projected image-overlap candidates. Raw counts do not establish exposure-adjusted risk. A camera marker alone does not establish a detected event.

## Prospective trajectories

The live observatory separates a continuous 511NY source player from the exact short window submitted for analysis. Acquisition times, analysis completion, and model observations sit beside that saved footage. A current source player must not lend its freshness to an older inference result. Search results remain candidate footage until the requested interaction is reviewed against the actual video.

Observed boxes and trails use actual YOLO frames. Optional dashed paths extend consistent recent image motion for at most two seconds; they are not a calibrated road trajectory or an uncertainty interval. The label **Potential projected image overlap** describes a review candidate, because perspective can place unrelated depths over the same pixels. Recorded moving-camera jobs suppress these projections. Keep severity, observation quality, and analyst review status separate. The [risk model](risk-model.md) specifies the gates; the [runtime record](runtime-verification.md) documents successful hosted live and recorded inference plus analyzed-video playback with visible boxes. Detection accuracy remains unvalidated.

The current workshop collection includes moving-camera New York clips. Their exact intersection is not established. Keep them in a replay evidence collection labeled with that limitation; do not attach them to a chosen intersection merely because it looks plausible. A single public snapshot supports scene inspection, not a measured speed or time to collision.

## Accessible interaction and trust

Map selections have list equivalents, visible focus states, and descriptive button names. Sidebar tabs use arrow keys, Home, and End. Shortcuts are W for walkthrough, H for heatmap, T for tilt, and / for search; typing into a field does not trigger them. Escape closes the connections dialog and ends the walkthrough. The dialog traps focus while open and restores it on close. Important controls should offer approximately 44px targets; a full target-size and contrast audit remains part of accessibility acceptance. A 2D view and reduced-motion transitions reduce navigation effort. Avoid auto-orbit, flashing hazard markers, and motion used only as decoration. These choices support the relevant color, contrast, keyboard, and motion principles in [WCAG 2.2](https://www.w3.org/TR/WCAG22/).

On smaller screens, the sidebar becomes a bottom panel while the map retains the selected location above it. The list remains usable if WebGL or map tiles fail. Loading, no evidence, stale evidence, source failure, and unsupported metric are different states with different explanations.

Low illumination, glare, occlusion, and low contrast may explain why an interaction is hard to see. Headphones alone are not a risk input. Avoid person-level labels such as “reckless,” identity tracking, or appearance-based blame. Review street geometry, yielding, speed, and visibility using the evidence actually available.

## Compact workspace copy

The main screen contains a place, a view, and the next action. The lockup reads “PharOS” without a slogan. Labels name their task or measure: “City,” “Camera area,” “Review,” “Injury crashes,” and “When it happens.” Counts and source modes carry more information than repeated explanatory paragraphs.

Keep a source type and useful age beside the item it qualifies. Put model names, provider details, camera-clock limitations, calibration notes, and full citations in expandable details or **Sources & connections**. Its status rows distinguish authenticated health checks from actual recent inference or retrieval: configured credentials alone do not mean “Connected.” Preserve failure states and uncertainty where they change interpretation: “Camera unavailable,” “Street image,” “Not observed,” and “Needs review” are useful status, not boilerplate. The [copy guide](interface-copy.md) gives concise placement rules.

## Acceptance checks

- The logo reads as headdress, eye and lighthouse in color and monochrome; the simplified icon remains recognizable at 24px.
- Map, list, and panel refer to the same selection; controls never hide the selected node.
- An analyst can move from City to Camera area to Review without confusing a nearby feed with coverage of the selected intersection.
- Source type and useful freshness remain visible; extended provenance and measurement limitations are available in details.
- Hourly crash history, injury-crash ranking, image projections, and reviewed video findings remain separate measures.
- Keyboard navigation, reduced motion, narrow layouts, stale sources, and map failure retain a useful inspection workflow.
