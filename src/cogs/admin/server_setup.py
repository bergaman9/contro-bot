"""Server setup commands."""
import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional, List
import logging
import asyncio
from datetime import datetime

from src.utils.core.formatting import create_embed
from src.utils.views.settings_views import MainSettingsView
from src.utils.views.views import MainSetupView
from src.utils.database.db_manager import db_manager
from src.bot.constants import Colors

# Set up logging
logger = logging.getLogger('admin.server_setup')

class ServerSetup(commands.Cog):
    """Server setup and configuration commands"""
    
    def __init__(self, bot):
        self.bot = bot
        self.db = None
        self.bot.loop.create_task(self.initialize_db())

    async def initialize_db(self):
        """Initialize the database connection"""
        try:
            if db_manager and hasattr(db_manager, 'get_database'):
                self.db = db_manager.get_database()
            else:
                self.db = getattr(self.bot, 'async_db', None)
            logger.info("Database connection initialized for ServerSetup cog")
        except Exception as e:
            logger.error(f"Error initializing database connection: {e}")

    @commands.hybrid_command(name="setup", description="Open the server setup panel")
    @commands.has_permissions(administrator=True)
    @app_commands.describe(ephemeral="Send the setup panel as ephemeral message")
    async def setup(self, ctx, ephemeral: bool = False):
        """Open the server setup panel"""
        await self.open_setup_panel(ctx, ephemeral)

    async def open_setup_panel(self, ctx, ephemeral=False):
        """Open the main setup panel"""
        try:
            view = MainSetupView(self.bot, ctx.guild.id)
            
            # Get server info for the embed
            guild = ctx.guild
            
            embed = discord.Embed(
                title="🚀 Server Setup Panel",
                description="Welcome to the comprehensive server setup system!\n"
                           "Configure all aspects of your server with ease.",
                color=Colors.INFO
            )
            
            # Add server info
            embed.add_field(
                name="📊 Server Information",
                value=f"**Server:** {guild.name}\n"
                      f"**Members:** {guild.member_count}\n"
                      f"**Owner:** {guild.owner.mention if guild.owner else 'Unknown'}\n"
                      f"**Created:** {guild.created_at.strftime('%d.%m.%Y')}",
                inline=True
            )
            
            # Add features overview
            embed.add_field(
                name="⚙️ Available Features",
                value="• **Templates** - Quick server setup\n"
                      "• **Channels** - Create channel structures\n" 
                      "• **Roles** - Configure role hierarchy\n"
                      "• **Business** - Business commands setup\n"
                      "• **Advanced** - Custom configurations",
                inline=True
            )
            
            # Add tips
            embed.add_field(
                name="💡 Quick Tips",
                value="• Use templates for fast setup\n"
                      "• Configure channels before roles\n"
                      "• Enable logging for monitoring\n"
                      "• Set up welcome messages last",
                inline=False
            )
            
            if guild.icon:
                embed.set_thumbnail(url=guild.icon.url)
            
            embed.set_footer(text="This panel is only accessible by administrators.")
            
            await ctx.send(embed=embed, view=view, ephemeral=ephemeral)
            
        except Exception as e:
            logger.error(f"Error opening setup panel: {e}")
            embed = create_embed(
                title="❌ Error",
                description="Failed to open setup panel. Please try again.",
                color=Colors.ERROR
            )
            await ctx.send(embed=embed, ephemeral=True)

    @commands.hybrid_command(name="quicksetup", description="Quick server setup wizard")
    @commands.has_permissions(administrator=True)
    @app_commands.describe(
        template="Choose a server template",
        ephemeral="Send as ephemeral message"
    )
    @app_commands.choices(template=[
        app_commands.Choice(name="Gaming Community", value="gaming"),
        app_commands.Choice(name="Study Group", value="study"),
        app_commands.Choice(name="Business/Work", value="business"),
        app_commands.Choice(name="Creative Hub", value="creative"),
        app_commands.Choice(name="General Community", value="general"),
        app_commands.Choice(name="Turkish Community", value="turkish")
    ])
    async def quicksetup(self, ctx, template: str = "general", ephemeral: bool = False):
        """Quick setup wizard for common server configurations"""
        await self.run_quick_setup(ctx, template, ephemeral)

    async def run_quick_setup(self, ctx, template: str, ephemeral: bool):
        """Run the quick setup process"""
        try:
            if ephemeral or not ctx.interaction:
                await ctx.defer(ephemeral=ephemeral)
            
            embed = create_embed(
                title="🚀 Quick Setup Started",
                description=f"Setting up your server with the **{template.title()}** template...",
                color=Colors.INFO
            )
            
            if ctx.interaction:
                await ctx.followup.send(embed=embed, ephemeral=ephemeral)
            else:
                message = await ctx.send(embed=embed)
            
            # Get template configuration
            template_config = await self.get_template_config(template)
            setup_results = []
            
            # Create channels
            if template_config.get('channels'):
                channel_results = await self.setup_channels(ctx.guild, template_config['channels'])
                setup_results.extend(channel_results)
            
            # Create roles
            if template_config.get('roles'):
                role_results = await self.setup_roles(ctx.guild, template_config['roles'])
                setup_results.extend(role_results)
            
            # Configure basic settings
            if template_config.get('settings'):
                settings_results = await self.configure_settings(ctx.guild.id, template_config['settings'])
                setup_results.extend(settings_results)
            
            # Create completion embed
            success_count = len([r for r in setup_results if r['success']])
            total_count = len(setup_results)
            
            completion_embed = create_embed(
                title="✅ Quick Setup Complete",
                description=f"Server setup completed! **{success_count}/{total_count}** items configured successfully.",
                color=Colors.SUCCESS if success_count == total_count else Colors.WARNING
            )
            
            # Add results summary
            if setup_results:
                success_items = [r['item'] for r in setup_results if r['success']]
                failed_items = [r['item'] for r in setup_results if not r['success']]
                
                if success_items:
                    completion_embed.add_field(
                        name="✅ Successfully Configured",
                        value="\n".join(f"• {item}" for item in success_items[:10]),
                        inline=False
                    )
                
                if failed_items:
                    completion_embed.add_field(
                        name="❌ Failed to Configure",
                        value="\n".join(f"• {item}" for item in failed_items[:5]),
                        inline=False
                    )
            
            completion_embed.add_field(
                name="🎯 Next Steps",
                value="• Use `/settings` to fine-tune configurations\n"
                      "• Set up welcome messages\n"
                      "• Configure moderation settings\n"
                      "• Enable logging features",
                inline=False
            )
            
            # Update the message
            if ctx.interaction:
                try:
                    await ctx.edit_original_response(embed=completion_embed)
                except:
                    await ctx.followup.send(embed=completion_embed, ephemeral=ephemeral)
            else:
                await message.edit(embed=completion_embed)
                
        except Exception as e:
            logger.error(f"Error in quick setup: {e}")
            error_embed = create_embed(
                title="❌ Setup Error",
                description=f"An error occurred during setup: {str(e)}",
                color=Colors.ERROR
            )
            
            if ctx.interaction:
                await ctx.followup.send(embed=error_embed, ephemeral=True)
            else:
                await ctx.send(embed=error_embed)

    async def get_template_config(self, template: str) -> dict:
        """Get configuration for a template"""
        templates = {
            "gaming": {
                "channels": [
                    {"name": "📢│announcements", "type": "text", "category": "Information"},
                    {"name": "📋│rules", "type": "text", "category": "Information"},
                    {"name": "💬│general-chat", "type": "text", "category": "General"},
                    {"name": "🎮│gaming-chat", "type": "text", "category": "General"},
                    {"name": "🎯│looking-for-group", "type": "text", "category": "Gaming"},
                    {"name": "🏆│achievements", "type": "text", "category": "Gaming"},
                    {"name": "🔊│General Voice", "type": "voice", "category": "Voice Channels"},
                    {"name": "🎮│Gaming Voice", "type": "voice", "category": "Voice Channels"},
                ],
                "roles": [
                    {"name": "🎮 Gamer", "color": 0x00ff00, "permissions": "default"},
                    {"name": "🏆 Pro Player", "color": 0xffd700, "permissions": "default"},
                    {"name": "👑 Admin", "color": 0xff0000, "permissions": "admin"},
                ],
                "settings": {
                    "welcome_enabled": True,
                    "leveling_enabled": True,
                    "moderation_enabled": True
                }
            },
            "turkish": {
                "channels": [
                    {"name": "📢│duyurular", "type": "text", "category": "Bilgi"},
                    {"name": "📋│kurallar", "type": "text", "category": "Bilgi"},
                    {"name": "💬│genel-sohbet", "type": "text", "category": "Genel"},
                    {"name": "🎮│oyun-sohbet", "type": "text", "category": "Genel"},
                    {"name": "🎯│etkinlikler", "type": "text", "category": "Etkinlikler"},
                    {"name": "📝│kayıt", "type": "text", "category": "Sistem"},
                    {"name": "🔊│Genel Ses", "type": "voice", "category": "Ses Kanalları"},
                    {"name": "🎮│Oyun Sesi", "type": "voice", "category": "Ses Kanalları"},
                ],
                "roles": [
                    {"name": "👤 Üye", "color": 0x3498db, "permissions": "default"},
                    {"name": "🎮 Oyuncu", "color": 0x2ecc71, "permissions": "default"},
                    {"name": "⭐ VIP", "color": 0xf39c12, "permissions": "default"},
                    {"name": "👑 Yönetici", "color": 0xe74c3c, "permissions": "admin"},
                ],
                "settings": {
                    "welcome_enabled": True,
                    "leveling_enabled": True,
                    "moderation_enabled": True
                }
            },
            "general": {
                "channels": [
                    {"name": "📢│announcements", "type": "text", "category": "Information"},
                    {"name": "📋│rules", "type": "text", "category": "Information"},
                    {"name": "💬│general-chat", "type": "text", "category": "General"},
                    {"name": "🎉│events", "type": "text", "category": "General"},
                    {"name": "🤖│bot-commands", "type": "text", "category": "General"},
                    {"name": "🔊│General Voice", "type": "voice", "category": "Voice Channels"},
                ],
                "roles": [
                    {"name": "👤 Member", "color": 0x3498db, "permissions": "default"},
                    {"name": "⭐ VIP", "color": 0xf39c12, "permissions": "default"},
                    {"name": "👑 Admin", "color": 0xe74c3c, "permissions": "admin"},
                ],
                "settings": {
                    "welcome_enabled": True,
                    "leveling_enabled": True,
                    "moderation_enabled": True
                }
            }
        }
        
        return templates.get(template, templates["general"])

    async def setup_channels(self, guild: discord.Guild, channels_config: List[dict]) -> List[dict]:
        """Set up channels based on configuration"""
        results = []
        categories = {}
        
        try:
            for channel_config in channels_config:
                try:
                    channel_name = channel_config['name']
                    channel_type = channel_config['type']
                    category_name = channel_config.get('category')
                    
                    # Get or create category
                    category = None
                    if category_name:
                        if category_name not in categories:
                            # Check if category already exists
                            existing_category = discord.utils.get(guild.categories, name=category_name)
                            if existing_category:
                                categories[category_name] = existing_category
                            else:
                                # Create new category
                                new_category = await guild.create_category(category_name)
                                categories[category_name] = new_category
                                await asyncio.sleep(0.5)  # Rate limit prevention
                        
                        category = categories[category_name]
                    
                    # Check if channel already exists
                    clean_name = channel_name.replace('│', '-').replace('│', '-')
                    existing_channel = discord.utils.get(guild.channels, name=clean_name)
                    if existing_channel:
                        results.append({"item": f"Channel: {channel_name}", "success": True, "reason": "Already exists"})
                        continue
                    
                    # Create channel
                    if channel_type == "text":
                        await guild.create_text_channel(
                            name=clean_name,
                            category=category
                        )
                    elif channel_type == "voice":
                        await guild.create_voice_channel(
                            name=channel_name,
                            category=category
                        )
                    
                    results.append({"item": f"Channel: {channel_name}", "success": True, "reason": "Created"})
                    await asyncio.sleep(0.5)  # Rate limit prevention
                    
                except Exception as e:
                    logger.error(f"Error creating channel {channel_config.get('name', 'Unknown')}: {e}")
                    results.append({"item": f"Channel: {channel_config.get('name', 'Unknown')}", "success": False, "reason": str(e)})
            
        except Exception as e:
            logger.error(f"Error in setup_channels: {e}")
            
        return results

    async def setup_roles(self, guild: discord.Guild, roles_config: List[dict]) -> List[dict]:
        """Set up roles based on configuration"""
        results = []
        
        try:
            for role_config in roles_config:
                try:
                    role_name = role_config['name']
                    role_color = role_config.get('color', 0x000000)
                    role_permissions = role_config.get('permissions', 'default')
                    
                    # Check if role already exists
                    existing_role = discord.utils.get(guild.roles, name=role_name)
                    if existing_role:
                        results.append({"item": f"Role: {role_name}", "success": True, "reason": "Already exists"})
                        continue
        
                    # Set permissions
                    permissions = discord.Permissions.default()
                    if role_permissions == 'admin':
                        permissions = discord.Permissions.all()
                    elif role_permissions == 'moderator':
                        permissions.kick_members = True
                        permissions.ban_members = True
                        permissions.manage_messages = True
                        permissions.manage_channels = True
                    
                    # Create role
                    await guild.create_role(
                        name=role_name,
                        color=discord.Color(role_color),
                        permissions=permissions,
                        reason="Quick Setup"
                    )
                    
                    results.append({"item": f"Role: {role_name}", "success": True, "reason": "Created"})
                    await asyncio.sleep(0.5)  # Rate limit prevention
                    
                except Exception as e:
                    logger.error(f"Error creating role {role_config.get('name', 'Unknown')}: {e}")
                    results.append({"item": f"Role: {role_config.get('name', 'Unknown')}", "success": False, "reason": str(e)})
                    
        except Exception as e:
            logger.error(f"Error in setup_roles: {e}")
            
        return results

    async def configure_settings(self, guild_id: int, settings_config: dict) -> List[dict]:
        """Configure basic bot settings"""
        results = []
        
        if not self.db:
            results.append({"item": "Database Settings", "success": False, "reason": "Database not available"})
            return results
        
        try:
            # Configure feature toggles
            feature_updates = {}
            for setting, value in settings_config.items():
                feature_updates[setting] = value
            
            await self.db.feature_toggles.update_one(
                {"guild_id": guild_id},
                {"$set": feature_updates},
                upsert=True
            )
            
            results.append({"item": "Feature Settings", "success": True, "reason": "Configured"})
            
            # Set default welcome message if enabled
            if settings_config.get('welcome_enabled'):
                await self.db.welcomer.update_one(
                    {"guild_id": guild_id},
                    {"$set": {
                        "welcome_message": "Welcome to our server, {user}! 🎉",
                        "welcome_message_enabled": True
                    }},
                    upsert=True
                )
                results.append({"item": "Welcome System", "success": True, "reason": "Enabled"})
            
            # Configure leveling if enabled
            if settings_config.get('leveling_enabled'):
                await self.db.leveling_settings.update_one(
                    {"guild_id": guild_id},
                    {"$set": {
                        "enabled": True,
                        "xp_per_message": 1,
                        "xp_cooldown": 60,
                        "levelup_notifications": True
                    }},
                    upsert=True
                )
                results.append({"item": "Leveling System", "success": True, "reason": "Enabled"})
                
        except Exception as e:
            logger.error(f"Error configuring settings: {e}")
            results.append({"item": "Settings Configuration", "success": False, "reason": str(e)})
            
        return results

async def setup(bot):
    """Add the ServerSetup cog to the bot"""
    await bot.add_cog(ServerSetup(bot))


