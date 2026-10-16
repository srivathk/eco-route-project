import json
import tempfile
import unittest
from unittest.mock import patch

import geopandas as gpd
import networkx as nx
from shapely.geometry import LineString, Point

from routes import build_graph
from routing import calculate_routes, dijkstra
from route_details import describe_route, export_geojson, nearby_landmarks, label


class RouteTests(unittest.TestCase):
    def setUp(self):
        self.osm = nx.MultiDiGraph(crs='EPSG:4326')
        self.osm.add_node(1, x=-121.98, y=37.75)
        self.osm.add_node(2, x=-121.979, y=37.75)
        self.osm.add_node(3, x=-121.978, y=37.75)
        self.osm.add_edge(1, 2, key=0, length=100, speed_kph=10, name='Slow Road')
        self.osm.add_edge(1, 2, key=7, length=150, speed_kph=60,
                          name=['Main Street', 'Main Street', 'Connector'], ref=['R1', 'R2'],
                          geometry=LineString([(-121.979, 37.75), (-121.9795, 37.7502), (-121.98, 37.75)]))
        self.osm.add_edge(2, 3, key=9, length=100, speed_kph=40, highway='residential')
        self.graph = build_graph(self.osm, emissions_source="baseline")

    def details(self):
        return [describe_route(self.osm, self.graph, path, name, cost)
                for name, (cost, path) in calculate_routes(self.graph, 1, 3).items()]

    def test_parallel_edges_and_actual_totals(self):
        routes = self.details()
        fastest, greenest, balanced = routes
        self.assertEqual(fastest['segments'][0]['edge_key'], 7)
        self.assertEqual(greenest['segments'][0]['edge_key'], 0)
        self.assertAlmostEqual(fastest['distance_m'], 250)
        self.assertAlmostEqual(greenest['distance_m'], 200)
        self.assertAlmostEqual(fastest['travel_time_min'], 0.3)
        self.assertAlmostEqual(fastest['emissions_g'], 250 / 1609.344 * 120)
        for route in routes:
            self.assertEqual(len(route['segments']), 2)
        for weight, expected in [(0, 7), (1, 0)]:
            self.assertEqual(calculate_routes(self.graph, 1, 3, weight)['balanced'][1].edges[0][2], expected)

    def test_geometry_order_names_and_fallback(self):
        route = self.details()[0]
        self.assertEqual(route['coordinates'], [[-121.98, 37.75], [-121.9795, 37.7502], [-121.979, 37.75], [-121.978, 37.75]])
        self.assertEqual(route['segments'][0]['street_name'], 'Main Street; Connector')
        self.assertEqual(route['segments'][0]['road_reference'], 'R1; R2')
        self.assertEqual(route['segments'][1]['label'], 'Unnamed residential')
        self.osm[2][3][9]['ref'] = 'R3'
        self.assertEqual(self.details()[0]['segments'][1]['label'], 'R3')

    def test_unreachable_and_same_node(self):
        self.assertEqual(calculate_routes(self.graph, 3, 1), {})
        with self.assertRaises(ValueError):
            dijkstra(self.graph, 4, 1, lambda e: e.time())
        route = describe_route(self.osm, self.graph, calculate_routes(self.graph, 1, 1)['balanced'][1], 'balanced', 0)
        self.assertEqual(route['distance_m'], 0)
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(json.loads(export_geojson(route, directory).read_text())['features'][0]['geometry']['type'], 'Point')

    def test_pois_batched_filtered_and_deduplicated(self):
        routes = self.details()
        calls = []
        features = gpd.GeoDataFrame({'name': ['Library', None, 'Far Away'],
                                    'geometry': [Point(-121.9795, 37.7501), Point(-121.979, 37.75), Point(-121, 38)]},
                                   crs='EPSG:4326')
        def fetch(bbox, tags):
            calls.append(bbox)
            return features
        nearby_landmarks(routes, fetch)
        self.assertEqual(len(calls), len(set(calls)))
        self.assertLessEqual(len(calls), 4)
        for route in routes:
            self.assertEqual([p['name'] for p in route['landmarks']], ['Library'])
            self.assertLess(route['landmarks'][0]['distance_from_route_m'], 20)
            self.assertEqual(route['landmark_status'], 'available')

    def test_missing_pois_and_query_cap(self):
        routes = self.details()
        def unavailable(*args, **kwargs):
            raise RuntimeError('offline')
        nearby_landmarks(routes, unavailable)
        self.assertEqual(routes[0]['landmark_status'], 'unavailable')
        empty = gpd.GeoDataFrame({'name': [], 'geometry': []}, crs='EPSG:4326')
        with patch('builtins.input', side_effect=AssertionError('unexpected prompt')):
            import routing
        calls = []
        nearby_landmarks(self.details(), lambda bbox, tags: calls.append(bbox) or empty,
                         tile_degrees=0.0001, max_queries=2)
        self.assertEqual(len(calls), 2)

    def test_empty_geometry_and_missing_labels(self):
        self.osm[2][3][9]['geometry'] = LineString()
        self.osm[2][3][9]['name'] = float('nan')
        self.osm[2][3][9].pop('highway')
        segment = self.details()[0]['segments'][1]
        self.assertEqual(segment['label'], 'Unnamed road')
        self.assertEqual(segment['coordinates'], [[-121.979, 37.75], [-121.978, 37.75]])
        self.assertEqual(label(None), '')

    def test_geojson_full_route_and_details(self):
        route = self.details()[0]
        with tempfile.TemporaryDirectory() as directory:
            document = json.loads(export_geojson(route, directory).read_text())
        self.assertEqual(document['type'], 'FeatureCollection')
        self.assertEqual(document['features'][0]['geometry']['coordinates'], route['coordinates'])
        self.assertEqual(document['features'][0]['properties']['segments'][0]['edge_key'], 7)
        self.assertEqual(document['features'][1]['properties']['street_name'], 'Main Street; Connector')


if __name__ == '__main__':
    unittest.main()
