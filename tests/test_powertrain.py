import json
import tempfile
import unittest
from unittest.mock import Mock, patch

import networkx as nx
import pandas as pd

from powertrain import MODEL_ID, predict_edges
from routes import build_graph
from routing import calculate_routes
from route_details import describe_route, export_geojson
from models import Edge


class PowertrainTests(unittest.TestCase):
    def setUp(self):
        self.osm = nx.MultiDiGraph()
        self.osm.add_node(1, x=0, y=0)
        self.osm.add_node(2, x=0.01, y=0)
        self.osm.add_edge(1, 2, key=17, length=1609.344, speed_kph=96.56064, name='Fast')
        self.osm.add_edge(1, 2, key=42, length=3218.688, speed_kph=48.28032, name='Green')
        self.model = Mock()
        self.model.predict.return_value = pd.DataFrame({'fuel_gge': [0.1, 0.02]})

    def test_batch_routing_and_export_use_exact_selected_edges(self):
        with patch('powertrain.load_routee_model', return_value=self.model) as load:
            graph = build_graph(self.osm)
            load.assert_called_once_with()
        self.model.predict.assert_called_once()
        inputs = self.model.predict.call_args.args[0]
        self.assertEqual(list(inputs.columns), ['speed_mph', 'distance_mi'])
        self.assertEqual(inputs.to_dict('records'), [dict(speed_mph=60, distance_mi=1), dict(speed_mph=30, distance_mi=2)])
        results = calculate_routes(graph, 1, 2)
        self.assertEqual(results['fastest'][1].edges, [(1, 2, 17)])
        self.assertEqual(results['lowest-emissions'][1].edges, [(1, 2, 42)])
        for weight, key in [(0, 17), (1, 42)]:
            self.assertEqual(calculate_routes(graph, 1, 2, weight)['balanced'][1].edges[0][2], key)
        for name, (cost, path) in results.items():
            route = describe_route(self.osm, graph, path, name, cost)
            fuel = 0.1 if path.edges[0][2] == 17 else 0.02
            self.assertAlmostEqual(route['emissions_g'], fuel * 8887)
            self.assertAlmostEqual(route['fuel_gge'], fuel)
            self.assertEqual(route['emissions_model'], MODEL_ID)
            with tempfile.TemporaryDirectory() as directory:
                props = json.loads(export_geojson(route, directory).read_text())['features'][0]['properties']
            self.assertEqual(props['emissions_g'], route['segments'][0]['emissions_g'])
            self.assertEqual(props['segments'][0]['edge_key'], path.edges[0][2])
        self.model.predict.assert_called_once()  # no inference during routing or export

    def test_baseline_is_explicit_and_does_not_load_model(self):
        with patch('powertrain.load_routee_model', side_effect=AssertionError('loaded')):
            graph = build_graph(self.osm, emissions_source='baseline')
        self.assertEqual(graph[1][2][17].emissions(), 120)
        self.assertEqual(calculate_routes(graph, 1, 2)['lowest-emissions'][1].edges, [(1, 2, 17)])

    def test_invalid_inputs_rejected_before_inference(self):
        for field, values in [('length', [-1, float('nan'), float('inf'), None, '1']),
                              ('speed_kph', [0, -1, float('nan'), float('inf'), True])]:
            for value in values:
                with self.subTest(field=field, value=value):
                    self.osm[1][2][17][field] = value
                    with self.assertRaises(ValueError):
                        build_graph(self.osm, model=self.model)
                    self.model.predict.assert_not_called()
            self.osm[1][2][17][field] = 1609.344 if field == 'length' else 96.56064

    def test_invalid_outputs_are_atomic(self):
        for output in [pd.DataFrame({'fuel_gge': [0.1, v]}) for v in [-1, float('nan'), float('inf'), None, 'bad', True]] + [
                pd.DataFrame({'wrong': [1, 2]}), pd.DataFrame({'fuel_gge': [1]}),
                pd.DataFrame({'fuel_gge': [1, 2]}, index=[1, 0]),
                pd.DataFrame({'fuel_gge': [1, 1e308]})]:
            edges = [Edge(1, 0, 0, 30), Edge(2, 0, 0, 30)]
            self.model.predict.return_value = output
            with self.subTest(output=output), self.assertRaises(ValueError):
                predict_edges(edges, self.model)
            self.assertTrue(all(e.fuel_gge is None for e in edges))

    def test_zero_fuel_is_valid_and_empty_graph_needs_no_model(self):
        self.model.predict.return_value = pd.DataFrame({'fuel_gge': [0, 0]})
        graph = build_graph(self.osm, model=self.model)
        self.assertEqual(graph[1][2][17].emissions(), 0)
        # Existing balanced normalization explicitly rejects a zero reference cost.
        with self.assertRaises(ValueError):
            calculate_routes(graph, 1, 2)
        with patch('powertrain.load_routee_model', side_effect=AssertionError('loaded')):
            self.assertEqual(build_graph(nx.MultiDiGraph()), {})
