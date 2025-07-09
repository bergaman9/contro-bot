import discord
from discord.ui import View, Button, Select
import logging
import datetime
import os
from discord.ext import commands
from typing import Optional, Dict, Any, List
import asyncio

from src.utils.formatting import create_embed

logger = logging.getLogger('community.views.level')

class LevelLeaderboardView(View):
    """Interactive view for the level leaderboard with sorting options"""
    
    def __init__(self, bot, mongo_db, guild_id):
        super().__init__(timeout=300)  # 5 minute timeout
        self.bot = bot
        self.mongo_db = mongo_db
        self.guild_id = guild_id
        self.current_page = 0
        self.sort_by = "xp"  # Default sort
        self.sort_direction = -1  # Descending
        self.items_per_page = 10
        self.message = None
    
    async def send_initial_message(self, ctx):
        """Send the initial leaderboard message"""
        embed = await self.create_leaderboard_embed()
        self.message = await ctx.send(embed=embed, view=self)
        return self.message
    
    async def create_leaderboard_embed(self):
        """Create the leaderboard embed with current settings"""
        # Calculate pagination values
        skip = self.current_page * self.items_per_page
        
        # Get users sorted by the selected field
        users = list(self.mongo_db.users.find(
            {"guild_id": self.guild_id}
        ).sort("level", -1).limit(10))
        
        # Get total count for pagination
        total_users = self.mongo_db.users.count_documents({"guild_id": self.guild_id})
        total_pages = (total_users + self.items_per_page - 1) // self.items_per_page
        
        # Create the embed
        if self.sort_by == "xp":
            title = "🏆 XP Sıralaması"
        elif self.sort_by == "level":
            title = "📊 Seviye Sıralaması"
        elif self.sort_by == "messages":
            title = "💬 Mesaj Sıralaması"
        elif self.sort_by == "voice_minutes":
            title = "🎙️ Ses Kanalı Sıralaması"
        else:
            title = "🏆 Liderlik Tablosu"
        
        embed = create_embed(
            title=title,
            description=f"Sayfa {self.current_page + 1}/{max(1, total_pages)}",
            color=discord.Color.gold()
        )
        
        guild = self.bot.get_guild(self.guild_id)
        
        if not users:
            embed.add_field(name="Bilgi", value="Bu sayfada henüz veri yok!", inline=False)
            return embed
        
        for i, user_data in enumerate(users):
            user_id = user_data["user_id"]
            member = guild.get_member(user_id) if guild else None
            
            if member:
                position = skip + i + 1
                medal = "🥇" if position == 1 else "🥈" if position == 2 else "🥉" if position == 3 else f"{position}."
                
                # Format field based on sort type
                if self.sort_by == "xp":
                    value = f"Seviye: {user_data.get('level', 0)} | XP: {user_data.get('xp', 0)}"
                elif self.sort_by == "level":
                    value = f"Seviye: {user_data.get('level', 0)} | XP: {user_data.get('xp', 0)}"
                elif self.sort_by == "messages":
                    value = f"Mesaj: {user_data.get('messages', 0)} | Seviye: {user_data.get('level', 0)}"
                elif self.sort_by == "voice_minutes":
                    hours = user_data.get('voice_minutes', 0) / 60
                    value = f"Ses: {hours:.1f} saat | Seviye: {user_data.get('level', 0)}"
                else:
                    value = f"Seviye: {user_data.get('level', 0)} | XP: {user_data.get('xp', 0)}"
                
                embed.add_field(
                    name=f"{medal} {member.display_name}",
                    value=value,
                    inline=False
                )
        
        return embed
    
    @discord.ui.button(label="◀️", style=discord.ButtonStyle.secondary)
    async def previous_page(self, interaction: discord.Interaction, button: Button):
        """Show the previous page"""
        await interaction.response.defer()
        
        if self.current_page > 0:
            self.current_page -= 1
            embed = await self.create_leaderboard_embed()
            await interaction.message.edit(embed=embed, view=self)
    
    @discord.ui.button(label="▶️", style=discord.ButtonStyle.secondary)
    async def next_page(self, interaction: discord.Interaction, button: Button):
        """Show the next page"""
        await interaction.response.defer()
        
        total_users = self.mongo_db.users.count_documents({"guild_id": self.guild_id})
        total_pages = (total_users + self.items_per_page - 1) // self.items_per_page
        
        if self.current_page < total_pages - 1:
            self.current_page += 1
            embed = await self.create_leaderboard_embed()
            await interaction.message.edit(embed=embed, view=self)
    
    @discord.ui.select(
        placeholder="Sıralama Kriteri",
        options=[
            discord.SelectOption(label="XP'ye Göre", value="xp", emoji="🏆", default=True),
            discord.SelectOption(label="Seviyeye Göre", value="level", emoji="📊"),
            discord.SelectOption(label="Mesaj Sayısına Göre", value="messages", emoji="💬"),
            discord.SelectOption(label="Ses Kanalı Süresine Göre", value="voice_minutes", emoji="🎙️")
        ]
    )
    async def sort_select(self, interaction: discord.Interaction, select: Select):
        """Handle sort selection"""
        await interaction.response.defer()
        
        self.sort_by = select.values[0]
        self.current_page = 0  # Reset to first page
        
        embed = await self.create_leaderboard_embed()
        await interaction.message.edit(embed=embed, view=self)
    
    async def on_timeout(self):
        """Remove buttons when the view times out"""
        if self.message:
            await self.message.edit(view=None)

