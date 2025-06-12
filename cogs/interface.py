import discord
from discord.ext import commands
from discord import app_commands
import logging
import asyncio
import re
import os
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Union, Any
import motor.motor_asyncio
from pymongo import ReturnDocument

from utils.database.connection import get_async_db, initialize_mongodb
from utils.core.formatting import create_embed
from utils.steam import SteamAPI

logger = logging.getLogger('interface')

# Database schema for user profiles
USER_PROFILE_SCHEMA = {
    "user_id": "",  # Discord user ID
    "guild_id": "",  # Discord guild ID
    "registered_at": None,  # Datetime of registration
    "username": "",  # Discord username
    "nickname": "",  # Server nickname
    "game_data": {
        "steam_id": None,  # Steam ID
        "valorant_id": None,  # Valorant ID
        "lol_username": None,  # League of Legends username
        "fortnite_username": None,  # Fortnite username
        # Add more games as needed
    },
    "temp_channel_settings": {
        "default_name": None,  # Default name for temp channels
        "default_limit": None,  # Default user limit
        "auto_lock": False,  # Automatically lock channel when created
        "bitrate": None,  # Custom bitrate for channels
    },
    "preferences": {
        "theme": "default",
        "notifications": True,
        "privacy_level": "public"  # public, friends, private
    }
}

class UserProfileModal(discord.ui.Modal):
    """Modal for user profile editing"""
    
    def __init__(self, user_data=None):
        super().__init__(title="Profil Düzenle")
        
        # Set default values from user data if available
        nickname = user_data.get("nickname", "") if user_data else ""
        steam_id = user_data.get("game_data", {}).get("steam_id", "") if user_data else ""
        valorant_id = user_data.get("game_data", {}).get("valorant_id", "") if user_data else ""
        lol_username = user_data.get("game_data", {}).get("lol_username", "") if user_data else ""
        
        self.nickname = discord.ui.TextInput(
            label="Kullanıcı Adı",
            placeholder="Sunucuda görünmesini istediğiniz isim",
            default=nickname,
            required=False
        )
        self.steam_id = discord.ui.TextInput(
            label="Steam ID",
            placeholder="Steam profilinizin ID'si veya özel URL'si",
            default=steam_id,
            required=False
        )
        self.valorant_id = discord.ui.TextInput(
            label="Valorant ID",
            placeholder="Valorant kullanıcı adınız ve tag (örn: username#tag)",
            default=valorant_id,
            required=False
        )
        self.lol_username = discord.ui.TextInput(
            label="League of Legends Kullanıcı Adı",
            placeholder="LoL hesabınızın kullanıcı adı",
            default=lol_username,
            required=False
        )
        
        # Add items to modal
        self.add_item(self.nickname)
        self.add_item(self.steam_id)
        self.add_item(self.valorant_id)
        self.add_item(self.lol_username)
    
    async def on_submit(self, interaction: discord.Interaction):
        # Values will be processed by the calling function
        await interaction.response.defer()

class TempChannelSettingsModal(discord.ui.Modal):
    """Modal for temporary channel settings"""
    
    def __init__(self, settings=None):
        super().__init__(title="Geçici Kanal Ayarları")
        
        # Set default values from settings if available
        default_name = settings.get("default_name", "") if settings else ""
        default_limit = str(settings.get("default_limit", "")) if settings and settings.get("default_limit") is not None else ""
        
        self.default_name = discord.ui.TextInput(
            label="Varsayılan Kanal Adı",
            placeholder="{user} kanalı - Desteklenen: {user}, {game}, {emoji}",
            default=default_name,
            required=False
        )
        self.default_limit = discord.ui.TextInput(
            label="Varsayılan Üye Limiti",
            placeholder="Boş bırakırsanız limit olmaz (0-99)",
            default=default_limit,
            required=False
        )
        
        # Add items to modal
        self.add_item(self.default_name)
        self.add_item(self.default_limit)
    
    async def on_submit(self, interaction: discord.Interaction):
        # Values will be processed by the calling function
        await interaction.response.defer()

