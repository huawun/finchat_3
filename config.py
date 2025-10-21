"""
Configuration module for RedShift Chatbot application.
Loads and validates environment variables.
"""

import os
import boto3
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Application configuration class."""
    
    # AWS Configuration
    AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')
    AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
    
    # Bedrock Configuration
    BEDROCK_MODEL_ID = os.getenv(
        'BEDROCK_MODEL_ID',
        'anthropic.claude-3-5-sonnet-20241022-v2:0'
    )
    BEDROCK_MAX_TOKENS = int(os.getenv('BEDROCK_MAX_TOKENS', '4096'))
    BEDROCK_TEMPERATURE = float(os.getenv('BEDROCK_TEMPERATURE', '0.0'))
    
    # RedShift Configuration
    REDSHIFT_HOST = os.getenv('REDSHIFT_HOST')
    REDSHIFT_PORT = int(os.getenv('REDSHIFT_PORT', '5439'))
    REDSHIFT_DATABASE = os.getenv('REDSHIFT_DATABASE')
    REDSHIFT_USER = os.getenv('REDSHIFT_USER')
    REDSHIFT_PASSWORD = os.getenv('REDSHIFT_PASSWORD')
    REDSHIFT_SSL = os.getenv('REDSHIFT_SSL', 'True').lower() == 'true'
    REDSHIFT_SCHEMA = os.getenv('REDSHIFT_SCHEMA', 'public')
    
    # Application Configuration
    FLASK_ENV = os.getenv('FLASK_ENV', 'development')
    FLASK_DEBUG = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'
    PORT = int(os.getenv('PORT', '5000'))
    MAX_QUERY_TIMEOUT = int(os.getenv('MAX_QUERY_TIMEOUT', '30'))
    MAX_RESULT_ROWS = int(os.getenv('MAX_RESULT_ROWS', '1000'))
    
    @staticmethod
    def validate_config():
        """
        Validate that all required configuration variables are set.
        
        Raises:
            ValueError: If any required configuration is missing.
        """
        # Try to load from SSM if running on EC2 and credentials not set
        if not Config.AWS_ACCESS_KEY_ID and Config._is_ec2_instance():
            Config._load_from_ssm()
        
        required_aws = [
            ('AWS_ACCESS_KEY_ID', Config.AWS_ACCESS_KEY_ID),
            ('AWS_SECRET_ACCESS_KEY', Config.AWS_SECRET_ACCESS_KEY),
        ]
        
        required_redshift = [
            ('REDSHIFT_HOST', Config.REDSHIFT_HOST),
            ('REDSHIFT_DATABASE', Config.REDSHIFT_DATABASE),
            ('REDSHIFT_USER', Config.REDSHIFT_USER),
            ('REDSHIFT_PASSWORD', Config.REDSHIFT_PASSWORD),
        ]
        
        missing = []
        
        # Skip AWS credential validation if using IAM roles on EC2
        if not Config._is_ec2_instance():
            for name, value in required_aws:
                if not value:
                    missing.append(name)
        
        for name, value in required_redshift:
            if not value:
                missing.append(name)
        
        if missing:
            raise ValueError(
                f"Missing required configuration: {', '.join(missing)}. "
                "Please check your .env file or SSM parameters."
            )
    
    @staticmethod
    def _is_ec2_instance():
        """Check if running on EC2 instance."""
        try:
            import requests
            response = requests.get(
                'http://169.254.169.254/latest/meta-data/instance-id',
                timeout=2
            )
            return response.status_code == 200
        except:
            return False
    
    @staticmethod
    def _load_from_ssm():
        """Load configuration from AWS Systems Manager Parameter Store."""
        try:
            ssm = boto3.client('ssm', region_name=Config.AWS_REGION)
            
            parameters = [
                '/finchat/aws-access-key-id',
                '/finchat/aws-secret-access-key',
                '/finchat/redshift-host',
                '/finchat/redshift-database',
                '/finchat/redshift-user',
                '/finchat/redshift-password'
            ]
            
            response = ssm.get_parameters(
                Names=parameters,
                WithDecryption=True
            )
            
            param_map = {
                '/finchat/aws-access-key-id': 'AWS_ACCESS_KEY_ID',
                '/finchat/aws-secret-access-key': 'AWS_SECRET_ACCESS_KEY',
                '/finchat/redshift-host': 'REDSHIFT_HOST',
                '/finchat/redshift-database': 'REDSHIFT_DATABASE',
                '/finchat/redshift-user': 'REDSHIFT_USER',
                '/finchat/redshift-password': 'REDSHIFT_PASSWORD'
            }
            
            for param in response['Parameters']:
                env_var = param_map.get(param['Name'])
                if env_var:
                    setattr(Config, env_var, param['Value'])
                    
        except Exception as e:
            print(f"Warning: Could not load from SSM: {e}")
    
    @staticmethod
    def get_redshift_connection_string():
        """
        Get RedShift connection string.
        
        Returns:
            str: Database connection string.
        """
        return (
            f"host={Config.REDSHIFT_HOST} "
            f"port={Config.REDSHIFT_PORT} "
            f"dbname={Config.REDSHIFT_DATABASE} "
            f"user={Config.REDSHIFT_USER} "
            f"password={Config.REDSHIFT_PASSWORD} "
            f"sslmode={'require' if Config.REDSHIFT_SSL else 'prefer'}"
        )
    
    @staticmethod
    def get_aws_credentials():
        """
        Get AWS credentials dictionary.
        
        Returns:
            dict: AWS credentials.
        """
        credentials = {'region_name': Config.AWS_REGION}
        
        # Only add explicit credentials if not using IAM roles
        if Config.AWS_ACCESS_KEY_ID and Config.AWS_SECRET_ACCESS_KEY:
            credentials.update({
                'aws_access_key_id': Config.AWS_ACCESS_KEY_ID,
                'aws_secret_access_key': Config.AWS_SECRET_ACCESS_KEY,
            })
        
        return credentials