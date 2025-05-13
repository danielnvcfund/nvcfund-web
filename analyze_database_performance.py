"""
Database Performance Analyzer Tool

This script analyzes database performance and provides recommendations
for optimization. It checks table sizes, missing indices, slow queries,
and suggests improvements for the NVC Banking Platform database.
"""

import os
import sys
import time
import logging
import psycopg2
from psycopg2.extras import DictCursor
from datetime import datetime
from typing import List, Dict, Any, Tuple

# Configure logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("DBAnalyzer")

class DatabasePerformanceAnalyzer:
    """Analyze PostgreSQL database performance and recommend optimizations"""
    
    def __init__(self):
        """Initialize the analyzer with database connection"""
        self.db_url = os.environ.get("DATABASE_URL")
        self.connection = None
        self.cursor = None
        self.results = {
            "large_tables": [],
            "missing_indices": [],
            "slow_queries": [],
            "recommendations": []
        }
        
    def connect(self) -> bool:
        """Connect to the database"""
        try:
            self.connection = psycopg2.connect(self.db_url)
            self.cursor = self.connection.cursor(cursor_factory=DictCursor)
            logger.info("Connected to database successfully")
            return True
        except Exception as e:
            logger.error(f"Database connection error: {str(e)}")
            return False
            
    def close(self):
        """Close database connection"""
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()
        logger.info("Database connection closed")
        
    def analyze_table_sizes(self):
        """Analyze table sizes and identify large tables"""
        query = """
            SELECT 
                relname as table_name,
                pg_size_pretty(pg_total_relation_size(relid)) as table_size,
                pg_total_relation_size(relid) as size_in_bytes
            FROM pg_catalog.pg_statio_user_tables
            ORDER BY pg_total_relation_size(relid) DESC;
        """
        
        try:
            self.cursor.execute(query)
            tables = self.cursor.fetchall()
            
            # Identify large tables (> 10MB)
            large_tables = [
                {
                    "table_name": table["table_name"],
                    "size": table["table_size"],
                    "bytes": table["size_in_bytes"]
                }
                for table in tables
                if table["size_in_bytes"] > 10 * 1024 * 1024  # > 10MB
            ]
            
            self.results["large_tables"] = large_tables
            
            # Add recommendations for large tables
            for table in large_tables:
                self.results["recommendations"].append(
                    f"Consider partitioning the large table {table['table_name']} ({table['size']})"
                )
                
            logger.info(f"Found {len(large_tables)} large tables")
        except Exception as e:
            logger.error(f"Error analyzing table sizes: {str(e)}")
            
    def analyze_missing_indices(self):
        """Find potential missing indices based on column naming patterns"""
        # Common columns that should be indexed
        common_indexed_columns = [
            "id", "user_id", "account_id", "order_id", "transaction_id",
            "email", "username", "external_id", "reference_number",
            "account_number", "account_holder_id", "from_account_id", "to_account_id"
        ]
        
        # Query to find tables
        table_query = """
            SELECT tablename 
            FROM pg_catalog.pg_tables 
            WHERE schemaname = 'public';
        """
        
        try:
            self.cursor.execute(table_query)
            tables = [row["tablename"] for row in self.cursor.fetchall()]
            
            missing_indices = []
            
            # Check each table for missing indices on common columns
            for table in tables:
                # Get columns for this table
                column_query = f"""
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_name = '{table}';
                """
                self.cursor.execute(column_query)
                columns = [row["column_name"] for row in self.cursor.fetchall()]
                
                # Get existing indices for this table
                index_query = f"""
                    SELECT indexname, indexdef
                    FROM pg_indexes
                    WHERE tablename = '{table}';
                """
                self.cursor.execute(index_query)
                indices = self.cursor.fetchall()
                indexed_columns = []
                
                # Extract column names from index definitions
                for idx in indices:
                    index_def = idx["indexdef"]
                    for col in columns:
                        if f"({col})" in index_def or f"({table}.{col})" in index_def:
                            indexed_columns.append(col)
                
                # Find missing indices on common columns
                for col in common_indexed_columns:
                    if col in columns and col not in indexed_columns:
                        missing_indices.append({
                            "table": table,
                            "column": col
                        })
                        
                        # Add recommendation
                        self.results["recommendations"].append(
                            f"Create index on {table}({col}) - commonly accessed column"
                        )
            
            self.results["missing_indices"] = missing_indices
            logger.info(f"Found {len(missing_indices)} potentially missing indices")
        except Exception as e:
            logger.error(f"Error analyzing missing indices: {str(e)}")
            
    def analyze_query_performance(self):
        """Analyze query performance from pg_stat_statements if available"""
        # Check if pg_stat_statements is installed
        check_query = """
            SELECT EXISTS (
                SELECT 1 FROM pg_extension WHERE extname = 'pg_stat_statements'
            );
        """
        
        try:
            self.cursor.execute(check_query)
            has_pg_stat = self.cursor.fetchone()[0]
            
            if has_pg_stat:
                # Query to get slow queries
                slow_query = """
                    SELECT 
                        round(mean_exec_time::numeric, 2) as avg_time,
                        calls,
                        query
                    FROM pg_stat_statements
                    WHERE mean_exec_time > 100  -- queries taking > 100ms
                    ORDER BY mean_exec_time DESC
                    LIMIT 10;
                """
                
                self.cursor.execute(slow_query)
                slow_queries = self.cursor.fetchall()
                
                # Process slow queries
                for query in slow_queries:
                    self.results["slow_queries"].append({
                        "avg_time_ms": query["avg_time"],
                        "calls": query["calls"],
                        "query": query["query"]
                    })
                    
                    # Add recommendation
                    if "SELECT" in query["query"]:
                        self.results["recommendations"].append(
                            f"Optimize slow SELECT query (avg: {query['avg_time']}ms, calls: {query['calls']})"
                        )
                    elif "UPDATE" in query["query"]:
                        self.results["recommendations"].append(
                            f"Optimize slow UPDATE query (avg: {query['avg_time']}ms, calls: {query['calls']})"
                        )
                    elif "INSERT" in query["query"]:
                        self.results["recommendations"].append(
                            f"Optimize slow INSERT query (avg: {query['avg_time']}ms, calls: {query['calls']})"
                        )
                
                logger.info(f"Found {len(slow_queries)} slow queries")
            else:
                logger.warning("pg_stat_statements extension not available - skipping query analysis")
                self.results["recommendations"].append(
                    "Enable pg_stat_statements extension to analyze query performance"
                )
        except Exception as e:
            logger.error(f"Error analyzing query performance: {str(e)}")
            
    def check_database_stats(self):
        """Check general database statistics"""
        stats_query = """
            SELECT 
                pg_database_size(current_database()) as db_size_bytes,
                pg_size_pretty(pg_database_size(current_database())) as db_size,
                (SELECT count(*) FROM pg_stat_activity) as connections
        """
        
        try:
            self.cursor.execute(stats_query)
            stats = self.cursor.fetchone()
            
            # Add overall stats to results
            self.results["database_stats"] = {
                "size_bytes": stats["db_size_bytes"],
                "size_pretty": stats["db_size"],
                "connections": stats["connections"]
            }
            
            # Add recommendations based on stats
            if stats["db_size_bytes"] > 1 * 1024 * 1024 * 1024:  # > 1GB
                self.results["recommendations"].append(
                    f"Large database ({stats['db_size']}) - consider regular vacuum and database maintenance"
                )
                
            if stats["connections"] > 20:
                self.results["recommendations"].append(
                    f"High connection count ({stats['connections']}) - optimize connection pooling"
                )
                
            logger.info(f"Database size: {stats['db_size']}, Connections: {stats['connections']}")
        except Exception as e:
            logger.error(f"Error checking database stats: {str(e)}")
            
    def run_analysis(self):
        """Run complete database performance analysis"""
        if not self.connect():
            return None
            
        try:
            logger.info("Starting database performance analysis")
            
            # Run all analysis functions
            self.analyze_table_sizes()
            self.analyze_missing_indices()
            self.analyze_query_performance()
            self.check_database_stats()
            
            logger.info(f"Analysis complete - found {len(self.results['recommendations'])} recommendations")
            
            # Close database connection
            self.close()
            
            return self.results
        except Exception as e:
            logger.error(f"Error during database analysis: {str(e)}")
            self.close()
            return None
            
    def print_report(self):
        """Print formatted performance analysis report"""
        if not self.results:
            logger.error("No analysis results available")
            return
            
        print("\n" + "=" * 80)
        print("DATABASE PERFORMANCE ANALYSIS REPORT")
        print("=" * 80)
        
        # Print database stats
        if "database_stats" in self.results:
            stats = self.results["database_stats"]
            print(f"\nDatabase Size: {stats['size_pretty']}")
            print(f"Active Connections: {stats['connections']}")
        
        # Print large tables
        if self.results["large_tables"]:
            print("\nLARGE TABLES:")
            for table in self.results["large_tables"]:
                print(f"  - {table['table_name']}: {table['size']}")
                
        # Print missing indices
        if self.results["missing_indices"]:
            print("\nPOTENTIALLY MISSING INDICES:")
            for idx in self.results["missing_indices"]:
                print(f"  - {idx['table']}.{idx['column']}")
                
        # Print slow queries
        if self.results["slow_queries"]:
            print("\nSLOW QUERIES:")
            for i, query in enumerate(self.results["slow_queries"], 1):
                print(f"  {i}. Avg Time: {query['avg_time_ms']}ms, Calls: {query['calls']}")
                print(f"     Query: {query['query'][:100]}..." if len(query['query']) > 100 else f"     Query: {query['query']}")
                print()
                
        # Print recommendations
        if self.results["recommendations"]:
            print("\nRECOMMENDATIONS:")
            for i, rec in enumerate(self.results["recommendations"], 1):
                print(f"  {i}. {rec}")
                
        print("\n" + "=" * 80)

if __name__ == "__main__":
    analyzer = DatabasePerformanceAnalyzer()
    analyzer.run_analysis()
    analyzer.print_report()