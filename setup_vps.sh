#!/bin/bash

# This script sets up a Ubuntu VPS for the NVC Banking Platform

# Exit on error
set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting NVC Banking Platform VPS setup...${NC}"

# Update system
echo -e "${GREEN}Updating system packages...${NC}"
sudo apt update
sudo apt upgrade -y

# Install dependencies
echo -e "${GREEN}Installing required system dependencies...${NC}"
sudo apt install -y \
    python3-pip \
    python3-dev \
    python3-venv \
    build-essential \
    libssl-dev \
    libffi-dev \
    git \
    nginx \
    postgresql \
    postgresql-contrib \
    ufw \
    curl \
    certbot \
    python3-certbot-nginx

# Set up PostgreSQL
echo -e "${GREEN}Setting up PostgreSQL database...${NC}"
sudo -u postgres psql -c "CREATE DATABASE nvcbanking;" || echo "Database may already exist"
sudo -u postgres psql -c "CREATE USER nvcadmin WITH PASSWORD 'changeme';" || echo "User may already exist"
sudo -u postgres psql -c "ALTER ROLE nvcadmin SET client_encoding TO 'utf8';"
sudo -u postgres psql -c "ALTER ROLE nvcadmin SET default_transaction_isolation TO 'read committed';"
sudo -u postgres psql -c "ALTER ROLE nvcadmin SET timezone TO 'UTC';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE nvcbanking TO nvcadmin;"

# Create application directory
echo -e "${GREEN}Creating application directory...${NC}"
sudo mkdir -p /var/www/nvcbanking
sudo chown $USER:$USER /var/www/nvcbanking

# Set up Python virtual environment
echo -e "${GREEN}Setting up Python virtual environment...${NC}"
cd /var/www/nvcbanking
python3 -m venv venv
source venv/bin/activate

# Create a sample .env file
echo -e "${GREEN}Creating sample .env file...${NC}"
cat > /var/www/nvcbanking/.env.sample << EOL
DATABASE_URL=postgresql://nvcadmin:changeme@localhost/nvcbanking
FLASK_SECRET_KEY=change_this_to_a_secure_random_string
SESSION_SECRET=change_this_to_another_secure_random_string
STRIPE_SECRET_KEY=your_stripe_secret_key
PAYPAL_CLIENT_ID=your_paypal_client_id
PAYPAL_CLIENT_SECRET=your_paypal_client_secret
INFURA_API_KEY=your_infura_api_key
SENDGRID_API_KEY=your_sendgrid_api_key
EOL

# Set up Gunicorn service
echo -e "${GREEN}Setting up Gunicorn service...${NC}"
cat > /tmp/nvcbanking.service << EOL
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
EOL

sudo mv /tmp/nvcbanking.service /etc/systemd/system/

# Set up Nginx configuration
echo -e "${GREEN}Setting up Nginx configuration...${NC}"
cat > /tmp/nvcbanking << EOL
server {
    listen 80;
    server_name nvcbanking.example.com;  # CHANGE THIS TO YOUR DOMAIN

    location / {
        proxy_pass http://localhost:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location /static/ {
        alias /var/www/nvcbanking/static/;
    }
}
EOL

sudo mv /tmp/nvcbanking /etc/nginx/sites-available/
sudo ln -sf /etc/nginx/sites-available/nvcbanking /etc/nginx/sites-enabled/

# Configure UFW
echo -e "${GREEN}Configuring firewall...${NC}"
sudo ufw allow 'Nginx Full'
sudo ufw allow ssh
echo "y" | sudo ufw enable || echo "Firewall may already be enabled"

# Print final instructions
echo -e "${GREEN}=======================================================${NC}"
echo -e "${GREEN}VPS setup complete! Follow these steps to finish deployment:${NC}"
echo -e "${GREEN}=======================================================${NC}"
echo ""
echo "1. Edit the Nginx configuration to use your domain name:"
echo "   sudo nano /etc/nginx/sites-available/nvcbanking"
echo ""
echo "2. Create and configure your .env file:"
echo "   cp /var/www/nvcbanking/.env.sample /var/www/nvcbanking/.env"
echo "   nano /var/www/nvcbanking/.env"
echo ""
echo "3. Upload your application files to /var/www/nvcbanking"
echo ""
echo "4. Set proper permissions:"
echo "   sudo chown -R www-data:www-data /var/www/nvcbanking"
echo ""
echo "5. Start the services:"
echo "   sudo systemctl daemon-reload"
echo "   sudo systemctl start nvcbanking"
echo "   sudo systemctl enable nvcbanking"
echo "   sudo systemctl restart nginx"
echo ""
echo "6. Set up SSL with Let's Encrypt:"
echo "   sudo certbot --nginx -d yourdomain.com"
echo ""
echo -e "${RED}IMPORTANT: Change the sample password in .env file and PostgreSQL!${NC}"