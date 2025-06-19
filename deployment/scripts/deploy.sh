#!/bin/bash

# Contro Bot Production Deployment Script
# Deploys the bot to Raspberry Pi 5 with full monitoring stack

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_DIR="$HOME/contro-bot"
BACKUP_DIR="$HOME/contro-bot-backups"
LOG_FILE="$PROJECT_DIR/logs/deployment.log"

# Logging function
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}" | tee -a "$LOG_FILE"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}" | tee -a "$LOG_FILE"
    exit 1
}

# Check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."
    
    # Check if Docker is installed
    if ! command -v docker &> /dev/null; then
        error "Docker is not installed. Please run install.sh first."
    fi
    
    # Check if Docker Compose is installed
    if ! command -v docker-compose &> /dev/null; then
        error "Docker Compose is not installed. Please run install.sh first."
    fi
    
    # Check if environment file exists
    ENV_FILE=""
    for env_location in "$PROJECT_DIR/.env" "$(pwd)/.env" "$HOME/contro-bot/.env"; do
        if [ -f "$env_location" ]; then
            ENV_FILE="$env_location"
            log "Found environment file at: $env_location"
            break
        fi
    done
    
    if [ -z "$ENV_FILE" ]; then
        error "Environment file (.env) not found. Please create one from .env.example"
    fi
    
    # Check if required tokens are set
    if ! grep -q "CONTRO_MAIN_TOKEN=" "$ENV_FILE" || grep -q "your_.*_token_here" "$ENV_FILE"; then
        error "Discord tokens not configured in .env file. Please update $ENV_FILE"
    fi
    
    log "Prerequisites check passed"
}

# Create backup
create_backup() {
    log "Creating backup..."
    
    mkdir -p "$BACKUP_DIR"
    BACKUP_NAME="backup-$(date +'%Y%m%d-%H%M%S')"
    BACKUP_PATH="$BACKUP_DIR/$BACKUP_NAME"
    
    # Create backup directory
    mkdir -p "$BACKUP_PATH"
    
    # Backup configuration files
    if [ -f "$PROJECT_DIR/.env" ]; then
        cp "$PROJECT_DIR/.env" "$BACKUP_PATH/"
    fi
    
    # Backup logs (last 7 days)
    if [ -d "$PROJECT_DIR/logs" ]; then
        find "$PROJECT_DIR/logs" -name "*.log" -mtime -7 -exec cp {} "$BACKUP_PATH/" \;
    fi
    
    # Backup database (if running locally)
    if docker ps | grep -q contro-mongodb; then
        log "Backing up MongoDB..."
        docker exec contro-mongodb mongodump --out /tmp/backup
        docker cp contro-mongodb:/tmp/backup "$BACKUP_PATH/mongodb/"
    fi
    
    # Compress backup
    cd "$BACKUP_DIR"
    tar -czf "$BACKUP_NAME.tar.gz" "$BACKUP_NAME"
    rm -rf "$BACKUP_NAME"
    
    log "Backup created: $BACKUP_NAME.tar.gz"
    
    # Keep only last 10 backups
    ls -t backup-*.tar.gz | tail -n +11 | xargs -r rm
}

# Pull latest code
pull_code() {
    log "Pulling latest code..."
    
    cd "$PROJECT_DIR"
    
    # Check if git repository exists
    if [ ! -d ".git" ]; then
        warn "Not a git repository. Skipping code pull."
        return
    fi
    
    # Save current branch
    CURRENT_BRANCH=$(git branch --show-current)
    
    # Stash any local changes
    git stash push -m "Deployment stash $(date)"
    
    # Pull latest changes
    git fetch origin
    git pull origin "$CURRENT_BRANCH"
    
    log "Code updated to latest version"
}

# Build Docker images
build_images() {
    log "Building Docker images..."
    
    cd "$PROJECT_DIR"
    
    # Build ARM64 image
    docker build -t contro-bot:latest -f deployment/docker/Dockerfile.arm64 .
    
    # Tag with timestamp
    TIMESTAMP=$(date +'%Y%m%d-%H%M%S')
    docker tag contro-bot:latest "contro-bot:$TIMESTAMP"
    
    log "Docker images built successfully"
}

