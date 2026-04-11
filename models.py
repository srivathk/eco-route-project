class Route:
    def __init__(self, name, distance, stops, elevation, avg_speed):
        self.name = name
        self.distance = distance
        self.stops = stops
        self.elevation = elevation
        self.avg_speed = avg_speed

        self.emissions = None
        self.time = None

        self.balanced_score = None
        
    def compute_metrics(self):
        self.emissions = (self.distance * 0.2) + (self.stops * 0.05) + (self.elevation * 0.001)
        self.time = (self.distance / self.avg_speed) + (self.stops * 0.01) + (self.elevation * 0.0005)
        


 
