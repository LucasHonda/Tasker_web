# Calendar & Task Manager - Windows Server 2012 Deployment Guide

## Prerequisites

- **Windows Server 2012 R2** (recommended) or Windows Server 2012
- **Administrator access** to the server
- **Domain name** pointing to your server IP
- **Firewall access** to ports 80, 443, 3000, 8001

## 1. Install Required Software

### Option A: Using Chocolatey (Recommended)

First, install Chocolatey package manager:
```powershell
# Run PowerShell as Administrator
Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
```

Install dependencies:
```powershell
# Install Node.js
choco install nodejs -y

# Install Python
choco install python3 -y

# Install Git
choco install git -y

# Install MongoDB
choco install mongodb -y

# Refresh environment variables
refreshenv
```

### Option B: Manual Installation

1. **Node.js**: Download from https://nodejs.org (v16 or higher)
2. **Python**: Download from https://python.org (v3.8 or higher)
3. **Git**: Download from https://git-scm.com
4. **MongoDB**: Download from https://mongodb.com/try/download/community

## 2. Setup MongoDB

### Configure MongoDB Service

Create MongoDB configuration file at `C:\Program Files\MongoDB\Server\6.0\bin\mongod.cfg`:
```yaml
# mongod.conf
storage:
  dbPath: C:\data\db
  journal:
    enabled: true

systemLog:
  destination: file
  logAppend: true
  path: C:\data\log\mongod.log

net:
  port: 27017
  bindIp: 127.0.0.1

# Enable authentication (optional but recommended)
security:
  authorization: enabled
```

Create required directories:
```cmd
mkdir C:\data\db
mkdir C:\data\log
```

Install MongoDB as Windows Service:
```cmd
# Run Command Prompt as Administrator
cd "C:\Program Files\MongoDB\Server\6.0\bin"
mongod.exe --config "C:\Program Files\MongoDB\Server\6.0\bin\mongod.cfg" --install --serviceName "MongoDB"

# Start the service
net start MongoDB
```

Set MongoDB to start automatically:
```cmd
sc config MongoDB start= auto
```

## 3. Clone and Setup Project

```cmd
# Navigate to your desired directory (e.g., C:\inetpub\wwwroot\)
cd C:\inetpub\wwwroot
git clone <your-repo-url> calendar-task-manager
cd calendar-task-manager
```

## 4. Backend Setup

```cmd
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt
```

### Backend Configuration

Create `backend\.env` file:
```env
MONGO_URL=mongodb://localhost:27017
DB_NAME=calendar_tasks
CORS_ORIGINS=https://yourdomain.com,http://localhost:3000
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
```

### Create Backend Windows Service

Create `backend\install_service.py`:
```python
import sys
import os
import win32serviceutil
import win32service
import win32event
import servicemanager
import socket
import subprocess
import time

class CalendarBackendService(win32serviceutil.ServiceFramework):
    _svc_name_ = "CalendarBackend"
    _svc_display_name_ = "Calendar Task Manager Backend"
    _svc_description_ = "Backend service for Calendar Task Manager"

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        socket.setdefaulttimeout(60)
        self.process = None

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.hWaitStop)
        if self.process:
            self.process.terminate()

    def SvcDoRun(self):
        servicemanager.LogMsg(servicemanager.EVENTLOG_INFORMATION_TYPE,
                              servicemanager.PYS_SERVICE_STARTED,
                              (self._svc_name_, ''))
        self.main()

    def main(self):
        # Change to backend directory
        backend_dir = r"C:\inetpub\wwwroot\calendar-task-manager\backend"
        os.chdir(backend_dir)
        
        # Start uvicorn server
        venv_python = os.path.join(backend_dir, "venv", "Scripts", "python.exe")
        cmd = [venv_python, "-m", "uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8001"]
        
        while True:
            try:
                self.process = subprocess.Popen(cmd)
                # Wait for service stop event
                win32event.WaitForSingleObject(self.hWaitStop, win32event.INFINITE)
                break
            except Exception as e:
                servicemanager.LogErrorMsg(f"Service error: {str(e)}")
                time.sleep(5)

if __name__ == '__main__':
    win32serviceutil.HandleCommandLine(CalendarBackendService)
```

