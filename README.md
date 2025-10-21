# RedShift Chatbot 🤖

A web-based chatbot that queries AWS RedShift databases using natural language, powered by AWS Bedrock's Claude 3.5 Sonnet.

## Quick Start 🚀

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

## Configuration

Edit `.env` file with:
- AWS credentials and region
- Bedrock model settings
- RedShift connection details

## Project Structure

```
finchat_3/
├── app.py              # Main Flask application
├── config.py           # Configuration management
├── start.sh            # Startup script
├── test_setup.py       # Setup validation
├── requirements.txt    # Dependencies
├── modules/            # Core modules
├── static/             # CSS/JS files
└── templates/          # HTML templates
```

## Dependencies

- Flask 3.0.0
- boto3 (AWS SDK)
- psycopg2-binary (PostgreSQL/RedShift)
- python-dotenv
- flask-cors

## Features

- Natural language to SQL conversion
- Interactive chat interface
- Real-time query execution
- Security built-in (read-only operations)
- Health check endpoints