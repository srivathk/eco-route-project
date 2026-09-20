from models import Edge

import osmnx

graph = osmnx.graph_from_place("San Ramon, California, USA", network_type="drive")

