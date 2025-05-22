from app import app  # noqa: F401
from routes.currency_exchange_routes import register_currency_exchange_routes

# Register the currency exchange routes
register_currency_exchange_routes(app)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)