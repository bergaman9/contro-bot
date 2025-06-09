# 🚀 CONTRO Bot - Complete Deployment Guide

This guide will walk you through deploying the CONTRO Discord bot from start to finish.

## 📋 Prerequisites

Before you begin, ensure you have:

- **Discord Bot Application** created at [Discord Developer Portal](https://discord.com/developers/applications)
- **Python 3.10+** installed
- **MongoDB** database (local or cloud)
- **Git** installed
- Basic command line knowledge

## 🎯 Quick Start (5 Minutes)

### 1. Clone and Setup

```powershell
# Clone the repository
git clone https://github.com/yourusername/contro-bot.git
cd contro-bot

# Install dependencies
pip install -r requirements.txt
```

### 2. Environment Configuration

Create a `.env` file in the root directory:

```env
# Required Settings
BOT_TOKEN=your_discord_bot_token_here
MONGODB_CONNECTION_STRING=mongodb://localhost:27017/contro_bot

# Optional API Keys (for enhanced features)
OPENAI_API_KEY=your_openai_key_here
PERPLEXITY_API_KEY=your_perplexity_key_here
STEAM_API_KEY=your_steam_key_here
RAWG_API_KEY=your_rawg_key_here
SPOTIFY_CLIENT_ID=your_spotify_client_id
SPOTIFY_CLIENT_SECRET=your_spotify_client_secret
TMDB_API_KEY=your_tmdb_key_here
```

### 3. Verify Setup

```powershell
python verify_deployment.py
```

### 4. Launch Bot

```powershell
python main.py
```

## 🤖 Discord Bot Setup

### Creating a Discord Application

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application" and give it a name
3. Go to "Bot" section
4. Click "Add Bot"
5. Under "Token", click "Copy" to get your bot token
6. Enable "Message Content Intent" if you want the bot to read message content

### Bot Permissions

Your bot needs these permissions:
```
Administrator (recommended for full functionality)
OR specific permissions:
- Send Messages
- Embed Links  
- Attach Files
- Read Message History
- Use Slash Commands
- Manage Roles
- Manage Channels
- Manage Messages
- Add Reactions
- Connect (Voice)
- Speak (Voice)
```

### Invite URL Generator

Replace `YOUR_CLIENT_ID` with your bot's Client ID:
```
https://discord.com/api/oauth2/authorize?client_id=YOUR_CLIENT_ID&permissions=8&scope=bot%20applications.commands
```

## 🗄️ Database Setup

### Option 1: Local MongoDB

```powershell
# Install MongoDB Community Edition
# Windows: Download from https://www.mongodb.com/try/download/community

# Start MongoDB service
net start MongoDB

# Your connection string will be:
# mongodb://localhost:27017/contro_bot
```

### Option 2: MongoDB Atlas (Cloud)

1. Create account at [MongoDB Atlas](https://www.mongodb.com/atlas)
2. Create a new cluster (free tier available)
3. Get connection string from "Connect" button
4. Replace `<password>` with your database user password
5. Use this connection string in your `.env` file

### Database Collections

The bot will automatically create these collections:
- `users` - User registration and XP data
- `guilds` - Server-specific settings
- `giveaways` - Active giveaways
- `tickets` - Support ticket data
- `logs` - Event logging data

## 🖥️ Server Deployment Options

### Option 1: Local Development

Perfect for testing and development:

```powershell
# Run directly
python main.py

# Or with auto-restart on changes
pip install watchdog
watchmedo auto-restart --patterns="*.py" --recursive -- python main.py
```

### Option 2: Windows Server

Create a batch file `start_bot.bat`:
```batch
@echo off
cd /d "C:\path\to\your\bot"
python main.py
pause
```

Use Windows Task Scheduler to run on startup.

### Option 3: Raspberry Pi 5 (Recommended)

Use the included deployment script:

```bash
# Make executable
chmod +x scripts/deploy_pi5.sh

# Run deployment
./scripts/deploy_pi5.sh
```

This will:
- Install all dependencies
- Optimize for Pi 5 performance
- Set up systemd service for auto-start
- Configure proper logging

### Option 4: VPS/Cloud Server

For Ubuntu/Debian servers:

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python 3.10+
sudo apt install python3.10 python3.10-pip python3.10-venv -y

# Install MongoDB
wget -qO - https://www.mongodb.org/static/pgp/server-6.0.asc | sudo apt-key add -
echo "deb [ arch=amd64,arm64 ] https://repo.mongodb.org/apt/ubuntu focal/mongodb-org/6.0 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-6.0.list
sudo apt update
sudo apt install -y mongodb-org

# Start MongoDB
sudo systemctl start mongod
sudo systemctl enable mongod

# Clone and setup bot
git clone https://github.com/yourusername/contro-bot.git
cd contro-bot
python3.10 -m pip install -r requirements.txt

# Create systemd service
sudo cp scripts/deploy_pi5.sh /usr/local/bin/
sudo chmod +x /usr/local/bin/deploy_pi5.sh
sudo /usr/local/bin/deploy_pi5.sh
```

## ⚙️ Bot Configuration

### First Setup

1. Invite the bot to your Discord server
2. Run `/setup` command in your server
3. Follow the interactive setup wizard
4. Configure features with `/settings`

### Essential Commands

```
/setup          - Complete server setup wizard
/settings       - Configure all bot features
/help           - View all available commands
/register       - User registration system
/level          - Check XP and level
/ticket create  - Create support ticket
```

### Feature Configuration

The bot has toggleable features. Configure them with `/settings`:

- **Registration System** - User onboarding and verification
- **Level System** - XP tracking and rewards
- **Welcome System** - Greeting messages with custom images
- **Ticket System** - Support ticket management
- **Auto Moderation** - Content filtering and automatic actions
- **Giveaway System** - Interactive giveaways
- **Starboard** - Highlight popular messages
- **Game Stats** - Track gaming activity
- **Birthday System** - Birthday tracking and announcements

## 🔧 Advanced Configuration

### Custom Backgrounds

Add custom welcome/goodbye backgrounds:
1. Place images in `data/Backgrounds/`
2. Supported formats: PNG, JPG, JPEG
3. Recommended size: 1920x1080
4. Use `/settings welcome` to configure

### Server Templates

Create custom server templates:
1. Edit `data/templates/` files
2. Use template variables: `{server}`, `{member}`, `{count}`
3. Apply with `/setup template`

### Version Control

The bot includes automated version tracking:
- Use `/version info` to check current version
- `/version changelog` to see recent changes
- Automatic git integration for version bumping

## 🐛 Troubleshooting

### Common Issues

**Bot not responding:**
- Check bot token in `.env` file
- Verify bot has necessary permissions
- Check if bot is online in Discord

**Database connection errors:**
- Verify MongoDB is running
- Check connection string format
- Ensure database user has proper permissions

**Missing dependencies:**
```powershell
pip install -r requirements.txt --upgrade
```

**Cog loading errors:**
- Check logs in `logs/` directory
- Verify all files exist with `python verify_deployment.py`
- Restart bot after fixing issues

### Performance Issues

**High memory usage:**
- Monitor with `/utility system`
- Restart bot periodically
- Check for memory leaks in logs

**Slow responses:**
- Optimize database queries
- Check network connection
- Monitor CPU usage

### Debugging

Enable debug logging in `.env`:
```env
DEBUG_MODE=true
LOG_LEVEL=DEBUG
```

View logs:
```powershell
# Real-time log viewing
Get-Content logs/bot.log -Wait

# Search for errors
Select-String -Path "logs/*.log" -Pattern "ERROR"
```

## 📊 Monitoring & Maintenance

### Health Checks

Use the built-in monitoring:
- `/utility system` - System resources
- `/utility ping` - Bot latency
- `/version status` - Bot status information

### Log Management

Logs are automatically rotated. Check these files:
- `logs/bot.log` - General bot operations
- `logs/errors.log` - Error tracking
- `logs/commands.log` - Command usage
- `logs/*.log` - Feature-specific logs

### Updates

Keep your bot updated:
```powershell
# Pull latest changes
git pull origin main

# Update dependencies
pip install -r requirements.txt --upgrade

# Restart bot
# Ctrl+C to stop, then python main.py
```

### Backup

Important files to backup:
- `.env` - Environment configuration
- `data/` - All data files
- `config/` - Configuration files
- Database - MongoDB data

## 🆘 Support

### Getting Help

1. **Documentation** - Check README.md and this guide
2. **Verification** - Run `python verify_deployment.py`
3. **Logs** - Check log files for error details
4. **GitHub Issues** - Report bugs or request features
5. **Community** - Join our Discord server (if available)

### Reporting Issues

When reporting issues, include:
- Bot version (`/version info`)
- Error logs from `logs/` directory
- Steps to reproduce
- System information (OS, Python version)

## 🚀 Going to Production

### Production Checklist

- [ ] Secure `.env` file (not in version control)
- [ ] Set up proper logging and monitoring
- [ ] Configure automatic backups
- [ ] Set up process monitoring (systemd/pm2)
- [ ] Configure firewall for database
- [ ] Set up SSL if using web features
- [ ] Test all critical features
- [ ] Prepare rollback plan

### Scaling Considerations

For large servers (1000+ members):
- Use MongoDB Atlas for better performance
- Consider using Redis for caching
- Monitor memory usage closely
- Set up load balancing if needed
- Implement rate limiting

---

🎉 **Congratulations!** Your CONTRO Discord bot is now ready for production use!

For the latest updates and documentation, visit the [GitHub repository](https://github.com/yourusername/contro-bot).