class UserProfileView(discord.ui.View):
    """View for managing user profile"""
    
    def __init__(self, bot, user_id: int, guild_id: int):
        super().__init__(timeout=300)
        self.bot = bot
        self.user_id = user_id
        self.guild_id = guild_id
        self.db = initialize_mongodb()
    
    async def get_user_data(self):
        """Get user data from database"""
        return await self.db.user_profiles.find_one({"user_id": str(self.user_id), "guild_id": str(self.guild_id)})
    
    async def save_user_data(self, data):
        """Save user data to database"""
        result = await self.db.user_profiles.update_one(
            {"user_id": str(self.user_id), "guild_id": str(self.guild_id)},
            {"$set": data},
            upsert=True
        )
        return result.acknowledged
    
    @discord.ui.button(label="Profil Düzenle", style=discord.ButtonStyle.primary, emoji="👤")
    async def edit_profile(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Open modal to edit profile"""
        user_data = await self.get_user_data()
        
        # Create and send the modal
        modal = UserProfileModal(user_data)
        await interaction.response.send_modal(modal)
        
        # Wait for modal submission
        await modal.wait()
        
        # Process the data from modal
        if modal.nickname.value or modal.steam_id.value or modal.valorant_id.value or modal.lol_username.value:
            # Prepare the update data
            update_data = {
                "nickname": modal.nickname.value,
                "game_data.steam_id": modal.steam_id.value.strip() if modal.steam_id.value else None,
                "game_data.valorant_id": modal.valorant_id.value.strip() if modal.valorant_id.value else None,
                "game_data.lol_username": modal.lol_username.value.strip() if modal.lol_username.value else None,
                "last_updated": datetime.now()
            }
            
            # If user has provided a nickname, update their server nickname
            if modal.nickname.value and interaction.guild:
                member = interaction.guild.get_member(self.user_id)
                if member:
                    try:
                        await member.edit(nick=modal.nickname.value)
                    except discord.Forbidden:
                        # Bot might not have permission to change nickname
                        pass
            
            # Save the data
            success = await self.save_user_data(update_data)
            if success:
                # Update the profile view
                embed = await self.create_profile_embed(interaction.user)
                await interaction.edit_original_response(embed=embed)
            else:
                await interaction.followup.send("❌ Profil bilgileriniz kaydedilirken bir hata oluştu.", ephemeral=True)
    
    @discord.ui.button(label="Geçici Kanal Ayarları", style=discord.ButtonStyle.primary, emoji="🔊")
    async def temp_channel_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Configure temporary channel settings"""
        user_data = await self.get_user_data()
        temp_settings = user_data.get("temp_channel_settings", {}) if user_data else {}
        
        # Create and send the modal
        modal = TempChannelSettingsModal(temp_settings)
        await interaction.response.send_modal(modal)
        
        # Wait for modal submission
        await modal.wait()
        
        # Process the data from modal
        try:
            # Validate user limit
            user_limit = None
            if modal.default_limit.value.strip():
                try:
                    user_limit = int(modal.default_limit.value)
                    if user_limit < 0 or user_limit > 99:
                        raise ValueError("User limit must be between 0 and 99")
                except ValueError:
                    await interaction.followup.send("❌ Geçersiz üye limiti! 0-99 arasında bir sayı olmalı.", ephemeral=True)
                    return
            
            # Prepare the update data
            update_data = {
                "temp_channel_settings.default_name": modal.default_name.value if modal.default_name.value else None,
                "temp_channel_settings.default_limit": user_limit,
                "last_updated": datetime.now()
            }
            
            # Save the data
            success = await self.save_user_data(update_data)
            if success:
                # Update the profile view with new settings
                embed = await self.create_profile_embed(interaction.user)
                await interaction.edit_original_response(embed=embed)
                
                # Show confirmation
                await interaction.followup.send("✅ Geçici kanal ayarlarınız kaydedildi.", ephemeral=True)
            else:
                await interaction.followup.send("❌ Ayarlarınız kaydedilirken bir hata oluştu.", ephemeral=True)
                
        except Exception as e:
            logger.error(f"Error saving temp channel settings: {e}")
            await interaction.followup.send(f"❌ Bir hata oluştu: {str(e)}", ephemeral=True)
    
    @discord.ui.button(label="Oyun Hesaplarını Göster", style=discord.ButtonStyle.secondary, emoji="🎮")
    async def show_game_accounts(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Show detailed game accounts information"""
        user_data = await self.get_user_data()
        
        if not user_data or not user_data.get("game_data"):
            await interaction.response.send_message("❌ Kayıtlı oyun hesabı bulunamadı.", ephemeral=True)
            return
        
        # Create embed with detailed game info
        embed = discord.Embed(
            title="🎮 Oyun Hesapları",
            description=f"<@{self.user_id}> kullanıcısının kayıtlı hesapları:",
            color=discord.Color.blue()
        )
        
        game_data = user_data.get("game_data", {})
        
        # Steam account
        if game_data.get("steam_id"):
            embed.add_field(
                name="<:steam:1177649830874759219> Steam",
                value=f"ID: `{game_data['steam_id']}`\n[Profile](https://steamcommunity.com/id/{game_data['steam_id']})",
                inline=True
            )
            
            # Try to get more Steam details if SteamAPI is available
            try:
                steam_api = SteamAPI()
                steam_info = await steam_api.get_user_summary(game_data['steam_id'])
                if steam_info:
                    embed.add_field(
                        name="Steam Profili",
                        value=f"İsim: {steam_info.get('personaname', 'N/A')}\nDurum: {steam_info.get('personastate_name', 'Bilinmiyor')}",
                        inline=True
                    )
            except Exception as e:
                logger.error(f"Error fetching Steam profile: {e}")
        
        # Valorant account
        if game_data.get("valorant_id"):
            embed.add_field(
                name="<:valorant:1177649832267268187> Valorant",
                value=f"ID: `{game_data['valorant_id']}`",
                inline=True
            )
        
        # League of Legends account
        if game_data.get("lol_username"):
            embed.add_field(
                name="<:lol:1177649833492082708> League of Legends",
                value=f"Kullanıcı Adı: `{game_data['lol_username']}`",
                inline=True
            )
        
        # Add more game accounts as needed
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @discord.ui.button(label="Gizlilik Ayarları", style=discord.ButtonStyle.secondary, emoji="🔒")
    async def privacy_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Configure privacy settings"""
        user_data = await self.get_user_data()
        current_privacy = user_data.get("preferences", {}).get("privacy_level", "public") if user_data else "public"
        
        # Create a select menu for privacy options
        select = discord.ui.Select(
            placeholder="Gizlilik seviyesi seçin",
            options=[
                discord.SelectOption(
                    label="Herkese Açık",
                    description="Profiliniz tüm sunucu üyelerine görünür",
                    emoji="🌐",
                    value="public",
                    default=current_privacy == "public"
                ),
                discord.SelectOption(
                    label="Sadece Arkadaşlar",
                    description="Profiliniz sadece arkadaşlarınıza görünür",
                    emoji="👥",
                    value="friends",
                    default=current_privacy == "friends"
                ),
                discord.SelectOption(
                    label="Gizli",
                    description="Profiliniz sadece size görünür",
                    emoji="🔒",
                    value="private",
                    default=current_privacy == "private"
                )
            ]
        )
        
        async def privacy_callback(interaction: discord.Interaction):
            new_privacy = select.values[0]
            
            # Update privacy setting
            update_data = {
                "preferences.privacy_level": new_privacy,
                "last_updated": datetime.now()
            }
            
            success = await self.save_user_data(update_data)
            if success:
                # Update the profile view
                embed = await self.create_profile_embed(interaction.user)
                await interaction.response.edit_message(embed=embed, view=self)
                
                # Show confirmation
                await interaction.followup.send(f"✅ Gizlilik ayarınız '{new_privacy}' olarak güncellendi.", ephemeral=True)
            else:
                await interaction.followup.send("❌ Gizlilik ayarı güncellenirken bir hata oluştu.", ephemeral=True)
        
        # Set the callback
        select.callback = privacy_callback
        
        # Create the view with the select menu
        privacy_view = discord.ui.View(timeout=60)
        privacy_view.add_item(select)
        
        await interaction.response.send_message("🔒 Gizlilik ayarınızı seçin:", view=privacy_view, ephemeral=True)
    
    async def create_profile_embed(self, user: discord.User) -> discord.Embed:
        """Create an embed for displaying user profile"""
        user_data = await self.get_user_data()
        
        embed = discord.Embed(
            title=f"👤 {user.display_name}'s Profil",
            color=discord.Color.blue()
        )
        
        # Add user avatar if available
        if user.avatar:
            embed.set_thumbnail(url=user.avatar.url)
        
        # Basic user info
        embed.add_field(name="Discord Kullanıcı Adı", value=user.name, inline=True)
        
        if user_data:
            # Registration info
            registered_at = user_data.get("registered_at")
            if registered_at:
                embed.add_field(
                    name="Kayıt Tarihi",
                    value=discord.utils.format_dt(registered_at, style="R"),
                    inline=True
                )
            
            # Game accounts summary
            game_data = user_data.get("game_data", {})
            game_accounts = []
            
            if game_data.get("steam_id"):
                game_accounts.append("Steam")
            if game_data.get("valorant_id"):
                game_accounts.append("Valorant")
            if game_data.get("lol_username"):
                game_accounts.append("League of Legends")
            
            if game_accounts:
                embed.add_field(
                    name="Oyun Hesapları",
                    value=", ".join(game_accounts),
                    inline=False
                )
            else:
                embed.add_field(
                    name="Oyun Hesapları",
                    value="Henüz oyun hesabı bağlanmamış",
                    inline=False
                )
            
            # Temp channel settings
            temp_settings = user_data.get("temp_channel_settings", {})
            if temp_settings:
                temp_info = []
                if temp_settings.get("default_name"):
                    temp_info.append(f"Kanal Adı: {temp_settings['default_name']}")
                if temp_settings.get("default_limit") is not None:
                    temp_info.append(f"Üye Limiti: {temp_settings['default_limit']}")
                
                if temp_info:                    embed.add_field(
                        name="Geçici Kanal Ayarları",
                        value="\n".join(temp_info),
                        inline=False
                    )
        else:
            embed.add_field(
                name="Profil",
                value="Henüz profil oluşturulmamış",
                inline=False
            )
        
        return embed


class Interface(commands.Cog):
    """
    User interface for managing profiles, game connections and temporary channels
    """
    
    def __init__(self, bot):
        self.bot = bot
        self.db = initialize_mongodb()
          # Initialize the database schema if needed
        asyncio.create_task(self.setup_database())

    async def setup_database(self):
        """Setup the database collections and indexes"""
        try:
            # Set unique index on user_id + guild_id
            self.db.user_profiles.create_index(
                [("user_id", 1), ("guild_id", 1)], 
                unique=True
            )
            logger.info("User profiles database initialized")
        except Exception as e:
            logger.error(f"Error setting up database: {e}")

    @app_commands.command(name="profile", description="View and manage user profile")
    @app_commands.describe(user="The user whose profile to view (optional)")
    async def profile(self, interaction: discord.Interaction, user: Optional[discord.User] = None):
        """View and manage user profile - merged profile and view_profile commands"""
        try:
            # If no user specified, show own profile
            target_user = user or interaction.user
            is_own_profile = target_user.id == interaction.user.id
            
            # Get user data from database
            user_data = await self.db.user_profiles.find_one({
                "user_id": str(target_user.id),
                "guild_id": str(interaction.guild_id)
            })
            
            # If viewing someone else's profile and they don't have one
            if not is_own_profile and not user_data:
                await interaction.response.send_message(
                    f"❌ {target_user.display_name} henüz profil oluşturmamış.",
                    ephemeral=True
                )
                return
            
            # Check privacy settings for other users' profiles
            if not is_own_profile and user_data:
                privacy_level = user_data.get("preferences", {}).get("privacy_level", "public")
                
                # If private, only show to the user themselves
                if privacy_level == "private":
                    await interaction.response.send_message(
                        f"❌ {target_user.display_name}'in profili gizli.",
                        ephemeral=True
                    )
                    return
                
                # If friends-only, check if they have roles in common
                if privacy_level == "friends":
                    member = interaction.guild.get_member(target_user.id)
                    viewer = interaction.guild.get_member(interaction.user.id)
                    
                    if member and viewer:
                        common_roles = set(role.id for role in member.roles) & set(role.id for role in viewer.roles)
                        if len(common_roles) <= 1:  # Only @everyone in common
                            await interaction.response.send_message(
                                f"❌ {target_user.display_name}'in profili sadece arkadaşlarına açık.",
                                ephemeral=True
                            )
                            return
            
            # Create the profile view
            view = UserProfileView(self.bot, target_user.id, interaction.guild_id)
            
            # For own profile, include interactive buttons; for others, view-only
            if not is_own_profile:
                view.clear_items()  # Remove interactive buttons for other users
            
            # Create the profile embed
            embed = await view.create_profile_embed(target_user)
            
            # Send response
            await interaction.response.send_message(
                embed=embed, 
                view=view if is_own_profile else None, 
                ephemeral=True
            )
            
        except Exception as e:
            logger.error(f"Error in profile command: {e}")
            await interaction.response.send_message(
                f"❌ Profil görüntülenirken bir hata oluştu: {str(e)}",
                ephemeral=True
            )
    
    @app_commands.command(name="register", description="Register yourself to the server")
    async def register(self, interaction: discord.Interaction, nickname: str = None):
        """Register to the server with optional nickname"""
        try:
            member = interaction.user
            
            # Check if user is already registered
            existing_profile = await self.db.user_profiles.find_one({
                "user_id": str(member.id),
                "guild_id": str(interaction.guild_id)
            })
            
            if existing_profile:
                await interaction.response.send_message(
                    "❗ Zaten kayıtlısınız! Profilinizi `/profile` komutu ile görüntüleyebilirsiniz.",
                    ephemeral=True
                )
                return
            
            # Create user profile
            user_profile = USER_PROFILE_SCHEMA.copy()
            user_profile.update({
                "user_id": str(member.id),
                "guild_id": str(interaction.guild_id),
                "registered_at": datetime.now(),
                "username": member.name,
                "nickname": nickname or member.display_name,
            })
            
            # Save profile to database
            await self.db.user_profiles.insert_one(user_profile)
            
            # Try to set nickname if provided
            if nickname:
                try:
                    await member.edit(nick=nickname)
                except discord.Forbidden:
                    pass  # Skip if bot doesn't have permission
            
            # Get configured member role from database
            guild_config = await self.db.guild_settings.find_one({"guild_id": str(interaction.guild_id)})
            
            member_role_id = None
            if guild_config and guild_config.get("roles", {}).get("member"):
                member_role_id = int(guild_config["roles"]["member"])
            
            # Assign member role if configured
            if member_role_id:
                try:
                    role = interaction.guild.get_role(member_role_id)
                    if role:
                        await member.add_roles(role, reason="User registration")
                except discord.Forbidden:
                    pass  # Skip if bot doesn't have permission
            
            # Create success embed
            embed = discord.Embed(
                title="✅ Kayıt Başarılı",
                description=f"{member.mention}, sunucuya başarıyla kaydoldunuz!",
                color=discord.Color.green()
            )
            
            embed.add_field(
                name="Profilini Ayarla",
                value="Oyun hesaplarını eklemek ve diğer ayarları yapmak için `/profile` komutunu kullanabilirsin.",
                inline=False
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error in register command: {e}")
            await interaction.response.send_message(
                f"❌ Kayıt olurken bir hata oluştu: {str(e)}",
                ephemeral=True
            )
  
    
    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        """
        Apply user temp channel settings when they create a temporary channel
        """
        # Skip if user didn't join a new channel
        if not after.channel:
            return
            
        try:
            # Check if this is a temp channel being created
            temp_channels_manager = self.bot.get_cog("TempChannels").manager
            if not temp_channels_manager:
                return
                
            # Get the temp channel config
            guild_config = await temp_channels_manager.get_temp_channel_config(member.guild.id)
            if not guild_config:
                return
                
            creator_channel_id = int(guild_config.get("creator_channel_id", 0))
            
            # Check if the user joined the temp creator channel
            if after.channel.id == creator_channel_id:
                # Get user profile to check for custom settings
                user_data = await self.db.user_profiles.find_one({
                    "user_id": str(member.id),
                    "guild_id": str(member.guild.id)
                })
                
                if not user_data or not user_data.get("temp_channel_settings"):
                    return  # No custom settings
                
                # Get the created channel (need to wait a moment)
                await asyncio.sleep(0.5)
                
                # Find the user's temp channel in the manager's temp_channels
                user_channel_id = None
                for ch_id, data in temp_channels_manager.temp_channels.items():
                    if data.get("creator_id") == member.id and data.get("guild_id") == member.guild.id:
                        user_channel_id = ch_id
                        break
                
                if not user_channel_id:
                    return
                    
                user_channel = member.guild.get_channel(user_channel_id)
                if not user_channel:
                    return
                
                # Apply user's custom settings
                temp_settings = user_data.get("temp_channel_settings", {})
                
                # Custom channel name
                if temp_settings.get("default_name"):
                    channel_name = temp_settings["default_name"]
                    
                    # Replace variables
                    channel_name = channel_name.replace("{user}", member.display_name)
                    
                    # Get game info for {game} and {emoji}
                    game_name = None
                    game_emoji = "🎮"
                    
                    for activity in member.activities:
                        if isinstance(activity, discord.Game) or isinstance(activity, discord.Activity):
                            game_name = activity.name
                            game_emoji = temp_channels_manager.get_game_emoji(game_name)
                            break
                    
                    # Replace {game} if available
                    if game_name and "{game}" in channel_name:
                        channel_name = channel_name.replace("{game}", game_name)
                    
                    # Replace {emoji} if available
                    channel_name = channel_name.replace("{emoji}", game_emoji)
                    
                    # Update channel name
                    await user_channel.edit(name=channel_name)
                
                # Custom user limit
                if temp_settings.get("default_limit") is not None:
                    await user_channel.edit(user_limit=temp_settings["default_limit"])
                
                # Auto-lock if set
                if temp_settings.get("auto_lock"):
                    overwrites = user_channel.overwrites
                    overwrites[member.guild.default_role] = discord.PermissionOverwrite(connect=False)
                    await user_channel.edit(overwrites=overwrites)
                
                # Custom bitrate
                if temp_settings.get("bitrate"):
                    # Ensure bitrate is within Discord's limits
                    bitrate = min(temp_settings["bitrate"], member.guild.bitrate_limit)
                    await user_channel.edit(bitrate=bitrate)
                    
        except Exception as e:
            logger.error(f"Error applying temp channel settings: {e}")

    @app_commands.command(name="support", description="Show support system information")
    async def support(self, interaction: discord.Interaction):
        """Show support system card with information"""
        try:
            # Import the support card function
            from utils.community.turkoyto.card_renderer import create_support_system_card
            
            # Create the support system card
            card_path = await create_support_system_card(interaction.guild, self.bot)
            
            if card_path and os.path.exists(card_path):
                # Create embed with the card
                embed = discord.Embed(
                    title="🎫 Destek Sistemi",
                    description="Sunucumuzun destek sistemi hakkında bilgiler:",
                    color=discord.Color.blue()
                )
                
                # Set the card as image
                embed.set_image(url="attachment://support_card.png")
                
                # Add instructions
                embed.add_field(
                    name="📋 Nasıl Kullanılır?",
                    value=(
                        "1. Destek kanalında bulunan **Destek Talebi** butonuna tıklayın\n"
                        "2. Açılan formu doldurun\n"
                        "3. Ekibimiz en kısa sürede size yardımcı olacaktır"
                    ),
                    inline=False
                )
                
                # Send with file
                file = discord.File(card_path, filename="support_card.png")
                await interaction.response.send_message(embed=embed, file=file, ephemeral=True)
                
                # Clean up the file
                try:
                    os.remove(card_path)
                except Exception as e:
                    logger.error(f"Error removing support card file: {e}")
            else:
                # Fallback if card creation fails
                embed = discord.Embed(
                    title="🎫 Destek Sistemi",
                    description=(
                        "Sunucumuzda destek sistemi aktif!\n\n"
                        "**Destek için:**\n"
                        "• Destek kanalında bulunan butonu kullanın\n"
                        "• Formunuzu doldurun\n"
                        "• Ekibimiz size yardımcı olacaktır\n\n"
                        "**Destek Türleri:**\n"
                        "🔧 Teknik Sorunlar\n"
                        "💡 Genel Sorular\n"
                        "⚙️ Özellik Talepleri\n"
                        "📋 Hata Raporları"
                    ),
                    color=discord.Color.blue()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                
        except Exception as e:
            logger.error(f"Error in support command: {e}")
            await interaction.response.send_message(
                f"❌ Destek sistemi bilgileri görüntülenirken bir hata oluştu: {str(e)}",
                ephemeral=True
            )

async def setup(bot):
    await bot.add_cog(Interface(bot))
    logger.info("Interface cog loaded")
