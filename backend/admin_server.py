from flask import Flask, render_template, jsonify, request, send_file
from flask_cors import CORS
from database import get_connection
import sqlite3
import os
import webbrowser
import io
from datetime import datetime

app = Flask(__name__, template_folder="templates")
CORS(app)


DB_NAME= "sales.db"
def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def split_aliases(raw_aliases):
    if not raw_aliases:
        return []

    aliases = []

    for part in raw_aliases.replace("\n", ",").split(","):
        alias = part.strip()

        if alias and alias not in aliases:
            aliases.append(alias)

    return aliases



@app.route("/")
def home():
    return "Admin Server Running Successfully"


@app.route("/admin")
def admin():
    return render_template("admin.html")


@app.route("/admin/menu", methods=["GET"])
def menu():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, menu_item, tamil_word, category, price
        FROM menu_items
        WHERE COALESCE(is_deleted, 0) = 0
        ORDER BY menu_item ASC
    """)

    data = [dict(row) for row in cur.fetchall()]
    conn.close()
    return jsonify(data)


@app.route("/admin/menu", methods=["POST"])
def add_menu_item():
    data = request.json or {}

    menu_item = data.get("menu_item") or data.get("item")
    tamil_word = data.get("tamil_word", "")
    category = data.get("category", "")
    price = data.get("price")

    if not menu_item or price is None:
        return jsonify({"status": "error", "message": "Menu item and price are required"}), 400

    conn = get_db()
    cur = conn.cursor()

    try:
        cur.execute("""
            INSERT INTO menu_items (menu_item, tamil_word, category, price, is_deleted)
            VALUES (?, ?, ?, ?, 0)
        """, (menu_item.upper(), tamil_word, category, float(price)))
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({"status": "error", "message": "Menu item already exists"}), 409

    conn.close()
    return jsonify({"status": "success", "message": "Menu item added successfully"})


@app.route("/admin/menu/<int:item_id>", methods=["PUT"])
def update_menu_item(item_id):
    data = request.json or {}

    menu_item = data.get("menu_item") or data.get("item")
    tamil_word = data.get("tamil_word", "")
    category = data.get("category", "")
    price = data.get("price")

    if not menu_item or price is None:
        return jsonify({"status": "error", "message": "Menu item and price are required"}), 400

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        UPDATE menu_items
        SET menu_item = ?, tamil_word = ?, category = ?, price = ?
        WHERE id = ?
    """, (menu_item.upper(), tamil_word, category, float(price), item_id))

    conn.commit()
    conn.close()

    return jsonify({"status": "success", "message": "Menu item updated successfully"})


@app.route("/admin/menu/<int:item_id>", methods=["DELETE"])
def delete_menu_item(item_id):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        UPDATE menu_items
        SET is_deleted = 1, deleted_at = ?
        WHERE id = ?
    """, (datetime.now().isoformat(timespec="seconds"), item_id))

    conn.commit()
    conn.close()

    return jsonify({"status": "success", "message": "Menu item moved to bin"})


@app.route("/admin/aliases", methods=["GET"])
def aliases():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            fa.id,
            fa.menu_id,
            mi.menu_item,
            fa.alias
        FROM food_aliases fa
        JOIN menu_items mi ON mi.id = fa.menu_id
        WHERE COALESCE(fa.is_deleted, 0) = 0
        ORDER BY mi.menu_item ASC, fa.alias ASC
    """)

    data = [dict(row) for row in cur.fetchall()]
    conn.close()
    return jsonify(data)


