"""Dijkstra routing with exact multigraph edge identities."""
from dataclasses import dataclass


@dataclass
class Path:
    nodes: list
    edges: list  # ordered (from_node, to_node, OSM edge key)

    def __bool__(self):
        return bool(self.nodes)


def dijkstra(graph, start, end, cost_function):
    if start not in graph or end not in graph:
        raise ValueError('Start and end points must exist in the graph')
    costs = {node: float('inf') for node in graph}
    costs[start] = 0
    previous = {node: None for node in graph}
    unvisited = list(graph.keys())
    while unvisited:
        next_route = min(unvisited, key=lambda node: costs[node])
        if costs[next_route] == float('inf') or next_route == end:
            break
        for neighbor, roads in graph[next_route].items():
            for key, edge in roads.items():
                new_cost = costs[next_route] + cost_function(edge)
                if new_cost < costs[neighbor]:
                    costs[neighbor] = new_cost
                    previous[neighbor] = (next_route, key)
        unvisited.remove(next_route)
    if costs[end] == float('inf'):
        return float('inf'), Path([], [])
    nodes, edges = [end], []
    current = end
    while previous[current] is not None:
        parent, key = previous[current]
        edges.append((parent, current, key))
        nodes.append(parent)
        current = parent
    return costs[end], Path(nodes[::-1], edges[::-1])


def calculate_routes(graph, start, end, weight=0.5):
    if not 0 <= weight <= 1:
        raise ValueError('Eco preference must be between 0 and 1')
    fastest_cost, fastest = dijkstra(graph, start, end, lambda edge: edge.time())
    greenest_cost, greenest = dijkstra(graph, start, end, lambda edge: edge.emissions())
    if not fastest:
        return {}
    if start == end:
        balanced_cost, balanced = 0, fastest
    elif fastest_cost <= 0 or greenest_cost <= 0:
        raise ValueError('Cannot normalize this trip because a reference cost is zero')
    else:
        balanced_cost, balanced = dijkstra(
            graph, start, end,
            lambda edge: edge.cost(weight, fastest_cost, greenest_cost),
        )
    return {'fastest': (fastest_cost, fastest),
            'lowest-emissions': (greenest_cost, greenest),
            'balanced': (balanced_cost, balanced)}


def main():
    import argparse
    import osmnx as ox
    from routes import load_graph
    from route_details import describe_route, export_geojson, nearby_landmarks
    from user_interface import get_emissions_weight, print_route
    parser = argparse.ArgumentParser(description='Calculate and export Eco Routes')
    parser.add_argument('--place', default='San Ramon, California, USA')
    parser.add_argument('--output-dir', default='output')
    args = parser.parse_args()
    weight = get_emissions_weight()
    start_lat = float(input('Start latitude: '))
    start_lon = float(input('Start longitude: '))
    end_lat = float(input('Destination latitude: '))
    end_lon = float(input('Destination longitude: '))
    osm_graph, graph = load_graph(args.place)
    start = ox.distance.nearest_nodes(osm_graph, X=start_lon, Y=start_lat)
    end = ox.distance.nearest_nodes(osm_graph, X=end_lon, Y=end_lat)
    results = calculate_routes(graph, start, end, weight)
    if not results:
        print('No route connects these locations.')
        return
    if start == end:
        print('Both locations snapped to the same road node.')
    details = [describe_route(osm_graph, graph, path, name, cost, weight)
               for name, (cost, path) in results.items()]
    nearby_landmarks(details, ox.features_from_bbox)
    for route in details:
        destination = export_geojson(route, args.output_dir)
        print_route(route)
        print(f'  GeoJSON: {destination}')


if __name__ == '__main__':
    main()
