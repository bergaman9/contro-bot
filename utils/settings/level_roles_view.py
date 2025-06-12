import discord
from discord import ui
import logging
from utils.core.formatting import create_embed
from utils.database.connection import initialize_mongodb

logger = logging.getLogger(__name__)

class LevelRolesManagementView(discord.ui.View):
    """Enhanced view for managing level roles with Add/Remove functionality"""
    
    def __init__(self, bot, guild_id):
        super().__init__(timeout=300)
        self.bot = bot
        self.guild_id = guild_id
        self.mongo_db = initialize_mongodb()
    
    async def get_level_roles(self):
        """Get current level roles configuration"""
        try:
            settings = await self.mongo_db.levelling_settings.find_one({"guild_id": int(self.guild_id)})
            return settings.get("level_roles", {}) if settings else {}
        except Exception as e:
            logger.error(f"Error getting level roles: {e}")
            return {}
    
    async def save_level_roles(self, level_roles):
        """Save level roles configuration"""
        try:
            await self.mongo_db.levelling_settings.update_one(
                {"guild_id": int(self.guild_id)},
                {"$set": {"level_roles": level_roles}},
                upsert=True
            )
            return True
        except Exception as e:
            logger.error(f"Error saving level roles: {e}")
            return False
    
    async def create_level_roles_embed(self):
        """Create embed showing current level roles"""
        level_roles = await self.get_level_roles()
        guild = self.bot.get_guild(self.guild_id)
        
        embed = discord.Embed(
            title="👑 Level Roles Configuration",
            description="Current level roles in your server:",
            color=discord.Color.gold()
        )
        
        if not level_roles:
            embed.add_field(
                name="📝 No Level Roles Configured",
                value="Use the 'Add Level Role' button to configure automatic role rewards for specific levels.",
                inline=False
            )
        else:
            # Sort by level and display
            sorted_roles = sorted(level_roles.items(), key=lambda x: int(x[0]))
            
            for level, role_id in sorted_roles:
                role = guild.get_role(int(role_id)) if guild else None
                if role:
                    embed.add_field(
                        name=f"Level {level}",
                        value=f"Role: {role.mention}",
                        inline=True
                    )
                else:
                    embed.add_field(
                        name=f"Level {level}",
                        value=f"Role: ❌ Role not found (ID: {role_id})",
                        inline=True
                    )
        
        embed.set_footer(text=f"Total configured: {len(level_roles)} level roles")
        return embed
    
    @discord.ui.button(label="➕ Add Level Role", style=discord.ButtonStyle.green, row=0)
    async def add_level_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Add a new level role"""
        try:
            modal = AddLevelRoleModal(self)
            await interaction.response.send_modal(modal)
        except Exception as e:
            await interaction.response.send_message(
                embed=create_embed(f"Error: {str(e)}", discord.Color.red()),
                ephemeral=True
            )
    
    @discord.ui.button(label="➖ Remove Level Role", style=discord.ButtonStyle.red, row=0)
    async def remove_level_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Remove a level role"""
        try:
            level_roles = await self.get_level_roles()
            if not level_roles:
                await interaction.response.send_message(
                    embed=create_embed("No level roles configured to remove.", discord.Color.yellow()),
                    ephemeral=True
                )
                return
            
            modal = RemoveLevelRoleModal(self)
            await interaction.response.send_modal(modal)
        except Exception as e:
            await interaction.response.send_message(
                embed=create_embed(f"Error: {str(e)}", discord.Color.red()),
                ephemeral=True
            )
    
    @discord.ui.button(label="🔄 Refresh View", style=discord.ButtonStyle.secondary, row=0)
    async def refresh_view(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Refresh the level roles view"""
        try:
            embed = await self.create_level_roles_embed()
            await interaction.response.edit_message(embed=embed, view=self)
        except Exception as e:
            await interaction.response.send_message(
                embed=create_embed(f"Error: {str(e)}", discord.Color.red()),
                ephemeral=True
            )
    
    @discord.ui.button(label="🗑️ Clear All Roles", style=discord.ButtonStyle.danger, row=1)
    async def clear_all_roles(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Clear all level roles"""
        try:
            view = ConfirmClearAllRolesView(self)
            embed = discord.Embed(
                title="⚠️ Confirm Clear All",
                description="Are you sure you want to remove ALL level roles? This action cannot be undone.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(
                embed=create_embed(f"Error: {str(e)}", discord.Color.red()),
                ephemeral=True
            )
    
    async def refresh_embed(self, interaction: discord.Interaction):
        """Refresh the main embed"""
        try:
            embed = await self.create_level_roles_embed()
            await interaction.edit_original_response(embed=embed, view=self)
        except Exception as e:
            logger.error(f"Error refreshing embed: {e}")

class AddLevelRoleModal(discord.ui.Modal, title="Add Level Role"):
    """Modal for adding a level role"""
    
    def __init__(self, parent_view):
        super().__init__()
        self.parent_view = parent_view
        
        self.level = discord.ui.TextInput(
            label="Level",
            placeholder="Level number (e.g., 5, 10, 25)",
            required=True,
            min_length=1,
            max_length=3
        )
        self.add_item(self.level)
        
        self.role = discord.ui.TextInput(
            label="Role",
            placeholder="Role ID or @role mention",
            required=True,
            min_length=1,
            max_length=100
        )
        self.add_item(self.role)
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle form submission"""
        try:
            # Validate level
            try:
                level = int(self.level.value)
                if level < 1 or level > 200:
                    await interaction.response.send_message(
                        embed=create_embed("❌ Level must be between 1 and 200!", discord.Color.red()),
                        ephemeral=True
                    )
                    return
            except ValueError:
                await interaction.response.send_message(
                    embed=create_embed("❌ Invalid level! Please enter a number.", discord.Color.red()),
                    ephemeral=True
                )
                return
            
            # Parse role input
            role_input = self.role.value.strip()
            role = None
            guild = interaction.guild
            
            # Try to parse role ID or mention
            if role_input.startswith('<@&') and role_input.endswith('>'):
                # Role mention format
                role_id = role_input[3:-1]
                try:
                    role = guild.get_role(int(role_id))
                except ValueError:
                    pass
            elif role_input.isdigit():
                # Role ID format
                try:
                    role = guild.get_role(int(role_input))
                except ValueError:
                    pass
            else:
                # Try to find role by name
                role = discord.utils.get(guild.roles, name=role_input)
            
            if not role:
                await interaction.response.send_message(
                    embed=create_embed("❌ Role not found! Please use a valid role ID, mention, or name.", discord.Color.red()),
                    ephemeral=True
                )
                return
            
            # Check if level already has a role
            level_roles = await self.parent_view.get_level_roles()
            if str(level) in level_roles:
                await interaction.response.send_message(
                    embed=create_embed(f"❌ Level {level} already has a role configured! Remove it first if you want to change it.", discord.Color.red()),
                    ephemeral=True
                )
                return
            
            # Add the level role
            level_roles[str(level)] = role.id
            if await self.parent_view.save_level_roles(level_roles):
                await interaction.response.send_message(
                    embed=create_embed(f"✅ Successfully added {role.mention} for level {level}!", discord.Color.green()),
                    ephemeral=True
                )
                # Refresh the parent view
                await self.parent_view.refresh_embed(interaction)
            else:
                await interaction.response.send_message(
                    embed=create_embed("❌ Failed to save level role configuration.", discord.Color.red()),
                    ephemeral=True
                )
                
        except Exception as e:
            logger.error(f"Error adding level role: {e}")
            await interaction.response.send_message(
                embed=create_embed("❌ An error occurred while adding the level role.", discord.Color.red()),
                ephemeral=True
            )

class RemoveLevelRoleModal(discord.ui.Modal, title="Remove Level Role"):
    """Modal for removing a level role"""
    
    def __init__(self, parent_view):
        super().__init__()
        self.parent_view = parent_view
        
        self.level = discord.ui.TextInput(
            label="Level",
            placeholder="Level number to remove (e.g., 5, 10, 25)",
            required=True,
            min_length=1,
            max_length=3
        )
        self.add_item(self.level)
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle form submission"""
        try:
            # Validate level
            try:
                level = int(self.level.value)
            except ValueError:
                await interaction.response.send_message(
                    embed=create_embed("❌ Invalid level! Please enter a number.", discord.Color.red()),
                    ephemeral=True
                )
                return
            
            # Check if level exists
            level_roles = await self.parent_view.get_level_roles()
            if str(level) not in level_roles:
                await interaction.response.send_message(
                    embed=create_embed(f"❌ No role configured for level {level}!", discord.Color.red()),
                    ephemeral=True
                )
                return
            
            # Remove the level role
            role_id = level_roles[str(level)]
            role = interaction.guild.get_role(role_id)
            role_name = role.name if role else f"Role ID {role_id}"
            
            del level_roles[str(level)]
            
            if await self.parent_view.save_level_roles(level_roles):
                await interaction.response.send_message(
                    embed=create_embed(f"✅ Successfully removed role '{role_name}' from level {level}!", discord.Color.green()),
                    ephemeral=True
                )
                # Refresh the parent view
                await self.parent_view.refresh_embed(interaction)
            else:
                await interaction.response.send_message(
                    embed=create_embed("❌ Failed to save level role configuration.", discord.Color.red()),
                    ephemeral=True
                )
                
        except Exception as e:
            logger.error(f"Error removing level role: {e}")
            await interaction.response.send_message(
                embed=create_embed("❌ An error occurred while removing the level role.", discord.Color.red()),
                ephemeral=True
            )

class ConfirmClearAllRolesView(discord.ui.View):
    """Confirmation view for clearing all level roles"""
    
    def __init__(self, parent_view):
        super().__init__(timeout=60)
        self.parent_view = parent_view
    
    @discord.ui.button(label="✅ Yes, Clear All", style=discord.ButtonStyle.danger)
    async def confirm_clear(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Confirm clearing all level roles"""
        try:
            if await self.parent_view.save_level_roles({}):
                await interaction.response.send_message(
                    embed=create_embed("✅ All level roles have been cleared!", discord.Color.green()),
                    ephemeral=True
                )
                # Refresh the parent view
                await self.parent_view.refresh_embed(interaction)
            else:
                await interaction.response.send_message(
                    embed=create_embed("❌ Failed to clear level roles.", discord.Color.red()),
                    ephemeral=True
                )
        except Exception as e:
            logger.error(f"Error clearing level roles: {e}")
            await interaction.response.send_message(
                embed=create_embed("❌ An error occurred while clearing level roles.", discord.Color.red()),
                ephemeral=True
            )
    
    @discord.ui.button(label="❌ Cancel", style=discord.ButtonStyle.secondary)
    async def cancel_clear(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Cancel clearing level roles"""
        await interaction.response.send_message(
            embed=create_embed("❌ Cancelled clearing level roles.", discord.Color.blue()),
            ephemeral=True
        )
