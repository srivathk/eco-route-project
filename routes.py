from models import Edge
import osmnx as ox

graph_outdated = {
    "A": {
        "B": Edge(distance=2, stops=1, elevation=0, avg_speed=30),
        "C": Edge(distance=3, stops=0, elevation=0, avg_speed=60),
    },
    "B": {
        "D": Edge(distance=2, stops=1, elevation=0, avg_speed=30),
    },
    "C": {
        "D": Edge(distance=3, stops=0, elevation=0, avg_speed=60),
    },
    "D": {},
}

imported_graph = ox.graph_from_place(
    "San Ramon, California, USA",
    network_type="drive",
)

imported_graph = ox.routing.add_edge_speeds(imported_graph, fallback=40)

graph = {node: {} for node in imported_graph.nodes}

for start, end, key, data in imported_graph.edges(keys=True, data=True):
    edge = Edge(
        distance=data["length"] / 1609.344,  # meters → miles
        avg_speed=data["speed_kph"] / 1.609344,  # km/h → mph
        stops=0,       # Placeholder until we add stop data
        elevation=0,   # Placeholder until we add elevation data
    )

    if end not in graph[start]:
        graph[start][end] = {}

    graph[start][end][key] = edge

print("Nodes:", len(graph))
print("Edges:", imported_graph.number_of_edges())

