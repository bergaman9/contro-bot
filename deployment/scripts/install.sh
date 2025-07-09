#!/bin/bash

# Contro Bot Raspberry Pi 5 Installation Script
# This script installs and configures Contro Bot on Raspberry Pi 5

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
    exit 1
}

# Check if running on Raspberry Pi
check_raspberry_pi() {
    if [ ! -f /proc/device-tree/model ]; then
        error "This script is designed for Raspberry Pi. Exiting."
    fi
    
    model=$(cat /proc/device-tree/model)
    if [[ ! "$model" == *"Raspberry Pi 5"* ]]; then
        warn "This script is optimized for Raspberry Pi 5. Current model: $model"
        read -p "Continue anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
    log "Detected: $model"
}

# Update system
update_system() {
    log "Updating system packages..."
    sudo apt-get update -y
    sudo apt-get upgrade -y
    log "System updated successfully"
}

# Install Docker
install_docker() {
    log "Installing Docker..."
    
    # Remove old versions
    sudo apt-get remove -y docker docker-engine docker.io containerd runc || true
    
    # Install dependencies
    sudo apt-get install -y \
        ca-certificates \
        curl \
        gnupg \
        lsb-release
    
    # Add Docker's official GPG key
    sudo mkdir -p /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/debian/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    
    # Set up repository
    echo \
        "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian \
        $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    
    # Install Docker Engine
    sudo apt-get update -y
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    
    # Add user to docker group
    sudo usermod -aG docker $USER
    
    # Enable and start Docker
    sudo systemctl enable docker
    sudo systemctl start docker
    
    log "Docker installed successfully"
}

