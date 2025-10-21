"""
Main Flask application for RedShift Chatbot.
"""

import logging
from datetime import datetime
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS

from config import Config
from modules import QueryGenerator, generate_conversation_id

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Validate configuration
try:
    Config.validate_config()
    logger.info("Configuration validated successfully")
except ValueError as e:
    logger.error(f"Configuration error: {e}")
    raise

# Initialize query generator
try:
    query_generator = QueryGenerator()
    logger.info("Query generator initialized")
except Exception as e:
    logger.error(f"Failed to initialize query generator: {e}")
    query_generator = None


@app.route('/')
def index():
    """Serve the main chat interface."""
    return render_template('index.html')


@app.route('/api/chat', methods=['POST'])
def chat():
    """
    Process user chat messages and return responses.
    
    Expected JSON body:
    {
        "message": "user question",
        "conversation_id": "optional-uuid"
    }
    
    Returns:
    {
        "response": "natural language response",
        "sql_query": "generated sql",
        "results": [...],
        "conversation_id": "uuid",
        "execution_time": 1.23,
        "error": null or "error message"
    }
    """
    try:
        # Parse request
        data = request.get_json()
        
        if not data or 'message' not in data:
            return jsonify({
                'error': 'Missing required field: message'
            }), 400
        
        user_message = data['message'].strip()
        
        if not user_message:
            return jsonify({
                'error': 'Message cannot be empty'
            }), 400
        
        # Get or create conversation ID
        conversation_id = data.get('conversation_id')
        if not conversation_id:
            conversation_id = generate_conversation_id()
        
        logger.info(
            f"Processing query - "
            f"conversation_id: {conversation_id}, "
            f"message: {user_message}"
        )
        
        # Check if query generator is available
        if not query_generator:
            return jsonify({
                'error': 'Service unavailable - database connection failed'
            }), 503
        
        # Generate and execute query
        result = query_generator.generate_and_execute(
            user_message,
            conversation_context={'conversation_id': conversation_id}
        )
        
        # Prepare response
        response_data = {
            'response': result['response'],
            'sql_query': result['sql_query'],
            'results': result['results'],
            'conversation_id': conversation_id,
            'execution_time': round(result['execution_time'], 2),
            'error': result['error'],
            'timestamp': datetime.utcnow().isoformat()
        }
        
        logger.info(
            f"Query completed - "
            f"conversation_id: {conversation_id}, "
            f"execution_time: {result['execution_time']:.2f}s"
        )
        
        return jsonify(response_data), 200
        
    except Exception as e:
        logger.error(f"Error processing chat request: {e}")
        return jsonify({
            'error': 'Internal server error',
            'message': str(e)
        }), 500


@app.route('/api/health', methods=['GET'])
def health():
    """
    Check application health and service connections.
    
    Returns:
    {
        "status": "healthy",
        "bedrock": "connected",
        "redshift": "connected",
        "timestamp": "2024-01-20T10:30:00Z"
    }
    """
    try:
        # Check if query generator is available
        if not query_generator:
            return jsonify({
                'status': 'unhealthy',
                'bedrock': 'unavailable',
                'redshift': 'unavailable',
                'error': 'Query generator not initialized',
                'timestamp': datetime.utcnow().isoformat()
            }), 503
        
        # Test connections
        connection_status = query_generator.test_connections()
        
        overall_status = (
            'healthy'
            if all(connection_status.values())
            else 'degraded'
        )
        
        return jsonify({
            'status': overall_status,
            'bedrock': (
                'connected' if connection_status['bedrock'] else 'error'
            ),
            'redshift': (
                'connected' if connection_status['redshift'] else 'error'
            ),
            'timestamp': datetime.utcnow().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 503


@app.route('/api/schema', methods=['GET'])
def schema():
    """
    Retrieve database schema information.
    
    Returns:
    {
        "tables": [
            {
                "name": "table_name",
                "columns": [
                    {"name": "col_name", "type": "col_type", ...}
                ]
            }
        ]
    }
    """
    try:
        if not query_generator:
            return jsonify({
                'error': 'Service unavailable - database connection failed'
            }), 503
        
        schema_info = query_generator.get_schema()
        return jsonify(schema_info), 200
        
    except Exception as e:
        logger.error(f"Schema retrieval failed: {e}")
        return jsonify({
            'error': 'Failed to retrieve schema',
            'message': str(e)
        }), 500


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({'error': 'Not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    logger.error(f"Internal server error: {error}")
    return jsonify({'error': 'Internal server error'}), 500


# Cleanup on shutdown
@app.teardown_appcontext
def cleanup(exception=None):
    """Clean up resources on app context teardown."""
    if exception:
        logger.error(f"App context teardown with exception: {exception}")


if __name__ == '__main__':
    try:
        logger.info(f"Starting Flask app on port {Config.PORT}")
        app.run(
            host='0.0.0.0',
            port=Config.PORT,
            debug=Config.FLASK_DEBUG
        )
    except KeyboardInterrupt:
        logger.info("Shutting down application")
        query_generator.close()
    except Exception as e:
        logger.error(f"Application error: {e}")
        raise