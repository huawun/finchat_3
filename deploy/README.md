# AWS EC2 Deployment Guide

This guide helps deploy the RedShift Chatbot to AWS EC2 with private network connectivity.

## Prerequisites

1. **AWS CLI configured** with appropriate permissions
2. **RedShift cluster** in private subnet
3. **VPC with private subnets** where RedShift is located
4. **EC2 Key Pair** for SSH access

## Deployment Steps

### 1. Store Credentials Securely

```bash
cd deploy
chmod +x setup-ssm-parameters.sh
./setup-ssm-parameters.sh
```

This stores all credentials in AWS Systems Manager Parameter Store (encrypted).

### 2. Deploy EC2 Instance

```bash
aws cloudformation create-stack \
  --stack-name finchat-chatbot \
  --template-body file://cloudformation-template.yaml \
  --parameters \
    ParameterKey=VpcId,ParameterValue=vpc-xxxxxxxxx \
    ParameterKey=SubnetId,ParameterValue=subnet-xxxxxxxxx \
    ParameterKey=KeyPairName,ParameterValue=your-key-pair \
  --capabilities CAPABILITY_IAM
```

### 3. Access Application

The application will be available at:
- **Private IP**: `http://<private-ip>:5000`
- Access via VPN, bastion host, or AWS Systems Manager Session Manager

## Network Configuration

### Security Groups Required

1. **EC2 Security Group** (created by template):
   - Inbound: Port 5000 from private network
   - Outbound: All traffic (for Docker pulls, AWS API calls)

2. **RedShift Security Group** (update existing):
   - Inbound: Port 5439 from EC2 security group

### Update RedShift Security Group

```bash
# Get EC2 security group ID from CloudFormation output
EC2_SG_ID=$(aws cloudformation describe-stacks \
  --stack-name finchat-chatbot \
  --query 'Stacks[0].Outputs[?OutputKey==`SecurityGroupId`].OutputValue' \
  --output text)

# Add rule to RedShift security group
aws ec2 authorize-security-group-ingress \
  --group-id <redshift-security-group-id> \
  --protocol tcp \
  --port 5439 \
  --source-group $EC2_SG_ID
```

## Troubleshooting

### Check Application Status

```bash
# SSH to EC2 instance
ssh -i your-key.pem ec2-user@<private-ip>

# Check Docker containers
docker ps

# Check application logs
cd /opt/finchat
docker-compose logs -f
```

### Common Issues

1. **RedShift Connection Failed**:
   - Verify security group rules
   - Check VPC routing
   - Confirm RedShift endpoint accessibility

2. **Bedrock Access Denied**:
   - Verify IAM role permissions
   - Check AWS region configuration
   - Ensure Bedrock model access

3. **Docker Issues**:
   - Check Docker service: `sudo systemctl status docker`
   - Rebuild container: `docker-compose up --build -d`

## Alternative: Use IAM Roles Instead of Access Keys

For better security, modify the application to use IAM roles:

1. Remove AWS credentials from SSM parameters
2. Update EC2 role with RedShift and Bedrock permissions
3. Modify `config.py` to use boto3 default credential chain

## Monitoring

- **CloudWatch Logs**: Application logs via CloudWatch agent
- **Health Check**: `curl http://localhost:5000/api/health`
- **Metrics**: Custom CloudWatch metrics for query performance