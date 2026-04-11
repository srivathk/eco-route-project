def route_score(routes, time_weight, emissions_weight):
  min_time = min(route.time for route in routes)
  max_time = max(route.time for route in routes)
  min_emissions = min(route.emissions for route in routes)
  max_emissions = max(route.emissions for route in routes)
  for route in routes:
    if max_time - min_time == 0:
      norm_time = 0
    else:
      norm_time = (route.time - min_time) / (max_time - min_time)
    if max_emissions - min_emissions == 0:
      norm_emissions = 0
    else:
      norm_emissions = (route.emissions - min_emissions) / (max_emissions - min_emissions)
    route.balanced_score = time_weight * (norm_time ** 1.5) + emissions_weight * (norm_emissions ** 1.4)

def metrics_calc(routes):
  for route in routes:
    route.compute_metrics()

def best_score(routes):
  best_route = min(routes, key=lambda x: x.balanced_score)
  return(best_route)

    
