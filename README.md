# Eco Route

Calculate fastest, lowest-emissions, and balanced driving routes using OSM roads.
The existing distance/speed, stops, elevation, emissions, and normalized balance
formulas are preserved. Stops and elevation remain zero placeholders.

## Run

Python 3.10+:

```sh
python -m pip install -r requirements.txt
python routing.py --place 'San Ramon, California, USA' --output-dir output
```

Enter an eco preference from 0 to 1 and start/destination latitude and longitude.
The CLI prints distance (km), estimated time (minutes), estimated emissions
(grams CO2), ordered road segments, and nearby named landmarks. Coordinates snap
to road nodes. A trip snapping to the same node produces a zero-distance Point.
Unreachable destinations produce a message without exports.

Each route is exported as `fastest.geojson`, `lowest-emissions.geojson`, or
`balanced.geojson` in the output directory (existing files are replaced). Each
FeatureCollection contains the full route geometry and aggregate metadata,
ordered segment metadata and segment geometry, and landmark Point features.
Segment metadata includes the exact OSM edge key, endpoints, street names,
road references, distance in meters, time in minutes, and emissions in grams.
Street names/references with multiple values are joined; unnamed roads use their
reference or road type. Geometry follows travel direction and uses node
coordinates where OSM edge geometry is absent.

OSM graph loading needs network access. Optional named POIs (amenities, tourism,
historic sites, leisure, shops) are fetched in shared 0.02-degree bounding boxes
covering a 200-meter route corridor, with at most 64 queries across all routes.
Results are filtered by distance and deduplicated by OSM identity. Area POIs use
a representative point. Distances are measured in a local meter projection.
`landmark_status` reports available, partial (query cap or some failures), or
unavailable. Landmark service failures do not prevent route calculation/export.
For large trips, POI coverage may be partial. Estimates are based on road lengths
and speeds, not live traffic or measured vehicle emissions.

## Offline tests and library use

```sh
python -m unittest discover -s tests -v
```

Importing modules does not load OSM data or prompt for input. `build_graph` accepts
an existing OSM MultiDiGraph; `calculate_routes` returns each objective cost and
a `Path` with ordered `nodes` and exact `(from_node, to_node, edge_key)` tuples.
`describe_route` assembles route details. `nearby_landmarks` accepts an injectable
OSMnx-compatible bbox fetcher, so tests and callers can use local fixtures.
