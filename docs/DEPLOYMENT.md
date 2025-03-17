# Deployment Guide

## Development Environment

### Local Setup

1. **Environment Setup**
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt
```

2. **Configuration**
```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your settings
nano .env
```

3. **Run Development Server**
```bash
uvicorn app.main:app --reload --port 8000
```

### Development Tools

1. **Code Formatting**
```bash
# Install development dependencies
pip install black isort flake8

# Format code
black app/
isort app/

# Check code style
flake8 app/
```

2. **Running Tests**
```bash
# Install test dependencies
pip install pytest pytest-cov pytest-asyncio

# Run tests
pytest tests/

# Run tests with coverage
pytest --cov=app tests/
```

## Production Deployment

### Prerequisites

1. **System Requirements**
- Python 3.8+
- pip
- Virtual environment
- Supervisor (for process management)
- Nginx (for reverse proxy)

2. **Server Setup**
```bash
# Update system
sudo apt-get update
sudo apt-get upgrade

# Install Python dependencies
sudo apt-get install python3-pip python3-dev

# Install Nginx
sudo apt-get install nginx

# Install Supervisor
sudo apt-get install supervisor
```

### Application Deployment

1. **Clone Repository**
```bash
git clone <repository-url>
cd company-chatbot
```

2. **Setup Virtual Environment**
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

3. **Configuration**
```bash
# Create production environment file
cp .env.example .env.prod

# Edit production settings
nano .env.prod
```

### Server Configuration

1. **Supervisor Setup**
```ini
# /etc/supervisor/conf.d/chatbot.conf

[program:chatbot]
command=/path/to/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
directory=/path/to/company-chatbot
user=www-data
autostart=true
autorestart=true
stopasgroup=true
killasgroup=true
stderr_logfile=/var/log/chatbot/chatbot.err.log
stdout_logfile=/var/log/chatbot/chatbot.out.log
```

2. **Nginx Configuration**
```nginx
# /etc/nginx/sites-available/chatbot

server {
    listen 80;
    server_name your_domain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}
```

3. **Start Services**
```bash
# Reload supervisor
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start chatbot

# Enable Nginx site
sudo ln -s /etc/nginx/sites-available/chatbot /etc/nginx/sites-enabled
sudo nginx -t
sudo systemctl restart nginx
```

### Monitoring Setup

1. **Log Directories**
```bash
# Create log directories
sudo mkdir -p /var/log/chatbot
sudo chown www-data:www-data /var/log/chatbot
```

2. **Log Rotation**
```bash
# /etc/logrotate.d/chatbot

/var/log/chatbot/*.log {
    daily
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 www-data www-data
    sharedscripts
    postrotate
        supervisorctl restart chatbot
    endscript
}
```

### Backup Setup

1. **Backup Script**
```bash
#!/bin/bash
# /usr/local/bin/backup-chatbot

BACKUP_DIR="/path/to/backups"
DATE=$(date +%Y%m%d_%H%M%S)

# Backup conversations
tar -czf $BACKUP_DIR