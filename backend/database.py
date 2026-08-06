import sqlite3
import json

DB_NAME = "sales.db"


def get_connection():
    return sqlite3.connect(DB_NAME)


def column_exists(cursor, table_name, column_name):
    cursor.execute(f"PRAGMA table_info({table_name})")
    return any(row[1] == column_name for row in cursor.fetchall())


def normalize_food_aliases_schema(cursor):
    if not column_exists(cursor, "food_aliases", "menu_id"):
        cursor.execute("ALTER TABLE food_aliases ADD COLUMN menu_id INTEGER")

    if not column_exists(cursor, "food_aliases", "is_deleted"):
        cursor.execute("ALTER TABLE food_aliases ADD COLUMN is_deleted INTEGER DEFAULT 0")

    if not column_exists(cursor, "food_aliases", "deleted_at"):
        cursor.execute("ALTER TABLE food_aliases ADD COLUMN deleted_at TEXT")

    if column_exists(cursor, "food_aliases", "menu_item"):
        cursor.execute("""
            UPDATE food_aliases
            SET menu_id = (
                SELECT mi.id
                FROM menu_items mi
                WHERE UPPER(TRIM(mi.menu_item)) = UPPER(TRIM(food_aliases.menu_item))
                LIMIT 1
            )
            WHERE menu_id IS NULL
              AND menu_item IS NOT NULL
              AND TRIM(menu_item) != ''
        """)

    cursor.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_food_aliases_menu_alias_active
        ON food_aliases(menu_id, alias)
        WHERE COALESCE(is_deleted, 0) = 0
    """)


def create_database():
    print("create_database() is running...")
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sales (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT,
        food_name TEXT,
        quantity INTEGER,
        price REAL,
        total REAL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS review_queue (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        voice_result_id INTEGER,
        spoken_text TEXT,
        suggested_food TEXT,
        score INTEGER,
        quantity INTEGER,
        status TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS voice_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        voice_text TEXT,
        matched_foods TEXT,
        unknown_foods TEXT,
        review_count INTEGER,
        total REAL,
        status TEXT,
        created_at TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS menu_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        menu_item TEXT UNIQUE,
        tamil_word TEXT,
        category TEXT,
        price REAL,
        is_deleted INTEGER DEFAULT 0,
        deleted_at TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS food_aliases (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        menu_id INTEGER,
        alias TEXT,
        is_deleted INTEGER DEFAULT 0,
        deleted_at TEXT,
        FOREIGN KEY (menu_id) REFERENCES menu_items(id)
    )
    """)

    normalize_food_aliases_schema(cursor)

    conn.commit()
    conn.close()


def save_sale(date, food_name, quantity, price, total):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO sales
    (date, food_name, quantity, price, total)
    VALUES (?, ?, ?, ?, ?)
    """, (date, food_name, quantity, price, total))

    conn.commit()
    conn.close()


def save_review(spoken_text, suggested_food, score, quantity):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO review_queue
    (
        spoken_text,
        suggested_food,
        score,
        quantity,
        status
    )
    VALUES (?, ?, ?, ?, ?)
    """, (spoken_text, suggested_food, score, quantity, "needs_review"))

    conn.commit()
    conn.close()


def save_voice_result(
    voice_text,
    matched_foods,
    unknown_foods,
    review_count,
    total,
    status,
    created_at
):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO voice_results (
        voice_text,
        matched_foods,
        unknown_foods,
        review_count,
        total,
        status,
        created_at
    )
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        voice_text,
        matched_foods,
        unknown_foods,
        review_count,
        total,
        status,
        created_at
    ))

    voice_result_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return voice_result_id


