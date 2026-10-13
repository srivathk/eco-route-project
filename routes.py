"""OSM loading is explicit so importing the routing library never uses the network."""
from models import Edge


def build_graph(osm_graph):
    graph = {node: {} for node in osm_graph.nodes}
    for start, end, key, data in osm_graph.edges(keys=True, data=True):
        edge = Edge(
            distance=data['length'] / 1609.344,
            avg_speed=data['speed_kph'] / 1.609344,
            stops=0,
            elevation=0,
        )
        graph[start].setdefault(end, {})[key] = edge
    return graph


def load_graph(place='San Ramon, California, USA'):
    import osmnx as ox
    osm_graph = ox.graph_from_place(place, network_type='drive')
    osm_graph = ox.routing.add_edge_speeds(osm_graph, fallback=40)
    return osm_graph, build_graph(osm_graph)