class LevelRolesView(View):
    """View for managing level roles settings"""
    
    def __init__(self, bot, mongo_db, guild_id):
        super().__init__(timeout=300)  # 5 minute timeout
        self.bot = bot
        self.mongo_db = mongo_db
        self.guild_id = guild_id
        self.message = None
    
    async def send_initial_message(self, ctx):
        """Send the initial level roles message"""
        embed = await self.create_roles_embed()
        self.message = await ctx.send(embed=embed, view=self)
        return self.message
    
    async def create_roles_embed(self):
        """Create the level roles configuration embed"""
        # Get current level role settings
        config = self.mongo_db.config.find_one({"guild_id": self.guild_id}) or {}
        level_roles = config.get("level_roles", {})
        
        embed = create_embed(
            title="⚙️ Seviye Rol Ayarları",
            description="Seviye sistemindeki roller ve ayarları:",
            color=discord.Color.blue()
        )
        
        guild = self.bot.get_guild(self.guild_id)
        
        if not level_roles:
            embed.add_field(
                name="Bilgi",
                value="Henüz seviye rolü ayarlanmamış. 'Rol Ekle' butonunu kullanarak rol ekleyebilirsiniz.",
                inline=False
            )
        else:
            for level, role_id in sorted(level_roles.items(), key=lambda x: int(x[0])):
                role = guild.get_role(int(role_id))
                if role:
                    embed.add_field(
                        name=f"Seviye {level}",
                        value=f"Rol: {role.mention}",
                        inline=False
                    )
        
        return embed
    
    @discord.ui.button(label="Rol Ekle", style=discord.ButtonStyle.green)
    async def add_role(self, interaction: discord.Interaction, button: Button):
        """Add a level role"""
        await interaction.response.send_modal(AddLevelRoleModal(self.bot, self.mongo_db, self.guild_id, self))
    
    @discord.ui.button(label="Rol Kaldır", style=discord.ButtonStyle.red)
    async def remove_role(self, interaction: discord.Interaction, button: Button):
        """Remove a level role"""
        await interaction.response.send_modal(RemoveLevelRoleModal(self.bot, self.mongo_db, self.guild_id, self))
    
    async def refresh(self, interaction: discord.Interaction):
        """Refresh the embed after changes"""
        embed = await self.create_roles_embed()
        await interaction.message.edit(embed=embed, view=self)
    
    async def on_timeout(self):
        """Remove buttons when the view times out"""
        if self.message:
            await self.message.edit(view=None)

