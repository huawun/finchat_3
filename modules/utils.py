"""
Utility functions for RedShift Chatbot application.
"""

import logging
import uuid
import re
from typing import List, Dict, Any, Tuple
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def format_query_results(
    results: List[Tuple],
    description: List[Tuple]
) -> List[Dict[str, Any]]:
    """
    Convert database results to structured format.
    
    Args:
        results: List of tuples from database query
        description: Cursor description with column information
        
    Returns:
        List of dictionaries with column names as keys
    """
    if not results:
        return []
    
    columns = [desc[0] for desc in description]
    return [dict(zip(columns, row)) for row in results]


def generate_conversation_id() -> str:
    """
    Generate a unique conversation ID.
    
    Returns:
        str: UUID string for conversation tracking
    """
    return str(uuid.uuid4())


def sanitize_sql(sql: str) -> str:
    """
    Basic SQL sanitization - removes comments and extra whitespace.
    
    Args:
        sql: SQL query string
        
    Returns:
        str: Sanitized SQL query
    """
    # Remove SQL comments (-- style)
    sql = re.sub(r'--.*$', '', sql, flags=re.MULTILINE)
    
    # Remove SQL comments (/* */ style)
    sql = re.sub(r'/\*.*?\*/', '', sql, flags=re.DOTALL)
    
    # Remove extra whitespace
    sql = ' '.join(sql.split())
    
    return sql.strip()


def validate_sql_safety(sql: str) -> Tuple[bool, str]:
    """
    Validate that SQL query is safe (read-only).
    
    Args:
        sql: SQL query string
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    sql_upper = sql.upper()
    
    # Dangerous keywords that should be blocked
    dangerous_keywords = [
        'DROP', 'DELETE', 'INSERT', 'UPDATE',
        'ALTER', 'CREATE', 'TRUNCATE', 'GRANT',
        'REVOKE', 'EXEC', 'EXECUTE'
    ]
    
    for keyword in dangerous_keywords:
        # Check for keyword as a whole word
        if re.search(r'\b' + keyword + r'\b', sql_upper):
            return False, f"Dangerous SQL keyword detected: {keyword}"
    
    # Must start with SELECT
    if not sql_upper.strip().startswith('SELECT'):
        return False, "Query must start with SELECT"
    
    # Check for multiple statements (semicolons)
    # Allow single trailing semicolon but not multiple statements
    semicolon_count = sql.count(';')
    if semicolon_count > 1:
        return False, "Multiple SQL statements not allowed"
    elif semicolon_count == 1 and not sql.rstrip().endswith(';'):
        return False, "Multiple SQL statements not allowed"
    
    return True, ""


def log_error(error: Exception, context: Dict[str, Any] = None) -> None:
    """
    Log error with context information.
    
    Args:
        error: Exception object
        context: Additional context information
    """
    error_info = {
        'error_type': type(error).__name__,
        'error_message': str(error),
        'timestamp': datetime.utcnow().isoformat(),
    }
    
    if context:
        error_info['context'] = context
    
    logger.error(f"Error occurred: {error_info}")


def format_execution_time(seconds: float) -> str:
    """
    Format execution time in human-readable format.
    
    Args:
        seconds: Execution time in seconds
        
    Returns:
        str: Formatted time string
    """
    if seconds < 1:
        return f"{seconds * 1000:.0f}ms"
    elif seconds < 60:
        return f"{seconds:.2f}s"
    else:
        minutes = int(seconds // 60)
        secs = seconds % 60
        return f"{minutes}m {secs:.2f}s"


def truncate_results(
    results: List[Dict[str, Any]],
    max_rows: int
) -> Tuple[List[Dict[str, Any]], bool]:
    """
    Truncate results to maximum number of rows.
    
    Args:
        results: List of result dictionaries
        max_rows: Maximum number of rows to return
        
    Returns:
        Tuple of (truncated_results, was_truncated)
    """
    was_truncated = len(results) > max_rows
    return results[:max_rows], was_truncated


def format_error_message(error: Exception, user_friendly: bool = True) -> str:
    """
    Format error message for display.
    
    Args:
        error: Exception object
        user_friendly: Whether to return user-friendly message
        
    Returns:
        str: Formatted error message
    """
    if user_friendly:
        error_type = type(error).__name__
        
        # Map technical errors to user-friendly messages
        friendly_messages = {
            'OperationalError': (
                'Database connection error. '
                'Please check your connection settings.'
            ),
            'ProgrammingError': (
                'Invalid SQL query generated. '
                'Please try rephrasing your question.'
            ),
            'TimeoutError': (
                'Query took too long to execute. '
                'Please try a more specific question.'
            ),
        }
        
        return friendly_messages.get(
            error_type,
            'An error occurred while processing your request. '
            'Please try again.'
        )
    else:
        return str(error)