@app.route("/admin/aliases", methods=["POST"])
def add_alias():
    data = request.json or {}

    menu_id = data.get("menu_id")
    raw_aliases = data.get("aliases") or data.get("alias")
    print("menu_id =", menu_id)
    print("aliases =", raw_aliases)
    aliases_to_add = split_aliases(raw_aliases)

    if not menu_id or not aliases_to_add:
        return jsonify({
            "status": "error",
            "message": "Menu item and at least one alias are required"
        }), 400

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT id
        FROM menu_items
        WHERE id = ? AND COALESCE(is_deleted, 0) = 0
    """, (menu_id,))

    if not cur.fetchone():
        conn.close()
        return jsonify({"status": "error", "message": "Invalid menu item"}), 400

    inserted = 0
    skipped = 0

    for alias in aliases_to_add:
        cur.execute("""
            SELECT id
            FROM food_aliases
            WHERE menu_id = ?
              AND alias = ?
              AND COALESCE(is_deleted, 0) = 0
        """, (menu_id, alias))

        if cur.fetchone():
            skipped += 1
            continue

        cur.execute("""
            INSERT INTO food_aliases (menu_id, alias, is_deleted)
            VALUES (?, ?, 0)
        """, (menu_id, alias))
        inserted += 1

    conn.commit()
    conn.close()

    return jsonify({
        "status": "success",
        "message": f"{inserted} alias added, {skipped} duplicate skipped",
        "inserted": inserted,
        "skipped": skipped
    })


@app.route("/admin/aliases/<int:alias_id>", methods=["PUT"])
def update_alias(alias_id):
    data = request.json or {}

    menu_id = data.get("menu_id")
    alias = (data.get("alias") or "").strip()

    if not menu_id or not alias:
        return jsonify({"status": "error", "message": "Menu item and alias are required"}), 400

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT id
        FROM food_aliases
        WHERE menu_id = ?
          AND alias = ?
          AND id != ?
          AND COALESCE(is_deleted, 0) = 0
    """, (menu_id, alias, alias_id))

    if cur.fetchone():
        conn.close()
        return jsonify({"status": "error", "message": "Duplicate alias for this menu item"}), 409

    cur.execute("""
        UPDATE food_aliases
        SET menu_id = ?, alias = ?
        WHERE id = ?
    """, (menu_id, alias, alias_id))

    conn.commit()
    conn.close()

    return jsonify({"status": "success", "message": "Alias updated successfully"})


@app.route("/admin/aliases/<int:alias_id>", methods=["DELETE"])
def delete_alias(alias_id):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        UPDATE food_aliases
        SET is_deleted = 1, deleted_at = ?
        WHERE id = ?
    """, (datetime.now().isoformat(timespec="seconds"), alias_id))

    conn.commit()
    conn.close()

    return jsonify({"status": "success", "message": "Alias moved to bin"})


@app.route("/admin/bin", methods=["GET"])
def bin_items():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, menu_item, tamil_word, category, price, deleted_at
        FROM menu_items
        WHERE COALESCE(is_deleted, 0) = 1
        ORDER BY deleted_at DESC
    """)
    deleted_menu = [dict(row) for row in cur.fetchall()]

    cur.execute("""
        SELECT
            fa.id,
            fa.menu_id,
            mi.menu_item,
            fa.alias,
            fa.deleted_at
        FROM food_aliases fa
        JOIN menu_items mi ON mi.id = fa.menu_id
        WHERE COALESCE(fa.is_deleted, 0) = 1
        ORDER BY fa.deleted_at DESC
    """)
    deleted_aliases = [dict(row) for row in cur.fetchall()]

    conn.close()

    return jsonify({
        "menu_items": deleted_menu,
        "food_aliases": deleted_aliases
    })


@app.route("/admin/bin/menu/<int:item_id>/restore", methods=["POST"])
def restore_menu_item(item_id):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        UPDATE menu_items
        SET is_deleted = 0, deleted_at = NULL
        WHERE id = ?
    """, (item_id,))

    conn.commit()
    conn.close()

    return jsonify({"status": "success", "message": "Menu item restored"})


@app.route("/admin/bin/aliases/<int:alias_id>/restore", methods=["POST"])
def restore_alias(alias_id):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        UPDATE food_aliases
        SET is_deleted = 0, deleted_at = NULL
        WHERE id = ?
    """, (alias_id,))

    conn.commit()
    conn.close()

    return jsonify({"status": "success", "message": "Alias restored"})


