import pandas as pd

def generate_analytics():

    df = pd.read_excel("sales.xlsx")

    # ------------------------
    # Daily Sales
    # ------------------------

    df["DATE"] = pd.to_datetime(
        df["DATE"],
        dayfirst=True,
        errors="coerce"
    )

    df = df.dropna(subset=["DATE"])

    daily_sales = (
        df.groupby("DATE")["TOTAL"]
        .sum()
        .reset_index()
        .sort_values("DATE")
    )

    dates = (
        daily_sales["DATE"]
        .dt.strftime("%d-%m-%Y")
        .tolist()
    )

    totals = daily_sales["TOTAL"].tolist()

    # ------------------------
    # Food Totals
    # ------------------------

    ignore = ["DATE", "TOTAL"]

    foods = {}

    for col in df.columns:

        if col not in ignore:

            foods[col] = int(df[col].sum())

    # ------------------------
    # Revenue
    # ------------------------

    monthly_total = int(sum(totals))

    avg_daily_sales = 0

    if len(totals) > 0:

        avg_daily_sales = round(
            monthly_total / len(totals),
            2
        )

    # ------------------------
    # Highest Day
    # ------------------------

    highest_sales = max(totals) if totals else 0

    highest_day = ""

    if totals:

        highest_day = dates[
            totals.index(highest_sales)
        ]

    # ------------------------
    # Lowest Day
    # ------------------------

    lowest_sales = min(totals) if totals else 0

    lowest_day = ""

    if totals:

        lowest_day = dates[
            totals.index(lowest_sales)
        ]

    # ------------------------
    # Active Foods
    # ------------------------

    active_foods = len(
        [
            qty
            for qty in foods.values()
            if qty > 0
        ]
    )

    # ------------------------
    # Total Units
    # ------------------------

    total_units = sum(
        foods.values()
    )

    # ------------------------
    # Top Food
    # ------------------------

    if foods:

        top_food = max(
            foods,
            key=foods.get
        )

        top_value = foods[top_food]

    else:

        top_food = "-"
        top_value = 0

    top_food_percent = 0

    if total_units > 0:

        top_food_percent = round(
            (top_value / total_units) * 100,
            1
        )

    # ------------------------
    # Top Foods
    # ------------------------

    top_foods = sorted(
        foods.items(),
        key=lambda x: x[1],
        reverse=True
    )

    # ------------------------
    # No Sales Foods
    # ------------------------

    no_sales_foods = []

    for food, qty in foods.items():

        if qty == 0:

            no_sales_foods.append(food)

    # ------------------------
    # Low Sales Foods
    # ------------------------

    low_sales_foods = []

    for food, qty in foods.items():

        if qty > 0 and qty < 50:

            low_sales_foods.append(
                {
                    "food": food,
                    "qty": qty
                }
            )

    # ------------------------
    # Return JSON
    # ------------------------

    return {

        "dates": dates,

        "totals": totals,

        "foods": foods,

        "monthly_total": monthly_total,

        "avg_daily_sales": avg_daily_sales,

        "highest_sales": highest_sales,

        "highest_day": highest_day,

        "lowest_sales": lowest_sales,

        "lowest_day": lowest_day,

        "active_foods": active_foods,

        "total_units": total_units,

        "top_food": top_food,

        "top_value": top_value,

        "top_food_percent": top_food_percent,

        "top_foods": top_foods[:5],

        "no_sales_foods": no_sales_foods,

        "low_sales_foods": low_sales_foods

    }