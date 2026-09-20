class Edge:
    def __init__(self, distance, stops, elevation, avg_speed):
        self.distance = distance
        self.stops = stops
        self.elevation = elevation
        self.avg_speed = avg_speed

        
    def emissions(self):
        base = self.distance * 120      # ~120g CO₂ per mile (rough)
        stop_penalty = self.stops * 20  # idling/acceleration
        elevation_penalty = self.elevation * 0.2
        return base + stop_penalty + elevation_penalty
    def time(self):
        drive_time = (self.distance / self.avg_speed) * 60  # minutes
        stop_delay = self.stops * 0.5                       # 30s per stop
        elevation_delay = self.elevation * 0.01             # tune this
        return drive_time + stop_delay + elevation_delay
    def cost(self, weightage):
        return (self.time() + (self.emissions() * weightage))




 