class AddLevelRoleModal(discord.ui.Modal, title="Seviye Rolü Ekle"):
    """Modal for adding a level role"""
    
    def __init__(self, bot, mongo_db, guild_id, parent_view):
        super().__init__()
        self.bot = bot
        self.mongo_db = mongo_db
        self.guild_id = guild_id
        self.parent_view = parent_view
        
        self.level = discord.ui.TextInput(
            label="Seviye",
            placeholder="Rolün verileceği seviye (örn: 5)",
            required=True,
            min_length=1,
            max_length=2
        )
        self.add_item(self.level)
        
        self.role_id = discord.ui.TextInput(
            label="Rol ID",
            placeholder="Rol ID'sini girin",
            required=True,
            min_length=17,
            max_length=20
        )
        self.add_item(self.role_id)
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle form submission"""
        try:
            # Validate level
            try:
                level = int(self.level.value)
                if level < 1 or level > 50:
                    await interaction.response.send_message(
                        embed=create_embed(
                            description="❌ Seviye 1-50 arasında olmalıdır!",
                            color=discord.Color.red()
                        ),
                        ephemeral=True
                    )
                    return
            except ValueError:
                await interaction.response.send_message(
                    embed=create_embed(
                        description="❌ Geçersiz seviye! Sayısal bir değer girin.",
                        color=discord.Color.red()
                    ),
                    ephemeral=True
                )
                return
            
            # Validate role ID
            try:
                role_id = int(self.role_id.value)
                guild = self.bot.get_guild(self.guild_id)
                role = guild.get_role(role_id)
                
                if not role:
                    await interaction.response.send_message(
                        embed=create_embed(
                            description="❌ Belirtilen ID'ye sahip bir rol bulunamadı!",
                            color=discord.Color.red()
                        ),
                        ephemeral=True
                    )
                    return
            except ValueError:
                await interaction.response.send_message(
                    embed=create_embed(
                        description="❌ Geçersiz rol ID! Sayısal bir değer girin.",
                        color=discord.Color.red()
                    ),
                    ephemeral=True
                )
                return
            
            # Update database
            self.mongo_db.config.update_one(
                {"guild_id": self.guild_id},
                {"$set": {f"level_roles.{level}": role_id}},
                upsert=True
            )
            
            await interaction.response.send_message(
                embed=create_embed(
                    description=f"✅ Seviye {level} için {role.mention} rolü başarıyla ayarlandı!",
                    color=discord.Color.green()
                ),
                ephemeral=True
            )
            
            # Refresh parent view
            await self.parent_view.refresh(interaction)
            
        except Exception as e:
            logger.error(f"Error adding level role: {e}", exc_info=True)
            await interaction.response.send_message(
                embed=create_embed(
                    description="❌ Rol eklenirken bir hata oluştu!",
                    color=discord.Color.red()
                ),
                ephemeral=True
            )

class RemoveLevelRoleModal(discord.ui.Modal, title="Seviye Rolü Kaldır"):
    """Modal for removing a level role"""
    
    def __init__(self, bot, mongo_db, guild_id, parent_view):
        super().__init__()
        self.bot = bot
        self.mongo_db = mongo_db
        self.guild_id = guild_id
        self.parent_view = parent_view
        
        self.level = discord.ui.TextInput(
            label="Seviye",
            placeholder="Kaldırmak istediğiniz rolün seviyesi (örn: 5)",
            required=True,
            min_length=1,
            max_length=2
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
                    embed=create_embed(
                        description="❌ Geçersiz seviye! Sayısal bir değer girin.",
                        color=discord.Color.red()
                    ),
                    ephemeral=True
                )
                return
            
            # Check if the level exists
            config = self.mongo_db.config.find_one({"guild_id": self.guild_id}) or {}
            level_roles = config.get("level_roles", {})
            
            if str(level) not in level_roles:
                await interaction.response.send_message(
                    embed=create_embed(
                        description=f"❌ Seviye {level} için tanımlanmış bir rol bulunamadı!",
                        color=discord.Color.red()
                    ),
                    ephemeral=True
                )
                return
            
            # Remove the level role
            self.mongo_db.config.update_one(
                {"guild_id": self.guild_id},
                {"$unset": {f"level_roles.{level}": ""}}
            )
            
            await interaction.response.send_message(
                embed=create_embed(
                    description=f"✅ Seviye {level} için tanımlanmış rol başarıyla kaldırıldı!",
                    color=discord.Color.green()
                ),
                ephemeral=True
            )
            
            # Refresh parent view
            await self.parent_view.refresh(interaction)
            
        except Exception as e:
            logger.error(f"Error removing level role: {e}", exc_info=True)
            await interaction.response.send_message(
                embed=create_embed(
                    description="❌ Rol kaldırılırken bir hata oluştu!",
                    color=discord.Color.red()
                ),
                ephemeral=True
            )
