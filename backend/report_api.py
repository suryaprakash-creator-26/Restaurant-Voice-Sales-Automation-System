from flask import Flask, jsonify
import pandas as pd

app = Flask(__name__)

@app.route("/api/report")
def report():

    df = pd.read_excel("sales.xlsx")

    # Daily Sales
    daily_sales = (
        df.groupby("DATE")["TOTAL"]
        .sum()
        .reset_index()
    )

    sales_chart = {
        "dates": daily_sales["DATE"].tolist(),
        "totals": daily_sales["TOTAL"].tolist()
    }

    # Food Sales
    ignore_cols = ["DATE", "TOTAL"]

    food_totals = {}

    for col in df.columns:

        if col not in ignore_cols:

            food_totals[col] = int(df[col].sum())

    return jsonify({
        "sales_chart": sales_chart,
        "food_sales": food_totals,
        "monthly_total": int(df["TOTAL"].sum())
    })

if __name__ == "__main__":
    app.run(port=5001)