"""OSM loading is explicit so importing the routing library never uses the network."""
from models import Edge
from powertrain import predict_edges, valid_number


def build_graph(osm_graph, emissions_source="routee", model=None):
    if emissions_source not in ("routee", "baseline"):
        raise ValueError("Emissions source must be routee or baseline")
    graph = {node: {} for node in osm_graph.nodes}
    for start, end, key, data in osm_graph.edges(keys=True, data=True):
        edge = Edge(
            distance=valid_number(data['length'], 'OSM length') / 1609.344,
            avg_speed=valid_number(data['speed_kph'], 'OSM speed_kph', positive=True) / 1.609344,
            stops=0,
            elevation=0,
        )
        graph[start].setdefault(end, {})[key] = edge
    if emissions_source == "routee":
        predict_edges([edge for neighbors in graph.values()
                       for roads in neighbors.values() for edge in roads.values()], model)
    return graph


def load_graph(place='San Ramon, California, USA', emissions_source='routee', model=None):
    import osmnx as ox
    osm_graph = ox.graph_from_place(place, network_type='drive')
    osm_graph = ox.routing.add_edge_speeds(osm_graph, fallback=40)
    return osm_graph, build_graph(osm_graph, emissions_source, model)
