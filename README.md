# 🤖 CONTRO - Advanced Discord Bot Management System

[![Version](https://img.shields.io/badge/version-2.0.0-blue.svg)](https://github.com/bergaman9/contro-bot)
[![Python](https://img.shields.io/badge/python-3.10+-green.svg)](https://python.org)
[![MongoDB](https://img.shields.io/badge/database-MongoDB-47A248.svg)](https://mongodb.com)
[![Discord.py](https://img.shields.io/badge/discord.py-2.3.2-7289DA.svg)](https://discordpy.readthedocs.io/)
[![Raspberry Pi](https://img.shields.io/badge/hosting-Raspberry%20Pi%205-C51A4A.svg)](https://raspberrypi.org)

**CONTRO** is an advanced, production-ready Discord bot with comprehensive server management capabilities, featuring modern async MongoDB integration, beautiful UI systems, and robust automated version control.

## ✨ Core Features Overview

<!-- Bot Features Showcase -->
<div align="center">
  <img src="https://raw.githubusercontent.com/bergaman9/contro-bot/main/images/backgrounds/welcome_blue.png" alt="CONTRO Bot Welcome System" width="400">
  <img src="https://raw.githubusercontent.com/bergaman9/contro-bot/main/images/register_card_d563575f-39ba-45e2-b306-30e1e0af7cb3.png" alt="Registration Card Example" width="400">
</div>

### 🎯 **Perfect Registration System** ✅
- **Advanced Registration Modal** - Comprehensive user registration with game preferences
- **Age Verification** - Automatic age role assignment with zodiac integration
- **Game Matching** - Find users with similar gaming interests  
- **Role Automation** - Intelligent role assignment based on registration data
- **Custom Interfaces** - Personalized registration experiences
- **Data Validation** - Robust input validation and error handling

### 📈 **Flawless Level System** ✅
- **XP Management** - Advanced experience tracking for messages and voice activity
- **Beautiful Level Cards** - Custom-generated level cards with backgrounds
- **Voice Activity Tracking** - XP rewards for voice channel participation
- **Registration Bonuses** - Extra XP incentives for community registration
- **Leaderboards** - Server-wide XP rankings with pagination
- **Smart Caching** - Optimized performance with intelligent data caching
- **Async MongoDB** - Modern async database operations for better performance

### 🎫 **Advanced Ticket System** ✅
- **Multi-Category Support** - Organized ticket categories for different support types
- **Support Role Management** - Designated helper roles with proper permissions
- **Automated Management** - Smart ticket creation, archiving, and cleanup
- **Custom Interfaces** - Personalized ticket creation with interactive buttons
- **Persistent Views** - Tickets survive bot restarts and maintain functionality
- **Detailed Logging** - Comprehensive ticket activity tracking

### 👋 **Beautiful Welcome System** ✅
- **Custom Welcome Cards** - Stunning welcome images with user avatars
- **Advanced Background System** - Multiple preset backgrounds or custom uploads
- **Message Templates** - Dynamic variables: {mention}, {name}, {server}, {count}
- **Dual Welcome/Goodbye** - Separate systems for arrivals and departures
- **Image Optimization** - Efficient image processing and caching
- **Role Integration** - Automatic role assignment for new members
### 🔧 **Advanced Feature Management System**
- **Granular Toggle Control** - Enable/disable any bot feature per server
- **Visual Status Dashboard** - See all feature states at a glance with beautiful UI
- **Category Organization** - Features organized by system (Moderation, Community, Fun)
- **Reset to Defaults** - Easily restore default configurations
- **Permission Management** - Role-based feature access control
- **Real-time Updates** - Instant feature state changes without restarts

### 🎮 **Comprehensive Server Management**
- **One-Click Setup** - `/setup` command with complete server configuration wizard
- **Template System** - Multiple pre-designed server templates for different communities
- **Discord Template Import** - Import and apply official Discord server templates
- **Settings Dashboard** - `/settings` for organized configuration management
- **Multi-language Support** - Full Turkish and English language support
- **Custom Branding** - Server-specific embed colors and bot personality

### 🎉 **Interactive Giveaway System**
- **Button-based Participation** - Modern Discord UI with interactive buttons
- **Role Restrictions** - Limit participation to specific roles or member types
- **Automatic Winner Selection** - Fair random selection with reroll capabilities
- **Persistent Management** - Giveaways survive bot restarts and maintain state
- **Advanced Scheduling** - Set custom duration and end times
- **Winner Notifications** - Automatic DM notifications to winners

### ⭐ **Smart Starboard System**
- **Popular Message Highlighting** - Showcase community favorites automatically
- **Custom Reaction Thresholds** - Set minimum reaction counts per server
- **Multiple Emoji Support** - Choose from various reaction triggers
- **Duplicate Prevention** - Smart filtering to avoid spam
- **Channel Restrictions** - Control which channels feed the starboard

### 🎮 **Game Statistics & Tracking**
- **Real-time Activity Monitoring** - Track what games members are playing
- **Server Game Analytics** - See most popular games with detailed statistics
- **Play Time Tracking** - Monitor total time spent in different games
- **Intelligent Caching** - Optimized performance with smart data management
- **Historical Data** - Track gaming trends over time
- **Integration Ready** - Steam profile and game data integration

### 🛡️ **Comprehensive Auto Moderation**
- **Advanced Word Filtering** - Intelligent content moderation with context awareness
- **Automated Role Management** - Smart role assignment based on user behavior
- **Action Logging** - Complete audit trail of all moderation actions
- **Punishment Escalation** - Progressive punishment system (warn → timeout → ban)
- **Whitelist System** - Exception handling for trusted users and roles
- **Custom Responses** - Personalized moderation messages

### 🎂 **Birthday & Zodiac System**
- **Automatic Birthday Tracking** - Smart birthday detection and announcements
- **Zodiac Role Assignment** - Automatic astrological sign roles based on birth dates
- **Age Calculation** - Intelligent age verification and role management
- **Custom Birthday Messages** - Personalized birthday greetings with mentions
- **Birthday Calendar** - Track upcoming birthdays in your server
- **Timezone Support** - Handle different timezones for accurate celebrations

### 🔨 **Advanced Utility Features**
- **Temporary Voice Channels** - Auto-creating and managing temporary voice rooms
- **Multi-server Bump Automation** - Automatic server bumping across platforms
- **Dynamic Content Loading** - Flexible content management system
- **Steam Integration** - Rich Steam profile and game data integration
- **Crypto Price Tracking** - Real-time cryptocurrency price monitoring
- **Reddit Integration** - Fetch and display content from subreddits

### 🎭 **Entertainment & Fun Commands**
- **AI-Powered Interactions** - OpenAI and Perplexity integration for smart responses
- **Entertainment Recommendations** - Movie, game, and music suggestions
- **Interactive Games** - 8ball, love calculator, word definitions, and more
- **Meme Generation** - Reddit meme fetching with filtering
- **Trivia Systems** - Knowledge-based games and competitions
- **Social Features** - User interaction commands and community building tools

### 📊 **Comprehensive Logging System**
- **Event Tracking** - Complete server activity monitoring
- **Action Auditing** - Detailed logs of all moderation and administrative actions
- **User Activity Logs** - Track member join/leave, role changes, and interactions
- **Error Monitoring** - Automatic error detection and reporting
- **Log Rotation** - Intelligent log file management to prevent disk overflow
- **Export Capabilities** - Easy log export for external analysis

### 🚀 **Performance & Technical Features**
- **Async MongoDB Integration** - Modern async database operations (migrated from deprecated Motor)
- **Intelligent Caching System** - Multi-layer caching for optimal performance
- **Resource Management** - Automatic cleanup and memory optimization
- **Rate Limiting Protection** - Built-in API abuse prevention
- **Load Distribution** - Efficient async operation handling
- **Error Recovery** - Graceful error handling with automatic recovery
- **Raspberry Pi 5 Optimized** - Specifically optimized for Raspberry Pi hosting

## 🚀 Quick Start Guide

### Prerequisites
- **Python 3.10+** (Python 3.11 recommended for optimal performance)
- **MongoDB** (Local or cloud instance)
- **Discord Bot Token** (from Discord Developer Portal)
- **Raspberry Pi 5** (or any Linux/Windows server)

### Installation Steps

1. **Clone & Setup**
   ```bash
   git clone https://github.com/bergaman9/contro-bot.git
   cd contro-bot
   pip install -r requirements.txt
   ```

2. **Environment Configuration**   Create `.env` file with:
   ```env
   BOT_TOKEN=your_discord_bot_token
   MONGODB_CONNECTION_STRING=mongodb+srv://username:password@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority
   OPENAI_API_KEY=your_openai_key (optional)
   PERPLEXITY_API_KEY=your_perplexity_key (optional)
   ```

3. **Database Setup**
   ```bash
   # MongoDB will auto-initialize collections on first run
   # No manual database setup required
   ```

4. **Launch Bot**
   ```bash
   python main.py
   ```

### Quick Configuration

1. **Invite Bot** - Use Discord Developer Portal to invite with necessary permissions
2. **Server Setup** - Run `/setup` in your Discord server
3. **Feature Configuration** - Use `/settings` to customize all features
4. **Registration Setup** - Configure `/register_settings` for your community

## 🛠️ Raspberry Pi 5 Deployment

### System Requirements
- **Raspberry Pi 5** with at least 4GB RAM (8GB recommended)
- **64GB+ MicroSD Card** (Class 10 or better)
- **Stable Internet Connection**
- **Raspberry Pi OS** (64-bit recommended)

### Optimization for Pi 5
```bash
# System optimization
sudo apt update && sudo apt upgrade -y
sudo apt install python3.11 python3.11-pip mongodb git -y

# Performance tuning
echo 'vm.swappiness=10' | sudo tee -a /etc/sysctl.conf
echo 'net.core.rmem_max = 134217728' | sudo tee -a /etc/sysctl.conf

# Start services
sudo systemctl enable mongodb
sudo systemctl start mongodb
```

### Auto-Start Configuration
```bash
# Create systemd service
sudo nano /etc/systemd/system/contro-bot.service
```

Service file content:
```ini
[Unit]
Description=CONTRO Discord Bot
After=network.target mongodb.service

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/contro-project/bot
ExecStart=/usr/bin/python3.11 main.py
Restart=always
RestartSec=10
Environment=PYTHONPATH=/home/pi/contro-project/bot

[Install]
WantedBy=multi-user.target
```

Enable service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable contro-bot
sudo systemctl start contro-bot
```

## 🔧 Recent Fixes & Improvements

### ✅ **Indentation Error Fixed:**
- **XP Manager Created** - Resolved IndentationError preventing spin and levelling cogs from loading
- **Missing File Added** - Created utils/community/turkoyto/xp_manager.py with proper structure
- **Cog Loading Fixed** - All 17 cogs now load successfully without errors

### ✅ **Database Issues Resolved:**
- **Fixed truth value testing** - Proper null checking for database connections
- **Improved error handling** - Better database initialization with fallback options
- **Connection stability** - Enhanced MongoDB connection management

### ✅ **Command Registration Fixed:**
- **Removed duplicate commands** - Fixed CommandAlreadyRegistered errors
- **Clean cog loading** - Proper handling of existing cog instances
- **Improved setup process** - Better initialization sequence

### ✅ **Enhanced Settings System:**
- **Unified settings interface** - Single `/settings` command for all configuration
- **Better error handling** - Comprehensive error messages and logging
- **Improved user experience** - Cleaner UI with better feedback

### ✅ **Template System:**
- **JSON-based Templates** - Flexible server template storage
- **Discord Template Import** - Import official Discord templates
- **Format Variables** - Dynamic content with server-specific mentions

## 📁 Project Structure

```
bot/
├── main.py                     # Bot entry point with cog loading
├── cogs/                       # Main cog files (17 total)
│   ├── settings.py             # Settings management system ✅
│   ├── server_setup.py         # Server setup with templates ✅
│   ├── welcomer.py             # Welcome/goodbye system ✅
│   ├── register.py             # Registration system ✅
│   ├── giveaways.py            # Giveaway management ✅
│   ├── ticket.py               # Support ticket system ✅
│   ├── moderation.py           # Moderation tools ✅
│   ├── levelling.py            # XP and leveling ✅
│   ├── spin.py                 # Spin wheel games ✅
│   ├── game_stats.py           # Game activity tracking ✅
│   ├── fun.py                  # Entertainment commands ✅
│   ├── utility.py              # General utilities ✅
│   ├── starboard.py            # Starboard system ✅
│   ├── logging.py              # Event logging ✅
│   ├── temp_channels.py        # Temporary voice channels ✅
│   ├── bump.py                 # Auto server bumping ✅
│   └── interface.py            # User interface components ✅
├── utils/                      # Organized utility modules
│   ├── database/               # Database management ✅
│   │   ├── __init__.py
│   │   └── connection.py       # MongoDB connection with error handling
│   ├── community/              # Community-specific features
│   │   └── turkoyto/           # TurkOyto community integration
│   │       ├── xp_manager.py   # XP management system ✅
│   │       └── registration_view.py # Registration modal views
│   ├── core/                   # Core utilities
│   │   ├── formatting.py       # Embed creation helpers
│   │   └── class_utils.py      # Utility classes
│   ├── settings/               # Settings system components
│   └── content_loader.py       # Dynamic content loading
├── data/                       # Data storage
│   ├── templates/              # Server templates (JSON)
│   ├── Backgrounds/            # Welcome image backgrounds
│   └── fonts/                  # Custom fonts
└── logs/                       # Log files
```

## 🛠️ Installation

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Configure environment variables (.env file):
   ```
   BOT_TOKEN=your_bot_token
   MONGODB_CONNECTION_STRING=your_mongodb_url
   OPENAI_API_KEY=your_openai_key (optional)
   PERPLEXITY_API_KEY=your_perplexity_key (optional)
   ```
4. Run the bot: `python main.py`

## 🎯 Usage Examples

### Settings Management
```
/settings
```
- Access comprehensive settings panel
- Configure by category (Server, Welcome, Moderation, etc.)
- View current settings anytime
- Remove or modify existing configurations
- Toggle features on/off with Feature Management

### Server Setup
```
/setup
```
- Complete server setup wizard
- Choose from pre-built templates
- Import Discord templates
- Configure all essential features

### Registration System
```
/register_settings
```
- Configure age roles and verification
- Set up registration channels
- Customize registration messages

### Quick Commands
```
/topgames          # Show most played games on server
/giveaway create   # Create interactive giveaways
/birthday         # Set birthday and get zodiac role
/crypto bitcoin   # Get cryptocurrency prices
```

## 🔄 Error Handling & Stability

### Database Connection
- **Graceful Fallbacks** - Bot continues operating even with database issues
- **Connection Retries** - Automatic reconnection attempts
- **Error Logging** - Comprehensive logging for troubleshooting
- **Null Checking** - Proper validation before database operations

### Command Registration
- **Duplicate Prevention** - Automatic handling of existing command instances
- **Clean Reloading** - Proper cog reloading without conflicts
- **State Management** - Consistent bot state across restarts

### Cog Loading
- **All 17 cogs load successfully** - Fixed indentation and import errors
- **Dependency Management** - Proper handling of cog dependencies
- **Graceful Failures** - Individual cog failures don't crash the bot

## 🌐 Language Support

The bot supports both Turkish and English interfaces:
- All UI components are bilingual
- Language selection at startup
- Contextual help in selected language
- Community-specific features for Turkish gaming communities

## 📊 Performance Features

### Caching System
- **Game Statistics Caching** - Reduces database queries
- **User Data Caching** - Faster XP calculations
- **Template Caching** - Improved setup performance

### Database Optimization
- **Batch Operations** - Efficient bulk updates
- **Index Usage** - Optimized queries
- **Connection Pooling** - Better resource management

### Load Distribution
- **Async Operations** - Non-blocking command execution
- **Rate Limiting** - Prevents API abuse
- **Resource Management** - Automatic cleanup of resources

## 📋 Complete Features Summary

✅ **All Issues Fixed:**
- **Indentation errors resolved** - XP Manager created with proper structure
- **Database connection errors** - Proper null checking and error handling
- **Command registration conflicts** - Clean cog loading system
- **All 17 cogs loading successfully** - No more startup errors

✅ **Fully Implemented Systems:**
- **Feature toggle system** with granular control for all features
- **Complete settings UI** with category-based organization
- **Server setup with templates** and Discord template import
- **Welcome/goodbye with custom card generation**
- **Advanced registration system** with game matching
- **Comprehensive giveaway system** with persistent views
- **Ticket system** with multi-category support
- **Moderation tools** (auto roles, word filter, logging)
- **XP and leveling system** with voice tracking
- **Game statistics tracking** with intelligent caching
- **Birthday system** with zodiac role automation
- **Utility features** (temp channels, bump automation)
- **Entertainment commands** with external API integration
- **Dual language support** (Turkish/English)
- **Clean modular architecture** with organized file structure
- **Comprehensive error handling** and logging
- **Performance optimizations** with caching and async operations

## 🚀 Production Ready

This is a complete, production-ready Discord bot system with:
- **Zero startup errors** - All cogs load successfully
- **Comprehensive feature set** - 17 different cog modules
- **Advanced UI system** - Interactive settings management
- **Database integration** - MongoDB with proper error handling
- **External integrations** - OpenAI, Steam, Reddit, Crypto APIs
- **Performance optimized** - Caching, async operations, rate limiting
- **Community features** - Special TurkOyto gaming community integration
- **Template system** - Quick server setup with pre-configured templates

The bot is ready for deployment and can handle multiple servers simultaneously with full feature sets for each community.

## 🤝 Contributing

This project maintains a clean, modular architecture that makes it easy to:
- Add new features as separate cogs
- Extend existing functionality
- Customize for specific communities
- Deploy across multiple servers

## 📝 License

This project is available under the MIT License. See the [LICENSE](LICENSE) file for details.

## 📊 Bot Showcase

![CONTRO Bot](https://raw.githubusercontent.com/bergaman9/contro-bot/main/images/contro_bot_showcase.png)

## 🔗 Links

- [Discord Bot](https://top.gg/tr/bot/783064615012663326)
- [GitHub Repository](https://github.com/bergaman9/contro-bot)
- [Documentation](https://github.com/bergaman9/contro-bot/wiki)