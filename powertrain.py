"""Batch RouteE consumption predictions, validated before graph publication."""
import math
import numbers

MODEL_ID = 'toyota/camry_ice/2016/rf_base_67ae9982/v1'
CO2_G_PER_GALLON = 8887


def valid_number(value, name, positive=False):
    if isinstance(value, bool) or not isinstance(value, numbers.Real):
        raise ValueError(f'{name} must be numeric')
    value = float(value)
    if not math.isfinite(value) or value < 0 or (positive and value == 0):
        raise ValueError(f'{name} must be finite and {"positive" if positive else "nonnegative"}')
    return value


def load_routee_model():
    from routee.powertrain import load_model
    model = load_model(MODEL_ID)
    config = model.metadata.config
    if set(model.feature_names) - {'speed_mph', 'distance_mi'}:
        raise ValueError('Selected model requires unavailable road features')
    if config.distance.name != 'distance_mi' or 'fuel_gge' not in [t.name for t in config.target.targets]:
        raise ValueError('Selected model has an incompatible distance or fuel contract')
    return model


def predict_edges(edges, model=None):
    import pandas as pd
    rows = [dict(speed_mph=valid_number(e.avg_speed, 'speed_mph', positive=True),
                 distance_mi=valid_number(e.distance, 'distance_mi')) for e in edges]
    if not rows:
        return
    if model is None:
        model = load_routee_model()
    inputs = pd.DataFrame(rows)
    predictions = model.predict(inputs)
    if not isinstance(predictions, pd.DataFrame) or 'fuel_gge' not in predictions:
        raise ValueError('RouteE must return a DataFrame containing fuel_gge')
    if len(predictions) != len(edges) or not predictions.index.equals(inputs.index):
        raise ValueError('RouteE output rows must match input rows in order')
    fuels = [valid_number(v, 'fuel_gge') for v in predictions['fuel_gge']]
    emissions = [valid_number(v * CO2_G_PER_GALLON, 'emissions_g') for v in fuels]
    for edge, fuel, co2 in zip(edges, fuels, emissions):
        edge.fuel_gge = fuel
        edge.predicted_emissions_g = co2
        edge.emissions_source = 'routee'
        edge.emissions_model = MODEL_ID


if __name__ == '__main__':
    from models import Edge
    sample = [Edge(distance=1, avg_speed=30, stops=0, elevation=0),
              Edge(distance=2, avg_speed=60, stops=0, elevation=0)]
    predict_edges(sample)
    print(f'Model: {MODEL_ID}')
    for edge in sample:
        print(f'{edge.distance} mi at {edge.avg_speed} mph: '
              f'{edge.fuel_gge:.8f} gasoline gallons, {edge.emissions():.3f} g CO2')