Install service dependencies and create service:
```cmd
pip install pywin32
python install_service.py install
python install_service.py start
```

## 5. Frontend Setup

```cmd
cd ..\frontend

# Install dependencies
npm install

# Build for production
npm run build
```

### Frontend Configuration

Create `frontend\.env.production`:
```env
REACT_APP_BACKEND_URL=https://yourdomain.com
```

## 6. Web Server Setup with IIS

### Install IIS and Required Features

Using PowerShell as Administrator:
```powershell
# Install IIS
Enable-WindowsOptionalFeature -Online -FeatureName IIS-WebServerRole

# Install IIS Management Console
Enable-WindowsOptionalFeature -Online -FeatureName IIS-ManagementConsole

# Install URL Rewrite Module
# Download from: https://www.iis.net/downloads/microsoft/url-rewrite
```

### Install Node.js IIS Integration

```cmd
# Install iisnode
# Download from: https://github.com/Azure/iisnode/releases
```

### Configure IIS Sites

1. **Open IIS Manager**
2. **Create Frontend Site**:
   - Right-click "Sites" → "Add Website"
   - Site name: `Calendar-Frontend`
   - Physical path: `C:\inetpub\wwwroot\calendar-task-manager\frontend\build`
   - Port: `3000`
   - Host name: `yourdomain.com`

3. **Create Backend Site**:
   - Right-click "Sites" → "Add Website"
   - Site name: `Calendar-Backend`
   - Physical path: `C:\inetpub\wwwroot\calendar-task-manager\backend`
   - Port: `8001`

### Configure URL Rewrite Rules

Create `frontend\build\web.config`:
```xml
<?xml version="1.0" encoding="utf-8"?>
<configuration>
  <system.webServer>
    <rewrite>
      <rules>
        <rule name="React Routes" stopProcessing="true">
          <match url=".*" />
          <conditions logicalGrouping="MatchAll">
            <add input="{REQUEST_FILENAME}" matchType="IsFile" negate="true" />
            <add input="{REQUEST_FILENAME}" matchType="IsDirectory" negate="true" />
            <add input="{REQUEST_URI}" pattern="^/(api)" negate="true" />
          </conditions>
          <action type="Rewrite" url="/" />
        </rule>
        <rule name="API Proxy" stopProcessing="true">
          <match url="^api/(.*)" />
          <action type="Rewrite" url="http://localhost:8001/api/{R:1}" />
        </rule>
      </rules>
    </rewrite>
    <staticContent>
      <mimeMap fileExtension=".json" mimeType="application/json" />
    </staticContent>
  </system.webServer>
</configuration>
```

## 7. Alternative: Using Nginx on Windows

### Install Nginx

```cmd
# Download nginx for Windows from http://nginx.org/en/download.html
# Extract to C:\nginx
```

### Configure Nginx

Create `C:\nginx\conf\calendar-app.conf`:
```nginx
server {
    listen 80;
    server_name yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl;
    server_name yourdomain.com;

    ssl_certificate C:\nginx\ssl\certificate.crt;
    ssl_certificate_key C:\nginx\ssl\private.key;

    # Frontend
    location / {
        root C:\inetpub\wwwroot\calendar-task-manager\frontend\build;
        try_files $uri $uri/ /index.html;
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

Include in main nginx.conf:
```nginx
http {
    include calendar-app.conf;
}
```

### Install Nginx as Windows Service

Download NSSM (Non-Sucking Service Manager):
```cmd
# Download from https://nssm.cc/download
# Extract to C:\nssm

