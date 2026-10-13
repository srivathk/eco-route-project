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
