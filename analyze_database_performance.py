#!/usr/bin/env python3
"""
Database Performance Analyzer for NVC Banking Platform

This script analyzes database performance and recommends optimizations.
"""

import logging
import time
import os
import sys
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker
from collections import defaultdict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("db_analyzer")

# Get database URL from environment
DATABASE_URL = os.environ.get("DATABASE_URL")

if not DATABASE_URL:
    logger.error("DATABASE_URL environment variable not set")
    sys.exit(1)

# Create engine
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

def time_query(query_text, params=None, iterations=3):
    """Time the execution of a query"""
    session = Session()
    try:
        # Warm up
        session.execute(text(query_text), params or {})
        
        times = []
        for _ in range(iterations):
            start = time.time()
            result = session.execute(text(query_text), params or {})
            execution_time = time.time() - start
            times.append(execution_time)
            # Fetch all results to ensure complete execution
            _ = result.fetchall()
            
        return {
            'min': min(times),
            'max': max(times),
            'avg': sum(times) / len(times),
            'iterations': iterations
        }
    finally:
        session.close()

def get_table_stats():
    """Get statistics on all tables"""
    inspector = inspect(engine)
    stats = {}
    
    for table_name in inspector.get_table_names():
        try:
            # Get row count
            with engine.connect() as conn:
                result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                row_count = result.scalar()
                
            # Get storage size
            with engine.connect() as conn:
                result = conn.execute(text(f"""
                    SELECT pg_size_pretty(pg_total_relation_size('{table_name}')) AS size
                """))
                size = result.scalar()
                
            # Get indices
            indices = inspector.get_indexes(table_name)
            
            stats[table_name] = {
                'row_count': row_count,
                'size': size,
                'indices': len(indices),
                'index_names': [idx['name'] for idx in indices]
            }
        except Exception as e:
            logger.error(f"Error getting stats for table {table_name}: {str(e)}")
            stats[table_name] = {'error': str(e)}
            
    return stats

def analyze_common_queries():
    """Analyze performance of common queries"""
    queries = [
        {
            'name': 'Currency Exchange Rate Lookup',
            'sql': """
                SELECT rate FROM currency_exchange_rate 
                WHERE from_currency = :from_currency AND to_currency = :to_currency 
                ORDER BY last_updated DESC LIMIT 1
            """,
            'params': {'from_currency': 'NVCT', 'to_currency': 'USD'}
        },
        {
            'name': 'Account Lookup',
            'sql': """
                SELECT id, account_number, account_name, balance 
                FROM bank_account 
                WHERE account_holder_id = :account_holder_id
            """,
            'params': {'account_holder_id': 1}
        },
        {
            'name': 'Recent Transactions',
            'sql': """
                SELECT * FROM currency_exchange_transaction 
                ORDER BY created_at DESC LIMIT 10
            """,
            'params': {}
        },
    ]
    
    results = {}
    for query in queries:
        try:
            logger.info(f"Analyzing query: {query['name']}")
            timing = time_query(query['sql'], query['params'])
            results[query['name']] = timing
            logger.info(f"  Avg time: {timing['avg']*1000:.2f}ms")
        except Exception as e:
            logger.error(f"Error analyzing query {query['name']}: {str(e)}")
            results[query['name']] = {'error': str(e)}
            
    return results

def suggest_indices():
    """Suggest indices based on common query patterns"""
    inspector = inspect(engine)
    
    # Known model relationships that might benefit from indexing
    index_suggestions = [
        {
            'table': 'bank_account',
            'column': 'account_holder_id',
            'reason': 'Frequent lookups by account holder'
        },
        {
            'table': 'currency_exchange_rate',
            'columns': ['from_currency', 'to_currency'],
            'reason': 'Frequent currency exchange rate lookups'
        },
        {
            'table': 'currency_exchange_transaction',
            'column': 'created_at',
            'reason': 'Sorting by creation time'
        },
        {
            'table': 'address',
            'column': 'account_holder_id',
            'reason': 'Frequent lookups by account holder'
        },
        {
            'table': 'phone_number',
            'column': 'account_holder_id',
            'reason': 'Frequent lookups by account holder'
        }
    ]
    
    # Check which suggested indices already exist
    existing_indices = {}
    for suggestion in index_suggestions:
        table = suggestion['table']
        if table not in existing_indices:
            try:
                existing_indices[table] = inspector.get_indexes(table)
            except Exception as e:
                logger.error(f"Error getting indices for table {table}: {str(e)}")
                existing_indices[table] = []
    
    # Filter out suggestions for indices that already exist
    filtered_suggestions = []
    for suggestion in index_suggestions:
        table = suggestion['table']
        if 'column' in suggestion:
            column = suggestion['column']
            exists = any(column in idx.get('column_names', []) for idx in existing_indices.get(table, []))
            if not exists:
                filtered_suggestions.append(suggestion)
        elif 'columns' in suggestion:
            columns = set(suggestion['columns'])
            exists = any(
                set(idx.get('column_names', [])) == columns or 
                any(col in idx.get('column_names', []) for col in columns)
                for idx in existing_indices.get(table, [])
            )
            if not exists:
                filtered_suggestions.append(suggestion)
    
    return filtered_suggestions

