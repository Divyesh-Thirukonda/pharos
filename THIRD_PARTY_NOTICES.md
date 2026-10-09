# Third party notices

## PharOS Elmir layout reference

The map-first workspace layout and interface organization were adapted with reference to [elmir132/pharos-elmir](https://github.com/elmir132/pharos-elmir), specifically commit [`c4bc68b8261542d78b35ca6147e863ecfedf9a4f`](https://github.com/elmir132/pharos-elmir/tree/c4bc68b8261542d78b35ca6147e863ecfedf9a4f), inspected on October 9, 2026.

The relevant source is [`web/pharos/index.html`](https://github.com/elmir132/pharos-elmir/blob/c4bc68b8261542d78b35ca6147e863ecfedf9a4f/web/pharos/index.html), with design context in [`design/README.md`](https://github.com/elmir132/pharos-elmir/blob/c4bc68b8261542d78b35ca6147e863ecfedf9a4f/design/README.md). The adapted elements are the full-screen map, compact map controls, right-hand tabbed workspace, and the progression from city history to a camera area and recorded-video review. They are implemented here in React and styled with PharOS's emerald, sage, and ivory palette. This project's original headdress/eye mark was revised to add a geometric lighthouse.

No `LICENSE`, `COPYING`, or `NOTICE` file, or explicit license declaration in the inspected README/interface source, was found at that reference revision. This attribution does not assert an open-source license or create a license grant. Rights in the reference material remain with its authors.

## Maps, data and dependencies

Map rendering uses MapLibre with OpenFreeMap/OpenStreetMap data; map attribution remains visible in the interface. Camera video and images are provided by 511NY/NYSDOT and NYC DOT. Historical crash records come from NYC Open Data. Their source links and access conditions are recorded in [data sources](design/data-sources.md).

Third-party packages retain their own notices and license terms. This document records the interface adaptation and source attribution; it does not replace notices distributed with installed dependencies or grant rights to provider footage.
