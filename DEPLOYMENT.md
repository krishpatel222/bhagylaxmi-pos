# Bhagyalaxmi Enterprise POS - Deployment Guide

**Shop Name**: ભાગ્યલક્ષ્મી એન્ટરપ્રાઇઝ  
**Address**: જ્યોતિ હોસ્પિટલની સામે નુતન રોડ, વિસનગર, ગુજરાત  
**Timezone**: `Asia/Kolkata`

---

## 1. Environment Overview
- **Framework**: Django 6.1.1 (Python 3.14.3)
- **WSGI Application**: `config.wsgi:application`
- **Application Server**: Gunicorn (`gunicorn`)
- **Database**: SQLite (Default local) or PostgreSQL (Environment driven)
- **Static File Handler**: Django `collectstatic` served via Reverse Proxy (Nginx) or WhiteNoise.

---

## 2. Step-by-Step Deployment Instructions

### Step 1: Clone / Copy Project Files
```bash
git clone <repository_url> /var/www/bhagyalaxmi_pos
cd /var/www/bhagyalaxmi_pos
```

### Step 2: Create & Activate Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Production Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 4: Configure Production Environment Variables (`.env`)
Copy `.env.example` to `.env` and populate production values:
```bash
cp .env.example .env
nano .env
```
Key production configurations:
```ini
SECRET_KEY=generate_a_secure_random_64_character_key_here
DEBUG=False
ALLOWED_HOSTS=pos.bhagyalaxmi.com,127.0.0.1
CSRF_TRUSTED_ORIGINS=https://pos.bhagyalaxmi.com

# Database (Leave default for SQLite or configure PostgreSQL)
DB_ENGINE=django.db.backends.sqlite3
DB_NAME=db.sqlite3

# HTTPS Security (Enable when SSL Certificate is installed)
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
SECURE_SSL_REDIRECT=True
```

### Step 5: Execute Database Migrations
```bash
python manage.py makemigrations --check
python manage.py migrate
```

### Step 6: Create Initial Admin Account
```bash
python manage.py createsuperuser
```

### Step 7: Collect Production Static Files
```bash
python manage.py collectstatic --noinput
```

### Step 8: Verify Gunicorn Server Execution
```bash
gunicorn config.wsgi:application --bind 127.0.0.1:8000
```

---

## 3. Systemd Service Configuration (`/etc/systemd/system/bhagyalaxmi_pos.service`)
Create a systemd service file to manage the Gunicorn background process:

```ini
[Unit]
Description=Bhagyalaxmi Enterprise POS Gunicorn Daemon
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/bhagyalaxmi_pos
ExecStart=/var/www/bhagyalaxmi_pos/venv/bin/gunicorn \
          --access-logfile - \
          --workers 3 \
          --bind unix:/var/www/bhagyalaxmi_pos/gunicorn.sock \
          config.wsgi:application

[Install]
WantedBy=multi-user.target
```

Enable and start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl start bhagyalaxmi_pos
sudo systemctl enable bhagyalaxmi_pos
```

---

## 4. Nginx Reverse Proxy Configuration (`/etc/nginx/sites-available/bhagyalaxmi_pos`)

```nginx
server {
    listen 80;
    server_name pos.bhagyalaxmi.com;

    location /static/ {
        alias /var/www/bhagyalaxmi_pos/staticfiles/;
    }

    location /media/ {
        alias /var/www/bhagyalaxmi_pos/media/;
    }

    location / {
        proxy_set_header Host $http_host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_pass http://unix:/var/www/bhagyalaxmi_pos/gunicorn.sock;
    }
}
```

Enable site & enable HTTPS with Certbot:
```bash
sudo ln -s /etc/nginx/sites-available/bhagyalaxmi_pos /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
sudo certbot --nginx -d pos.bhagyalaxmi.com
```

---

## 5. Automated Database Backup Cron Job
Add a daily cron job to run the internal backup service or trigger a daily copy:
```bash
0 2 * * * /var/www/bhagyalaxmi_pos/venv/bin/python /var/www/bhagyalaxmi_pos/manage.py test core.tests
```
Backups are available at `/settings/backup/` inside the application for authenticated Admins.