# Update configuration
update_config() {
    log "Updating configuration..."
    
    # Create necessary directories
    mkdir -p "$PROJECT_DIR"/{logs,ssl,monitoring/prometheus,monitoring/grafana}
    
    # Copy environment file to deployment location if different
    if [ "$ENV_FILE" != "$PROJECT_DIR/.env" ]; then
        log "Copying environment file to project directory..."
        cp "$ENV_FILE" "$PROJECT_DIR/.env"
    fi
    
    # Update production-specific settings in deployment .env
    if [ -f "$PROJECT_DIR/.env" ]; then
        # Create backup
        cp "$PROJECT_DIR/.env" "$PROJECT_DIR/.env.backup"
        
        # Update for production deployment
        sed -i 's/BOT_ENV=development/BOT_ENV=production/g' "$PROJECT_DIR/.env" 2>/dev/null || true
        
        # Add Docker-specific MongoDB settings if not present
        if ! grep -q "MONGO_USERNAME" "$PROJECT_DIR/.env"; then
            cat >> "$PROJECT_DIR/.env" << EOF

# Docker MongoDB Configuration (added by deployment)
MONGO_USERNAME=root
MONGO_PASSWORD=password
EOF
        fi
        
        log "Environment file configured for production deployment"
    fi
    
    # Set proper permissions
    sudo chown -R $USER:$USER "$PROJECT_DIR"
    chmod 755 "$PROJECT_DIR"
    chmod 600 "$PROJECT_DIR/.env"  # Secure the .env file
    
    # Create Prometheus config if not exists
    if [ ! -f "$PROJECT_DIR/monitoring/prometheus/prometheus.yml" ]; then
        cat > "$PROJECT_DIR/monitoring/prometheus/prometheus.yml" << EOF
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'contro-bot'
    static_configs:
      - targets: ['contro-bot:9090']
    scrape_interval: 5s
    metrics_path: /metrics

  - job_name: 'node-exporter'
    static_configs:
      - targets: ['localhost:9100']
    scrape_interval: 15s

  - job_name: 'mongodb'
    static_configs:
      - targets: ['contro-mongodb:27017']
    scrape_interval: 30s

  - job_name: 'redis'
    static_configs:
      - targets: ['contro-redis:6379']
    scrape_interval: 30s
EOF
    fi
    
    log "Configuration updated"
}

# Deploy services
deploy_services() {
    log "Deploying services..."
    
    cd "$PROJECT_DIR"
    
    # Stop existing services
    if [ -f "deployment/docker/docker-compose.pi.yml" ]; then
        docker-compose -f deployment/docker/docker-compose.pi.yml down
    fi
    
    # Start services with new configuration
    docker-compose -f deployment/docker/docker-compose.pi.yml up -d
    
    log "Services deployed successfully"
}

# Wait for services to be ready
wait_for_services() {
    log "Waiting for services to be ready..."
    
    # Wait for MongoDB
    log "Waiting for MongoDB..."
    timeout=60
    counter=0
    while ! docker exec contro-mongodb mongosh --eval "db.runCommand('ping')" &>/dev/null; do
        if [ $counter -ge $timeout ]; then
            error "MongoDB failed to start within $timeout seconds"
        fi
        sleep 2
        ((counter += 2))
    done
    log "MongoDB is ready"
    
    # Wait for Redis
    log "Waiting for Redis..."
    timeout=30
    counter=0
    while ! docker exec contro-redis redis-cli ping &>/dev/null; do
        if [ $counter -ge $timeout ]; then
            error "Redis failed to start within $timeout seconds"
        fi
        sleep 1
        ((counter += 1))
    done
    log "Redis is ready"
    
    # Wait for bot
    log "Waiting for bot..."
    timeout=120
    counter=0
    while ! curl -sf http://localhost:8080/health &>/dev/null; do
        if [ $counter -ge $timeout ]; then
            error "Bot failed to start within $timeout seconds"
        fi
        sleep 2
        ((counter += 2))
    done
    log "Bot is ready"
    
    # Wait for Grafana
    log "Waiting for Grafana..."
    timeout=60
    counter=0
    while ! curl -sf http://localhost:3000/api/health &>/dev/null; do
        if [ $counter -ge $timeout ]; then
            warn "Grafana failed to start within $timeout seconds"
            break
        fi
        sleep 2
        ((counter += 2))
    done
    
    if [ $counter -lt $timeout ]; then
        log "Grafana is ready"
    fi
}