# Install nginx as service
C:\nssm\nssm.exe install nginx C:\nginx\nginx.exe
C:\nssm\nssm.exe set nginx AppDirectory C:\nginx
C:\nssm\nssm.exe start nginx
```

## 8. SSL Certificate Setup

### Option A: Self-Signed Certificate (Development)

```powershell
# Create self-signed certificate
New-SelfSignedCertificate -DnsName "yourdomain.com" -CertStoreLocation "cert:\LocalMachine\My"

# Export certificate
$cert = Get-ChildItem -Path "Cert:\LocalMachine\My" | Where-Object {$_.Subject -match "yourdomain.com"}
Export-Certificate -Cert $cert -FilePath "C:\nginx\ssl\certificate.crt"
```

### Option B: Let's Encrypt with Certbot

```cmd
# Install Certbot for Windows
# Download from https://certbot.eff.org/instructions?ws=other&os=windows

# Generate certificate
certbot certonly --standalone -d yourdomain.com
```

## 9. Firewall Configuration

```cmd
# Open required ports
netsh advfirewall firewall add rule name="HTTP" dir=in action=allow protocol=TCP localport=80
netsh advfirewall firewall add rule name="HTTPS" dir=in action=allow protocol=TCP localport=443
netsh advfirewall firewall add rule name="Frontend" dir=in action=allow protocol=TCP localport=3000
netsh advfirewall firewall add rule name="Backend" dir=in action=allow protocol=TCP localport=8001
```

## 10. Task Scheduler Setup (Alternative to Services)

### Create Scheduled Task for Backend

```powershell
# Create task to run backend on startup
$action = New-ScheduledTaskAction -Execute "C:\inetpub\wwwroot\calendar-task-manager\backend\venv\Scripts\python.exe" -Argument "-m uvicorn server:app --host 0.0.0.0 --port 8001" -WorkingDirectory "C:\inetpub\wwwroot\calendar-task-manager\backend"

$trigger = New-ScheduledTaskTrigger -AtStartup

$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -RunOnlyIfNetworkAvailable

Register-ScheduledTask -TaskName "CalendarBackend" -Action $action -Trigger $trigger -Settings $settings -User "SYSTEM"
```

## 11. Environment Variables (System-wide)

```cmd
# Set system environment variables
setx MONGO_URL "mongodb://localhost:27017" /M
setx DB_NAME "calendar_tasks" /M
setx CORS_ORIGINS "https://yourdomain.com" /M
setx GOOGLE_CLIENT_ID "your-client-id" /M
setx GOOGLE_CLIENT_SECRET "your-client-secret" /M
```

## 12. Monitoring and Logs

### View Service Logs

```cmd
# View Windows Event Logs
eventvwr.msc

# View MongoDB logs
type C:\data\log\mongod.log

# View IIS logs
type C:\inetpub\logs\LogFiles\W3SVC1\*.log
```

### Create Log Rotation Script

Create `scripts\rotate_logs.ps1`:
```powershell
# Rotate application logs
$logPath = "C:\inetpub\wwwroot\calendar-task-manager\logs"
$date = Get-Date -Format "yyyyMMdd"

if (Test-Path "$logPath\app.log") {
    Move-Item "$logPath\app.log" "$logPath\app_$date.log"
}

# Keep only last 30 days of logs
Get-ChildItem $logPath -Name "app_*.log" | 
    Where-Object { $_.CreationTime -lt (Get-Date).AddDays(-30) } | 
    Remove-Item
```

Schedule this script to run daily:
```powershell
$action = New-ScheduledTaskAction -Execute "PowerShell.exe" -Argument "-File C:\inetpub\wwwroot\calendar-task-manager\scripts\rotate_logs.ps1"
$trigger = New-ScheduledTaskTrigger -Daily -At "02:00AM"
Register-ScheduledTask -TaskName "LogRotation" -Action $action -Trigger $trigger
```

## 13. Backup Strategy

### MongoDB Backup Script

Create `scripts\backup_mongodb.ps1`:
```powershell
$backupPath = "C:\backups\mongodb"
$date = Get-Date -Format "yyyyMMdd"
$backupDir = "$backupPath\$date"

