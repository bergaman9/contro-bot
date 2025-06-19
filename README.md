# 🤖 Contro Discord Bot

A powerful, modular Discord bot built for scalability and advanced features. Now with AI-powered server design and comprehensive security framework.

## 🚀 Features

### ✅ Core Features (Completed)
- **🛡️ Advanced Moderation System** - Comprehensive moderation tools with AI assistance
- **👋 Welcome & Goodbye System** - Customizable welcome/goodbye with dynamic images
- **📈 Leveling & XP System** - Advanced XP system with voice chat tracking
- **🎟️ Ticket System** - Professional support ticket management
- **⚙️ Unified Settings Panel** - All configurations in one place (`/settings`)
- **🏗️ Server Setup Wizard** - Complete server setup with templates (`/setup`)
- **🎮 Fun & Games** - Mini-games, economy, and entertainment features
- **📊 Analytics & Logging** - Comprehensive logging and analytics system

### 🆕 Phase 5 Features (NEW)
- **🤖 AI-Powered Server Designer** - Natural language server creation with Perplexity AI
- **🛡️ Modular Security Framework** - Advanced security modules with threat detection
- **🔧 Bot Invitation System** - One-click invitation for popular bots (Carl-bot, ProBot, etc.)
- **🏭 Raspberry Pi 5 Deployment** - Optimized for ARM64 with Docker containerization
- **📊 Advanced Monitoring** - Prometheus, Grafana, and real-time performance tracking
- **🔄 Multi-Client Architecture** - Support for multiple bot instances with shared security

## 🎯 AI Integration

### Perplexity AI Features
- **Server Designer**: Describe your server in natural language, get complete structure
- **Smart Recommendations**: AI-powered optimization suggestions
- **Content Analysis**: Intelligent content moderation and safety analysis
- **Bot Suggestions**: Automatic bot recommendations based on server type

### Example AI Commands
```
/design description:"Create a gaming community server for Turkish players with voice channels and tournaments"
/analyze - Get AI-powered optimization suggestions for your server
/ask question:"How do I set up a ticket system?" - AI assistant for help
```

## 🏗️ Installation & Deployment

### Quick Setup

1. **Clone and Configure**
```bash
git clone https://github.com/bergasoft/contro-bot.git
cd contro-bot

# Copy and configure environment file
cp .env.example .env
nano .env  # Edit with your tokens and settings
```

2. **Development Setup**
```bash
# Install dependencies
pip install -r requirements.txt

# Run bot
python main.py
```

### Raspberry Pi 5 (Recommended for Production)

```bash
# Clone repository first
git clone https://github.com/bergasoft/contro-bot.git
cd contro-bot

# Configure environment
cp .env.example .env
nano .env  # Add your Discord tokens and API keys

# Download and run installation script
curl -fsSL https://raw.githubusercontent.com/bergasoft/contro-bot/main/deployment/scripts/install.sh | bash

# Deploy with Docker
cd ~/contro-bot
./deployment/scripts/deploy.sh
```

### Docker Deployment

```bash
# Ensure .env file is configured
cp .env.example .env
nano .env  # Configure your settings

# Build and run with Docker Compose
docker-compose -f deployment/docker/docker-compose.pi.yml up -d

# Check status
docker logs contro-bot
```

## ⚙️ Configuration

### Environment Variables (.env file)

Copy `.env.example` to `.env` and configure the following:

```env
# Required: Discord Bot Tokens
CONTRO_MAIN_TOKEN=your_main_bot_token
CONTRO_DEV_TOKEN=your_dev_bot_token (optional)
CONTRO_PREMIUM_TOKEN=your_premium_bot_token (optional)

# Required: Database
MONGO_DB=your_mongodb_connection_string

# Required: AI Integration
PERPLEXITY_API_KEY=your_perplexity_api_key

# Optional: Additional APIs
OPENAI_API_KEY=your_openai_api_key
SPOTIFY_CLIENT_ID=your_spotify_client_id
REDDIT_CLIENT_ID=your_reddit_client_id

# Bot Configuration
BOT_ENV=development  # or production
DEFAULT_PREFIX=>
LOG_LEVEL=INFO
```

### Security Notes

