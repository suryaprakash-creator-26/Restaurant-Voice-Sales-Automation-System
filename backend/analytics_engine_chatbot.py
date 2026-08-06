import sqlite3
from datetime import datetime
from typing import Dict, Any

DB_PATH = "sales.db"



# -----------------------------
# Helper Function
# -----------------------------
def normalize_date(date_str):
    """
    Convert YYYY-MM-DD to DD-MM-YYYY.
    If already DD-MM-YYYY, return as is.
    """
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return dt.strftime("%d-%m-%Y")
    except ValueError:
        return date_str
    
class AnalyticsEngine:

    VALID_COLUMNS = {
        "date",
        "food_name",
        "quantity",
        "price",
        "total"
    }

    VALID_OPERATIONS = {
        "sum",
        "avg",
        "min",
        "max",
        "count",
        "top",
        "bottom"
    }

    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        
    

    def execute(self, request: Dict[str, Any]):
        
        print("STEP 1 : execute() called")
        print("Request:", request)

        dimension = request.get("dimension")
        metric = request.get("metric")
        operation = request.get("operation")
        filters = request.get("filters", {})
        group_by = request.get("group_by")
        limit = request.get("limit")
        
        print("STEP 2 : Validation Passed")

        if dimension not in self.VALID_COLUMNS:
            return {"status": "error", "message": "Invalid dimension"}

        if metric not in self.VALID_COLUMNS:
            return {"status": "error", "message": "Invalid metric"}

        if operation not in self.VALID_OPERATIONS:
            return {"status": "error", "message": "Invalid operation"}

        sql = self.build_query(
            metric,
            operation,
            filters,
            group_by,
            limit
        )

        return self.run_query(sql["query"], sql["params"])

    def build_query(
        self,
        metric,
        operation,
        filters,
        group_by,
        limit
    ):
        
        

        params = []

        if operation == "sum":
            select = f"SUM({metric})"

        elif operation == "avg":
            select = f"AVG({metric})"

        elif operation == "min":
            select = f"MIN({metric})"

        elif operation == "max":
            select = f"MAX({metric})"

        elif operation == "count":
            select = "COUNT(*)"

        elif operation in ("top", "bottom"):
            select = f"{group_by}, SUM({metric}) AS value"

        sql = f"SELECT {select} FROM sales"

        where = []

        for key, value in filters.items():

            if key not in self.VALID_COLUMNS:
                continue

            # Convert date to database format
            if key == "date":
                value = normalize_date(value)
                
            where.append(f"{key}=?")
            params.append(value)

        if where:
            sql += " WHERE " + " AND ".join(where)

        if operation in ("top", "bottom"):

            sql += f" GROUP BY {group_by}"

            order = "DESC" if operation == "top" else "ASC"

            sql += f" ORDER BY value {order}"

            if limit:
                sql += f" LIMIT {limit}"
        
        
        # ✅ Debug here
        print("STEP 3 : SQL Generated")
        print("SQL :", sql)
        print("Params :", params)

        return {
            "query": sql,
            "params": params
        }
        

    def run_query(self, query, params):

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row

        cur = conn.cursor()

        cur.execute(query, params)

        rows = cur.fetchall()

        conn.close()

        return {
            "status": "success",
            "data": [dict(i) for i in rows]
        }