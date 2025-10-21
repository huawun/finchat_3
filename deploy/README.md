# AWS EC2 Deployment Guide

This guide helps deploy the RedShift Chatbot to AWS EC2 with private network connectivity and addresses common network issues.

## Prerequisites

1. **AWS CLI configured** with appropriate permissions
2. **RedShift cluster** in private subnet
3. **VPC with private subnets** where RedShift is located
4. **EC2 Key Pair** for SSH access
5. **Proper IAM permissions** for CloudFormation, EC2, SSM, and Bedrock

## Quick Deployment

### Option 1: Interactive Deployment (Recommended)

```bash
cd deploy
chmod +x deploy.sh setup-ssm-parameters.sh
./deploy.sh
```

The script will:
- Guide you through parameter collection
- Set up SSM parameters for credentials
- Deploy CloudFormation stack
- Configure security groups
- Provide access instructions

### Option 2: Manual Deployment

1. **Store Credentials in SSM**
   ```bash
   ./setup-ssm-parameters.sh
   ```

2. **Deploy CloudFormation Stack**
   ```bash
   aws cloudformation create-stack \
     --stack-name finchat-chatbot \
     --template-body file://improved-cloudformation.yaml \
     --parameters \
       ParameterKey=VpcId,ParameterValue=vpc-xxxxxxxxx \
       ParameterKey=SubnetId,ParameterValue=subnet-xxxxxxxxx \
       ParameterKey=KeyPairName,ParameterValue=your-key-pair \
       ParameterKey=RedShiftSecurityGroupId,ParameterValue=sg-xxxxxxxxx \
       ParameterKey=Environment,ParameterValue=nonprod \
     --capabilities CAPABILITY_NAMED_IAM
   ```

## Network Configuration

### Understanding the Network Setup

The deployment creates a secure network configuration:

```
Internet → VPC → Private Subnet → EC2 Instance → RedShift Cluster
                                              → AWS Bedrock (via IAM)
```

### Security Groups

1. **EC2 Security Group** (automatically created):
   - Inbound: Port 5000 from private network (10.0.0.0/8)
   - Inbound: Port 22 from private network (SSH)
   - Outbound: All traffic (for Docker pulls, AWS API calls)

2. **RedShift Security Group** (automatically updated):
   - Inbound: Port 5439 from EC2 security group

### Common Network Issues and Solutions

#### Issue 1: RedShift Connection Timeout

**Symptoms:**
- Application logs show "Connection timeout" to RedShift
- Health check shows RedShift as "disconnected"

**Solutions:**
1. **Check Security Groups:**
   ```bash
   # Get EC2 security group ID
   EC2_SG_ID=$(aws cloudformation describe-stacks \
     --stack-name finchat-chatbot \
     --query 'Stacks[0].Outputs[?OutputKey==`SecurityGroupId`].OutputValue' \
     --output text)
   
   # Verify RedShift security group allows access
   aws ec2 describe-security-groups --group-ids <redshift-sg-id>
   ```

2. **Check VPC Route Tables:**
   ```bash
   # Ensure private subnet has route to NAT Gateway for internet access
   aws ec2 describe-route-tables --filters "Name=association.subnet-id,Values=<subnet-id>"
   ```

3. **Test Network Connectivity:**
   ```bash
   # SSH to EC2 and test RedShift connectivity
   ssh -i your-key.pem ec2-user@<private-ip>
   telnet <redshift-endpoint> 5439
   ```

#### Issue 2: Docker Container Won't Start

**Symptoms:**
- `docker ps` shows no running containers
- Application not accessible on port 5000

**Solutions:**
1. **Check Docker Service:**
   ```bash
   sudo systemctl status docker
   sudo systemctl start docker
   ```

2. **Check Application Logs:**
   ```bash
   cd /opt/finchat
   docker-compose logs -f
   ```

3. **Rebuild Container:**
   ```bash
   docker-compose down
   docker-compose up --build -d
   ```

#### Issue 3: Bedrock Access Denied

**Symptoms:**
- Health check shows Bedrock as "disconnected"
- Logs show "Access Denied" for Bedrock

**Solutions:**
1. **Check IAM Role Permissions:**
   ```bash
   # Verify EC2 instance has the correct IAM role
   aws ec2 describe-instances --instance-ids <instance-id> \
     --query 'Reservations[0].Instances[0].IamInstanceProfile'
   ```

2. **Check Bedrock Model Access:**
   ```bash
   # Test Bedrock access from EC2
   aws bedrock list-foundation-models --region us-east-1
   ```

3. **Verify Region Configuration:**
   - Ensure Bedrock is available in your region
   - Check if model access is enabled in Bedrock console

