from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import json
import pandas as pd
import sqlite3
import os
import webbrowser

import reports
import analytics

from database import (
    create_database,
    get_latest_voice_result,
    import_menu_prices,
    import_food_aliases,
    save_menu_to_db,
    database_is_empty
)



create_database()


if database_is_empty():
    print("📦 First run detected → importing data...")
    import_menu_prices()
    import_food_aliases()
else:
    print("✅ Database already initialized → skipping import")

app = Flask(__name__)
CORS(app)

# ----------------------------------------
# SAVE MENU PRICES
# ----------------------------------------



@app.route("/save-menu", methods=["POST"])
def save_menu():

    data = request.json

    save_menu_to_db(data)

    return jsonify({
        "message": "Menu saved successfully"
    })


# ----------------------------------------
# GENERATE REPORT IMAGE
# ----------------------------------------

@app.route("/generate-report")
def generate_report():

    reports.generate_daily_sales_chart()

    return jsonify({
        "status": "success",
        "message": "Report Generated"
    })


# ----------------------------------------
# SALES REPORT API
# ----------------------------------------

@app.route("/sales-report")
def sales_report():

    try:

        df = pd.read_excel("sales.xlsx")

        # Daily Sales
        daily_sales = (
            df.groupby("DATE")["TOTAL"]
            .sum()
            .reset_index()
        )

        # Food Totals
        food_totals = {}

        ignore_columns = ["DATE", "TOTAL"]

        for col in df.columns:

            if col not in ignore_columns:

                food_totals[col] = int(
                    df[col].fillna(0).sum()
                )

        # Monthly Total
        monthly_total = int(
            df["TOTAL"].fillna(0).sum()
        )

        # Top Selling Food
        top_food = "N/A"
        top_value = 0

        if food_totals:

            top_food = max(
                food_totals,
                key=food_totals.get
            )

            top_value = food_totals[top_food]

        return jsonify({

            "dates":
                daily_sales["DATE"].tolist(),

            "totals":
                daily_sales["TOTAL"].tolist(),

            "foods":
                food_totals,

            "monthly_total":
                monthly_total,

            "top_food":
                top_food,

            "top_value":
                top_value

        })

    except Exception as e:

        return jsonify({
            "error": str(e)
        })



# ----------------------------------------
# HOME PAGE
# ----------------------------------------

@app.route("/")
def home():

    return render_template("index.html")

@app.route("/analytics")
def analytics_report():

    data = analytics.generate_analytics()

    return jsonify(data)

@app.route("/reports")
def reports_page():
    return render_template("reports.html")


# ----------------------------------------
# VOICE DASHBOARD PAGE
# ----------------------------------------

@app.route("/voice-results")
def voice_results_page():
    return render_template("voice_results.html")

@app.route("/voice-results-data")
def voice_results_data():

    data = get_latest_voice_result()

    return jsonify(data)


# ----------------------------------------
# DASHBOARD DATA API
# ----------------------------------------

@app.route("/dashboard-data")
def dashboard_data():

    reviews = []

    try:

        conn = sqlite3.connect("sales.db")
        cursor = conn.cursor()

        cursor.execute("""
        SELECT spoken_text,
               suggested_food,
               score,
               quantity
        FROM review_queue
        WHERE status='needs_review'
        """)

        rows = cursor.fetchall()

        conn.close()

        for row in rows:

            reviews.append({
                "spoken_text": row[0],
                "suggested_food": row[1],
                "score": row[2],
                "quantity": row[3]
            })

    except:
        pass

    data = {
        "text": "",
        "matched": [],
        "unknown": [],
        "total": 0,
        "reviews": reviews
    }

    return jsonify(data)


# ----------------------------------------
# RUN SERVER
# ----------------------------------------
if __name__ == "__main__":

    if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        webbrowser.open("http://127.0.0.1:8000/voice-results")
        
    
    print(app.url_map)
    app.run(
        host="0.0.0.0",
        port=8000,
        debug=True
    )