- The `.env` file is gitignored for security
- Use `.env.example` as a template
- Never commit real tokens to version control
- Deployment scripts automatically secure .env permissions (600)

### Production Configuration

For production deployment:
- Set `BOT_ENV=production` in .env
- Use strong MongoDB credentials
- Enable monitoring with `PROMETHEUS_ENABLED=true`
- Set up SSL certificates for HTTPS

## 🛡️ Security Features

### Modular Security System
- **Anti-Spam Protection** - Advanced spam detection with ML
- **Anti-Raid Protection** - Automated raid detection and response
- **Role Guard** - Role hierarchy protection and auditing
- **Channel Guard** - Channel permission monitoring
- **AI Threat Detection** - Behavioral analysis and content scanning

### Security Dashboard
Access comprehensive security controls via `/security` command:
- Real-time threat monitoring
- Security module configuration
- Incident response management
- Alert configuration

## 🤖 Bot Management

### Multi-Bot Invitation System
Easily invite popular bots to enhance your server:

```
/bots invite carl - Invite Carl-bot for advanced moderation
/bots invite probot - Invite ProBot for leveling system
/bots invite mee6 - Invite MEE6 for XP and music
/bots recommend gaming - Get bot recommendations for gaming servers
```

### Supported Bots
- **Carl-bot** - Advanced automoderation and custom commands
- **ProBot** - Leveling, welcome messages, and statistics
- **MEE6** - XP system, moderation, and music
- **Dyno** - Comprehensive moderation and server management
- **Groovy/Rythm** - High-quality music streaming
- **Ticket Tool** - Professional ticket system

## 📊 Monitoring & Analytics

### Real-time Dashboards
- **Grafana Dashboard**: http://localhost:3000
- **Prometheus Metrics**: http://localhost:9091
- **Bot Health Check**: http://localhost:8080/health
- **API Endpoint**: http://localhost:8000/api

### Performance Metrics
- System resource usage (CPU, RAM, Storage)
- Discord API rate limit monitoring
- Database connection health
- AI API usage and costs
- Security incident tracking

## 🎮 Commands Overview

### Administrative Commands
- `/settings` - Unified settings panel for all configurations
- `/setup` - Complete server setup wizard with templates
- `/security` - Comprehensive security dashboard
- `/bots` - Bot invitation and management system

### AI-Powered Commands
- `/design` - AI server designer with natural language input
- `/analyze` - Server optimization suggestions
- `/ask` - AI assistant for help and guidance

### Community Features
- `/register` - User registration system
- `/level` - Check XP and ranking
- `/leaderboard` - Server XP leaderboard
- `/ticket` - Create support tickets

### Fun & Games
- `/spin` - Spin wheel game with rewards
- `/games` - Various mini-games and entertainment
- `/giveaway` - Create and manage giveaways

## 🏆 Performance Optimizations

### Raspberry Pi 5 Optimizations
- ARM64 native Docker images
- Memory usage under 1GB
- CPU temperature monitoring
- Automatic performance scaling
- Storage optimization with log rotation

### Production Features
- Auto-restart on failure
- Health check endpoints
- Graceful shutdown handling
- SSL/TLS certificate automation
- Firewall configuration (UFW)

## 📈 Development Roadmap

### Phase 6: Advanced AI Features (In Progress)
- [ ] Advanced AI content generation
- [ ] Predictive server analytics
- [ ] Smart auto-moderation with learning
- [ ] Voice recognition and processing
- [ ] Advanced threat prediction

### Phase 7: Enterprise Features (Planned)
- [ ] Multi-server management dashboard
- [ ] Advanced analytics and reporting
- [ ] White-label bot deployment
- [ ] Custom AI model training
- [ ] Enterprise security compliance

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 📞 Support

- **Discord Server**: [Join our support server](https://discord.gg/your-server)
- **Documentation**: [Full documentation](https://docs.contro-bot.com)
- **Issues**: [GitHub Issues](https://github.com/bergasoft/contro-bot/issues)
- **Email**: support@contro-bot.com

## 🙏 Acknowledgments

- Discord.py community for the excellent framework
- Perplexity AI for intelligent server design capabilities
- Open source community for various tools and libraries
- Raspberry Pi Foundation for affordable computing solutions

---

**Made with ❤️ by [Bergasoft](https://github.com/bergasoft)**