def get_latest_voice_result():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT *
    FROM voice_results
    ORDER BY id DESC
    LIMIT 1
    """)

    row = cursor.fetchone()
    conn.close()

    if not row:
        return {}

    return {
        "id": row[0],
        "voice_text": row[1],
        "matched_foods": json.loads(row[2]),
        "unknown_foods": json.loads(row[3]),
        "review_count": row[4],
        "total": row[5],
        "status": row[6],
        "created_at": row[7]
    }


def load_menu_prices():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT menu_item, price
    FROM menu_items
    WHERE COALESCE(is_deleted, 0) = 0
    """)

    rows = cursor.fetchall()
    conn.close()

    price_map = {}

    for menu_item, price in rows:
        price_map[menu_item] = price

    return price_map


def save_menu_to_db(menu_data):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM menu_items")

    for item in menu_data:
        cursor.execute("""
        INSERT INTO menu_items
        (menu_item, tamil_word, category, price, is_deleted)
        VALUES (?, ?, ?, ?, 0)
        """, (
            item["menu_item"],
            item["tamil_word"],
            item["category"],
            item["price"]
        ))

    normalize_food_aliases_schema(cursor)

    conn.commit()
    conn.close()


def import_menu_prices():
    conn = get_connection()
    cursor = conn.cursor()

    with open("menu_prices.json", "r", encoding="utf-8") as f:
        menu_data = json.load(f)

    for item in menu_data:
        cursor.execute("""
        INSERT OR REPLACE INTO menu_items
        (menu_item, tamil_word, category, price, is_deleted)
        VALUES (?, ?, ?, ?, 0)
        """, (
            item["menu_item"],
            item["tamil_word"],
            item["category"],
            item["price"]
        ))

    normalize_food_aliases_schema(cursor)

    conn.commit()
    conn.close()

    print("Menu imported successfully!")


def import_food_aliases():
    conn = get_connection()
    cursor = conn.cursor()

    normalize_food_aliases_schema(cursor)

    cursor.execute("SELECT COUNT(*) FROM food_aliases WHERE COALESCE(is_deleted, 0) = 0")
    count = cursor.fetchone()[0]

    if count > 0:
        print("Food aliases already imported.")
        conn.close()
        return

    with open("food_aliases.json", "r", encoding="utf-8") as f:
        aliases_data = json.load(f)

    inserted = 0
    skipped = 0

    for menu_item, alias_list in aliases_data.items():
        cursor.execute("""
        SELECT id
        FROM menu_items
        WHERE UPPER(TRIM(menu_item)) = UPPER(TRIM(?))
        LIMIT 1
        """, (menu_item,))

        row = cursor.fetchone()

        if not row:
            skipped += len(alias_list)
            continue

        menu_id = row[0]

        for alias in alias_list:
            alias = str(alias).strip()

            if not alias:
                skipped += 1
                continue

            cursor.execute("""
            SELECT id
            FROM food_aliases
            WHERE menu_id = ?
              AND alias = ?
              AND COALESCE(is_deleted, 0) = 0
            """, (menu_id, alias))

            if cursor.fetchone():
                skipped += 1
                continue

            cursor.execute("""
            INSERT INTO food_aliases
            (menu_id, alias, is_deleted)
            VALUES (?, ?, 0)
            """, (menu_id, alias))
            inserted += 1

    conn.commit()
    conn.close()

    print(f"Food aliases imported successfully! Inserted: {inserted}, skipped: {skipped}")


def load_food_aliases():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT mi.menu_item, fa.alias
    FROM food_aliases fa
    JOIN menu_items mi ON mi.id = fa.menu_id
    WHERE COALESCE(fa.is_deleted, 0) = 0
      AND COALESCE(mi.is_deleted, 0) = 0
    ORDER BY mi.menu_item, fa.alias
    """)

    aliases = cursor.fetchall()
    conn.close()

    return aliases


def load_all_foods():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT menu_item
    FROM menu_items
    WHERE COALESCE(is_deleted, 0) = 0
    """)

    rows = cursor.fetchall()
    conn.close()

    return [row[0] for row in rows]


def database_is_empty():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM menu_items")
    menu_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM food_aliases")
    alias_count = cursor.fetchone()[0]

    conn.close()

    return menu_count == 0 and alias_count == 0
