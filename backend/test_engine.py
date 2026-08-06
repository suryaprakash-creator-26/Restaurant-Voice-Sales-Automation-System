from analytics_engine_chatbot import AnalyticsEngine

engine = AnalyticsEngine()

request = {
    "dimension": "date",
    "metric": "total",
    "operation": "sum",
    "filters": {
        "date": "08-06-2026"
    }
}

result = engine.execute(request)

print(result)