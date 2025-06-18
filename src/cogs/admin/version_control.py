"""
CONTRO Bot - Version Management Commands
Advanced version control commands for administrators
"""

import discord
from discord.ext import commands
from discord import app_commands
import json
from datetime import datetime
from typing import Optional, List
import logging

from utils.version.version_manager import get_version_manager
from utils.core.formatting import create_embed

logger = logging.getLogger(__name__)

class VersionCommands(commands.Cog):
    """Version control and management commands"""
    
    def __init__(self, bot):
        self.bot = bot
        self.version_manager = get_version_manager()
    
    @app_commands.command(name="version", description="🔖 Show current bot version and information")
    async def version_info(self, interaction: discord.Interaction):
        """Display current version information"""
        try:
            current_version = self.version_manager.get_current_version()
            version_history = self.version_manager.get_version_history(1)
            
            embed = create_embed(
                title="🤖 CONTRO Bot Version Information",
                description=f"**Current Version:** `{current_version}`",
                color=discord.Color.blue()
            )
            
            if version_history:
                latest = version_history[0]
                embed.add_field(
                    name="📅 Release Date",
                    value=latest.get('date', 'Unknown'),
                    inline=True
                )
                
                if latest.get('git_commit'):
                    embed.add_field(
                        name="🔄 Git Commit",
                        value=f"`{latest['git_commit']}`",
                        inline=True
                    )
                
                embed.add_field(
                    name="🚀 Hosting",
                    value="Raspberry Pi 5",
                    inline=True
                )
                
                if latest.get('features'):
                    features_text = "\\n".join([f"• {f}" for f in latest['features'][:5]])
                    if len(latest['features']) > 5:
                        features_text += f"\\n• ... and {len(latest['features']) - 5} more"
                    
                    embed.add_field(
                        name="✨ Recent Features",
                        value=features_text,
                        inline=False
                    )
            
            embed.add_field(
                name="🔗 System Info",
                value=f"• **Database:** MongoDB (Async)\\n• **Language:** Python 3.10+\\n• **Framework:** discord.py 2.3.2",
                inline=False
            )
            
            embed.set_footer(text=f"Bot developed by your team • Version tracked automatically")
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in version command: {e}")
            await interaction.response.send_message(
                "❌ Error retrieving version information.", 
                ephemeral=True
            )
    
    @app_commands.command(name="version_history", description="📖 Show version history and changelog")
    @app_commands.describe(limit="Number of versions to show (default: 5, max: 20)")
    async def version_history(self, interaction: discord.Interaction, limit: Optional[int] = 5):
        """Display version history"""
        try:
            if limit > 20:
                limit = 20
            elif limit < 1:
                limit = 5
            
            versions = self.version_manager.get_version_history(limit)
            
            if not versions:
                embed = create_embed(
                    title="📖 Version History",
                    description="No version history available.",
                    color=discord.Color.orange()
                )
                await interaction.response.send_message(embed=embed)
                return
            
            embed = create_embed(
                title="📖 CONTRO Bot Version History",
                description=f"Showing last {len(versions)} versions",
                color=discord.Color.green()
            )
            
            for version in reversed(versions):  # Show newest first
                features_text = ""
                if version.get('features'):
                    features_text += "**Features:**\\n" + "\\n".join([f"• {f}" for f in version['features'][:3]])
                    if len(version['features']) > 3:
                        features_text += f"\\n• ... {len(version['features']) - 3} more"
                
                if version.get('fixes'):
                    if features_text:
                        features_text += "\\n\\n"
                    features_text += "**Fixes:**\\n" + "\\n".join([f"• {f}" for f in version['fixes'][:2]])
                    if len(version['fixes']) > 2:
                        features_text += f"\\n• ... {len(version['fixes']) - 2} more"
                
                if not features_text:
                    features_text = "No detailed changelog available"
                
                embed.add_field(
                    name=f"🔖 Version {version['version']} - {version.get('date', 'Unknown')}",
                    value=features_text[:1024],  # Discord field limit
                    inline=False
                )
            
            embed.set_footer(text="Use /version for current version details")
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in version history command: {e}")
            await interaction.response.send_message(
                "❌ Error retrieving version history.", 
                ephemeral=True
            )
    
    @app_commands.command(name="create_version", description="🎯 Create a new version (Admin only)")
    @app_commands.describe(
        version_type="Type of version increment",
        description="Description of this version"
    )
    @app_commands.choices(version_type=[
        app_commands.Choice(name="Major (X.0.0)", value="major"),
        app_commands.Choice(name="Minor (0.X.0)", value="minor"),
        app_commands.Choice(name="Patch (0.0.X)", value="patch")
    ])
    async def create_version(
        self, 
        interaction: discord.Interaction, 
        version_type: str = "patch",
        description: Optional[str] = None
    ):
        """Create a new version (Admin only)"""
        try:
            if not interaction.user.guild_permissions.administrator:
                await interaction.response.send_message(
                    "❌ You need administrator permissions to create versions.", 
                    ephemeral=True
                )
                return
            
            # Show modal for detailed version info
            modal = VersionCreationModal(self.version_manager, version_type, description)
            await interaction.response.send_modal(modal)
            
        except Exception as e:
            logger.error(f"Error in create version command: {e}")
            await interaction.response.send_message(
                "❌ Error creating version.", 
                ephemeral=True
            )
    
    @app_commands.command(name="version_check", description="🔍 Check for potential version updates")
    async def version_check(self, interaction: discord.Interaction):
        """Check if version should be updated"""
        try:
            if not interaction.user.guild_permissions.administrator:
                await interaction.response.send_message(
                    "❌ You need administrator permissions to check versions.", 
                    ephemeral=True
                )
                return
            
            check_result = self.version_manager.auto_version_check()
            
            embed = create_embed(
                title="🔍 Version Update Check",
                color=discord.Color.blue()
            )
            
            if check_result:
                embed.description = f"⚠️ **Update Recommended**\\n{check_result}"
                embed.color = discord.Color.orange()
                embed.add_field(
                    name="Recommended Action",
                    value="Consider creating a new version with `/create_version`",
                    inline=False
                )
            else:
                embed.description = "✅ **Version is up to date**\\nNo version update needed at this time."
                embed.color = discord.Color.green()
            
            embed.add_field(
                name="Current Version",
                value=f"`{self.version_manager.get_current_version()}`",
                inline=True
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error in version check command: {e}")
            await interaction.response.send_message(
                "❌ Error checking version status.", 
                ephemeral=True
            )

class VersionCreationModal(discord.ui.Modal):
    """Modal for creating new versions with detailed information"""
    
    def __init__(self, version_manager, version_type: str, description: str = None):
        super().__init__(title=f"Create New {version_type.title()} Version")
        self.version_manager = version_manager
        self.version_type = version_type
        
        # Description field
        self.description_field = discord.ui.TextInput(
            label="Version Description",
            placeholder="Brief description of this version...",
            default=description or f"New {version_type} version release",
            max_length=200,
            required=True
        )
        self.add_item(self.description_field)
        
        # Features field
        self.features_field = discord.ui.TextInput(
            label="New Features (one per line)",
            placeholder="• Feature 1\\n• Feature 2\\n• Feature 3",
            style=discord.TextStyle.paragraph,
            max_length=1000,
            required=False
        )
        self.add_item(self.features_field)
        
        # Fixes field
        self.fixes_field = discord.ui.TextInput(
            label="Bug Fixes (one per line)",
            placeholder="• Fixed issue 1\\n• Resolved problem 2",
            style=discord.TextStyle.paragraph,
            max_length=800,
            required=False
        )
        self.add_item(self.fixes_field)
        
        # Upcoming field
        self.upcoming_field = discord.ui.TextInput(
            label="Upcoming Features (one per line)",
            placeholder="• Planned feature 1\\n• Future enhancement 2",
            style=discord.TextStyle.paragraph,
            max_length=600,
            required=False
        )
        self.add_item(self.upcoming_field)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Parse features, fixes, and upcoming
            features = [f.strip().lstrip('•').strip() for f in self.features_field.value.split('\\n') if f.strip()]
            fixes = [f.strip().lstrip('•').strip() for f in self.fixes_field.value.split('\\n') if f.strip()]
            upcoming = [f.strip().lstrip('•').strip() for f in self.upcoming_field.value.split('\\n') if f.strip()]
            
            # Create version
            new_version = self.version_manager.add_version(
                version_type=self.version_type,
                features=features,
                fixes=fixes,
                upcoming=upcoming,
                description=self.description_field.value
            )
            
            # Create success embed
            embed = create_embed(
                title="✅ Version Created Successfully",
                description=f"**New Version:** `{new_version}`\\n**Type:** {self.version_type.title()}",
                color=discord.Color.green()
            )
            
            embed.add_field(
                name="📝 Description",
                value=self.description_field.value,
                inline=False
            )
            
            if features:
                embed.add_field(
                    name="✨ Features Added",
                    value="\\n".join([f"• {f}" for f in features[:5]]),
                    inline=False
                )
            
            if fixes:
                embed.add_field(
                    name="🐛 Fixes Applied",
                    value="\\n".join([f"• {f}" for f in fixes[:3]]),
                    inline=False
                )
            
            embed.add_field(
                name="📅 Created",
                value=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                inline=True
            )
            
            embed.set_footer(text="Version tracking updated automatically • CHANGELOG.md updated")
            
            await interaction.response.send_message(embed=embed)
            
            # Try to create git tag
            if self.version_manager.create_git_tag(new_version):
                await interaction.followup.send(
                    f"🏷️ Git tag `v{new_version}` created and pushed successfully!",
                    ephemeral=True
                )
            
        except Exception as e:
            logger.error(f"Error creating version: {e}")
            await interaction.response.send_message(
                f"❌ Error creating version: {str(e)}",
                ephemeral=True
            )

async def setup(bot):
    await bot.add_cog(VersionCommands(bot))
    logger.info("VersionCommands cog loaded successfully")
