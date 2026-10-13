from models import Edge
from routes import graph, imported_graph
import osmnx as ox

import user_interface


weightage = user_interface.get_emissions_weight()

def dijkstra(graph, start, end, cost_function):
  if start not in graph or end not in graph:
    raise ValueError("Start and end points must exist in the graph")
  costs = {node: float("inf") for node in graph}
  costs[start] = 0
  previous = {node: None for node in graph}
  unvisited = list(graph.keys())

  while unvisited:
    next_route = min(unvisited, key=lambda node: costs[node])

    # No more reachable nodes.
    if costs[next_route] == float("inf"):
      break

    if next_route == end:
      break

    for neighbor, roads in graph[next_route].items():
      for key, edge in roads.items():
        new_cost = costs[next_route] + cost_function(edge)

        if new_cost < costs[neighbor]:
          costs[neighbor] = new_cost
          previous[neighbor] = next_route

    unvisited.remove(next_route)


  if costs[end] == float("inf"):
    return (float("inf"), [])
  path = []
  current = end
  while current is not None:
    path.append(current)
    current = previous[current]  
  path.reverse()

  return (costs[end], path)



start_lat = float(input("Start latitude: "))
start_lon = float(input("Start longitude: "))

end_lat = float(input("Destination latitude: "))
end_lon = float(input("Destination longitude: "))

start = ox.distance.nearest_nodes(
    imported_graph, X=start_lon, Y=start_lat
)

end = ox.distance.nearest_nodes(
    imported_graph, X=end_lon, Y=end_lat
)

print("Testing from", start, "to", end)

fastest_cost, fastest_path = dijkstra(
    graph, start, end, lambda edge: edge.time()
)

greenest_cost, greenest_path = dijkstra(
    graph, start, end, lambda edge: edge.emissions()
)

if not fastest_path or not greenest_path:
    print("No route connects these locations.")

elif start == end:
    print("Both locations snapped to the same road node.")

elif fastest_cost <= 0 or greenest_cost <= 0:
    print("Cannot normalize this trip because a reference cost is zero.")

else:
    balanced_cost, balanced_path = dijkstra(
        graph,
        start,
        end,
        lambda edge: edge.cost(
            weightage,
            fastest_cost,
            greenest_cost,
        ),
    )

    print("Fastest:", fastest_cost, fastest_path)
    print("Lowest emissions:", greenest_cost, greenest_path)
    print("Your preference:", balanced_cost, balanced_path)
