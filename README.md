# Eco Route

Calculate fastest, lowest-emissions, and balanced driving routes using OSM roads
and Python **3.12**. RouteE is the default emissions source. Dijkstra, exact
OSM multigraph edge keys, path reconstruction, street names, landmarks, and
GeoJSON geometry are preserved.

## Emissions model

The pinned pretrained gasoline model is
`toyota/camry_ice/2016/rf_base_67ae9982/v1` from RouteE Powertrain 2.x.
Its verified input contract uses `speed_mph` and `distance_mi`; `fuel_gge`
represents US gasoline gallons consumed on each segment. OSM `length` is
converted from meters using 1609.344 meters/mile; OSMnx `speed_kph` is converted
using 1.609344 km/h per mph. Speeds are estimates from tags and OSMnx imputation,
including the existing 40 km/h fallback, rather than observed speeds or live traffic.

Every directed road edge, including parallel edges, is predicted in a single
batch before routing. The model is loaded once per graph build, never in
Dijkstra. Each edge stores its fuel prediction and tailpipe CO2 estimate:
`emissions_g = fuel_gge * 8887`. **Do not multiply by distance again.**
RouteE's prediction API already applies its real-world adjustment; the app
adds no further adjustment. These estimates assume the selected 2016 gasoline
Camry; they exclude upstream emissions and other greenhouse gases. No elevation,
grade, or stop placeholders are supplied to RouteE.

Inputs must be numeric and finite, with nonnegative distance and positive speed.
Outputs must contain one ordered `fuel_gge` value per input, all numeric,
finite, and nonnegative; converted CO2 must also be finite. Invalid values
raise errors before any prediction is attached, with no silent baseline fallback.
Zero fuel is valid, though the existing balanced normalization rejects a
nontrivial trip whose reference emissions cost is zero.

Lowest-emissions routing uses predicted CO2; balanced routing uses the existing
normalized time/emissions formula. Fastest routing keeps its existing time
formula. Totals sum the exact selected `(u, v, key)` edges. GeoJSON includes
segment and aggregate emissions source, model ID, fuel gallons, and CO2, plus
the conversion factor on the route. Same-node trips have zero totals.

The explicitly selectable `baseline` retains the original formula:
`distance_miles * 120 + stops * 20 + elevation * 0.2` grams CO2.
The existing loader leaves baseline stops and elevation at zero, so it reduces
to 120 g/mile. These legacy terms are uncalibrated assumptions, not measurements.

## Run

Use the existing Python 3.12 environment; do not install globally:

```sh
.venv-routee/bin/python -m pip install -r requirements.txt
.venv-routee/bin/python routing.py --place 'San Ramon, California, USA' --output-dir output --emissions-source routee
# Explicit comparison using the old formula:
.venv-routee/bin/python routing.py --place 'San Ramon, California, USA' --output-dir output-baseline --emissions-source baseline
```

Enter an eco preference from 0 to 1 and start/destination latitude and longitude.
The CLI prints distance, time, CO2, ordered road segments, and nearby landmarks.
Coordinates snap to road nodes; unreachable destinations produce no exports.
Each route is exported as `fastest.geojson`, `lowest-emissions.geojson`, or
`balanced.geojson` (existing files are replaced). FeatureCollections contain
route geometry and totals, ordered segment metadata and geometry, and landmark
Points. Segments retain exact edge keys, endpoints, street names, references,
distance, time, fuel, and emissions. Geometry follows travel direction.

OSM loading needs network access. Optional named landmarks are fetched in shared
0.02-degree bounding boxes covering a 200-meter route corridor, capped at 64
queries across all routes, filtered by distance and deduplicated by OSM identity.
`landmark_status` reports available, partial, or unavailable; service failures
do not prevent route export.

## Verification and offline tests

Real predictions were verified using the locally cached model in Hugging Face
offline mode, after registry requests encountered DNS failures. No packages were
installed. Run this exact command from the project directory to reproduce the
real segment verification (also usable outside the sandbox):

```sh
HF_HUB_OFFLINE=1 .venv-routee/bin/python powertrain.py
```

The verification produced 0.03285837 gallons / 292.012 g CO2 for 1 mile at
30 mph and 0.05921797 gallons / 526.270 g CO2 for 2 miles at 60 mph.
Omit `HF_HUB_OFFLINE=1` to allow registry access if the model is not cached.
To verify routing
against actual OSM roads, run the RouteE app command above.

```sh
.venv-routee/bin/python -m unittest discover -s tests -v
```

Offline tests mock the model's DataFrame predictions and cover batch inputs,
unit conversion, distinct fastest/greenest parallel roads, balanced endpoints,
selected-edge totals/exports, invalid inputs/outputs, and explicit baseline use.
Existing geometry, street-name, landmark, and reconstruction tests also run.

Imports never load the model, OSM data, or prompt for input. `build_graph(osm_graph,
emissions_source='routee', model=None)` accepts an existing OSM MultiDiGraph
and an injectable predictor. Use `emissions_source='baseline'` for comparison.
`calculate_routes` returns objective costs and paths with ordered nodes and exact
edge tuples; `describe_route` assembles details and `nearby_landmarks` accepts an
injectable OSMnx-compatible bbox fetcher.
