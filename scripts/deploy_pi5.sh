#!/bin/bash

# CONTRO Bot - Raspberry Pi 5 Deployment Script
# Advanced deployment and management script for Raspberry Pi 5

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
BOT_NAME="contro-bot"
BOT_DIR="/home/pi/contro-project/bot"
PYTHON_VERSION="3.11"
MONGODB_VERSION="7.0"
SERVICE_NAME="contro-bot"

# Functions
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_raspberry_pi() {
    print_status "Checking if running on Raspberry Pi..."
    if ! grep -q "Raspberry Pi" /proc/cpuinfo; then
        print_error "This script is designed for Raspberry Pi systems"
        exit 1
    fi
    
    # Check if it's Pi 5
    if grep -q "Raspberry Pi 5" /proc/cpuinfo; then
        print_success "Raspberry Pi 5 detected - optimizations will be applied"
        PI_VERSION="5"
    else
        print_warning "Not Raspberry Pi 5 - some optimizations may not apply"
        PI_VERSION="other"
    fi
}

update_system() {
    print_status "Updating system packages..."
    sudo apt update
    sudo apt upgrade -y
    print_success "System updated"
}

install_python() {
    print_status "Installing Python ${PYTHON_VERSION}..."
    
    # Install Python and pip
    sudo apt install -y python${PYTHON_VERSION} python${PYTHON_VERSION}-pip python${PYTHON_VERSION}-venv
    
    # Create symlinks if needed
    if ! command -v python3 &> /dev/null; then
        sudo ln -sf /usr/bin/python${PYTHON_VERSION} /usr/bin/python3
    fi
    
    if ! command -v pip3 &> /dev/null; then
        sudo ln -sf /usr/bin/pip${PYTHON_VERSION} /usr/bin/pip3
    fi
    
    print_success "Python ${PYTHON_VERSION} installed"
}

install_mongodb() {
    print_status "Installing MongoDB..."
    
    # Import MongoDB public GPG key
    wget -qO - https://www.mongodb.org/static/pgp/server-${MONGODB_VERSION}.asc | sudo apt-key add -
    
    # Add MongoDB repository
    echo "deb [ arch=arm64 ] https://repo.mongodb.org/apt/ubuntu focal/mongodb-org/${MONGODB_VERSION} multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-${MONGODB_VERSION}.list
    
    sudo apt update
    sudo apt install -y mongodb-org
    
    # Enable and start MongoDB
    sudo systemctl enable mongod
    sudo systemctl start mongod
    
    print_success "MongoDB installed and started"
}

optimize_pi5() {
    if [ "$PI_VERSION" = "5" ]; then
        print_status "Applying Raspberry Pi 5 optimizations..."
        
        # Memory optimization
        echo 'vm.swappiness=10' | sudo tee -a /etc/sysctl.conf
        echo 'vm.vfs_cache_pressure=50' | sudo tee -a /etc/sysctl.conf
        
        # Network optimization
        echo 'net.core.rmem_max = 134217728' | sudo tee -a /etc/sysctl.conf
        echo 'net.core.wmem_max = 134217728' | sudo tee -a /etc/sysctl.conf
        
        # GPU memory split (reduce GPU memory for more system RAM)
        if ! grep -q "gpu_mem" /boot/config.txt; then
            echo 'gpu_mem=64' | sudo tee -a /boot/config.txt
        fi
        
        # Enable performance governor
        echo 'performance' | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor
        
        print_success "Pi 5 optimizations applied"
    fi
}

setup_bot_directory() {
    print_status "Setting up bot directory..."
    
    # Create directory if it doesn't exist
    mkdir -p "$BOT_DIR"
    cd "$BOT_DIR"
    
    # Set proper permissions
    sudo chown -R pi:pi "$BOT_DIR"
    
    print_success "Bot directory setup complete"
}

