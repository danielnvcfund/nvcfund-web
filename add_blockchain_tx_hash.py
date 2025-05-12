"""
Add missing tx_hash column to blockchain_transaction table
"""
import os
import sys
import psycopg2
from psycopg2 import sql
from sqlalchemy import create_engine, MetaData, Table, Column, String
from sqlalchemy.exc import OperationalError

# Get database URL from environment
DATABASE_URL = os.environ.get('DATABASE_URL')

if not DATABASE_URL:
    print("Error: DATABASE_URL not set in environment")
    sys.exit(1)

try:
    # Use a dedicated URL parser to handle PostgreSQL URLs correctly
    from urllib.parse import urlparse, parse_qs
    
    # Parse the DATABASE_URL
    parsed_url = urlparse(DATABASE_URL)
    
    # Extract connection parameters
    username = parsed_url.username
    password = parsed_url.password
    hostname = parsed_url.hostname
    port = parsed_url.port or '5432'
    
    # Handle path (remove leading slash) and query parameters
    path_parts = parsed_url.path.split('/')
    db_name = path_parts[-1] if path_parts[-1] else path_parts[-2]  # Handle trailing slash
    
    # Connect directly with psycopg2
    print(f"Connecting to database {db_name} on {hostname}:{port} as {username}...")
    conn = psycopg2.connect(
        dbname=db_name,
        user=username,
        password=password,
        host=hostname,
        port=port
    )
    conn.autocommit = True
    cursor = conn.cursor()
    
    # Check if the table exists
    cursor.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'blockchain_transaction');")
    if not cursor.fetchone()[0]:
        print("Error: blockchain_transaction table does not exist")
        sys.exit(1)
    
    # Check if tx_hash column already exists
    cursor.execute("SELECT EXISTS (SELECT FROM information_schema.columns WHERE table_name = 'blockchain_transaction' AND column_name = 'tx_hash');")
    if cursor.fetchone()[0]:
        print("Column tx_hash already exists in blockchain_transaction table")
        sys.exit(0)
    
    # Add the tx_hash column
    print("Adding tx_hash column to blockchain_transaction table...")
    cursor.execute("ALTER TABLE blockchain_transaction ADD COLUMN tx_hash VARCHAR(66) UNIQUE;")
    
    print("Column tx_hash added successfully")
    
except OperationalError as e:
    print(f"Database error: {str(e)}")
    sys.exit(1)
except Exception as e:
    print(f"Error: {str(e)}")
    sys.exit(1)