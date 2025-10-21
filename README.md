# RedShift Chatbot 🤖

A web-based chatbot that queries AWS RedShift databases using natural language, powered by AWS Bedrock's Claude 3.5 Sonnet.

## Quick Start 🚀

### Local Development

1. **Setup Environment**
   ```bash
   cp .env.example .env
   # Edit .env with your AWS and RedShift credentials
   ```

2. **Run Application**
   ```bash
   ./start.sh
   ```

3. **Access**
   Open `http://localhost:5000`

### AWS EC2 Deployment

For production deployment on AWS EC2 with private network access:

1. **Prepare Deployment**
   ```bash
   cd deploy
   chmod +x setup-ssm-parameters.sh deploy.sh
   
   # Store RedShift credentials securely in SSM
   ./setup-ssm-parameters.sh
   ```

2. **Deploy to EC2**
   ```bash
   # Interactive deployment script
   ./deploy.sh
   ```

   Or manually with CloudFormation:
   ```bash
   aws cloudformation create-stack \
     --stack-name finchat-chatbot \
     --template-body file://improved-cloudformation.yaml \
     --parameters \
       ParameterKey=VpcId,ParameterValue=vpc-xxxxxxxxx \
       ParameterKey=SubnetId,ParameterValue=subnet-xxxxxxxxx \
       ParameterKey=KeyPairName,ParameterValue=your-key-pair \
       ParameterKey=RedShiftSecurityGroupId,ParameterValue=sg-xxxxxxxxx \
     --capabilities CAPABILITY_NAMED_IAM
   ```

3. **Access Application**
   - Application runs on port 5000
   - Access via private IP from within VPC
   - Use VPN, bastion host, or AWS Systems Manager Session Manager

## Configuration

### Environment Variables

Edit `.env` file with:
- AWS credentials and region (optional on EC2 with IAM roles)
- Bedrock model settings
- RedShift connection details
- Application settings

### IAM-Based Configuration (Recommended for EC2)

For enhanced security on EC2, switch to IAM role-based configuration:

```bash
# Switch to IAM-based config (uses EC2 IAM roles)
./switch-to-iam.sh

# Revert to original config if needed
./revert-config.sh
```

## Project Structure

```
finchat_3/
├── app.py              # Main Flask application
├── config.py           # Configuration management
├── start.sh            # Local startup script
├── test_setup.py       # Setup validation
├── requirements.txt    # Dependencies
├── Dockerfile          # Container configuration
├── docker-compose.yml  # Container orchestration
├── modules/            # Core modules
├── static/             # CSS/JS files
├── templates/          # HTML templates
└── deploy/             # AWS deployment files
    ├── deploy.sh                    # Interactive deployment
    ├── improved-cloudformation.yaml # Enhanced CF template
    ├── setup-ssm-parameters.sh     # SSM parameter setup
    └── README.md                   # Deployment guide
```

## Dependencies

- Flask 3.0.0
- boto3 (AWS SDK)
- psycopg2-binary (PostgreSQL/RedShift)
- python-dotenv
- flask-cors
- gunicorn (production server)

## Features

- Natural language to SQL conversion
- Interactive chat interface
- Real-time query execution
- Security built-in (read-only operations)
- Health check endpoints
- Deployment information API
- IAM role support for EC2
- Private network connectivity

## API Endpoints

- `GET /` - Main chat interface
- `POST /api/chat` - Process chat messages
- `GET /api/health` - Health check with service status
- `GET /api/info` - Deployment and configuration information

## Network Architecture

### Local Development
```
Developer Machine → Internet → AWS Bedrock
                            → RedShift (public/private)
```

### EC2 Production Deployment
```
User → VPC → EC2 Instance → RedShift (private)
                         → AWS Bedrock (via IAM role)
```

## Security Features

- **IAM Roles**: Uses EC2 IAM roles instead of hardcoded credentials
- **Private Network**: RedShift access through private subnets
- **Encrypted Parameters**: Credentials stored in SSM Parameter Store
- **Read-Only Access**: Database queries are read-only
- **Security Groups**: Proper network isolation

## Troubleshooting

### Common Issues

1. **RedShift Connection Failed**
   - Check security group rules between EC2 and RedShift
   - Verify VPC routing and subnet configuration
   - Confirm RedShift endpoint accessibility

2. **Bedrock Access Denied**
   - Verify IAM role permissions for Bedrock
   - Check AWS region configuration
   - Ensure Bedrock model access is enabled

3. **Docker Issues on EC2**
   - Check Docker service: `sudo systemctl status docker`
   - View application logs: `cd /opt/finchat && docker-compose logs -f`
   - Restart application: `sudo systemctl restart finchat`

### Health Checks

```bash
# Check application health
curl http://localhost:5000/api/health

# Get deployment information
curl http://localhost:5000/api/info

# View application logs
docker-compose logs -f
```

### SSH Access to EC2

```bash
# Connect to EC2 instance
ssh -i your-key.pem ec2-user@<private-ip>

# Check application status
cd /opt/finchat
docker ps
docker-compose logs -f

# Restart services
sudo systemctl restart finchat
```

## Monitoring

- **Health Endpoint**: `/api/health` for service monitoring
- **Info Endpoint**: `/api/info` for deployment details
- **CloudWatch Logs**: Application logs via CloudWatch agent
- **Custom Metrics**: Query performance and error rates

## Development

### Local Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run tests
python test_setup.py

# Start development server
python app.py
```

### Testing Configuration

```bash
# Test local configuration
python test_setup.py

# Test EC2 deployment
curl http://<ec2-private-ip>:5000/api/health
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is licensed under the MIT License.