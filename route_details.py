"""Route geometry, road metadata, bounded POI lookup, and GeoJSON export."""
import json
import math
from pathlib import Path as FilePath


def label(value):
    if isinstance(value, (list, tuple)):
        return '; '.join(dict.fromkeys(filter(None, (label(v) for v in value))))
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return ''
    return str(value).strip()


def node_coordinate(osm_graph, node):
    data = osm_graph.nodes[node]
    return [float(data['x']), float(data['y'])]


def edge_coordinates(osm_graph, u, v, data):
    start, end = node_coordinate(osm_graph, u), node_coordinate(osm_graph, v)
    geometry = data.get('geometry')
    if geometry is None or geometry.is_empty:
        return [start, end]
    coordinates = [[float(x), float(y)] for x, y, *_ in geometry.coords]
    def distance(a, b):
        return (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2
    if distance(coordinates[-1], start) + distance(coordinates[0], end) < distance(coordinates[0], start) + distance(coordinates[-1], end):
        coordinates.reverse()
    if coordinates[0] != start:
        coordinates.insert(0, start)
    if coordinates[-1] != end:
        coordinates.append(end)
    return coordinates


def describe_route(osm_graph, graph, path, name, cost, weight=0.5):
    coordinates, segments = [], []
    for u, v, key in path.edges:
        data = osm_graph[u][v][key]
        edge = graph[u][v][key]
        shape = edge_coordinates(osm_graph, u, v, data)
        coordinates.extend(shape[1:] if coordinates and coordinates[-1] == shape[0] else shape)
        street, reference = label(data.get('name')), label(data.get('ref'))
        road_type = label(data.get('highway'))
        road_label = street or reference or ('Unnamed ' + (road_type.replace('_', ' ') or 'road'))
        segments.append(dict(from_node=u, to_node=v, edge_key=key,
                             street_name=street or None, road_reference=reference or None,
                             label=road_label, highway=road_type or None,
                             distance_m=edge.distance * 1609.344,
                             travel_time_min=edge.time(), emissions_g=edge.emissions(),
                             coordinates=shape))
    if not coordinates:
        coordinates = [node_coordinate(osm_graph, path.nodes[0])]
    return dict(route_type=name, objective_cost=cost, emissions_weight=weight,
                distance_m=sum(s['distance_m'] for s in segments),
                travel_time_min=sum(s['travel_time_min'] for s in segments),
                emissions_g=sum(s['emissions_g'] for s in segments),
                coordinates=coordinates, segments=segments, landmarks=[],
                landmark_status='not requested')


def nearby_landmarks(routes, fetcher, radius_m=200, tile_degrees=0.02, max_queries=64):
    """Fetch each small bbox once; cap requests and report incomplete coverage.

    fetcher follows OSMnx features_from_bbox((west, south, east, north), tags).
    Distances use a local azimuthal equidistant projection in meters.
    """
    from pyproj import CRS, Transformer
    from shapely.geometry import LineString, Point, box
    from shapely.ops import transform
    if not routes:
        return
    if radius_m <= 0 or tile_degrees <= 0 or max_queries < 1:
        raise ValueError('Landmark query limits must be positive')
    points = [p for r in routes for p in r['coordinates']]
    lon, lat = points[0]
    projection = Transformer.from_crs('EPSG:4326', CRS.from_proj4(
        f'+proj=aeqd +lat_0={lat} +lon_0={lon} +datum=WGS84 +units=m'), always_xy=True)
    inverse = Transformer.from_crs(projection.target_crs, 'EPSG:4326', always_xy=True)
    shapes = [Point(r['coordinates'][0]) if len(r['coordinates']) == 1 else LineString(r['coordinates']) for r in routes]
    metric_shapes = [transform(projection.transform, s) for s in shapes]
    corridors = [transform(inverse.transform, s.buffer(radius_m)) for s in metric_shapes]
    tiles = set()
    capped = False
    for corridor in corridors:
        west, south, east, north = corridor.bounds
        for x in range(math.floor(west / tile_degrees), math.floor(east / tile_degrees) + 1):
            for y in range(math.floor(south / tile_degrees), math.floor(north / tile_degrees) + 1):
                bbox = (x * tile_degrees, y * tile_degrees, (x + 1) * tile_degrees, (y + 1) * tile_degrees)
                if corridor.intersects(box(*bbox)):
                    tiles.add(bbox)
                    if len(tiles) > max_queries:
                        capped = True
                        break
            if capped:
                break
        if capped:
            break
    failures, seen = 0, set()
    for bbox in sorted(tiles)[:max_queries]:
        try:
            features = fetcher(bbox, tags={'amenity': True, 'tourism': True, 'historic': True, 'leisure': True, 'shop': True})
            if features.crs is not None:
                features = features.to_crs('EPSG:4326')
            for identity, row in features.iterrows():
                name = label(row.get('name'))
                geometry = row.get('geometry')
                if not name or geometry is None or geometry.is_empty or identity in seen:
                    continue
                seen.add(identity)
                point = geometry if geometry.geom_type == 'Point' else geometry.representative_point()
                metric_point = transform(projection.transform, point)
                for route, shape in zip(routes, metric_shapes):
                    distance = shape.distance(metric_point)
                    if distance <= radius_m:
                        route['landmarks'].append(dict(name=name, osm_id=str(identity),
                            longitude=point.x, latitude=point.y, distance_from_route_m=distance))
        except Exception:
            # POIs are optional: a failed service/query must not lose the route.
            failures += 1
    for route in routes:
        route['landmarks'].sort(key=lambda p: (p['distance_from_route_m'], p['name']))
        route['landmark_status'] = 'partial' if capped or failures else 'available'
        if failures == min(len(tiles), max_queries):
            route['landmark_status'] = 'unavailable'


def export_geojson(route, output_dir):
    def geometry(coordinates):
        if len(coordinates) == 1:
            return dict(type='Point', coordinates=coordinates[0])
        return dict(type='LineString', coordinates=coordinates)
    properties = {k: v for k, v in route.items() if k not in ('coordinates', 'segments', 'landmarks')}
    properties['segments'] = [{k: v for k, v in s.items() if k != 'coordinates'} for s in route['segments']]
    features = [dict(type='Feature', geometry=geometry(route['coordinates']), properties=properties)]
    for segment in route['segments']:
        features.append(dict(type='Feature', geometry=geometry(segment['coordinates']),
            properties=dict(feature_type='road_segment', **{k: v for k, v in segment.items() if k != 'coordinates'})))
    for poi in route['landmarks']:
        features.append(dict(type='Feature', geometry=dict(type='Point', coordinates=[poi['longitude'], poi['latitude']]),
                             properties=dict(feature_type='landmark', **poi)))
    destination = FilePath(output_dir) / (route['route_type'] + '.geojson')
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(dict(type='FeatureCollection', features=features), indent=2, allow_nan=False) + '\n')
    return destination
