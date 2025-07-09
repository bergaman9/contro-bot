"""
AI-Powered Server Designer Cog
Uses Perplexity AI to design Discord servers based on natural language descriptions
"""

import asyncio
import json
import re
from typing import Dict, List, Optional, Any
import discord
from discord.ext import commands
from discord import app_commands
import logging

from src.cogs.base import BaseCog
from src.ai.providers.perplexity import PerplexityProvider, ServerStructure
from src.integrations.discord_bots.bot_manager import BotManager
from src.utils.common.error_handler import handle_command_error

logger = logging.getLogger(__name__)

class ServerDesignView(discord.ui.View):
    """Interactive view for server design process"""
    
    def __init__(self, server_structure: ServerStructure, bot_manager: BotManager, user_id: int):
        super().__init__(timeout=300)
        self.server_structure = server_structure
        self.bot_manager = bot_manager
        self.user_id = user_id
        self.confirmed = False
    
    @discord.ui.button(label="✅ Create Server", style=discord.ButtonStyle.green)
    async def confirm_creation(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Only the command user can confirm server creation.", ephemeral=True)
            return
        
        self.confirmed = True
        button.disabled = True
        self.stop()
        
        await interaction.response.edit_message(content="🔄 Creating server structure...", view=self)
    
    @discord.ui.button(label="📝 Modify Description", style=discord.ButtonStyle.secondary)
    async def modify_description(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Only the command user can modify the description.", ephemeral=True)
            return
        
        modal = ModifyDescriptionModal(self.server_structure)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="🤖 Suggest Bots", style=discord.ButtonStyle.primary)
    async def suggest_bots(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Only the command user can view bot suggestions.", ephemeral=True)
            return
        
        # Determine server type from description
        description_lower = self.server_structure.description.lower()
        server_type = "community"  # default
        
        if any(word in description_lower for word in ["game", "gaming", "esports"]):
            server_type = "gaming"
        elif any(word in description_lower for word in ["business", "work", "professional"]):
            server_type = "business"
        elif any(word in description_lower for word in ["music", "band", "artist"]):
            server_type = "music"
        elif any(word in description_lower for word in ["türk", "turkish", "turkey"]):
            server_type = "turkish"
        
        recommended_bots = self.bot_manager.get_recommended_bots_for_server_type(server_type)
        
        embed = discord.Embed(
            title="🤖 Recommended Bots",
            description=f"Based on your server type (**{server_type}**), here are some recommended bots:",
            color=discord.Color.blue()
        )
        
        for bot_name in recommended_bots[:5]:  # Limit to top 5
            bot_config = self.bot_manager.get_bot_config(bot_name)
            if bot_config:
                embed.add_field(
                    name=f"{bot_config.name}",
                    value=f"{bot_config.description}\n**Features:** {', '.join(bot_config.features[:3])}",
                    inline=False
                )
        
        embed.set_footer(text="Use /bots invite <bot_name> to invite these bots after server creation")
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @discord.ui.button(label="❌ Cancel", style=discord.ButtonStyle.red)
    async def cancel_creation(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Only the command user can cancel.", ephemeral=True)
            return
        
        self.stop()
        await interaction.response.edit_message(content="❌ Server creation cancelled.", view=None)

class ModifyDescriptionModal(discord.ui.Modal):
    """Modal for modifying server description"""
    
    def __init__(self, server_structure: ServerStructure):
        super().__init__(title="Modify Server Description")
        self.server_structure = server_structure
        
        self.description_input = discord.ui.TextInput(
            label="New Server Description",
            placeholder="Describe your server in detail...",
            default=server_structure.description,
            style=discord.TextStyle.paragraph,
            max_length=2000
        )
        self.add_item(self.description_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            "📝 Description updated! Please use the command again to regenerate the server structure.",
            ephemeral=True
        )

class ServerDesigner(BaseCog):
    """AI-powered server designer cog"""
    
    def __init__(self, bot: commands.Bot):
        super().__init__(bot)
        self.perplexity_api_key = self.bot.config.get("ai", {}).get("providers", {}).get("perplexity", {}).get("api_key")
        self.bot_manager = BotManager()
        
        if not self.perplexity_api_key:
            logger.warning("Perplexity API key not configured. AI server designer will not work.")
    
    @app_commands.command(name="design", description="🎨 Design a Discord server using AI")
    @app_commands.describe(
        description="Describe your ideal Discord server (purpose, theme, audience, etc.)",
        server_type="Type of server (optional, AI will auto-detect)"
    )
    async def design_server(
        self,
        interaction: discord.Interaction,
        description: str,
        server_type: Optional[str] = None
    ):
        """Design a Discord server using AI"""
        try:
            if not self.perplexity_api_key:
                await interaction.response.send_message(
                    "❌ AI server designer is not configured. Please contact an administrator.",
                    ephemeral=True
                )
                return
            
            # Defer response since AI generation might take time
            await interaction.response.defer()
            
            # Generate server structure using AI
            async with PerplexityProvider(self.perplexity_api_key) as provider:
                server_structure = await provider.generate_server_structure(
                    description, 
                    server_type or "community"
                )
            
            # Create preview embed
            embed = await self._create_preview_embed(server_structure)
            
            # Create interactive view
            view = ServerDesignView(server_structure, self.bot_manager, interaction.user.id)
            
            await interaction.followup.send(embed=embed, view=view)
            
            # Wait for user confirmation
            await view.wait()
            
            if view.confirmed:
                await self._create_server_structure(interaction, server_structure)
        
        except Exception as e:
            await handle_command_error(interaction, e, "design server")
    
    @app_commands.command(name="analyze", description="📊 Analyze current server and get optimization suggestions")
    async def analyze_server(self, interaction: discord.Interaction):
        """Analyze current server structure and suggest optimizations"""
        try:
            if not self.perplexity_api_key:
                await interaction.response.send_message(
                    "❌ AI server analyzer is not configured. Please contact an administrator.",
                    ephemeral=True
                )
                return
            
            await interaction.response.defer()
            
            # Gather current server data
            server_data = await self._gather_server_data(interaction.guild)
            
            # Get AI suggestions
            async with PerplexityProvider(self.perplexity_api_key) as provider:
                suggestions = await provider.suggest_optimizations(server_data)
            
            # Create suggestions embed
            embed = discord.Embed(
                title="📊 Server Analysis & Optimization Suggestions",
                description=f"Analysis for **{interaction.guild.name}**",
                color=discord.Color.blue()
            )
            
            if not suggestions:
                embed.add_field(
                    name="✅ No Issues Found",
                    value="Your server structure looks well-organized!",
                    inline=False
                )
            else:
                for i, suggestion in enumerate(suggestions[:5], 1):  # Limit to 5 suggestions
                    priority_emoji = {
                        "high": "🔴",
                        "medium": "🟡", 
                        "low": "🟢"
                    }.get(suggestion.get("priority", "medium"), "🟡")
                    
                    embed.add_field(
                        name=f"{priority_emoji} {suggestion['title']}",
                        value=f"{suggestion['description']}\n\n**Implementation:** {suggestion['implementation']}",
                        inline=False
                    )
            
            embed.set_footer(text="💡 These suggestions are AI-generated. Use your best judgment when implementing them.")
            
            await interaction.followup.send(embed=embed)
        
        except Exception as e:
            await handle_command_error(interaction, e, "analyze server")
    
    async def _create_preview_embed(self, server_structure: ServerStructure) -> discord.Embed:
        """Create preview embed for server structure"""
        embed = discord.Embed(
            title=f"🎨 Server Design: {server_structure.name}",
            description=server_structure.description,
            color=discord.Color.green()
        )
        
        # Add categories and channels
        if server_structure.categories:
            categories_text = ""
            for category in server_structure.categories[:5]:  # Limit to first 5 categories
                categories_text += f"**📁 {category['name']}**\n"
                for channel in category.get('channels', [])[:3]:  # Limit to 3 channels per category
                    channel_emoji = "🔊" if channel.get('type') == 'voice' else "💬"
                    categories_text += f"  {channel_emoji} {channel['name']}\n"
                if len(category.get('channels', [])) > 3:
                    categories_text += f"  ... and {len(category['channels']) - 3} more\n"
                categories_text += "\n"
            
            if len(server_structure.categories) > 5:
                categories_text += f"... and {len(server_structure.categories) - 5} more categories"
            
            embed.add_field(
                name="📂 Categories & Channels",
                value=categories_text or "No categories defined",
                inline=False
            )
        
        # Add roles
        if server_structure.roles:
            roles_text = ""
            for role in server_structure.roles[:8]:  # Limit to 8 roles
                color = role.get('color', '#99AAB5')
                roles_text += f"🎭 **{role['name']}** `{color}`\n"
            
            if len(server_structure.roles) > 8:
                roles_text += f"... and {len(server_structure.roles) - 8} more roles"
            
            embed.add_field(
                name="🎭 Roles",
                value=roles_text or "No roles defined",
                inline=True
            )
        
        # Add rules preview
        if server_structure.rules:
            rules_text = ""
            for i, rule in enumerate(server_structure.rules[:3], 1):
                rules_text += f"{i}. {rule}\n"
            
            if len(server_structure.rules) > 3:
                rules_text += f"... and {len(server_structure.rules) - 3} more rules"
            
            embed.add_field(
                name="📋 Server Rules",
                value=rules_text or "No rules defined",
                inline=True
            )
        
        embed.add_field(
            name="👋 Welcome Message",
            value=server_structure.welcome_message[:200] + ("..." if len(server_structure.welcome_message) > 200 else ""),
            inline=False
        )
        
        embed.set_footer(text="⚠️ This is a preview. Click ✅ to create the actual server structure.")
        
        return embed
    
    async def _create_server_structure(self, interaction: discord.Interaction, server_structure: ServerStructure):
        """Actually create the server structure"""
        guild = interaction.guild
        created_items = {
            "categories": 0,
            "channels": 0,
            "roles": 0,
            "errors": []
        }
        
        try:
            # Create roles first
            for role_data in server_structure.roles:
                try:
                    color = discord.Color(int(role_data.get('color', '#99AAB5').replace('#', ''), 16))
                    await guild.create_role(
                        name=role_data['name'],
                        color=color,
                        hoist=role_data.get('hoist', False),
                        mentionable=role_data.get('mentionable', True),
                        reason="AI Server Designer"
                    )
                    created_items["roles"] += 1
                    await asyncio.sleep(1)  # Rate limit protection
                except Exception as e:
                    created_items["errors"].append(f"Role '{role_data['name']}': {str(e)}")
            
            # Create categories and channels
            for category_data in server_structure.categories:
                try:
                    category = await guild.create_category(
                        name=category_data['name'],
                        reason="AI Server Designer"
                    )
                    created_items["categories"] += 1
                    
                    # Create channels in category
                    for channel_data in category_data.get('channels', []):
                        try:
                            channel_type = channel_data.get('type', 'text')
                            
                            if channel_type == 'voice':
                                await category.create_voice_channel(
                                    name=channel_data['name'],
                                    reason="AI Server Designer"
                                )
                            else:  # text channel
                                await category.create_text_channel(
                                    name=channel_data['name'],
                                    topic=channel_data.get('description'),
                                    nsfw=channel_data.get('nsfw', False),
                                    slowmode_delay=channel_data.get('slowmode', 0),
                                    reason="AI Server Designer"
                                )
                            
                            created_items["channels"] += 1
                            await asyncio.sleep(1)  # Rate limit protection
                        
                        except Exception as e:
                            created_items["errors"].append(f"Channel '{channel_data['name']}': {str(e)}")
                    
                    await asyncio.sleep(2)  # Extra delay between categories
                
                except Exception as e:
                    created_items["errors"].append(f"Category '{category_data['name']}': {str(e)}")
            
            # Create summary embed
            summary_embed = discord.Embed(
                title="✅ Server Structure Created!",
                description=f"Successfully created server structure for **{server_structure.name}**",
                color=discord.Color.green()
            )
            
            summary_embed.add_field(
                name="📊 Created Items",
                value=f"Categories: {created_items['categories']}\nChannels: {created_items['channels']}\nRoles: {created_items['roles']}",
                inline=True
            )
            
            if created_items["errors"]:
                error_text = "\n".join(created_items["errors"][:5])
                if len(created_items["errors"]) > 5:
                    error_text += f"\n... and {len(created_items['errors']) - 5} more errors"
                
                summary_embed.add_field(
                    name="⚠️ Errors",
                    value=error_text,
                    inline=True
                )
            
            summary_embed.add_field(
                name="💡 Next Steps",
                value="• Configure channel permissions\n• Set up welcome messages\n• Invite recommended bots\n• Customize server settings",
                inline=False
            )
            
            await interaction.edit_original_response(embed=summary_embed, view=None)
        
        except Exception as e:
            error_embed = discord.Embed(
                title="❌ Error Creating Server Structure",
                description=f"An error occurred while creating the server structure: {str(e)}",
                color=discord.Color.red()
            )
            await interaction.edit_original_response(embed=error_embed, view=None)
    
    async def _gather_server_data(self, guild: discord.Guild) -> Dict[str, Any]:
        """Gather current server data for analysis"""
        data = {
            "name": guild.name,
            "member_count": guild.member_count,
            "categories": [],
            "channels": [],
            "roles": [],
            "permissions": {}
        }
        
        # Gather categories and channels
        for category in guild.categories:
            category_data = {
                "name": category.name,
                "position": category.position,
                "channels": []
            }
            
            for channel in category.channels:
                channel_data = {
                    "name": channel.name,
                    "type": str(channel.type),
                    "position": channel.position
                }
                category_data["channels"].append(channel_data)
            
            data["categories"].append(category_data)
        
        # Gather channels without category
        for channel in guild.channels:
            if channel.category is None:
                data["channels"].append({
                    "name": channel.name,
                    "type": str(channel.type),
                    "position": getattr(channel, 'position', 0)
                })
        
        # Gather roles
        for role in guild.roles[1:]:  # Skip @everyone
            data["roles"].append({
                "name": role.name,
                "color": str(role.color),
                "position": role.position,
                "permissions": [perm for perm, value in role.permissions if value]
            })
        
        return data

async def setup(bot: commands.Bot):
    await bot.add_cog(ServerDesigner(bot)) 