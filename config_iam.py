"""
Enhanced configuration module for RedShift Chatbot application.
Prioritizes IAM roles over access keys for better security.
"""

import os
import boto3
import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Application configuration class with IAM role support."""
    
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
    ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')
    
    # Runtime flags
    _is_ec2 = None
    _ssm_loaded = False
    
    @staticmethod
    def validate_config():
        """
        Validate that all required configuration variables are set.
        Automatically loads from SSM if running on EC2.
        """
        # Load from SSM if on EC2 and not already loaded
        if Config.is_ec2_instance() and not Config._ssm_loaded:
            Config._load_from_ssm()
        
        # Check required RedShift configuration
        required_redshift = [
            ('REDSHIFT_HOST', Config.REDSHIFT_HOST),
            ('REDSHIFT_DATABASE', Config.REDSHIFT_DATABASE),
            ('REDSHIFT_USER', Config.REDSHIFT_USER),
            ('REDSHIFT_PASSWORD', Config.REDSHIFT_PASSWORD),
        ]
        
        missing = []
        for name, value in required_redshift:
            if not value:
                missing.append(name)
        
        if missing:
            raise ValueError(
                f"Missing required configuration: {', '.join(missing)}. "
                "Please check your .env file or SSM parameters."
            )
        
        # Validate AWS access
        try:
            Config._test_aws_access()
        except Exception as e:
            raise ValueError(f"AWS access validation failed: {e}")
    
    @staticmethod
    def is_ec2_instance():
        """Check if running on EC2 instance with caching."""
        if Config._is_ec2 is None:
            try:
                response = requests.get(
                    'http://169.254.169.254/latest/meta-data/instance-id',
                    timeout=2
                )
                Config._is_ec2 = response.status_code == 200
            except:
                Config._is_ec2 = False
        return Config._is_ec2
    
    @staticmethod
    def _test_aws_access():
        """Test AWS access with current configuration."""
        try:
            credentials = Config.get_aws_credentials()
            sts = boto3.client('sts', **credentials)
            sts.get_caller_identity()
            return True
        except Exception as e:
            raise Exception(f"Cannot access AWS: {e}")
    
    @staticmethod
    def _load_from_ssm():
        """Load configuration from AWS Systems Manager Parameter Store."""
        if Config._ssm_loaded:
            return
            
        try:
            # Use IAM role credentials if on EC2
            if Config.is_ec2_instance():
                ssm = boto3.client('ssm', region_name=Config.AWS_REGION)
            else:
                credentials = Config.get_aws_credentials()
                ssm = boto3.client('ssm', **credentials)
            
            # Parameter mapping
            param_map = {
                '/finchat/redshift-host': 'REDSHIFT_HOST',
                '/finchat/redshift-database': 'REDSHIFT_DATABASE',
                '/finchat/redshift-user': 'REDSHIFT_USER',
                '/finchat/redshift-password': 'REDSHIFT_PASSWORD'
            }
            
            # Get all parameters at once
            try:
                response = ssm.get_parameters(
                    Names=list(param_map.keys()),
                    WithDecryption=True
                )
                
                for param in response['Parameters']:
                    env_var = param_map.get(param['Name'])
                    if env_var:
                        setattr(Config, env_var, param['Value'])
                        print(f"Loaded {env_var} from SSM")
                
                # Check for missing parameters
                missing_params = []
                for param_name in param_map.keys():
                    if not any(p['Name'] == param_name for p in response['Parameters']):
                        missing_params.append(param_name)
                
                if missing_params:
                    print(f"Warning: Missing SSM parameters: {missing_params}")
                
            except ssm.exceptions.ParameterNotFound as e:
                print(f"Warning: Some SSM parameters not found: {e}")
            except Exception as e:
                print(f"Warning: Could not load from SSM: {e}")
            
            Config._ssm_loaded = True
                    
        except Exception as e:
            print(f"Warning: Could not load from SSM: {e}")
    
    @staticmethod
    def get_redshift_connection_string():
        """Get RedShift connection string."""
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
        Prioritizes IAM roles over access keys.
        """
        credentials = {'region_name': Config.AWS_REGION}
        
        # If running on EC2, prefer IAM role (don't add explicit credentials)
        if Config.is_ec2_instance():
            print("Using IAM role credentials (EC2)")
            return credentials
        
        # Otherwise, use explicit credentials if available
        if Config.AWS_ACCESS_KEY_ID and Config.AWS_SECRET_ACCESS_KEY:
            credentials.update({
                'aws_access_key_id': Config.AWS_ACCESS_KEY_ID,
                'aws_secret_access_key': Config.AWS_SECRET_ACCESS_KEY,
            })
            print("Using explicit AWS credentials")
        else:
            print("Using default credential chain")
        
        return credentials
    
    @staticmethod
    def get_deployment_info():
        """Get deployment information for debugging."""
        info = {
            'environment': Config.ENVIRONMENT,
            'is_ec2': Config.is_ec2_instance(),
            'aws_region': Config.AWS_REGION,
            'redshift_host': Config.REDSHIFT_HOST[:20] + '...' if Config.REDSHIFT_HOST else None,
            'redshift_database': Config.REDSHIFT_DATABASE,
            'bedrock_model': Config.BEDROCK_MODEL_ID,
            'ssm_loaded': Config._ssm_loaded
        }
        
        if Config.is_ec2_instance():
            try:
                # Get instance metadata
                instance_id = requests.get(
                    'http://169.254.169.254/latest/meta-data/instance-id',
                    timeout=2
                ).text
                availability_zone = requests.get(
                    'http://169.254.169.254/latest/meta-data/placement/availability-zone',
                    timeout=2
                ).text
                info.update({
                    'instance_id': instance_id,
                    'availability_zone': availability_zone
                })
            except:
                pass
        
        return info
