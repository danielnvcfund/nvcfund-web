from flask import Flask
from sqlalchemy.dialects import postgresql
from models import WireTransfer, db

app = Flask(__name__)

with app.app_context():
    # Create a sample instance
    new_wire = WireTransfer()
    
    # Get the SQL for an INSERT operation
    insert_stmt = postgresql.insert(WireTransfer.__table__).values({})
    
    # Print the SQL statement string without executing it
    print(str(insert_stmt))