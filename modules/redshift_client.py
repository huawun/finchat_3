"""
AWS RedShift client for database operations.
"""

import logging
from typing import List, Dict, Any, Tuple
import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor

from config import Config
from .utils import validate_sql_safety

logger = logging.getLogger(__name__)


class RedShiftClient:
    """Client for AWS RedShift database operations."""
    
    def __init__(self):
        """Initialize RedShift client with connection pool."""
        self.connection_pool = None
        self._initialize_connection_pool()
    
    def _initialize_connection_pool(self):
        """
        Initialize database connection pool.
        
        Raises:
            Exception: If connection pool creation fails
        """
        try:
            self.connection_pool = pool.SimpleConnectionPool(
                minconn=1,
                maxconn=10,
                **self._get_connection_params()
            )
            logger.info("RedShift connection pool initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize connection pool: {e}")
            self.connection_pool = None
            # Don't raise - allow app to start with degraded functionality
    
    def _get_connection_params(self) -> Dict[str, Any]:
        """
        Get connection parameters as dictionary.
        
        Returns:
            dict: Connection parameters
        """
        return {
            'host': Config.REDSHIFT_HOST,
            'port': Config.REDSHIFT_PORT,
            'database': Config.REDSHIFT_DATABASE,
            'user': Config.REDSHIFT_USER,
            'password': Config.REDSHIFT_PASSWORD,
            'sslmode': 'require' if Config.REDSHIFT_SSL else 'prefer',
            'connect_timeout': 10,
        }
    
    def get_connection(self):
        """
        Get a connection from the pool.
        
        Returns:
            Connection object
            
        Raises:
            Exception: If connection retrieval fails
        """
        if not self.connection_pool:
            raise Exception("Connection pool not initialized")
        try:
            return self.connection_pool.getconn()
        except Exception as e:
            logger.error(f"Failed to get connection from pool: {e}")
            raise
    
    def return_connection(self, conn):
        """
        Return connection to the pool.
        
        Args:
            conn: Connection object to return
        """
        if conn:
            self.connection_pool.putconn(conn)
    
    def execute_query(
        self,
        sql: str,
        params: Tuple = None,
        timeout_seconds: int = None
    ) -> List[Dict[str, Any]]:
        """
        Execute SQL query and return results.
        
        Args:
            sql: SQL query string
            params: Optional query parameters
            timeout_seconds: Optional timeout override
            
        Returns:
            List of dictionaries containing query results
            
        Raises:
            ValueError: If SQL query is not safe
            Exception: If query execution fails
        """
        # Validate SQL safety for user queries (skip for schema queries)
        # Skip validation for schema information queries
        schema_prefixes = ('SELECT TABLE_SCHEMA', 'SELECT COLUMN_NAME')
        if not sql.strip().upper().startswith(schema_prefixes):
            is_safe, error_msg = validate_sql_safety(sql)
            if not is_safe:
                raise ValueError(f"Unsafe SQL query: {error_msg}")
        
        conn = None
        cursor = None
        
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # Set query timeout (use override or default)
            timeout_ms = (timeout_seconds or Config.MAX_QUERY_TIMEOUT) * 1000
            cursor.execute(f"SET statement_timeout = {timeout_ms}")
            
            # Execute query
            if params:
                cursor.execute(sql, params)
            else:
                cursor.execute(sql)
            
            # Fetch results
            results = cursor.fetchall()
            
            # Convert RealDictRow to regular dict
            results_list = [dict(row) for row in results]
            
            # Limit results
            if len(results_list) > Config.MAX_RESULT_ROWS:
                logger.warning(
                    f"Query returned {len(results_list)} rows, "
                    f"limiting to {Config.MAX_RESULT_ROWS}"
                )
                results_list = results_list[:Config.MAX_RESULT_ROWS]
            
            logger.info(
                f"Query executed successfully, {len(results_list)} rows"
            )
            return results_list
            
        except psycopg2.Error as e:
            logger.error(f"Database error: {e}")
            raise
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            raise
        finally:
            if cursor:
                cursor.close()
            if conn:
                self.return_connection(conn)
    
    def get_schema(self, target_schema: str = None) -> Dict[str, Any]:
        """
        Retrieve database schema information.
        
        Args:
            target_schema: Optional specific schema to retrieve
                          (e.g., 'public')
        
        Returns:
            Dictionary containing schema information
        """
        schema_info = {'tables': []}
        
        try:
            # Optimize query by targeting specific schema or using LIMIT
            # Use longer timeout for schema queries (2 minutes)
            if target_schema:
                tables_sql = """
                    SELECT table_schema, table_name
                    FROM information_schema.tables
                    WHERE table_type = 'BASE TABLE'
                        AND table_schema = %s
                    ORDER BY table_name
                    LIMIT 100
                """
                tables = self.execute_query(
                    tables_sql,
                    (target_schema,),
                    timeout_seconds=120
                )
            else:
                # Get tables from public schema by default, limit to 50 tables
                tables_sql = """
                    SELECT table_schema, table_name
                    FROM information_schema.tables
                    WHERE table_type = 'BASE TABLE'
                        AND table_schema NOT IN (
                            'information_schema',
                            'pg_catalog',
                            'pg_internal'
                        )
                        AND table_schema LIKE 'public%'
                    ORDER BY table_schema, table_name
                    LIMIT 50
                """
                tables = self.execute_query(tables_sql, timeout_seconds=120)
            
            # For each table, get column information
            for table in tables:
                table_schema = table['table_schema']
                table_name = table['table_name']
                full_table_name = f"{table_schema}.{table_name}"
                
                columns_sql = """
                    SELECT
                        column_name,
                        data_type,
                        is_nullable
                    FROM information_schema.columns
                    WHERE table_schema = %s
                        AND table_name = %s
                    ORDER BY ordinal_position
                """
                
                columns = self.execute_query(
                    columns_sql, 
                    (table_schema, table_name),
                    timeout_seconds=120
                )
                
                schema_info['tables'].append({
                    'name': full_table_name,
                    'columns': [
                        {
                            'name': col['column_name'],
                            'type': col['data_type'],
                            'nullable': col['is_nullable'] == 'YES'
                        }
                        for col in columns
                    ]
                })
            
            logger.info(
                f"Retrieved schema for {len(schema_info['tables'])} tables"
            )
            return schema_info
            
        except Exception as e:
            logger.error(f"Failed to retrieve schema: {e}")
            return {'tables': []}
    
    def test_connection(self) -> bool:
        """
        Test database connection.
        
        Returns:
            bool: True if connection successful
        """
        if not self.connection_pool:
            return False
        try:
            result = self.execute_query("SELECT 1 as test")
            return len(result) > 0 and result[0]['test'] == 1
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False
    
    def close(self):
        """Close all connections in the pool."""
        if self.connection_pool:
            self.connection_pool.closeall()
            logger.info("RedShift connection pool closed")