install_bot_dependencies() {
    print_status "Installing bot dependencies..."
    
    cd "$BOT_DIR"
    
    # Create virtual environment
    python3 -m venv venv
    source venv/bin/activate
    
    # Upgrade pip
    pip install --upgrade pip
    
    # Install dependencies
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt
    else
        print_warning "requirements.txt not found, installing basic dependencies"
        pip install discord.py pymongo pillow aiohttp python-dotenv
    fi
    
    print_success "Bot dependencies installed"
}

create_systemd_service() {
    print_status "Creating systemd service..."
    
    # Create service file
    sudo tee /etc/systemd/system/${SERVICE_NAME}.service > /dev/null <<EOF
[Unit]
Description=CONTRO Discord Bot
After=network.target mongodb.service
Wants=mongodb.service

[Service]
Type=simple
User=pi
Group=pi
WorkingDirectory=${BOT_DIR}
Environment=PATH=${BOT_DIR}/venv/bin
ExecStart=${BOT_DIR}/venv/bin/python main.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=${SERVICE_NAME}

# Resource limits
LimitNOFILE=65536
MemoryMax=1G

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=${BOT_DIR}

[Install]
WantedBy=multi-user.target
EOF
    
    # Reload systemd and enable service
    sudo systemctl daemon-reload
    sudo systemctl enable ${SERVICE_NAME}
    
    print_success "Systemd service created and enabled"
}

setup_log_rotation() {
    print_status "Setting up log rotation..."
    
    # Create logrotate configuration
    sudo tee /etc/logrotate.d/${SERVICE_NAME} > /dev/null <<EOF
${BOT_DIR}/logs/*.log {
    daily
    missingok
    rotate 7
    compress
    delaycompress
    notifempty
    create 644 pi pi
    postrotate
        systemctl reload ${SERVICE_NAME} 2>/dev/null || true
    endscript
}
EOF
    
    print_success "Log rotation configured"
}

create_backup_script() {
    print_status "Creating backup script..."
    
    # Create backup directory
    mkdir -p /home/pi/backups
    
    # Create backup script
    tee /home/pi/backup-contro.sh > /dev/null <<'EOF'
#!/bin/bash

# CONTRO Bot Backup Script
BACKUP_DIR="/home/pi/backups"
BOT_DIR="/home/pi/contro-project/bot"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="contro_backup_${DATE}"

# Create backup
mkdir -p "${BACKUP_DIR}/${BACKUP_NAME}"

# Backup bot files
cp -r "${BOT_DIR}" "${BACKUP_DIR}/${BACKUP_NAME}/"

# Backup MongoDB (if running)
if systemctl is-active --quiet mongod; then
    mongodump --out "${BACKUP_DIR}/${BACKUP_NAME}/mongodb_backup"
fi

# Create archive
cd "${BACKUP_DIR}"
tar -czf "${BACKUP_NAME}.tar.gz" "${BACKUP_NAME}"
rm -rf "${BACKUP_NAME}"

# Keep only last 7 backups
ls -t *.tar.gz | tail -n +8 | xargs -r rm

echo "Backup completed: ${BACKUP_NAME}.tar.gz"
EOF
    
    chmod +x /home/pi/backup-contro.sh
    
    # Add to crontab for daily backups
    (crontab -l 2>/dev/null; echo "0 2 * * * /home/pi/backup-contro.sh") | crontab -
    
    print_success "Backup script created and scheduled"
}

setup_monitoring() {
    print_status "Setting up monitoring..."
    
    # Create monitoring script
    tee /home/pi/monitor-contro.sh > /dev/null <<'EOF'
#!/bin/bash

# CONTRO Bot Monitoring Script
SERVICE_NAME="contro-bot"
LOG_FILE="/home/pi/monitor.log"

# Check if service is running
if ! systemctl is-active --quiet ${SERVICE_NAME}; then
    echo "[$(date)] Service ${SERVICE_NAME} is not running. Attempting restart..." >> ${LOG_FILE}
    sudo systemctl restart ${SERVICE_NAME}
    sleep 10
    
    if systemctl is-active --quiet ${SERVICE_NAME}; then
        echo "[$(date)] Service ${SERVICE_NAME} restarted successfully" >> ${LOG_FILE}
    else
        echo "[$(date)] Failed to restart ${SERVICE_NAME}" >> ${LOG_FILE}
    fi
fi

# Check memory usage
MEMORY_USAGE=$(ps -o pid,ppid,%mem,%cpu,comm -p $(pgrep -f "python.*main.py") | tail -n 1 | awk '{print $3}')
if (( $(echo "$MEMORY_USAGE > 80" | bc -l) )); then
    echo "[$(date)] High memory usage detected: ${MEMORY_USAGE}%" >> ${LOG_FILE}
fi
EOF
    
    chmod +x /home/pi/monitor-contro.sh
    
    # Add to crontab for monitoring every 5 minutes
    (crontab -l 2>/dev/null; echo "*/5 * * * * /home/pi/monitor-contro.sh") | crontab -
    
    print_success "Monitoring script created and scheduled"
}