def check_missing_updates():
    """Check for missing database updates/migrations"""
    issues = []
    
    # Check for JSON fields where text might have been used
    with engine.connect() as conn:
        # Check if currency_exchange_rate has the right enum type
        result = conn.execute(text("""
            SELECT data_type FROM information_schema.columns 
            WHERE table_name = 'currency_exchange_rate' AND column_name = 'from_currency'
        """))
        data_type = result.scalar()
        if data_type != 'USER-DEFINED':
            issues.append({
                'table': 'currency_exchange_rate',
                'column': 'from_currency',
                'issue': f'Not using proper enum type (found {data_type})',
                'fix': 'Alter column to use CurrencyType enum'
            })
    
    return issues

def generate_report(stats, query_results, index_suggestions, issues):
    """Generate a comprehensive performance report"""
    print("\n" + "="*80)
    print("NVC BANKING PLATFORM DATABASE PERFORMANCE REPORT")
    print("="*80)
    
    print("\nTABLE STATISTICS:")
    print("-"*80)
    print(f"{'Table':<30} {'Rows':<10} {'Size':<15} {'Indices':<10}")
    print("-"*80)
    for table, data in stats.items():
        if 'error' not in data:
            print(f"{table:<30} {data['row_count']:<10} {data['size']:<15} {data['indices']:<10}")
    
    print("\nQUERY PERFORMANCE:")
    print("-"*80)
    print(f"{'Query':<40} {'Avg (ms)':<15} {'Min (ms)':<15} {'Max (ms)':<15}")
    print("-"*80)
    for query, data in query_results.items():
        if 'error' not in data:
            print(f"{query:<40} {data['avg']*1000:<15.2f} {data['min']*1000:<15.2f} {data['max']*1000:<15.2f}")
        else:
            print(f"{query:<40} ERROR: {data['error']}")
    
    print("\nSUGGESTED INDICES:")
    print("-"*80)
    if index_suggestions:
        for suggestion in index_suggestions:
            if 'column' in suggestion:
                print(f"Table: {suggestion['table']}, Column: {suggestion['column']}")
            else:
                print(f"Table: {suggestion['table']}, Columns: {', '.join(suggestion['columns'])}")
            print(f"  Reason: {suggestion['reason']}")
            print()
    else:
        print("No additional indices recommended.")
    
    print("\nDATABASE ISSUES:")
    print("-"*80)
    if issues:
        for issue in issues:
            print(f"Table: {issue['table']}, Column: {issue['column']}")
            print(f"  Issue: {issue['issue']}")
            print(f"  Fix: {issue['fix']}")
            print()
    else:
        print("No database issues detected.")
    
    print("\nOPTIMIZATION RECOMMENDATIONS:")
    print("-"*80)
    print("1. Add suggested indices to improve query performance")
    print("2. Consider adding caching for frequently accessed data")
    print("3. Optimize ORM queries to reduce N+1 query problems")
    print("4. Consider using connection pooling for better database utilization")
    print("5. Review slow queries and optimize their execution plans")
    
    print("\nNote: These suggestions are based on a simple analysis and should be")
    print("      thoroughly tested before applying to a production environment.")

def run_analysis():
    """Run complete database performance analysis"""
    try:
        logger.info("Getting table statistics...")
        stats = get_table_stats()
        
        logger.info("Analyzing common queries...")
        query_results = analyze_common_queries()
        
        logger.info("Suggesting indices...")
        index_suggestions = suggest_indices()
        
        logger.info("Checking for database issues...")
        issues = check_missing_updates()
        
        logger.info("Generating report...")
        generate_report(stats, query_results, index_suggestions, issues)
        
    except Exception as e:
        logger.error(f"Error during analysis: {str(e)}")
        raise

if __name__ == "__main__":
    run_analysis()