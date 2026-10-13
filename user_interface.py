def get_emissions_weight():
    while True:
        user_input = input(
            "Enter eco preference from 0 to 1 "
            "(0 = fastest, 1 = greenest, 0.5 = balanced): "
        )

        try:
            emissions_weight = float(user_input)

            if 0 <= emissions_weight <= 1:
                return (emissions_weight)
            else:
                print("Please enter a number between 0 and 1.")

        except ValueError:
            print("Invalid input. Enter a decimal like 0, 0.5, or 1.")


def print_route(route):
    print(f"\n{route['route_type'].replace('-', ' ').title()}")
    print(f"  Distance: {route['distance_m'] / 1000:.2f} km | "
          f"Estimated time: {route['travel_time_min']:.1f} min | "
          f"Estimated emissions: {route['emissions_g']:.1f} g CO2")
    for index, segment in enumerate(route['segments'], 1):
        reference = segment['road_reference']
        suffix = f' ({reference})' if reference and reference != segment['label'] else ''
        print(f"  {index}. {segment['label']}{suffix}: {segment['distance_m']:.0f} m, "
              f"{segment['travel_time_min']:.1f} min, {segment['emissions_g']:.1f} g CO2")
    print(f"  Nearby landmarks ({route['landmark_status']}):")
    for poi in route['landmarks']:
        print(f"    {poi['name']}: {poi['distance_from_route_m']:.0f} m from route "
              f"({poi['latitude']:.6f}, {poi['longitude']:.6f})")
    if not route['landmarks']:
        print('    None available.')
