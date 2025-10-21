#!/bin/bash

# FinChat Deployment Script
# This script deploys the RedShift Chatbot to AWS EC2 with proper network configuration

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
STACK_NAME="finchat-chatbot"
TEMPLATE_FILE="improved-cloudformation.yaml"
ENVIRONMENT="nonprod"  # Change to "prod" for production

echo -e "${GREEN}🚀 FinChat Deployment Script${NC}"
echo "=================================="

# Check if AWS CLI is configured
if ! aws sts get-caller-identity &> /dev/null; then
    echo -e "${RED}❌ AWS CLI not configured or no valid credentials${NC}"
    echo "Please run 'aws configure' or set up your AWS credentials"
    exit 1
fi

echo -e "${GREEN}✅ AWS CLI configured${NC}"

# Get current AWS account and region
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION=$(aws configure get region)

echo "Account ID: $ACCOUNT_ID"
echo "Region: $REGION"
echo "Environment: $ENVIRONMENT"

# Function to get user input with default
get_input() {
    local prompt="$1"
    local default="$2"
    local result
    
    if [ -n "$default" ]; then
        read -p "$prompt [$default]: " result
        result=${result:-$default}
    else
        read -p "$prompt: " result
    fi
    
    echo "$result"
}

# Get deployment parameters
echo -e "\n${YELLOW}📋 Deployment Configuration${NC}"
echo "Please provide the following information:"

VPC_ID=$(get_input "VPC ID (where RedShift is located)")
SUBNET_ID=$(get_input "Private Subnet ID (same VPC as RedShift)")
KEY_PAIR=$(get_input "EC2 Key Pair name")
REDSHIFT_SG_ID=$(get_input "RedShift Security Group ID")
INSTANCE_TYPE=$(get_input "EC2 Instance Type" "t3.medium")

# Validate inputs
if [[ -z "$VPC_ID" || -z "$SUBNET_ID" || -z "$KEY_PAIR" || -z "$REDSHIFT_SG_ID" ]]; then
    echo -e "${RED}❌ Missing required parameters${NC}"
    exit 1
fi

echo -e "\n${YELLOW}🔧 Setting up SSM Parameters${NC}"
echo "Please ensure you have run './setup-ssm-parameters.sh' to store RedShift credentials"
read -p "Have you set up SSM parameters? (y/n): " SSM_SETUP

if [[ "$SSM_SETUP" != "y" && "$SSM_SETUP" != "Y" ]]; then
    echo -e "${YELLOW}⚠️  Running SSM parameter setup...${NC}"
    if [ -f "./setup-ssm-parameters.sh" ]; then
        chmod +x ./setup-ssm-parameters.sh
        ./setup-ssm-parameters.sh
    else
        echo -e "${RED}❌ setup-ssm-parameters.sh not found${NC}"
        echo "Please run it manually before continuing"
        exit 1
    fi
fi

# Check if stack exists
STACK_EXISTS=$(aws cloudformation describe-stacks --stack-name "$STACK_NAME" --query 'Stacks[0].StackStatus' --output text 2>/dev/null || echo "NOT_EXISTS")

if [ "$STACK_EXISTS" != "NOT_EXISTS" ]; then
    echo -e "\n${YELLOW}⚠️  Stack '$STACK_NAME' already exists${NC}"
    echo "Current status: $STACK_EXISTS"
    
    UPDATE_CHOICE=$(get_input "Do you want to update the existing stack? (y/n)" "n")
    
    if [[ "$UPDATE_CHOICE" == "y" || "$UPDATE_CHOICE" == "Y" ]]; then
        ACTION="update-stack"
        echo -e "${YELLOW}🔄 Updating existing stack...${NC}"
    else
        echo -e "${RED}❌ Deployment cancelled${NC}"
        exit 1
    fi
else
    ACTION="create-stack"
    echo -e "${GREEN}🆕 Creating new stack...${NC}"
fi

# Deploy CloudFormation stack
echo -e "\n${YELLOW}☁️  Deploying CloudFormation stack...${NC}"

aws cloudformation $ACTION \
    --stack-name "$STACK_NAME" \
    --template-body "file://$TEMPLATE_FILE" \
    --parameters \
        ParameterKey=VpcId,ParameterValue="$VPC_ID" \
        ParameterKey=SubnetId,ParameterValue="$SUBNET_ID" \
        ParameterKey=KeyPairName,ParameterValue="$KEY_PAIR" \
        ParameterKey=RedShiftSecurityGroupId,ParameterValue="$REDSHIFT_SG_ID" \
        ParameterKey=InstanceType,ParameterValue="$INSTANCE_TYPE" \
        ParameterKey=Environment,ParameterValue="$ENVIRONMENT" \
    --capabilities CAPABILITY_NAMED_IAM \
    --tags \
        Key=Project,Value=FinChat \
        Key=Environment,Value="$ENVIRONMENT" \
        Key=Owner,Value="$(aws sts get-caller-identity --query Arn --output text)"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ CloudFormation deployment initiated${NC}"
    
    echo -e "\n${YELLOW}⏳ Waiting for stack deployment to complete...${NC}"
    aws cloudformation wait stack-${ACTION%-stack}-complete --stack-name "$STACK_NAME"
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}🎉 Deployment completed successfully!${NC}"
        
        # Get outputs
        echo -e "\n${GREEN}📊 Deployment Information:${NC}"
        INSTANCE_ID=$(aws cloudformation describe-stacks --stack-name "$STACK_NAME" --query 'Stacks[0].Outputs[?OutputKey==`InstanceId`].OutputValue' --output text)
        PRIVATE_IP=$(aws cloudformation describe-stacks --stack-name "$STACK_NAME" --query 'Stacks[0].Outputs[?OutputKey==`PrivateIP`].OutputValue' --output text)
        APP_URL=$(aws cloudformation describe-stacks --stack-name "$STACK_NAME" --query 'Stacks[0].Outputs[?OutputKey==`ApplicationURL`].OutputValue' --output text)
        
        echo "Instance ID: $INSTANCE_ID"
        echo "Private IP: $PRIVATE_IP"
        echo "Application URL: $APP_URL"
        
        echo -e "\n${GREEN}🔗 Access Instructions:${NC}"
        echo "1. SSH to instance: ssh -i $KEY_PAIR.pem ec2-user@$PRIVATE_IP"
        echo "2. Check application status: docker ps"
        echo "3. View logs: cd /opt/finchat && docker-compose logs -f"
        echo "4. Access application: $APP_URL (from within VPC)"
        
        echo -e "\n${YELLOW}🔍 Troubleshooting:${NC}"
        echo "- Check application logs: ssh to instance and run 'cd /opt/finchat && docker-compose logs'"
        echo "- Restart application: 'sudo systemctl restart finchat'"
        echo "- Check system status: 'sudo systemctl status finchat'"
        
    else
        echo -e "${RED}❌ Stack deployment failed${NC}"
        echo "Check CloudFormation console for details"
        exit 1
    fi
else
    echo -e "${RED}❌ Failed to initiate CloudFormation deployment${NC}"
    exit 1
fi

echo -e "\n${GREEN}✨ Deployment script completed!${NC}"
