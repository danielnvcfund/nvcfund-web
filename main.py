from app import app  # noqa: F401
from flask import send_file
from routes.currency_exchange_routes import register_currency_exchange_routes
from routes.portfolio_routes import portfolio_bp

# Register blueprints
app.register_blueprint(portfolio_bp)

# Register the currency exchange routes
register_currency_exchange_routes(app)

# Add a route to show the color comparison demo
@app.route('/color-demo')
def color_demo():
    return send_file('static/demo_colors.html')

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)