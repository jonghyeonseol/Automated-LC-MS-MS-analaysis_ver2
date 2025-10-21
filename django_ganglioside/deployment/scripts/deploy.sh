#!/bin/bash
###############################################################################
# Production Deployment Script
# Ganglioside Analysis Platform
###############################################################################

set -e  # Exit on error

echo "=========================================="
echo "Ganglioside Deployment Script"
echo "=========================================="

# Configuration
APP_DIR="/var/www/ganglioside"
VENV_DIR="$APP_DIR/venv"
USER="ganglioside"
GROUP="ganglioside"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

step() {
    echo -e "${GREEN}[STEP]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    error "Please run as root (use sudo)"
fi

step "1. Pulling latest code from repository..."
cd "$APP_DIR"
sudo -u "$USER" git pull origin main || error "Git pull failed"

step "2. Activating virtual environment..."
source "$VENV_DIR/bin/activate"

step "3. Installing/updating dependencies..."
sudo -u "$USER" "$VENV_DIR/bin/pip" install -r requirements/production.txt || error "Dependency installation failed"

step "4. Collecting static files..."
sudo -u "$USER" DJANGO_SETTINGS_MODULE=config.settings.production \
    "$VENV_DIR/bin/python" manage.py collectstatic --noinput || error "Collectstatic failed"

step "5. Running database migrations..."
sudo -u "$USER" DJANGO_SETTINGS_MODULE=config.settings.production \
    "$VENV_DIR/bin/python" manage.py migrate --noinput || error "Migration failed"

step "6. Restarting services..."
systemctl restart ganglioside-django.service
systemctl restart ganglioside-daphne.service
systemctl restart ganglioside-celery-worker.service
systemctl restart ganglioside-celery-beat.service

step "7. Checking service status..."
sleep 2

services=(
    "ganglioside-django"
    "ganglioside-daphne"
    "ganglioside-celery-worker"
    "ganglioside-celery-beat"
)

all_ok=true
for service in "${services[@]}"; do
    if systemctl is-active --quiet "$service.service"; then
        echo -e "  ✓ $service: ${GREEN}RUNNING${NC}"
    else
        echo -e "  ✗ $service: ${RED}FAILED${NC}"
        all_ok=false
    fi
done

if [ "$all_ok" = false ]; then
    error "Some services failed to start. Check logs with: journalctl -u ganglioside-* -n 50"
fi

step "8. Reloading Nginx..."
nginx -t && systemctl reload nginx || error "Nginx reload failed"

echo ""
echo "=========================================="
echo -e "${GREEN}Deployment completed successfully!${NC}"
echo "=========================================="
echo ""
echo "Service URLs:"
echo "  - Application: https://your-domain.com"
echo "  - Health Check: https://your-domain.com/health"
echo ""
echo "Logs:"
echo "  - Django: journalctl -u ganglioside-django -f"
echo "  - Celery: tail -f /var/log/celery/ganglioside_worker.log"
echo "  - Nginx: tail -f /var/log/nginx/ganglioside_access.log"
echo ""
