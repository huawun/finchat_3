# RedShift Chatbot - Maintenance Guide 🤖

## Quick Reference

| Service | Status Check | Restart Command |
|---------|-------------|-----------------|
| Application | `curl http://10.35.10.16:5000/api/health` | `sudo systemctl restart finchat` |
| EC2 Instance | `aws ec2 describe-instances --instance-ids i-07687d799d109c9dd` | N/A |
| RedShift | Health endpoint shows `"redshift": "connected"` | Check security groups |
| Bedrock | Health endpoint shows `"bedrock": "connected"` | Check IAM permissions |

## 🚀 Starting the Application

### Method 1: Using systemd Service (Recommended)
```bash
# Start the service
sudo systemctl start finchat

# Enable auto-start on boot
sudo systemctl enable finchat

# Check status
sudo systemctl status finchat
```

### Method 2: Manual Start (Development)
```bash
cd /opt/finchat
export $(cat .env | xargs)
nohup python3 app.py > app.log 2>&1 &
```

### Method 3: Using Docker (Alternative)
```bash
cd /opt/finchat
docker-compose up -d
```

## 🔍 Health Monitoring

### Check Application Health
```bash
# Basic health check
curl http://10.35.10.16:5000/api/health

# Detailed deployment info
curl http://10.35.10.16:5000/api/info

# Expected healthy response:
{
  "bedrock": "connected",
  "redshift": "connected", 
  "status": "healthy"
}
```

### Check Application Logs
```bash
# View recent logs
tail -50 /opt/finchat/app.log

# Follow logs in real-time
tail -f /opt/finchat/app.log

# Search for errors
grep -i error /opt/finchat/app.log
```

### Check Process Status
```bash
# Check if app is running
ps aux | grep "python3 app.py" | grep -v grep

# Check port usage
netstat -tlnp | grep :5000
```

## 🔧 Maintenance Tasks

### Restart Application
```bash
# Method 1: Using systemd
sudo systemctl restart finchat

# Method 2: Manual restart
pkill -f "python3 app.py"
cd /opt/finchat
export $(cat .env | xargs)
nohup python3 app.py > app.log 2>&1 &
```

### Update Configuration
```bash
# Edit environment variables
sudo nano /opt/finchat/.env

# Restart after changes
sudo systemctl restart finchat
```

### Log Rotation
```bash
# Archive current log
mv /opt/finchat/app.log /opt/finchat/app.log.$(date +%Y%m%d)

# Restart to create new log
sudo systemctl restart finchat
```

## 🚨 Troubleshooting

### Common Issues

#### 1. Application Not Starting
```bash
# Check logs for errors
tail -20 /opt/finchat/app.log

# Common fixes:
python3 -m pip install --user flask boto3 psycopg2-binary python-dotenv flask-cors requests

# Restart application
sudo systemctl restart finchat
```

#### 2. RedShift Connection Failed
```bash
# Test connection manually
python3 -c "
import psycopg2
from config import Config
Config.validate_config()
conn = psycopg2.connect(Config.get_redshift_connection_string())
print('RedShift OK')
"

# Check security groups
aws ec2 describe-security-groups --group-ids sg-0ea8315bf549db264
```

#### 3. Bedrock Access Denied
```bash
# Check IAM role
aws sts get-caller-identity

# Test Bedrock access
aws bedrock list-foundation-models --region ap-southeast-1 --max-items 1

# Fix model ID if needed
sed -i 's/BEDROCK_MODEL_ID=.*/BEDROCK_MODEL_ID=apac.anthropic.claude-3-5-sonnet-20241022-v2:0/' /opt/finchat/.env
```

#### 4. Port 5000 Already in Use
```bash
# Find process using port
sudo lsof -i :5000

# Kill process if needed
sudo kill -9 <PID>
```

### Error Codes Reference

| Error | Cause | Solution |
|-------|-------|----------|
| `ModuleNotFoundError` | Missing Python packages | Install dependencies |
| `Connection refused` | App not running | Start application |
| `Access denied` | IAM permissions | Check EC2 role permissions |
| `Unknown host` | Network/DNS issue | Check security groups |

