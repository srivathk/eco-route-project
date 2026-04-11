import models

def load_routes(csv_path):
  routes = [] #list to compare routes later

  with open(csv_path, "r") as file:
    data = file.read()

  lines = data.strip().split("\n")


  for line in lines[1:]:
    parts = line.split(",")

    route = models.Route(
      name=parts[0],
      distance=float(parts[1]),
      stops=int(parts[2]),
      elevation=float(parts[3]),
      avg_speed=float(parts[4])
    )

    routes.append(route)

  return routes


