# Calendar & Task Manager - Deployment Guide

## Prerequisites

- **Node.js** (v16 or higher)
- **Python** (v3.8 or higher)
- **MongoDB** (v4.4 or higher)
- **Domain name** (for Google OAuth)

## 1. Server Setup

### Install Dependencies

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install nodejs npm python3 python3-pip mongodb

# CentOS/RHEL
sudo yum install nodejs npm python3 python3-pip mongodb-org
```

## 2. Clone and Setup Project

```bash
# Clone the project
git clone <your-repo> calendar-task-manager
cd calendar-task-manager

# Setup Backend
cd backend
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Setup Frontend
cd ../frontend
npm install
# or if you prefer yarn:
# yarn install
```

## 3. Configuration

### Backend Configuration (backend/.env)
```env
MONGO_URL="mongodb://localhost:27017"
DB_NAME="calendar_tasks"
CORS_ORIGINS="https://yourdomain.com,http://localhost:3000"
GOOGLE_CLIENT_ID="your-google-client-id"
GOOGLE_CLIENT_SECRET="your-google-client-secret"
```

### Frontend Configuration (frontend/.env)
```env
REACT_APP_BACKEND_URL="https://yourdomain.com"
```

## 4. Google OAuth Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable Google Calendar API
4. Create OAuth 2.0 credentials:
   - **Authorized JavaScript origins**: `https://yourdomain.com`
   - **Authorized redirect URIs**: `https://yourdomain.com/api/auth/google/callback`

## 5. MongoDB Setup

### Local MongoDB
```bash
# Start MongoDB service
sudo systemctl start mongod
sudo systemctl enable mongod

# Create database (optional - will be created automatically)
mongo
> use calendar_tasks
> db.createUser({
    user: "calendar_user",
    pwd: "secure_password",
    roles: ["readWrite"]
})
```

### MongoDB Connection String (if using authentication)
```env
MONGO_URL="mongodb://calendar_user:secure_password@localhost:27017/calendar_tasks"
```

## 6. Production Deployment

### Option A: Using PM2 (Recommended)

```bash
# Install PM2
npm install -g pm2

# Build frontend
cd frontend
npm run build

# Create PM2 configuration
```

Create `ecosystem.config.js`:
```javascript
module.exports = {
  apps: [
    {
      name: 'calendar-backend',
      script: 'venv/bin/python',
      args: '-m uvicorn server:app --host 0.0.0.0 --port 8001',
      cwd: './backend',
      env: {
        NODE_ENV: 'production'
      }
    },
    {
      name: 'calendar-frontend',
      script: 'npx',
      args: 'serve -s build -l 3000',
      cwd: './frontend'
    }
  ]
};
```

```bash
# Start services
pm2 start ecosystem.config.js
pm2 save
pm2 startup
```

### Option B: Using Docker

Create `docker-compose.yml`:
```yaml
version: '3.8'
services:
  mongodb:
    image: mongo:4.4
    volumes:
      - mongodb_data:/data/db
    environment:
      MONGO_INITDB_ROOT_USERNAME: admin
      MONGO_INITDB_ROOT_PASSWORD: password

  backend:
    build: ./backend
    ports:
      - "8001:8001"
    environment:
      - MONGO_URL=mongodb://admin:password@mongodb:27017/calendar_tasks?authSource=admin
    depends_on:
      - mongodb

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      - REACT_APP_BACKEND_URL=https://yourdomain.com

volumes:
  mongodb_data:
```

## 7. Nginx Configuration

Create `/etc/nginx/sites-available/calendar-app`:
```nginx
server {
    listen 80;
    server_name yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl;
    server_name yourdomain.com;

    ssl_certificate /path/to/your/certificate.crt;
    ssl_certificate_key /path/to/your/private.key;

    # Frontend
    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }

    # Backend API
    location /api {
        proxy_pass http://localhost:8001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }
}
```

Enable the site:
```bash
sudo ln -s /etc/nginx/sites-available/calendar-app /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## 8. SSL Certificate (Let's Encrypt)

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com
```

## 9. Environment Variables for Production

### Backend (.env)
```env
MONGO_URL="mongodb://localhost:27017"
DB_NAME="calendar_tasks"
CORS_ORIGINS="https://yourdomain.com"
GOOGLE_CLIENT_ID="your-production-google-client-id"
GOOGLE_CLIENT_SECRET="your-production-google-client-secret"
```

### Frontend (.env.production)
```env
REACT_APP_BACKEND_URL="https://yourdomain.com"
```

## 10. Security Considerations

1. **Use HTTPS**: Always use SSL certificates in production
2. **Environment Variables**: Keep sensitive data in environment variables
3. **MongoDB Security**: Use authentication and restrict access
4. **Firewall**: Configure firewall to only allow necessary ports
5. **Regular Updates**: Keep all dependencies updated

## 11. Monitoring and Logs

```bash
# PM2 logs
pm2 logs

# System logs
sudo journalctl -u nginx
sudo journalctl -u mongod

# Application logs
tail -f backend/logs/app.log
```

## 12. Backup Strategy

```bash
# MongoDB backup
mongodump --db calendar_tasks --out /backup/mongodb/$(date +%Y%m%d)

# Application backup
tar -czf /backup/app/calendar-app-$(date +%Y%m%d).tar.gz /path/to/calendar-task-manager
```

## Troubleshooting

### Common Issues:

1. **Date Display Issues**: Ensure timezone configuration is correct
2. **Google OAuth Issues**: Check redirect URIs match exactly
3. **CORS Errors**: Verify CORS_ORIGINS includes your domain
4. **MongoDB Connection**: Check MongoDB service status and connection string

### Health Check Endpoints:

- Backend: `https://yourdomain.com/api/`
- Frontend: `https://yourdomain.com/`

## Support

For issues, check:
1. Application logs
2. Browser console (F12)
3. Network tab for API errors
4. MongoDB connection status