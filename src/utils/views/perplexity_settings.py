import discord
import logging
from discord.ext import commands
from src.utils.core.formatting import create_embed
from src.utils.database.connection import initialize_mongodb

# Configure logger
logger = logging.getLogger('perplexity_settings')

class PerplexitySettingsView(discord.ui.View):
    """Main view for Perplexity AI settings"""
    
    def __init__(self, bot, timeout=180):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.mongo_db = initialize_mongodb()
    
    @discord.ui.button(label="API Anahtarı Ayarla", style=discord.ButtonStyle.primary, custom_id="set_api_key", row=0)
    async def set_api_key_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Set custom API key for this server"""
        await interaction.response.send_modal(APIKeyModal(self.bot))
    
    @discord.ui.button(label="Kredi Ayarları", style=discord.ButtonStyle.primary, custom_id="credit_settings", row=0)
    async def credit_settings_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Configure credit settings"""
        await interaction.response.send_modal(CreditSettingsModal(self.bot))
    
    @discord.ui.button(label="Kanal İzinleri", style=discord.ButtonStyle.primary, custom_id="channel_permissions", row=1)
    async def channel_permissions_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Set which channels AI can be used in"""
        # Get current settings
        server_config = await self.mongo_db.perplexity_config.find_one({"guild_id": str(interaction.guild.id)})
        allowed_channels = server_config.get("allowed_channels", []) if server_config else []
        
        # Create a selector with the server's text channels
        view = discord.ui.View(timeout=180)
        
        # Add channel selector
        channel_select = ChannelSelector(allowed_channels)
        view.add_item(channel_select)
        
        # Add save button
        async def save_callback(save_interaction):
            if save_interaction.user != interaction.user:
                return await save_interaction.response.send_message("Bu butonu kullanamazsınız.", ephemeral=True)
            
            selected_channels = channel_select.selected_channels
            
            # Update in database
            await self.mongo_db.perplexity_config.update_one(
                {"guild_id": str(interaction.guild.id)},
                {"$set": {"allowed_channels": selected_channels}},
                upsert=True
            )
            
            await save_interaction.response.send_message(
                embed=create_embed(f"✅ İzin verilen kanallar güncellendi. Seçilen kanal sayısı: {len(selected_channels)}", discord.Color.green()),
                ephemeral=True
            )
        
        save_button = discord.ui.Button(label="Kaydet", style=discord.ButtonStyle.success)
        save_button.callback = save_callback
        view.add_item(save_button)
        
        # Send message with the view
        allowed_count = len(allowed_channels)
        embed = discord.Embed(
            title="🔒 Kanal İzinleri",
            description="AI sohbetin kullanılabileceği kanalları seçin.",
            color=discord.Color.blue()
        )
        embed.add_field(
            name="Mevcut Ayarlar",
            value=f"Şu anda {allowed_count} kanalda AI sohbet aktif." if allowed_count > 0 else "Şu anda tüm kanallarda AI sohbet aktif.",
            inline=False
        )
        embed.add_field(
            name="Not",
            value="Hiçbir kanal seçilmezse, AI tüm kanallarda kullanılabilir.",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @discord.ui.button(label="Üye Kredileri", style=discord.ButtonStyle.primary, custom_id="user_credits", row=1)
    async def user_credits_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Manage user credits"""
        await interaction.response.send_modal(UserCreditsModal(self.bot))
    
    @discord.ui.button(label="Cevap Gönderimi", style=discord.ButtonStyle.primary, custom_id="response_style", row=2)
    async def response_style_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Configure response streaming settings"""
        # Get current settings
        server_config = await self.mongo_db.perplexity_config.find_one({"guild_id": str(interaction.guild.id)})
        streaming = server_config.get("streaming", True) if server_config else True
        
        # Create view for toggling streaming
        view = discord.ui.View(timeout=180)
        
        # Add toggle buttons
        async def enable_streaming(enable_interaction):
            if enable_interaction.user != interaction.user:
                return await enable_interaction.response.send_message("Bu butonu kullanamazsınız.", ephemeral=True)
            
            # Update in database
            await self.mongo_db.perplexity_config.update_one(
                {"guild_id": str(interaction.guild.id)},
                {"$set": {"streaming": True}},
                upsert=True
            )
            
            await enable_interaction.response.send_message(
                embed=create_embed("✅ Akan yanıt modu etkinleştirildi. AI yanıtları gerçek zamanlı olarak gönderilecek.", discord.Color.green()),
                ephemeral=True
            )
        
        async def disable_streaming(disable_interaction):
            if disable_interaction.user != interaction.user:
                return await disable_interaction.response.send_message("Bu butonu kullanamazsınız.", ephemeral=True)
            
            # Update in database
            await self.mongo_db.perplexity_config.update_one(
                {"guild_id": str(interaction.guild.id)},
                {"$set": {"streaming": False}},
                upsert=True
            )
            
            await disable_interaction.response.send_message(
                embed=create_embed("✅ Akan yanıt modu devre dışı bırakıldı. AI yanıtları tek seferde gönderilecek.", discord.Color.green()),
                ephemeral=True
            )
        
        # Add buttons
        streaming_button = discord.ui.Button(
            label="Akan Yanıt Modu", 
            style=discord.ButtonStyle.success if streaming else discord.ButtonStyle.secondary,
            emoji="🔄"
        )
        streaming_button.callback = enable_streaming
        
        complete_button = discord.ui.Button(
            label="Tam Yanıt Modu", 
            style=discord.ButtonStyle.success if not streaming else discord.ButtonStyle.secondary,
            emoji="📝"
        )
        complete_button.callback = disable_streaming
        
        view.add_item(streaming_button)
        view.add_item(complete_button)
        
        # Send message with the view
        embed = discord.Embed(
            title="🔄 Yanıt Gönderim Modu",
            description="AI yanıtlarının nasıl gönderileceğini seçin.",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="Akan Yanıt Modu",
            value="AI yanıtları, yazılırken gerçek zamanlı olarak görünür. Daha doğal bir deneyim sağlar.",
            inline=False
        )
        
        embed.add_field(
            name="Tam Yanıt Modu",
            value="AI yanıtları tek seferde, tamamen hazır olduğunda gönderilir. Sunucu kaynaklarını daha az kullanır.",
            inline=False
        )
        
        embed.add_field(
            name="Mevcut Ayar",
            value=f"Şu anda {'Akan Yanıt Modu' if streaming else 'Tam Yanıt Modu'} aktif.",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @discord.ui.button(label="AI Durumu", style=discord.ButtonStyle.primary, custom_id="ai_status", row=2)
    async def ai_status_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Toggle AI on/off for this server"""
        # Get current settings
        server_config = await self.mongo_db.perplexity_config.find_one({"guild_id": str(interaction.guild.id)})
        enabled = server_config.get("enabled", True) if server_config else True
        
        # Create view for toggling status
        view = discord.ui.View(timeout=180)
        
        # Add toggle buttons
        async def enable_ai(enable_interaction):
            if enable_interaction.user != interaction.user:
                return await enable_interaction.response.send_message("Bu butonu kullanamazsınız.", ephemeral=True)
            
            # Update in database
            await self.mongo_db.perplexity_config.update_one(
                {"guild_id": str(interaction.guild.id)},
                {"$set": {"enabled": True}},
                upsert=True
            )
            
            await enable_interaction.response.send_message(
                embed=create_embed("✅ AI sohbet etkinleştirildi.", discord.Color.green()),
                ephemeral=True
            )
        
        async def disable_ai(disable_interaction):
            if disable_interaction.user != interaction.user:
                return await disable_interaction.response.send_message("Bu butonu kullanamazsınız.", ephemeral=True)
            
            # Update in database
            await self.mongo_db.perplexity_config.update_one(
                {"guild_id": str(interaction.guild.id)},
                {"$set": {"enabled": False}},
                upsert=True
            )
            
            await disable_interaction.response.send_message(
                embed=create_embed("✅ AI sohbet devre dışı bırakıldı.", discord.Color.green()),
                ephemeral=True
            )
        
        # Add buttons
        enable_button = discord.ui.Button(
            label="Etkinleştir", 
            style=discord.ButtonStyle.success,
            emoji="✅"
        )
        enable_button.callback = enable_ai
        
        disable_button = discord.ui.Button(
            label="Devre Dışı Bırak", 
            style=discord.ButtonStyle.danger,
            emoji="❌"
        )
        disable_button.callback = disable_ai
        
        view.add_item(enable_button)
        view.add_item(disable_button)
        
        # Send message with the view
        embed = discord.Embed(
            title="🤖 AI Sohbet Durumu",
            description="Bu sunucuda AI sohbeti etkinleştirin veya devre dışı bırakın.",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="Mevcut Durum",
            value=f"AI sohbet şu anda {'etkin' if enabled else 'devre dışı'}.",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @discord.ui.button(label="Geri", style=discord.ButtonStyle.danger, custom_id="back", row=3)
    async def back_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Return to main settings panel"""
        # This will be handled by the bot_settings cog
        await interaction.response.defer(ephemeral=True)


class APIKeyModal(discord.ui.Modal, title="Perplexity API Anahtarı Ayarla"):
    """Modal for setting a custom API key"""
    
    api_key = discord.ui.TextInput(
        label="API Anahtarı",
        placeholder="pplx-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
        required=True,
        style=discord.TextStyle.short
    )
    
    def __init__(self, bot):
        super().__init__()
        self.bot = bot
        self.mongo_db = initialize_mongodb()
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Validate API key format
            if not self.api_key.value.startswith("pplx-"):
                return await interaction.response.send_message(
                    embed=create_embed("❌ Geçersiz API anahtarı formatı. Perplexity API anahtarları 'pplx-' ile başlar.", discord.Color.red()),
                    ephemeral=True
                )
            
            # Save to database
            await self.mongo_db.perplexity_config.update_one(
                {"guild_id": str(interaction.guild.id)},
                {"$set": {"api_key": self.api_key.value}},
                upsert=True
            )
            
            await interaction.response.send_message(
                embed=create_embed("✅ API anahtarı başarıyla kaydedildi.", discord.Color.green()),
                ephemeral=True
            )
            
        except Exception as e:
            logger.error(f"Error setting API key: {e}")
            await interaction.response.send_message(
                embed=create_embed(f"❌ API anahtarı kaydedilirken bir hata oluştu: {str(e)}", discord.Color.red()),
                ephemeral=True
            )


class CreditSettingsModal(discord.ui.Modal, title="AI Kredi Ayarları"):
    """Modal for configuring credit settings"""
    
    default_credits = discord.ui.TextInput(
        label="Başlangıç Kredisi",
        placeholder="Yeni üyelere verilecek başlangıç kredisi (örn: 10)",
        required=True,
        style=discord.TextStyle.short
    )
    
    max_credits = discord.ui.TextInput(
        label="Maksimum Kredi",
        placeholder="Bir üyenin biriktirebileceği maksimum kredi (örn: 30)",
        required=True,
        style=discord.TextStyle.short
    )
    
    daily_reset = discord.ui.TextInput(
        label="Günlük Sıfırlama",
        placeholder="Krediler her gün sıfırlansın mı? (evet/hayır)",
        required=True,
        style=discord.TextStyle.short
    )
    
    def __init__(self, bot):
        super().__init__()
        self.bot = bot
        self.mongo_db = initialize_mongodb()
        
        # Try to get current settings
        self.load_current_settings()
    
    async def load_current_settings(self):
        try:
            # Get current settings
            server_config = await self.mongo_db.perplexity_config.find_one({"guild_id": str(self.interaction.guild.id)})
            
            if server_config:
                if "default_credits" in server_config:
                    self.default_credits.default = str(server_config["default_credits"])
                
                if "max_credits" in server_config:
                    self.max_credits.default = str(server_config["max_credits"])
                
                if "daily_reset" in server_config:
                    self.daily_reset.default = "evet" if server_config["daily_reset"] else "hayır"
        except:
            # Use defaults if can't load
            pass
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Validate input
            try:
                default_credits = int(self.default_credits.value)
                max_credits = int(self.max_credits.value)
                
                if default_credits < 0 or max_credits < 0:
                    return await interaction.response.send_message(
                        embed=create_embed("❌ Kredi değerleri negatif olamaz.", discord.Color.red()),
                        ephemeral=True
                    )
                
                daily_reset_value = self.daily_reset.value.lower()
                if daily_reset_value not in ["evet", "hayır", "e", "h", "yes", "no", "y", "n"]:
                    return await interaction.response.send_message(
                        embed=create_embed("❌ Günlük sıfırlama değeri 'evet' veya 'hayır' olmalıdır.", discord.Color.red()),
                        ephemeral=True
                    )
                
                daily_reset = daily_reset_value in ["evet", "e", "yes", "y"]
                
            except ValueError:
                return await interaction.response.send_message(
                    embed=create_embed("❌ Kredi değerleri geçerli sayılar olmalıdır.", discord.Color.red()),
                    ephemeral=True
                )
            
            # Save to database
            await self.mongo_db.perplexity_config.update_one(
                {"guild_id": str(interaction.guild.id)},
                {"$set": {
                    "default_credits": default_credits,
                    "max_credits": max_credits,
                    "daily_reset": daily_reset
                }},
                upsert=True
            )
            
            await interaction.response.send_message(
                embed=create_embed(f"✅ Kredi ayarları güncellendi:\n• Başlangıç Kredisi: {default_credits}\n• Maksimum Kredi: {max_credits}\n• Günlük Sıfırlama: {'Evet' if daily_reset else 'Hayır'}", discord.Color.green()),
                ephemeral=True
            )
            
        except Exception as e:
            logger.error(f"Error setting credit settings: {e}")
            await interaction.response.send_message(
                embed=create_embed(f"❌ Kredi ayarları güncellenirken bir hata oluştu: {str(e)}", discord.Color.red()),
                ephemeral=True
            )


class UserCreditsModal(discord.ui.Modal, title="Üye Kredisi Ekle/Çıkar"):
    """Modal for adding or removing credits from a user"""
    
    user_id = discord.ui.TextInput(
        label="Üye ID",
        placeholder="Kredi değişikliği yapılacak üyenin ID'si",
        required=True,
        style=discord.TextStyle.short
    )
    
    credits = discord.ui.TextInput(
        label="Kredi Miktarı",
        placeholder="Eklemek için pozitif, çıkarmak için negatif değer (örn: 5 veya -3)",
        required=True,
        style=discord.TextStyle.short
    )
    
    def __init__(self, bot):
        super().__init__()
        self.bot = bot
        self.mongo_db = initialize_mongodb()
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Validate input
            try:
                user_id = int(self.user_id.value)
                credits_change = int(self.credits.value)
            except ValueError:
                return await interaction.response.send_message(
                    embed=create_embed("❌ Üye ID ve kredi miktarı geçerli sayılar olmalıdır.", discord.Color.red()),
                    ephemeral=True
                )
            
            # Check if user exists in the guild
            member = interaction.guild.get_member(user_id)
            if not member:
                try:
                    member = await interaction.guild.fetch_member(user_id)
                except:
                    return await interaction.response.send_message(
                        embed=create_embed("❌ Bu ID'ye sahip bir üye bulunamadı.", discord.Color.red()),
                        ephemeral=True
                    )
            
            # Get current credits
            user_data = await self.mongo_db.perplexity_credits.find_one({
                "guild_id": str(interaction.guild.id),
                "user_id": str(user_id)
            })
            
            current_credits = user_data["credits"] if user_data else 0
            
            # Calculate new credits
            new_credits = current_credits + credits_change
            if new_credits < 0:
                new_credits = 0
            
            # Update in database
            await self.mongo_db.perplexity_credits.update_one(
                {"guild_id": str(interaction.guild.id), "user_id": str(user_id)},
                {"$set": {"credits": new_credits}},
                upsert=True
            )
            
            # Create response message
            if credits_change > 0:
                message = f"✅ {member.mention} üyesine **{credits_change}** kredi eklendi. Yeni kredi: **{new_credits}**"
            elif credits_change < 0:
                message = f"✅ {member.mention} üyesinden **{abs(credits_change)}** kredi çıkarıldı. Yeni kredi: **{new_credits}**"
            else:
                message = f"ℹ️ {member.mention} üyesinin kredisi değişmedi. Mevcut kredi: **{new_credits}**"
            
            await interaction.response.send_message(
                embed=create_embed(message, discord.Color.green()),
                ephemeral=True
            )
            
        except Exception as e:
            logger.error(f"Error modifying user credits: {e}")
            await interaction.response.send_message(
                embed=create_embed(f"❌ Üye kredisi güncellenirken bir hata oluştu: {str(e)}", discord.Color.red()),
                ephemeral=True
            )


class ChannelSelector(discord.ui.ChannelSelect):
    """Channel selector for AI permissions"""
    
    def __init__(self, allowed_channels):
        super().__init__(
            channel_types=[discord.ChannelType.text],
            placeholder="AI'nın kullanılabileceği kanalları seçin",
            min_values=0,
            max_values=25  # Discord's limit
        )
        self.selected_channels = allowed_channels
    
    async def callback(self, interaction: discord.Interaction):
        # Update selected channels
        self.selected_channels = [str(channel.id) for channel in self.values]
        
        # Acknowledge the selection
        channel_count = len(self.selected_channels)
        if channel_count > 0:
            message = f"✅ {channel_count} kanal seçildi. Kaydetmek için 'Kaydet' butonuna tıklayın."
        else:
            message = "ℹ️ Hiçbir kanal seçilmedi. Bu, AI'nın tüm kanallarda kullanılabileceği anlamına gelir. Kaydetmek için 'Kaydet' butonuna tıklayın."
        
        await interaction.response.send_message(message, ephemeral=True)