@app.route("/admin/sales", methods=["GET"])
def sales():
    date = request.args.get("date", "").strip()
    start_date = request.args.get("start_date", "").strip()
    end_date = request.args.get("end_date", "").strip()
    food_name = request.args.get("food_name", "").strip()

    query = """
        SELECT id, date, food_name, quantity, price, total
        FROM sales
        WHERE 1 = 1
    """
    params = []

    if date:
        query += " AND date = ?"
        params.append(date)

    if start_date:
        query += " AND date >= ?"
        params.append(start_date)

    if end_date:
        query += " AND date <= ?"
        params.append(end_date)

    if food_name:
        query += " AND food_name = ?"
        params.append(food_name)

    query += " ORDER BY date DESC, id DESC"

    conn = get_db()
    cur = conn.cursor()
    cur.execute(query, params)

    data = [dict(row) for row in cur.fetchall()]
    conn.close()

    return jsonify(data)


@app.route("/admin/sales/foods", methods=["GET"])
def sales_foods():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT DISTINCT food_name
        FROM sales
        WHERE food_name IS NOT NULL AND food_name != ''
        ORDER BY food_name ASC
    """)

    data = [row["food_name"] for row in cur.fetchall()]
    conn.close()

    return jsonify(data)


@app.route("/admin/sales/pdf", methods=["GET"])
def sales_pdf():
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet
    except ImportError:
        return jsonify({
            "status": "error",
            "message": "Install reportlab first: pip install reportlab"
        }), 500

    date = request.args.get("date", "").strip()
    start_date = request.args.get("start_date", "").strip()
    end_date = request.args.get("end_date", "").strip()
    food_name = request.args.get("food_name", "").strip()

    query = """
        SELECT id, date, food_name, quantity, price, total
        FROM sales
        WHERE 1 = 1
    """
    params = []

    if date:
        query += " AND date = ?"
        params.append(date)

    if start_date:
        query += " AND date >= ?"
        params.append(start_date)

    if end_date:
        query += " AND date <= ?"
        params.append(end_date)

    if food_name:
        query += " AND food_name = ?"
        params.append(food_name)

    query += " ORDER BY date DESC, id DESC"

    conn = get_db()
    cur = conn.cursor()
    cur.execute(query, params)
    rows = [dict(row) for row in cur.fetchall()]
    conn.close()

    total_qty = sum(row["quantity"] or 0 for row in rows)
    total_amount = sum(row["total"] or 0 for row in rows)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph("Voice Sales Report", styles["Title"]))
    elements.append(Spacer(1, 12))

    filter_text = f"Date: {date or '-'} | From: {start_date or '-'} | To: {end_date or '-'} | Food: {food_name or 'All'}"
    elements.append(Paragraph(filter_text, styles["Normal"]))
    elements.append(Spacer(1, 12))

    table_data = [["ID", "Date", "Food", "Qty", "Price", "Total"]]

    for row in rows:
        table_data.append([
            row["id"],
            row["date"],
            row["food_name"],
            row["quantity"],
            row["price"],
            row["total"]
        ])

    table_data.append(["", "", "TOTAL", total_qty, "", total_amount])

    table = Table(table_data, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightblue),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("BACKGROUND", (0, -1), (-1, -1), colors.whitesmoke),
    ]))

    elements.append(table)
    doc.build(elements)

    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name="sales_report.pdf",
        mimetype="application/pdf"
    )


@app.route("/admin/add_food", methods=["POST"])
def add_food_old():
    return add_menu_item()


if __name__ == "__main__":
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        webbrowser.open("http://127.0.0.1:5001/admin")

    print("Admin Server Starting on http://127.0.0.1:5001/admin")

    app.run(
        host="0.0.0.0",
        port=5001,
        debug=True
    )
