import discord
from discord.ext import commands
import logging
import asyncio
from typing import Dict, Optional, List
from utils.database.connection import get_async_db, initialize_mongodb
from utils.core.formatting import create_embed

logger = logging.getLogger('temp_channels')

class TempChannelsManager:
    """Manages temporary voice channels that are created when users join a specific channel"""
    
    def __init__(self, bot):
        self.bot = bot
        self.temp_channels = {}  # Maps channel_id -> {'creator_id': user_id, 'guild_id': guild_id}
        self.channel_timers = {}  # Maps channel_id -> deletion timer task
        self.mongo_db = initialize_mongodb()
    
    async def get_temp_channel_config(self, guild_id: int) -> Optional[Dict]:
        """Get temporary channel configuration for a guild"""
        try:
            config = self.mongo_db.temp_channels.find_one({"guild_id": str(guild_id)})
            return config
        except Exception as e:
            logger.error(f"Error getting temp channel config for guild {guild_id}: {e}")
            return None
    
    async def set_temp_channel_config(self, guild_id: int, channel_id: int, config: Dict) -> bool:
        """Set temporary channel configuration for a guild"""
        try:
            self.mongo_db.temp_channels.update_one(
                {"guild_id": str(guild_id)},
                {
                    "$set": {
                        "creator_channel_id": str(channel_id),
                        "category_id": config.get("category_id"),
                        "channel_name_format": config.get("channel_name_format", "{user} kanalı"),
                        "game_emojis_enabled": config.get("game_emojis_enabled", True),
                        "auto_delete": config.get("auto_delete", True),
                        "delete_delay": config.get("delete_delay", 0),  # 0 = immediate deletion
                        "max_temp_channels": config.get("max_temp_channels", 50)
                    }
                },
                upsert=True
            )
            return True
        except Exception as e:
            logger.error(f"Error setting temp channel config for guild {guild_id}: {e}")
            return False
    
    async def on_voice_state_update(self, member, before, after):
        """Handle voice state updates for temporary channel creation and deletion"""
        try:
            guild_config = await self.get_temp_channel_config(member.guild.id)
            if not guild_config:
                return
            
            creator_channel_id = int(guild_config["creator_channel_id"])
            
            # User joined the creator channel
            if after.channel and after.channel.id == creator_channel_id:
                await self.create_temp_channel(member, after.channel, guild_config)
                return
                
            # User left a temporary channel - handle deletion
            if before.channel and before.channel.id in self.temp_channels:
                await self.handle_channel_empty(before.channel, guild_config)
                
            # User joined a channel that was scheduled for deletion - cancel deletion
            if after.channel and after.channel.id in self.channel_timers:
                timer_task = self.channel_timers[after.channel.id]
                if timer_task and not timer_task.done():
                    timer_task.cancel()
                    self.channel_timers[after.channel.id] = None
                    logger.info(f"Cancelled deletion timer for channel {after.channel.name} ({after.channel.id})")
                    
        except Exception as e:
            logger.error(f"Error in temp channel voice state update handler: {e}", exc_info=True)
    
    async def create_temp_channel(self, member, creator_channel, config):
        """Create a temporary voice channel for a member and move them to it"""
        try:
            guild = creator_channel.guild
            
            # Check if user already has a temp channel
            user_temp_channels = [ch_id for ch_id, data in self.temp_channels.items() 
                                 if data['creator_id'] == member.id and data['guild_id'] == guild.id]
            if user_temp_channels:
                logger.info(f"User {member.display_name} already has a temp channel")
                return
            
            # Check max temp channels limit
            guild_temp_channels = [ch_id for ch_id, data in self.temp_channels.items() 
                                  if data['guild_id'] == guild.id]
            max_channels = config.get("max_temp_channels", 50)
            if len(guild_temp_channels) >= max_channels:
                logger.warning(f"Max temp channels ({max_channels}) reached for guild {guild.id}")
                return
            
            # Determine the category to place the channel in
            category = None
            if config.get("category_id"):
                category = guild.get_channel(int(config["category_id"]))
            if not category:
                category = creator_channel.category
            
            # Get game information if available and enabled
            game_name = None
            game_emoji = "🎮"  # Default emoji
            
            if config.get("game_emojis_enabled", True):
                # Try to get the member's activity (game)
                for activity in member.activities:
                    if isinstance(activity, discord.Game) or isinstance(activity, discord.Activity):
                        game_name = activity.name
                        game_emoji = self.get_game_emoji(game_name)
                        break
            
            # Create channel name using format
            channel_name_format = config.get("channel_name_format", "{user} kanalı")
            if game_name and "{game}" in channel_name_format:
                channel_name = channel_name_format.format(
                    user=member.display_name,
                    game=game_name,
                    emoji=game_emoji
                )
            else:
                channel_name = channel_name_format.format(
                    user=member.display_name,
                    emoji=game_emoji
                )
            
            # Create the channel
            temp_channel = await guild.create_voice_channel(
                name=channel_name,
                category=category,
                reason=f"Temporary channel for {member.display_name}"
            )
            
            # Register the channel in our tracking dict
            self.temp_channels[temp_channel.id] = {
                'creator_id': member.id,
                'guild_id': guild.id,
                'created_at': discord.utils.utcnow()
            }
            
            # Move the member to the new channel
            await member.move_to(temp_channel)
            
            logger.info(f"Created temporary channel {temp_channel.name} ({temp_channel.id}) for {member.display_name}")
            return temp_channel
            
        except Exception as e:
            logger.error(f"Error creating temporary channel: {e}", exc_info=True)
            return None
    
    async def handle_channel_empty(self, channel, config):
        """Handle when a temporary channel becomes empty"""
        try:
            if len(channel.members) == 0:
                delete_delay = config.get("delete_delay", 0)
                if delete_delay > 0:
                    # Schedule deletion after delay
                    await self.schedule_channel_deletion(channel, delete_delay)
                else:
                    # Delete immediately
                    await self.delete_channel(channel)
        except Exception as e:
            logger.error(f"Error handling empty channel {channel.id}: {e}")
    
    async def delete_channel(self, channel):
        """Delete a channel immediately"""
        try:
            # Check if the channel still exists and is empty
            try:
                channel = await self.bot.fetch_channel(channel.id)
                if len(channel.members) == 0:
                    await channel.delete(reason="Temporary channel is empty")
                    # Remove from our tracking
                    if channel.id in self.temp_channels:
                        del self.temp_channels[channel.id]
                    if channel.id in self.channel_timers:
                        del self.channel_timers[channel.id]
                    logger.info(f"Deleted empty temporary channel {channel.name} ({channel.id})")
            except discord.NotFound:
                # Channel already deleted
                if channel.id in self.temp_channels:
                    del self.temp_channels[channel.id]
                if channel.id in self.channel_timers:
                    del self.channel_timers[channel.id]
                logger.info(f"Channel {channel.id} was already deleted")
                
        except Exception as e:
            logger.error(f"Error in delete_channel: {e}", exc_info=True)
    
    async def schedule_channel_deletion(self, channel, delay=15):
        """Schedule a channel for deletion after a delay (in seconds)"""
        try:
            # Cancel any existing deletion timer
            if channel.id in self.channel_timers:
                timer_task = self.channel_timers[channel.id]
                if timer_task and not timer_task.done():
                    timer_task.cancel()
            
            # Schedule new deletion
            timer_task = asyncio.create_task(self._delete_after_delay(channel, delay))
            self.channel_timers[channel.id] = timer_task
            logger.info(f"Scheduled deletion of channel {channel.name} ({channel.id}) in {delay} seconds")
            
        except Exception as e:
            logger.error(f"Error scheduling channel deletion: {e}", exc_info=True)
    
    async def _delete_after_delay(self, channel, delay):
        """Internal method to delete a channel after a delay"""
        try:
            await asyncio.sleep(delay)
            # Check if channel is still empty before deleting
            if len(channel.members) == 0:
                await self.delete_channel(channel)
        except asyncio.CancelledError:
            logger.info(f"Deletion of channel {channel.id} was cancelled")
        except Exception as e:
            logger.error(f"Error in delayed deletion: {e}")
    
    def get_game_emoji(self, game_name):
        """Get an appropriate emoji for a game"""
        if not game_name:
            return "🎮"
            
        game_name_lower = game_name.lower()
        
        # Common games and their emojis
        game_emojis = {
            "minecraft": "⛏️",
            "valorant": "🔫",
            "league of legends": "🧙",
            "fortnite": "🏝️",
            "counter-strike": "💣",
            "cs2": "💣",
            "apex legends": "🎯",
            "call of duty": "🪖",
            "gta": "🚗",
            "rocket league": "⚽",
            "among us": "👨‍🚀",
            "pubg": "🔫",
            "overwatch": "🦸",
            "rust": "🪓",
            "rainbow six": "🛡️",
            "fall guys": "👾",
            "fifa": "⚽",
            "world of warcraft": "⚔️",
            "dota": "🏰",
            "battlefield": "🎖️"
        }
        
        # Check if game name contains any of our known games
        for known_game, emoji in game_emojis.items():
            if known_game in game_name_lower:
                return emoji
        
        # Default emoji for games
        return "🎮"

