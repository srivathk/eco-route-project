class Edge:
    def __init__(self, distance, stops, elevation, avg_speed):
        self.distance = distance
        self.stops = stops
        self.elevation = elevation
        self.avg_speed = avg_speed
        self.emissions_source = "baseline"
        self.emissions_model = None
        self.fuel_gge = None
        self.predicted_emissions_g = None


    def emissions(self):
        if self.emissions_source == "routee":
            return self.predicted_emissions_g
        return self.baseline_emissions()

    def baseline_emissions(self):
        base = self.distance * 120      # ~120g CO₂ per mile (rough)
        stop_penalty = self.stops * 20  # idling/acceleration
        elevation_penalty = self.elevation * 0.2
        return base + stop_penalty + elevation_penalty
    def time(self):
        drive_time = (self.distance / self.avg_speed) * 60  # minutes
        stop_delay = self.stops * 0.5                       # 30s per stop
        elevation_delay = self.elevation * 0.01             # tune this
        return drive_time + stop_delay + elevation_delay
    def cost(self, weightage, time_reference, emissions_reference):
        normalized_time = self.time() / time_reference
        normalized_emissions = self.emissions() / emissions_reference

        return (1 - weightage) * normalized_time + weightage * normalized_emissions