# Run health checks
run_health_checks() {
    log "Running health checks..."
    
    # Check bot health
    if curl -sf http://localhost:8080/health > /dev/null; then
        log "✅ Bot health check passed"
    else
        error "❌ Bot health check failed"
    fi
    
    # Check API
    if curl -sf http://localhost:8000/api/health > /dev/null; then
        log "✅ API health check passed"
    else
        warn "⚠️ API health check failed"
    fi
    
    # Check database connection
    if docker exec contro-bot python -c "
import asyncio
import sys
sys.path.append('/app')
from src.database.connection import get_database
async def test():
    try:
        db = await get_database()
        await db.admin.command('ping')
        print('Database connection successful')
    except Exception as e:
        print(f'Database connection failed: {e}')
        sys.exit(1)
asyncio.run(test())
" 2>/dev/null; then
        log "✅ Database connection check passed"
    else
        error "❌ Database connection check failed"
    fi
    
    # Check Discord connection
    sleep 10  # Wait for bot to fully initialize
    if docker logs contro-bot 2>&1 | grep -q "Bot is ready"; then
        log "✅ Discord connection check passed"
    else
        error "❌ Discord connection check failed"
    fi
}

# Setup monitoring
setup_monitoring() {
    log "Setting up monitoring..."
    
    # Check if Prometheus is accessible
    if curl -sf http://localhost:9091/api/v1/status/config > /dev/null; then
        log "✅ Prometheus is running"
    else
        warn "⚠️ Prometheus is not accessible"
    fi
    
    # Check if Grafana is accessible
    if curl -sf http://localhost:3000/api/health > /dev/null; then
        log "✅ Grafana is running"
    else
        warn "⚠️ Grafana is not accessible"
    fi
    
    log "Monitoring setup completed"
}

# Performance optimization
optimize_performance() {
    log "Applying performance optimizations..."
    
    # Set Docker daemon settings for Raspberry Pi
    if [ ! -f "/etc/docker/daemon.json" ]; then
        sudo tee /etc/docker/daemon.json > /dev/null << EOF
{
    "log-driver": "json-file",
    "log-opts": {
        "max-size": "10m",
        "max-file": "3"
    },
    "storage-driver": "overlay2",
    "experimental": false
}
EOF
        sudo systemctl restart docker
        log "Docker daemon optimized"
    fi
    
    # Set container memory limits
    docker update --memory=1g --memory-swap=1g contro-bot
    docker update --memory=512m --memory-swap=512m contro-mongodb
    docker update --memory=128m --memory-swap=128m contro-redis
    
    log "Performance optimizations applied"
}

# Display deployment summary
show_summary() {
    log "Deployment completed successfully! 🎉"
    log ""
    log "=== DEPLOYMENT SUMMARY ==="
    log "Bot Status: $(docker ps --filter name=contro-bot --format 'table {{.Status}}')"
    log "Database Status: $(docker ps --filter name=contro-mongodb --format 'table {{.Status}}')"
    log "Cache Status: $(docker ps --filter name=contro-redis --format 'table {{.Status}}')"
    log ""
    log "=== ACCESS INFORMATION ==="
    log "Bot API: http://localhost:8000"
    log "Health Check: http://localhost:8080/health"
    log "Metrics: http://localhost:9090/metrics"
    log "Grafana: http://localhost:3000 (admin/admin)"
    log "Prometheus: http://localhost:9091"
    log ""
    log "=== USEFUL COMMANDS ==="
    log "View logs: docker logs -f contro-bot"
    log "Restart bot: docker restart contro-bot"
    log "Stop all: docker-compose -f deployment/docker/docker-compose.pi.yml down"
    log "System status: systemctl status contro-bot"
    log ""
    log "=== MONITORING ==="
    log "Check system resources: htop"
    log "Monitor Docker: docker stats"
    log "Check disk usage: df -h"
    log ""
    
    # Display system information
    log "=== SYSTEM INFORMATION ==="
    log "CPU Temperature: $(vcgencmd measure_temp 2>/dev/null || echo 'N/A')"
    log "Memory Usage: $(free -h | grep Mem | awk '{print $3 "/" $2}')"
    log "Disk Usage: $(df -h / | tail -1 | awk '{print $3 "/" $2 " (" $5 " used)"}')"
    log "Load Average: $(uptime | awk -F'load average:' '{print $2}')"
}

# Main deployment function
main() {
    log "Starting Contro Bot deployment..."
    
    # Ensure log directory exists
    mkdir -p "$(dirname "$LOG_FILE")"
    
    check_prerequisites
    create_backup
    pull_code
    build_images
    update_config
    deploy_services
    wait_for_services
    run_health_checks
    setup_monitoring
    optimize_performance
    show_summary
    
    log "Deployment process completed successfully!"
}

# Handle script interruption
trap 'error "Deployment interrupted"' INT TERM

# Run main function
main "$@" 