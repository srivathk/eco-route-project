from models import Edge
from routes import graph

import user_interface


weightage = user_interface.get_emissions_weight()

def dijkstra(graph, start, end, cost_function):
  costs = {node: float("inf") for node in graph}
  costs[start] = 0
  previous = {node: None for node in graph}
  unvisited = list(graph.keys())

  while unvisited:
    next_route = min(unvisited, key=lambda x: costs.get(x))

    if next_route == end:
      break

    for neighbor, edge_data in graph.get(next_route).items():
      new_cost = costs[next_route] + cost_function(edge_data)
      if new_cost < costs[neighbor]: 
        costs[neighbor] = new_cost
        previous[neighbor] = next_route

    unvisited.remove(next_route)

  path = []
  current = end
  while current is not None:
    path.append(current)
    current = previous[current]  
  path.reverse()

  return (costs[end], path)



print(dijkstra(graph, "A", "Z", lambda edge: edge.cost(weightage)))
print(dijkstra(graph, "A", "Z", lambda edge: edge.time()))



  


"""while end in visited == False
    for key in start_node.keys():
      route = models.Route(
        name=key #ix this you need the dictionary's key here
        distance=float(key[distance]),
        stops=int(key[stops]),
        elevation=float(key[elevation]),
        avg_speed=float(key[speed]))
      
      route.compute_metrics()
      visited.append(route)

    processing.route_score(routes)


    new_start = processing.best_route_func(routes)
    start_node = new_start.name"""

  



  