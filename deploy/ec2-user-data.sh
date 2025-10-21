#!/bin/bash

# EC2 User Data Script for RedShift Chatbot Deployment
# This script runs on instance launch

# Update system
yum update -y

# Install Docker
yum install -y docker
systemctl start docker
systemctl enable docker
usermod -a -G docker ec2-user

# Install Docker Compose
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Install git
yum install -y git

# Create application directory
mkdir -p /opt/finchat
cd /opt/finchat

# Clone repository (replace with your repo URL)
git clone https://github.com/huawun/finchat_3.git .

# Create .env file from Systems Manager Parameter Store
# Note: Configure these parameters in AWS Systems Manager first
aws ssm get-parameter --name "/finchat/aws-region" --with-decryption --query 'Parameter.Value' --output text > /tmp/aws_region
aws ssm get-parameter --name "/finchat/aws-access-key-id" --with-decryption --query 'Parameter.Value' --output text > /tmp/aws_access_key
aws ssm get-parameter --name "/finchat/aws-secret-access-key" --with-decryption --query 'Parameter.Value' --output text > /tmp/aws_secret_key
aws ssm get-parameter --name "/finchat/redshift-host" --with-decryption --query 'Parameter.Value' --output text > /tmp/redshift_host
aws ssm get-parameter --name "/finchat/redshift-database" --with-decryption --query 'Parameter.Value' --output text > /tmp/redshift_db
aws ssm get-parameter --name "/finchat/redshift-user" --with-decryption --query 'Parameter.Value' --output text > /tmp/redshift_user
aws ssm get-parameter --name "/finchat/redshift-password" --with-decryption --query 'Parameter.Value' --output text > /tmp/redshift_pass

# Create .env file
cat > .env << EOF
AWS_REGION=$(cat /tmp/aws_region)
AWS_ACCESS_KEY_ID=$(cat /tmp/aws_access_key)
AWS_SECRET_ACCESS_KEY=$(cat /tmp/aws_secret_key)
BEDROCK_MODEL_ID=anthropic.claude-3-5-sonnet-20241022-v2:0
BEDROCK_MAX_TOKENS=4096
BEDROCK_TEMPERATURE=0.0
REDSHIFT_HOST=$(cat /tmp/redshift_host)
REDSHIFT_PORT=5439
REDSHIFT_DATABASE=$(cat /tmp/redshift_db)
REDSHIFT_USER=$(cat /tmp/redshift_user)
REDSHIFT_PASSWORD=$(cat /tmp/redshift_pass)
REDSHIFT_SSL=True
REDSHIFT_SCHEMA=public
FLASK_ENV=production
FLASK_DEBUG=False
PORT=5000
MAX_QUERY_TIMEOUT=30
MAX_RESULT_ROWS=1000
EOF

# Clean up temp files
rm /tmp/aws_* /tmp/redshift_*

# Set permissions
chown -R ec2-user:ec2-user /opt/finchat
chmod 600 .env

# Start application
docker-compose up -d

# Setup log rotation
cat > /etc/logrotate.d/finchat << EOF
/opt/finchat/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 644 ec2-user ec2-user
}
EOF