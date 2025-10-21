"""
Query generator module that orchestrates between Bedrock and RedShift.
"""

import logging
import time
from typing import Dict, Any

from config import Config
from .bedrock_client import BedrockClient
from .redshift_client import RedShiftClient
from .utils import (
    sanitize_sql,
    log_error,
    format_execution_time,
    format_error_message
)

logger = logging.getLogger(__name__)


class QueryGenerator:
    """Orchestrates SQL generation and execution."""
    
    def __init__(self):
        """Initialize query generator with clients."""
        try:
            self.bedrock_client = BedrockClient()
            self.redshift_client = RedShiftClient()
            self.schema_cache = None
            self.schema_cache_time = None
            logger.info("QueryGenerator initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize QueryGenerator: {e}")
            # Don't raise - allow partial initialization
            self.bedrock_client = None
            self.redshift_client = None
    
    def generate_and_execute(
        self,
        user_query: str,
        conversation_context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Main workflow: generate SQL and execute query.
        
        Args:
            user_query: User's natural language question
            conversation_context: Optional conversation context
            
        Returns:
            Dictionary containing:
                - response: Natural language response
                - sql_query: Generated SQL
                - results: Query results
                - execution_time: Time taken
                - error: Error message if any
        """
        start_time = time.time()
        
        try:
            # Get schema information
            schema_info = self._get_schema_info()
            
            if not schema_info or not schema_info.get('tables'):
                return {
                    'response': (
                        'Unable to retrieve database schema. '
                        'Please check your RedShift connection.'
                    ),
                    'sql_query': None,
                    'results': [],
                    'execution_time': time.time() - start_time,
                    'error': 'Schema retrieval failed'
                }
            
            # Generate SQL from natural language
            logger.info(f"Generating SQL for query: {user_query}")
            sql_query = self.bedrock_client.generate_sql(
                user_query,
                schema_info
            )
            
            # Sanitize SQL
            sql_query = sanitize_sql(sql_query)
            
            # Execute query
            logger.info(f"Executing SQL: {sql_query}")
            results = self.redshift_client.execute_query(sql_query)
            
            # Format response
            response = self.bedrock_client.format_response(
                sql_query,
                results,
                user_query
            )
            
            execution_time = time.time() - start_time
            
            logger.info(
                f"Query completed successfully in "
                f"{format_execution_time(execution_time)}"
            )
            
            return {
                'response': response,
                'sql_query': sql_query,
                'results': results,
                'execution_time': execution_time,
                'error': None
            }
            
        except ValueError as e:
            # SQL validation error
            error_msg = str(e)
            logger.warning(f"SQL validation error: {error_msg}")
            
            return {
                'response': (
                    f"I couldn't generate a safe query for that request. "
                    f"{error_msg}"
                ),
                'sql_query': None,
                'results': [],
                'execution_time': time.time() - start_time,
                'error': error_msg
            }
            
        except Exception as e:
            # General error
            log_error(e, {'user_query': user_query})
            error_msg = format_error_message(e, user_friendly=True)
            
            return {
                'response': error_msg,
                'sql_query': None,
                'results': [],
                'execution_time': time.time() - start_time,
                'error': str(e)
            }
    
    def _get_schema_info(self) -> Dict[str, Any]:
        """
        Get schema information with caching.
        
        Returns:
            Dictionary containing schema information
        """
        # Cache schema for 5 minutes to reduce database queries
        current_time = time.time()
        cache_duration = 300  # 5 minutes
        
        if (
            self.schema_cache is not None
            and self.schema_cache_time is not None
            and (current_time - self.schema_cache_time) < cache_duration
        ):
            logger.debug("Using cached schema information")
            return self.schema_cache
        
        # Fetch fresh schema (use configured schema if available)
        logger.info(
            f"Fetching database schema for schema: "
            f"{Config.REDSHIFT_SCHEMA}"
        )
        self.schema_cache = self.redshift_client.get_schema(
            target_schema=Config.REDSHIFT_SCHEMA
        )
        self.schema_cache_time = current_time
        
        return self.schema_cache
    
    def test_connections(self) -> Dict[str, bool]:
        """
        Test connections to Bedrock and RedShift.
        
        Returns:
            Dictionary with connection status for each service
        """
        return {
            'bedrock': self.bedrock_client.test_connection(),
            'redshift': self.redshift_client.test_connection()
        }
    
    def get_schema(self) -> Dict[str, Any]:
        """
        Get database schema information.
        
        Returns:
            Dictionary containing schema information
        """
        return self._get_schema_info()
    
    def close(self):
        """Clean up resources."""
        if self.redshift_client:
            self.redshift_client.close()
        logger.info("QueryGenerator resources cleaned up")