## 🔐 Security Maintenance

### Update IAM Permissions
```bash
# Check current role
aws iam get-role --role-name FinChatEC2Role-nonprod

# List attached policies
aws iam list-attached-role-policies --role-name FinChatEC2Role-nonprod
```

### Rotate Credentials (if using hardcoded)
```bash
# Switch to IAM roles (recommended)
cd /opt/finchat
./switch-to-iam.sh
sudo systemctl restart finchat
```

## 📊 Performance Monitoring

### Check Resource Usage
```bash
# CPU and Memory
top -p $(pgrep -f "python3 app.py")

# Disk usage
df -h /opt/finchat

# Network connections
ss -tulpn | grep :5000
```

### Query Performance
```bash
# Check recent query times in logs
grep "execution_time" /opt/finchat/app.log | tail -10
```

## 🔄 Updates and Deployment

### Update Application Code
```bash
cd /opt/finchat
git pull origin main
sudo systemctl restart finchat
```

### Update Dependencies
```bash
cd /opt/finchat
python3 -m pip install --user -r requirements.txt --upgrade
sudo systemctl restart finchat
```

### Backup Configuration
```bash
# Backup current config
cp /opt/finchat/.env /opt/finchat/.env.backup.$(date +%Y%m%d)

# Backup logs
tar -czf /opt/finchat/logs_backup_$(date +%Y%m%d).tar.gz /opt/finchat/*.log
```

## 🌐 Network Access

### Access Methods
1. **VPN Connection**: Connect to VPC network
2. **Bastion Host**: SSH through jump server
3. **AWS Session Manager**: 
   ```bash
   aws ssm start-session --target i-07687d799d109c9dd
   ```

### Port Forwarding (for external access)
```bash
# Using SSH tunnel
ssh -L 8080:10.35.10.16:5000 -i your-key.pem ec2-user@bastion-host

# Access via: http://localhost:8080
```

## 📱 API Usage

### Test Chat Functionality
```bash
# Simple test
curl -X POST http://10.35.10.16:5000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Show me GL accounts"}'

# Health check
curl http://10.35.10.16:5000/api/health | jq .
```

### Available Endpoints
- `GET /` - Web interface
- `POST /api/chat` - Chat with AI
- `GET /api/health` - Health status
- `GET /api/info` - Deployment info

## 🚨 Emergency Procedures

### Complete System Restart
```bash
# 1. Stop application
sudo systemctl stop finchat

# 2. Check for hanging processes
pkill -f "python3 app.py"

# 3. Clear logs if needed
> /opt/finchat/app.log

# 4. Start fresh
sudo systemctl start finchat

# 5. Verify
curl http://10.35.10.16:5000/api/health
```

### Rollback Configuration
```bash
# Restore previous config
cp /opt/finchat/.env.backup.YYYYMMDD /opt/finchat/.env
sudo systemctl restart finchat
```

## 📞 Support Information

### Key Files
- **Application**: `/opt/finchat/app.py`
- **Configuration**: `/opt/finchat/.env`
- **Logs**: `/opt/finchat/app.log`
- **Service**: `/etc/systemd/system/finchat.service`

### AWS Resources
- **EC2 Instance**: `i-07687d799d109c9dd`
- **IAM Role**: `FinChatEC2Role-nonprod`
- **Security Group**: `sg-0ea8315bf549db264`
- **Region**: `ap-southeast-1`

### Quick Commands Cheat Sheet
```bash
# Status check
curl -s http://10.35.10.16:5000/api/health | jq .status

# Restart app
sudo systemctl restart finchat

# View logs
tail -f /opt/finchat/app.log

# Check process
ps aux | grep app.py

# Test RedShift
python3 -c "from modules.redshift_client import RedShiftClient; print('OK' if RedShiftClient().test_connections()['redshift'] else 'FAIL')"
```

---

**Last Updated**: October 21, 2025  
**Version**: 1.0  
**Environment**: Production (nonprod)
