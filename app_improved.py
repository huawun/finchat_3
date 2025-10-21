"""
Main Flask application for RedShift Chatbot with enhanced configuration.
"""

import logging
from datetime import datetime
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS

# Import improved config if available, fallback to original
try:
    from config_iam import Config
    print("Using enhanced IAM-based configuration")
except ImportError:
    from config import Config
    print("Using standard configuration")

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
    
    # Log deployment info if available
    if hasattr(Config, 'get_deployment_info'):
        deployment_info = Config.get_deployment_info()
        logger.info(f"Deployment info: {deployment_info}")
        
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
    
    Expected JSON payload:
    {
        "message": "user message",
        "conversation_id": "optional conversation ID"
    }
    
    Returns:
    {
        "response": "AI response",
        "conversation_id": "conversation ID",
        "query": "generated SQL query (if applicable)",
        "results": "query results (if applicable)"
    }
    """
    try:
        if not query_generator:
            return jsonify({
                'error': 'Query generator not available',
                'conversation_id': request.json.get('conversation_id', generate_conversation_id())
            }), 503
        
        data = request.get_json()
        if not data or 'message' not in data:
            return jsonify({'error': 'Message is required'}), 400
        
        user_message = data['message']
        conversation_id = data.get('conversation_id', generate_conversation_id())
        
        logger.info(f"Processing message for conversation {conversation_id}: {user_message[:100]}...")
        
        # Process the message
        response = query_generator.process_message(user_message, conversation_id)
        
        logger.info(f"Response generated for conversation {conversation_id}")
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error processing chat message: {e}")
        return jsonify({
            'error': 'Internal server error',
            'conversation_id': request.json.get('conversation_id', generate_conversation_id()) if request.json else generate_conversation_id()
        }), 500


@app.route('/api/health', methods=['GET'])
def health():
    """
    Check application health and service connections.
    
    Returns:
    {
        "status": "healthy|degraded|unhealthy",
        "bedrock": "connected|disconnected",
        "redshift": "connected|disconnected",
        "timestamp": "ISO timestamp",
        "deployment": {...}  # deployment info if available
    }
    """
    try:
        if not query_generator:
            response = {
                'status': 'unhealthy',
                'bedrock': 'unavailable',
                'redshift': 'unavailable',
                'error': 'Query generator not initialized',
                'timestamp': datetime.utcnow().isoformat()
            }
            
            # Add deployment info if available
            if hasattr(Config, 'get_deployment_info'):
                response['deployment'] = Config.get_deployment_info()
            
            return jsonify(response), 503
        
        # Test connections
        connection_status = query_generator.test_connections()
        
        overall_status = (
            'healthy'
            if all(connection_status.values())
            else 'degraded'
        )
        
        response = {
            'status': overall_status,
            'bedrock': 'connected' if connection_status.get('bedrock', False) else 'disconnected',
            'redshift': 'connected' if connection_status.get('redshift', False) else 'disconnected',
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Add deployment info if available
        if hasattr(Config, 'get_deployment_info'):
            response['deployment'] = Config.get_deployment_info()
        
        status_code = 200 if overall_status == 'healthy' else 503
        return jsonify(response), status_code
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        response = {
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Add deployment info if available
        if hasattr(Config, 'get_deployment_info'):
            try:
                response['deployment'] = Config.get_deployment_info()
            except:
                pass
        
        return jsonify(response), 503


@app.route('/api/info', methods=['GET'])
def deployment_info():
    """
    Get detailed deployment and configuration information.
    Useful for debugging and monitoring.
    """
    try:
        info = {
            'application': 'RedShift Chatbot',
            'version': '1.0.0',
            'timestamp': datetime.utcnow().isoformat(),
            'flask_env': Config.FLASK_ENV,
            'environment': getattr(Config, 'ENVIRONMENT', 'unknown')
        }
        
        # Add deployment info if available
        if hasattr(Config, 'get_deployment_info'):
            info.update(Config.get_deployment_info())
        
        # Add service status
        if query_generator:
            try:
                connections = query_generator.test_connections()
                info['services'] = {
                    'bedrock': 'available' if connections.get('bedrock', False) else 'unavailable',
                    'redshift': 'available' if connections.get('redshift', False) else 'unavailable'
                }
            except:
                info['services'] = {'status': 'unknown'}
        else:
            info['services'] = {'status': 'unavailable'}
        
        return jsonify(info)
        
    except Exception as e:
        logger.error(f"Info endpoint failed: {e}")
        return jsonify({
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
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


if __name__ == '__main__':
    # Development server
    app.run(
        host='0.0.0.0',
        port=Config.PORT,
        debug=Config.FLASK_DEBUG
    )
