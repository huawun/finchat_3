#!/bin/bash

# Script to setup AWS Systems Manager parameters for secure credential storage
# Run this script to store credentials securely before deploying EC2 instance

echo "Setting up AWS Systems Manager parameters for FinChat..."

# Check if AWS CLI is configured
if ! aws sts get-caller-identity > /dev/null 2>&1; then
    echo "Error: AWS CLI not configured. Please run 'aws configure' first."
    exit 1
fi

# Function to create secure parameter
create_parameter() {
    local name=$1
    local description=$2
    
    echo -n "Enter $description: "
    read -s value
    echo
    
    aws ssm put-parameter \
        --name "/finchat/$name" \
        --description "$description" \
        --value "$value" \
        --type "SecureString" \
        --overwrite
    
    if [ $? -eq 0 ]; then
        echo "✓ Parameter /finchat/$name created successfully"
    else
        echo "✗ Failed to create parameter /finchat/$name"
    fi
}

# Create parameters
echo "Creating secure parameters in AWS Systems Manager..."
echo "Note: Values will be hidden as you type"
echo

create_parameter "aws-region" "AWS Region (e.g., us-east-1)"
create_parameter "aws-access-key-id" "AWS Access Key ID"
create_parameter "aws-secret-access-key" "AWS Secret Access Key"
create_parameter "redshift-host" "RedShift Cluster Endpoint"
create_parameter "redshift-database" "RedShift Database Name"
create_parameter "redshift-user" "RedShift Username"
create_parameter "redshift-password" "RedShift Password"

echo
echo "All parameters created successfully!"
echo "You can now deploy the EC2 instance using the CloudFormation template."
echo
echo "To view parameters:"
echo "aws ssm get-parameters --names \"/finchat/aws-region\" \"/finchat/redshift-host\" --with-decryption"