# Install Docker Compose
install_docker_compose() {
    log "Installing Docker Compose..."
    
    # Get latest version
    DOCKER_COMPOSE_VERSION=$(curl -s https://api.github.com/repos/docker/compose/releases/latest | grep -Po '"tag_name": "\K.*?(?=")')
    
    # Download and install
    sudo curl -L "https://github.com/docker/compose/releases/download/${DOCKER_COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
    
    # Create symlink
    sudo ln -sf /usr/local/bin/docker-compose /usr/bin/docker-compose
    
    log "Docker Compose installed successfully"
}

# Configure firewall
configure_firewall() {
    log "Configuring firewall..."
    
    # Install UFW if not installed
    sudo apt-get install -y ufw
    
    # Default policies
    sudo ufw default deny incoming
    sudo ufw default allow outgoing
    
    # Allow SSH
    sudo ufw allow ssh
    
    # Allow HTTP and HTTPS
    sudo ufw allow 80
    sudo ufw allow 443
    
    # Allow Grafana
    sudo ufw allow 3000
    
    # Enable firewall
    sudo ufw --force enable
    
    log "Firewall configured successfully"
}

# Install fail2ban
install_fail2ban() {
    log "Installing Fail2ban..."
    
    sudo apt-get install -y fail2ban
    
    # Create jail.local configuration
    sudo tee /etc/fail2ban/jail.local > /dev/null << EOF
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 5

[sshd]
enabled = true
port = ssh
logpath = /var/log/auth.log
maxretry = 3
EOF
    
    sudo systemctl enable fail2ban
    sudo systemctl start fail2ban
    
    log "Fail2ban installed and configured"
}

# Create directory structure
create_directories() {
    log "Creating directory structure..."
    
    mkdir -p ~/contro-bot/{logs,ssl,configs,monitoring}
    mkdir -p ~/contro-bot/monitoring/{prometheus,grafana}
    mkdir -p ~/contro-bot/deployment/{nginx,mongodb,redis}
    
    log "Directory structure created"
}

# Generate SSL certificate
generate_ssl() {
    log "Generating self-signed SSL certificate..."
    
    sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout ~/contro-bot/ssl/contro-bot.key \
        -out ~/contro-bot/ssl/contro-bot.crt \
        -subj "/C=TR/ST=Turkey/L=Istanbul/O=Contro Bot/CN=localhost"
    
    sudo chown $USER:$USER ~/contro-bot/ssl/*
    
    log "SSL certificate generated"
}

# Create environment file
create_env_file() {
    log "Creating environment configuration..."
    
    # Check if source .env exists in project directory
    SOURCE_ENV=""
    for possible_location in "$PROJECT_DIR/.env" "$(pwd)/.env" "$HOME/contro-bot/.env"; do
        if [ -f "$possible_location" ]; then
            SOURCE_ENV="$possible_location"
            break
        fi
    done
    
    if [ -n "$SOURCE_ENV" ]; then
        log "Found existing .env file at $SOURCE_ENV, copying to deployment location..."
        cp "$SOURCE_ENV" ~/contro-bot/.env
        
        # Update production-specific settings
        sed -i 's/BOT_ENV=development/BOT_ENV=production/g' ~/contro-bot/.env 2>/dev/null || true
        
        # Add Docker MongoDB settings if not present
        if ! grep -q "MONGO_USERNAME" ~/contro-bot/.env; then
            cat >> ~/contro-bot/.env << EOF

# MongoDB Docker Configuration (added by installer)
MONGO_USERNAME=root
MONGO_PASSWORD=password
EOF
        fi
        
        log "Existing .env file copied and configured for production"
    else
        log "No existing .env file found, creating template..."
        cat > ~/contro-bot/.env << EOF
# Discord Bot Configuration
CONTRO_MAIN_TOKEN=your_main_token_here
CONTRO_DEV_TOKEN=your_dev_token_here
CONTRO_PREMIUM_TOKEN=your_premium_token_here

# Admin Configuration
ADMIN_USER_ID=your_discord_user_id_here
AUTHORIZATION=your_authorization_token_here

# Database Configuration
DB=contro-bot-db
MONGO_DB=mongodb://root:password@mongodb:27017/contro-bot-db?authSource=admin

# MongoDB Docker Configuration
MONGO_USERNAME=root
MONGO_PASSWORD=password

# AI Integration
PERPLEXITY_API_KEY=your_perplexity_api_key_here
OPENAI_API_KEY=your_openai_api_key_here

# Monitoring
GRAFANA_PASSWORD=admin

# Bot Configuration
BOT_ENV=production
DEFAULT_PREFIX=>
LOG_LEVEL=INFO

# Deployment Configuration
MEMORY_LIMIT=1G
CPU_LIMIT=2.0
EOF
        error "Template .env file created at ~/contro-bot/.env. Please edit it with your actual tokens and API keys before deployment!"
    fi
}

# Create systemd service
create_systemd_service() {
    log "Creating systemd service..."
    
    sudo tee /etc/systemd/system/contro-bot.service > /dev/null << EOF
[Unit]
Description=Contro Discord Bot
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/home/$USER/contro-bot
ExecStart=/usr/local/bin/docker-compose -f deployment/docker/docker-compose.pi.yml up -d
ExecStop=/usr/local/bin/docker-compose -f deployment/docker/docker-compose.pi.yml down
TimeoutStartSec=0
User=$USER
Group=$USER

[Install]
WantedBy=multi-user.target
EOF
    
    sudo systemctl daemon-reload
    sudo systemctl enable contro-bot.service
    
    log "Systemd service created and enabled"
}

# Setup log rotation
setup_log_rotation() {
    log "Setting up log rotation..."
    
    sudo tee /etc/logrotate.d/contro-bot > /dev/null << EOF
/home/$USER/contro-bot/logs/*.log {
    daily
    missingok
    rotate 7
    compress
    delaycompress
    notifempty
    create 644 $USER $USER
    postrotate
        docker restart contro-bot 2>/dev/null || true
    endscript
}
EOF
    
    log "Log rotation configured"
}

# Setup monitoring
setup_monitoring() {
    log "Setting up monitoring configuration..."
    
    # Prometheus configuration
    cat > ~/contro-bot/monitoring/prometheus/prometheus.yml << EOF
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'contro-bot'
    static_configs:
      - targets: ['contro-bot:9090']
    scrape_interval: 5s
    metrics_path: /metrics

  - job_name: 'node-exporter'
    static_configs:
      - targets: ['localhost:9100']
EOF
    
    log "Monitoring configuration created"
}

# Install additional tools
install_tools() {
    log "Installing additional tools..."
    
    sudo apt-get install -y \
        htop \
        iotop \
        nethogs \
        ncdu \
        tree \
        git \
        nano \
        curl \
        wget \
        unzip
    
    log "Additional tools installed"
}

# Performance optimization
optimize_performance() {
    log "Applying Raspberry Pi performance optimizations..."
    
    # GPU memory split
    if ! grep -q "gpu_mem=" /boot/config.txt; then
        echo "gpu_mem=16" | sudo tee -a /boot/config.txt
    fi
    
    # Disable unnecessary services
    sudo systemctl disable bluetooth
    sudo systemctl disable hciuart
    
    # Set CPU governor to performance
    echo 'GOVERNOR="performance"' | sudo tee /etc/default/cpufrequtils
    
    log "Performance optimizations applied"
}

# Main installation function
main() {
    log "Starting Contro Bot installation on Raspberry Pi 5..."
    
    check_raspberry_pi
    update_system
    install_docker
    install_docker_compose
    configure_firewall
    install_fail2ban
    create_directories
    generate_ssl
    create_env_file
    create_systemd_service
    setup_log_rotation
    setup_monitoring
    install_tools
    optimize_performance
    
    log "Installation completed successfully!"
    log ""
    log "Next steps:"
    log "1. Edit ~/contro-bot/.env with your actual tokens"
    log "2. Clone the bot repository to ~/contro-bot/"
    log "3. Start the bot: sudo systemctl start contro-bot"
    log "4. Check status: sudo systemctl status contro-bot"
    log "5. View logs: docker logs contro-bot"
    log ""
    log "Monitoring:"
    log "- Grafana: http://your-pi-ip:3000 (admin/admin)"
    log "- Prometheus: http://your-pi-ip:9091"
    log ""
    warn "Please reboot your Raspberry Pi to apply all changes"
}

# Run main function
main "$@" 