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
    # Parse the DATABASE_URL to extract connection parameters
    # Assuming format: postgresql://username:password@hostname:port/database
    db_url_parts = DATABASE_URL.replace('postgresql://', '').split('/')
    db_name = db_url_parts[-1]
    conn_parts = db_url_parts[0].split('@')
    user_pass = conn_parts[0].split(':')
    host_port = conn_parts[1].split(':')
    
    username = user_pass[0]
    password = user_pass[1] if len(user_pass) > 1 else ''
    hostname = host_port[0]
    port = host_port[1] if len(host_port) > 1 else '5432'
    
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