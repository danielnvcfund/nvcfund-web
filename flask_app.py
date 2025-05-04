import os
from app import app

# Use the PORT environment variable provided by Replit if available, default to 8080
port = int(os.environ.get("PORT", 8080))
app.run(host="0.0.0.0", port=port, debug=True)