class TempChannelsModal(discord.ui.Modal, title="Geçici Kanal Ayarları"):
    """Modal for configuring temporary channels"""
    
    creator_channel = discord.ui.TextInput(
        label="Oluşturucu Kanal ID",
        placeholder="Geçici kanalları tetikleyecek kanal ID'sini girin",
        required=True
    )
    
    category_id = discord.ui.TextInput(
        label="Kategori ID (İsteğe bağlı)",
        placeholder="Geçici kanalların oluşturulacağı kategori ID'si",
        required=False
    )
    
    channel_name_format = discord.ui.TextInput(
        label="Kanal Adı Formatı",
        placeholder="{emoji} {user} kanalı - Kullanılabilir: {user}, {game}, {emoji}",
        default="{emoji} {user} kanalı",
        required=False
    )
    
    max_channels = discord.ui.TextInput(
        label="Maksimum Kanal Sayısı",
        placeholder="Aynı anda oluşturulabilecek maksimum geçici kanal sayısı (varsayılan: 50)",
        default="50",
        required=False
    )
    
    def __init__(self, bot, manager):
        super().__init__()
        self.bot = bot
        self.manager = manager
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            guild = interaction.guild
            
            # Validate creator channel
            try:
                creator_channel_id = int(self.creator_channel.value.strip())
                creator_channel = guild.get_channel(creator_channel_id)
                if not creator_channel:
                    return await interaction.response.send_message(f"Oluşturucu kanal bulunamadı: {creator_channel_id}", ephemeral=True)
                if not isinstance(creator_channel, discord.VoiceChannel):
                    return await interaction.response.send_message("Oluşturucu kanal bir ses kanalı olmalıdır.", ephemeral=True)
            except ValueError:
                return await interaction.response.send_message("Geçersiz oluşturucu kanal ID'si", ephemeral=True)
            
            # Validate category if provided
            category_id = None
            if self.category_id.value.strip():
                try:
                    category_id = int(self.category_id.value.strip())
                    category = guild.get_channel(category_id)
                    if not category:
                        return await interaction.response.send_message(f"Kategori bulunamadı: {category_id}", ephemeral=True)
                    if not isinstance(category, discord.CategoryChannel):
                        return await interaction.response.send_message("Kategori ID'si bir kategori kanalı olmalıdır.", ephemeral=True)
                except ValueError:
                    return await interaction.response.send_message("Geçersiz kategori ID'si", ephemeral=True)
            
            # Validate max channels
            try:
                max_channels = int(self.max_channels.value.strip()) if self.max_channels.value.strip() else 50
                if max_channels < 1 or max_channels > 100:
                    return await interaction.response.send_message("Maksimum kanal sayısı 1-100 arasında olmalıdır.", ephemeral=True)
            except ValueError:
                return await interaction.response.send_message("Geçersiz maksimum kanal sayısı", ephemeral=True)
            
            # Create configuration
            config = {
                "category_id": str(category_id) if category_id else None,
                "channel_name_format": self.channel_name_format.value.strip() or "{emoji} {user} kanalı",
                "game_emojis_enabled": True,
                "auto_delete": True,
                "delete_delay": 0,
                "max_temp_channels": max_channels
            }
            
            # Save configuration
            success = await self.manager.set_temp_channel_config(guild.id, creator_channel_id, config)
            
            if success:
                embed = create_embed(
                    title="✅ Geçici Kanal Sistemi Ayarlandı",
                    description=f"Geçici kanal sistemi başarıyla yapılandırıldı!\n\n"
                               f"**Oluşturucu Kanal:** {creator_channel.mention}\n"
                               f"**Kategori:** {category.mention if category_id else 'Oluşturucu kanalın kategorisi'}\n"
                               f"**Kanal Adı Formatı:** `{config['channel_name_format']}`\n"
                               f"**Maksimum Kanal:** {max_channels}",
                    color=discord.Color.green()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                await interaction.response.send_message("Ayarları kaydederken bir hata oluştu.", ephemeral=True)
                
        except Exception as e:
            logger.error(f"Error in temp channels modal: {e}")
            await interaction.response.send_message(f"Bir hata oluştu: {str(e)}", ephemeral=True)

class TempChannelsView(discord.ui.View):
    """View for managing temporary channels settings"""
    
    def __init__(self, bot, manager):
        super().__init__(timeout=300)
        self.bot = bot
        self.manager = manager
    
    @discord.ui.button(label="Ayarla", style=discord.ButtonStyle.primary, emoji="⚙️")
    async def setup_temp_channels(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Open temp channels configuration modal"""
        try:
            modal = TempChannelsModal(self.bot, self.manager)
            await interaction.response.send_modal(modal)
        except Exception as e:
            logger.error(f"Error opening temp channels modal: {e}")
            await interaction.response.send_message(
                embed=create_embed(f"Modal açılırken bir hata oluştu: {str(e)}", discord.Color.red()),
                ephemeral=True
            )
    
    @discord.ui.button(label="Mevcut Ayarları Göster", style=discord.ButtonStyle.secondary, emoji="📋")
    async def show_current_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Show current temp channels settings"""
        try:
            config = await self.manager.get_temp_channel_config(interaction.guild.id)
            
            if not config:
                embed = create_embed(
                    title="📋 Geçici Kanal Ayarları",
                    description="Bu sunucu için geçici kanal sistemi henüz ayarlanmamış.",
                    color=discord.Color.orange()
                )
            else:
                creator_channel = interaction.guild.get_channel(int(config["creator_channel_id"]))
                category = interaction.guild.get_channel(int(config["category_id"])) if config.get("category_id") else None
                
                embed = create_embed(
                    title="📋 Mevcut Geçici Kanal Ayarları",
                    description="Bu sunucunun geçici kanal sistemi ayarları:",
                    color=discord.Color.blue()
                )
                
                embed.add_field(
                    name="Oluşturucu Kanal",
                    value=creator_channel.mention if creator_channel else "Kanal bulunamadı",
                    inline=True
                )
                
                embed.add_field(
                    name="Kategori",
                    value=category.mention if category else "Oluşturucu kanalın kategorisi",
                    inline=True
                )
                
                embed.add_field(
                    name="Kanal Adı Formatı",
                    value=f"`{config.get('channel_name_format', '{emoji} {user} kanalı')}`",
                    inline=False
                )
                
                embed.add_field(
                    name="Oyun Emojileri",
                    value="✅ Etkin" if config.get("game_emojis_enabled", True) else "❌ Devre dışı",
                    inline=True
                )
                
                embed.add_field(
                    name="Maksimum Kanal",
                    value=str(config.get("max_temp_channels", 50)),
                    inline=True
                )
                
                # Show current temp channels count
                current_count = len([ch_id for ch_id, data in self.manager.temp_channels.items() 
                                    if data['guild_id'] == interaction.guild.id])
                embed.add_field(
                    name="Aktif Geçici Kanallar",
                    value=f"{current_count}",
                    inline=True
                )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error showing temp channels settings: {e}")
            await interaction.response.send_message(
                embed=create_embed(f"Ayarları gösterirken bir hata oluştu: {str(e)}", discord.Color.red()),
                ephemeral=True
            )
    
    @discord.ui.button(label="Sistemi Kaldır", style=discord.ButtonStyle.danger, emoji="🗑️")
    async def remove_temp_channels(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Remove temp channels configuration"""
        try:
            # Delete configuration from database
            result = self.manager.mongo_db.temp_channels.delete_one({"guild_id": str(interaction.guild.id)})
            
            if result.deleted_count > 0:
                embed = create_embed(
                    title="🗑️ Geçici Kanal Sistemi Kaldırıldı",
                    description="Geçici kanal sistemi ayarları başarıyla kaldırıldı.\n\n"
                               "⚠️ **Not:** Mevcut geçici kanallar hala aktif kalacak ancak yenileri oluşturulmayacak.",
                    color=discord.Color.orange()
                )
            else:
                embed = create_embed(
                    title="ℹ️ Sistem Zaten Ayarlanmamış",
                    description="Bu sunucu için geçici kanal sistemi zaten ayarlanmamış.",
                    color=discord.Color.blue()
                )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error removing temp channels: {e}")
            await interaction.response.send_message(
                embed=create_embed(f"Sistemi kaldırırken bir hata oluştu: {str(e)}", discord.Color.red()),
                ephemeral=True
            )

class TempChannels(commands.Cog):
    """
    General temporary voice channels system
    """
    
    def __init__(self, bot):
        self.bot = bot
        self.manager = TempChannelsManager(bot)
    
    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        """Handle voice state updates for temporary channels"""
        await self.manager.on_voice_state_update(member, before, after)
    
    @commands.hybrid_command(name="temp_channels", description="Configure temporary voice channels system")
    @commands.has_permissions(manage_channels=True)
    async def temp_channels_config(self, ctx):
        """
        Configure the temporary voice channels system for your server.
        
        This system allows users to create temporary voice channels by joining a designated "creator" channel.
        The temporary channels are automatically deleted when empty.
        """
        try:
            embed = discord.Embed(
                title="🎮 Geçici Sesli Kanal Sistemi",
                description=(
                    "Sunucunuz için geçici sesli kanal sistemini yapılandırın.\n\n"
                    "**Nasıl Çalışır:**\n"
                    "• Kullanıcılar belirli bir kanala katıldığında otomatik olarak kendi özel kanalları oluşturulur\n"
                    "• Kanal boşaldığında otomatik olarak silinir\n"
                    "• Oyun adlarına göre özel emojiler eklenebilir\n"
                    "• Kanal adı formatı özelleştirilebilir"
                ),
                color=discord.Color.purple()
            )
            
            embed.add_field(
                name="⚙️ Ayarla",
                value="Sistemi yapılandırın ve oluşturucu kanalı ayarlayın",
                inline=False
            )
            
            embed.add_field(
                name="📋 Mevcut Ayarları Göster",
                value="Şu anki ayarları görüntüleyin",
                inline=False
            )
            
            embed.add_field(
                name="🗑️ Sistemi Kaldır",
                value="Geçici kanal sistemini tamamen kaldırın",
                inline=False
            )
            
            view = TempChannelsView(self.bot, self.manager)
            await ctx.send(embed=embed, view=view, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error in temp_channels command: {e}")
            await ctx.send(
                embed=create_embed(f"Komut işlenirken bir hata oluştu: {str(e)}", discord.Color.red()),
                ephemeral=True
            )
    
    @commands.hybrid_command(name="list_temp_channels", description="List all active temporary channels")
    @commands.has_permissions(manage_channels=True)
    async def list_temp_channels(self, ctx):
        """List all active temporary channels in the server"""
        try:
            guild_temp_channels = [
                (ch_id, data) for ch_id, data in self.manager.temp_channels.items() 
                if data['guild_id'] == ctx.guild.id
            ]
            
            if not guild_temp_channels:
                embed = create_embed(
                    title="📋 Aktif Geçici Kanallar",
                    description="Bu sunucuda aktif geçici kanal bulunmuyor.",
                    color=discord.Color.blue()
                )
            else:
                embed = create_embed(
                    title="📋 Aktif Geçici Kanallar",
                    description=f"Bu sunucuda {len(guild_temp_channels)} aktif geçici kanal var:",
                    color=discord.Color.green()
                )
                
                for channel_id, data in guild_temp_channels[:10]:  # Limit to 10 for embed space
                    channel = ctx.guild.get_channel(channel_id)
                    creator = ctx.guild.get_member(data['creator_id'])
                    
                    if channel and creator:
                        member_count = len(channel.members)
                        created_time = data.get('created_at', 'Bilinmiyor')
                        
                        embed.add_field(
                            name=f"🎮 {channel.name}",
                            value=(
                                f"**Oluşturan:** {creator.mention}\n"
                                f"**Üye Sayısı:** {member_count}\n"
                                f"**Oluşturulma:** {discord.utils.format_dt(created_time, style='R') if created_time != 'Bilinmiyor' else 'Bilinmiyor'}"
                            ),
                            inline=True
                        )
                
                if len(guild_temp_channels) > 10:
                    embed.set_footer(text=f"Ve {len(guild_temp_channels) - 10} kanal daha...")
            
            await ctx.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error listing temp channels: {e}")
            await ctx.send(
                embed=create_embed(f"Kanalları listelerken bir hata oluştu: {str(e)}", discord.Color.red()),
                ephemeral=True
            )

async def setup(bot):
    await bot.add_cog(TempChannels(bot))
    logger.info("TempChannels cog loaded")