create_update_script() {
    print_status "Creating update script..."
    
    tee /home/pi/update-contro.sh > /dev/null <<'EOF'
#!/bin/bash

# CONTRO Bot Update Script
BOT_DIR="/home/pi/contro-project/bot"
SERVICE_NAME="contro-bot"

cd "${BOT_DIR}"

# Backup current version
/home/pi/backup-contro.sh

# Pull latest changes
git pull origin main

# Update dependencies
source venv/bin/activate
pip install -r requirements.txt --upgrade

# Restart service
sudo systemctl restart ${SERVICE_NAME}

# Check if service started successfully
sleep 5
if systemctl is-active --quiet ${SERVICE_NAME}; then
    echo "Update completed successfully"
    echo "Service status: $(systemctl is-active ${SERVICE_NAME})"
else
    echo "Update failed - service not running"
    exit 1
fi
EOF
    
    chmod +x /home/pi/update-contro.sh
    
    print_success "Update script created"
}

show_management_commands() {
    print_success "Deployment completed! Here are the management commands:"
    echo ""
    echo -e "${BLUE}Service Management:${NC}"
    echo "  sudo systemctl start ${SERVICE_NAME}     # Start the bot"
    echo "  sudo systemctl stop ${SERVICE_NAME}      # Stop the bot"
    echo "  sudo systemctl restart ${SERVICE_NAME}   # Restart the bot"
    echo "  sudo systemctl status ${SERVICE_NAME}    # Check bot status"
    echo ""
    echo -e "${BLUE}Logs:${NC}"
    echo "  sudo journalctl -u ${SERVICE_NAME} -f    # Follow live logs"
    echo "  sudo journalctl -u ${SERVICE_NAME} -n 50 # Show last 50 log entries"
    echo ""
    echo -e "${BLUE}Maintenance:${NC}"
    echo "  /home/pi/backup-contro.sh                # Manual backup"
    echo "  /home/pi/update-contro.sh                # Update bot"
    echo "  /home/pi/monitor-contro.sh               # Manual health check"
    echo ""
    echo -e "${BLUE}Configuration Files:${NC}"
    echo "  ${BOT_DIR}/.env                         # Environment variables"
    echo "  ${BOT_DIR}/config/version_config.json   # Version control config"
    echo ""
}

# Main deployment process
main() {
    print_status "Starting CONTRO Bot deployment for Raspberry Pi 5..."
    
    check_raspberry_pi
    update_system
    install_python
    install_mongodb
    optimize_pi5
    setup_bot_directory
    install_bot_dependencies
    create_systemd_service
    setup_log_rotation
    create_backup_script
    setup_monitoring
    create_update_script
    
    show_management_commands
    
    print_success "CONTRO Bot deployment completed successfully!"
    print_status "You can now start the bot with: sudo systemctl start ${SERVICE_NAME}"
}

# Run main function
main "$@"