## Deployment Verification

### 1. Check Stack Status

```bash
aws cloudformation describe-stacks --stack-name finchat-chatbot
```

### 2. Get Instance Information

```bash
# Get instance details
INSTANCE_ID=$(aws cloudformation describe-stacks \
  --stack-name finchat-chatbot \
  --query 'Stacks[0].Outputs[?OutputKey==`InstanceId`].OutputValue' \
  --output text)

PRIVATE_IP=$(aws cloudformation describe-stacks \
  --stack-name finchat-chatbot \
  --query 'Stacks[0].Outputs[?OutputKey==`PrivateIP`].OutputValue' \
  --output text)

echo "Instance ID: $INSTANCE_ID"
echo "Private IP: $PRIVATE_IP"
```

### 3. Test Application

```bash
# SSH to instance
ssh -i your-key.pem ec2-user@$PRIVATE_IP

# Check application status
cd /opt/finchat
docker ps
docker-compose logs --tail=50

# Test health endpoint
curl http://localhost:5000/api/health

# Test info endpoint
curl http://localhost:5000/api/info
```

## Access Methods

### 1. VPN Access
If you have VPN access to the VPC:
```bash
curl http://<private-ip>:5000
```

### 2. Bastion Host
Through a bastion host in a public subnet:
```bash
ssh -i your-key.pem -L 5000:<private-ip>:5000 ec2-user@<bastion-ip>
# Then access http://localhost:5000
```

### 3. AWS Systems Manager Session Manager
```bash
aws ssm start-session --target <instance-id>
```

### 4. Port Forwarding via SSH
```bash
ssh -i your-key.pem -L 5000:<private-ip>:5000 ec2-user@<jump-host>
```

## Monitoring and Maintenance

### Health Monitoring

```bash
# Automated health check
curl -s http://<private-ip>:5000/api/health | jq '.'

# Get deployment information
curl -s http://<private-ip>:5000/api/info | jq '.'
```

### Log Management

```bash
# Application logs
cd /opt/finchat
docker-compose logs -f

# System logs
sudo journalctl -u finchat.service -f

# Docker logs
sudo journalctl -u docker.service -f
```

### Application Management

```bash
# Restart application
sudo systemctl restart finchat

# Stop application
sudo systemctl stop finchat

# Start application
sudo systemctl start finchat

# Check service status
sudo systemctl status finchat
```

## Scaling and Performance

### Vertical Scaling
Update the CloudFormation stack with a larger instance type:

```bash
aws cloudformation update-stack \
  --stack-name finchat-chatbot \
  --use-previous-template \
  --parameters \
    ParameterKey=InstanceType,ParameterValue=t3.large \
    # ... other parameters remain the same
```

### Horizontal Scaling
For multiple instances, consider:
1. Application Load Balancer
2. Auto Scaling Group
3. Shared session storage (Redis/ElastiCache)

## Security Best Practices

1. **Use IAM Roles**: Never hardcode AWS credentials
2. **Private Subnets**: Keep RedShift and EC2 in private subnets
3. **Security Groups**: Use least privilege access
4. **Encrypted Storage**: Use encrypted EBS volumes
5. **Parameter Store**: Store sensitive data in SSM Parameter Store
6. **VPC Flow Logs**: Enable for network monitoring
7. **CloudTrail**: Enable for API call auditing

## Troubleshooting Commands

```bash
# Check EC2 instance status
aws ec2 describe-instances --instance-ids <instance-id>

# Check security group rules
aws ec2 describe-security-groups --group-ids <sg-id>

# Check SSM parameters
aws ssm get-parameters --names "/finchat/redshift-host" --with-decryption

# Test network connectivity
nc -zv <redshift-endpoint> 5439

# Check Docker network
docker network ls
docker network inspect finchat_default

# Check application configuration
cd /opt/finchat && cat .env
```

## Cleanup

To remove all resources:

```bash
aws cloudformation delete-stack --stack-name finchat-chatbot

# Wait for deletion to complete
aws cloudformation wait stack-delete-complete --stack-name finchat-chatbot

# Clean up SSM parameters (optional)
aws ssm delete-parameters --names \
  "/finchat/redshift-host" \
  "/finchat/redshift-database" \
  "/finchat/redshift-user" \
  "/finchat/redshift-password"
```

## Support

For issues:
1. Check application logs: `docker-compose logs`
2. Check system logs: `sudo journalctl -u finchat.service`
3. Verify network connectivity: `telnet <redshift-endpoint> 5439`
4. Test AWS access: `aws sts get-caller-identity`
5. Review CloudFormation events in AWS console