# Create backup directory
New-Item -ItemType Directory -Path $backupDir -Force

# Run mongodump
& "C:\Program Files\MongoDB\Server\6.0\bin\mongodump.exe" --db calendar_tasks --out $backupDir

# Compress backup
Compress-Archive -Path $backupDir -DestinationPath "$backupDir.zip"
Remove-Item -Path $backupDir -Recurse

# Keep only last 7 days of backups
Get-ChildItem $backupPath -Name "*.zip" | 
    Where-Object { $_.CreationTime -lt (Get-Date).AddDays(-7) } | 
    Remove-Item
```

## 14. Performance Tuning

### IIS Optimization

```xml
<!-- Add to web.config -->
<system.webServer>
  <urlCompression doDynamicCompression="true" doStaticCompression="true" />
  <httpCompression>
    <dynamicTypes>
      <add mimeType="application/json" enabled="true" />
      <add mimeType="application/javascript" enabled="true" />
    </dynamicTypes>
  </httpCompression>
  <staticContent>
    <clientCache cacheControlMode="UseMaxAge" cacheControlMaxAge="7.00:00:00" />
  </staticContent>
</system.webServer>
```

### MongoDB Optimization

```javascript
// Connect to MongoDB
mongo

// Create indexes for better performance
use calendar_tasks
db.tasks.createIndex({"user_id": 1})
db.tasks.createIndex({"user_id": 1, "completed": 1})
db.tasks.createIndex({"user_id": 1, "due_date": 1})
db.users.createIndex({"email": 1})
db.users.createIndex({"session_token": 1})
```

## 15. Security Considerations

### Windows Security

1. **Keep Windows Updated**:
   ```cmd
   sconfig
   # Select option 6 for Windows Updates
   ```

2. **Configure Windows Firewall**:
   ```cmd
   # Enable firewall
   netsh advfirewall set allprofiles state on
   
   # Block all unnecessary ports
   netsh advfirewall firewall add rule name="Block All" dir=in action=block
   ```

3. **User Account Control**:
   - Run services with limited user accounts
   - Don't run as Administrator unless necessary

## 16. Troubleshooting

### Common Issues

1. **Node.js/Python not found**:
   - Add to PATH: `C:\Program Files\nodejs\` and `C:\Python39\`

2. **MongoDB connection issues**:
   ```cmd
   # Check if MongoDB service is running
   sc query MongoDB
   
   # Restart if needed
   net stop MongoDB
   net start MongoDB
   ```

3. **IIS module errors**:
   ```cmd
   # Re-register .NET
   C:\Windows\Microsoft.NET\Framework64\v4.0.30319\aspnet_regiis.exe -i
   ```

4. **Port conflicts**:
   ```cmd
   # Check what's using a port
   netstat -ano | findstr :8001
   ```

### Health Check URLs

- Frontend: `https://yourdomain.com/`
- Backend API: `https://yourdomain.com/api/`
- MongoDB: `mongodb://localhost:27017`

## 17. Maintenance Scripts

Create `scripts\maintenance.ps1`:
```powershell
# System maintenance script
Write-Host "Starting maintenance..."

# Clear temporary files
Remove-Item -Path $env:TEMP\* -Recurse -Force -ErrorAction SilentlyContinue

# Restart services
Restart-Service -Name "MongoDB" -Force
Restart-Service -Name "CalendarBackend" -Force

# Compact MongoDB
& "C:\Program Files\MongoDB\Server\6.0\bin\mongo.exe" --eval "db.runCommand({compact: 'tasks'})" calendar_tasks

Write-Host "Maintenance completed."
```

This guide provides comprehensive instructions for deploying the Calendar & Task Manager application on Windows Server 2012. Choose the configuration options that best fit your environment and security requirements.