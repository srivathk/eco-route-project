import data_loader
import user_interface
import processing

routes = data_loader.load_routes("routes.csv")

emissions_weight = user_interface.get_emissions_weight()
time_weight = 1 - emissions_weight

processing.metrics_calc(routes)
processing.route_score(routes, time_weight, emissions_weight)
best_route = processing.best_score(routes)

for r in routes:
  print(f"Route name: {r.name} score={r.balanced_score:.3f} emissions={r.emissions:.3f}, Route time={r.time:.3f}")

print(f"{best_route.name} is the best route with a score of {best_route.balanced_score:.3f}")



