import sqlite3

conn = sqlite3.connect("sales.db")

cursor = conn.cursor()

print("\n===== SALES TABLE =====\n")

cursor.execute("SELECT * FROM sales")

rows = cursor.fetchall()

for row in rows:
    print(row)


print("\n===== REVIEW QUEUE TABLE =====\n")

cursor.execute("SELECT * FROM review_queue")

review_rows = cursor.fetchall()

for row in review_rows:
    print(row)


conn.close()