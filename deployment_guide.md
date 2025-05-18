# NVC Banking Platform Deployment Guide

This guide provides step-by-step instructions for deploying the NVC Banking Platform to a Virtual Private Server (VPS).

## Prerequisites

- A VPS with at least 4GB RAM and 2 CPUs
- Ubuntu 22.04 LTS or similar Linux distribution
- Root access to the server
- Domain name pointed to your VPS
- Python 3.11+ installed

## 1. Server Setup

### Update System Packages

```bash
sudo apt update
sudo apt upgrade -y
```

### Install Required System Dependencies

```bash
sudo apt install -y python3-pip python3-dev python3-venv build-essential libssl-dev libffi-dev postgresql postgresql-contrib nginx
```

## 2. Set Up PostgreSQL Database

### Configure PostgreSQL

```bash
sudo -u postgres psql -c "CREATE DATABASE nvcbanking;"
sudo -u postgres psql -c "CREATE USER nvcadmin WITH PASSWORD 'your_secure_password';"
sudo -u postgres psql -c "ALTER ROLE nvcadmin SET client_encoding TO 'utf8';"
sudo -u postgres psql -c "ALTER ROLE nvcadmin SET default_transaction_isolation TO 'read committed';"
sudo -u postgres psql -c "ALTER ROLE nvcadmin SET timezone TO 'UTC';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE nvcbanking TO nvcadmin;"
```

## 3. Set Up Python Environment

### Create Project Directory

```bash
mkdir -p /var/www/nvcbanking
cd /var/www/nvcbanking
```

### Create and Activate Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
```

## 4. Application Deployment

### Clone the Repository (Alternative: Upload Via SFTP)

```bash
git clone [your-repo-url] .
```

*Note: Alternatively, upload the application files via SFTP.*

### Install Required Python Packages

```bash
pip install -r requirements.txt
pip install gunicorn psycopg2-binary
```

### Create .env File

Create a `.env` file with all necessary environment variables:

```bash
touch .env
nano .env
```

Add the following variables:

```
DATABASE_URL=postgresql://nvcadmin:your_secure_password@localhost/nvcbanking
FLASK_SECRET_KEY=your_secret_key
SESSION_SECRET=your_session_secret
STRIPE_SECRET_KEY=your_stripe_key
PAYPAL_CLIENT_ID=your_paypal_client_id
PAYPAL_CLIENT_SECRET=your_paypal_client_secret
SENDGRID_API_KEY=your_sendgrid_api_key
INFURA_API_KEY=your_infura_api_key
```

Replace each value with your actual secure credentials.

## 5. Set Up Gunicorn

### Test Gunicorn Service

```bash
gunicorn --bind 0.0.0.0:5000 wsgi:app
```

Press CTRL+C to exit after testing.

### Create Gunicorn Service File

```bash
sudo nano /etc/systemd/system/nvcbanking.service
```

Add the following content:

```
[Unit]
Description=NVC Banking Platform Gunicorn Service
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/nvcbanking
Environment="PATH=/var/www/nvcbanking/venv/bin"
EnvironmentFile=/var/www/nvcbanking/.env
ExecStart=/var/www/nvcbanking/venv/bin/gunicorn --workers 3 --bind 0.0.0.0:5000 wsgi:app
Restart=always

[Install]
WantedBy=multi-user.target
```

### Start and Enable Gunicorn Service

```bash
sudo systemctl start nvcbanking
sudo systemctl enable nvcbanking
sudo systemctl status nvcbanking
```

## 6. Configure Nginx

### Create Nginx Server Block

```bash
sudo nano /etc/nginx/sites-available/nvcbanking
```

Add the following configuration:

```
server {
    listen 80;
    server_name your_domain.com www.your_domain.com;

    location / {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static/ {
        alias /var/www/nvcbanking/static/;
    }
}
```

Replace `your_domain.com` with your actual domain name.

### Enable the Nginx Server Block

```bash
sudo ln -s /etc/nginx/sites-available/nvcbanking /etc/nginx/sites-enabled
sudo nginx -t
sudo systemctl restart nginx
```

## 7. Set Up SSL/TLS with Let's Encrypt

### Install Certbot

```bash
sudo apt install -y certbot python3-certbot-nginx
```

### Obtain and Install SSL Certificate

```bash
sudo certbot --nginx -d your_domain.com -d www.your_domain.com
```

Follow the prompts to complete the certificate installation.

## 8. Application Database Initialization

### Initialize the Database

```bash
cd /var/www/nvcbanking
source venv/bin/activate
python -c "from main import app, db; app.app_context().push(); db.create_all()"
```

## 9. Security Considerations

### Set Up Firewall

```bash
sudo ufw allow 'Nginx Full'
sudo ufw allow ssh
sudo ufw enable
```

### Secure PostgreSQL (Optional)

Edit the PostgreSQL configuration to restrict access:

```bash
sudo nano /etc/postgresql/14/main/pg_hba.conf
```

### Regular Backups

Set up regular database backups:

```bash
sudo -u postgres pg_dump nvcbanking > /backup/nvcbanking_$(date +%Y-%m-%d).sql
```

## 10. Monitoring and Maintenance

### Set Up Logging

Configure application logging to a file:

```bash
sudo mkdir -p /var/log/nvcbanking
sudo chown www-data:www-data /var/log/nvcbanking
```

Add proper logging configuration to your application.

### Restart Services After Updates

After updating application code:

```bash
cd /var/www/nvcbanking
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart nvcbanking
```

## Troubleshooting

- Check Gunicorn logs: `sudo journalctl -u nvcbanking`
- Check Nginx logs: `sudo tail -f /var/log/nginx/error.log`
- Check application logs in your configured log directory

## Important Notes

1. Store database backups in a secure off-server location
2. Regularly update all system packages with `sudo apt update && sudo apt upgrade`
3. Keep certificates renewed (Let's Encrypt will handle this automatically)
4. Monitor server performance and scale resources as needed