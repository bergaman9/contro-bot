import discord
from typing import Dict, List, Optional, Union
import logging
import asyncio

# Configure logger
logger = logging.getLogger('ticket_settings')

class TicketSettingsView(discord.ui.View):
    """Interactive view for configuring ticket system settings"""
    
    def __init__(self, bot, guild_id, timeout=180):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.guild_id = guild_id
        self.message = None
        
    async def start(self, interaction: discord.Interaction):
        """Start the ticket settings view"""
        embed = self.create_settings_embed()
        await interaction.response.send_message(embed=embed, view=self, ephemeral=True)
        
    def create_settings_embed(self):
        """Create the ticket settings embed"""
        embed = discord.Embed(
            title="🎫 Ticket Sistemi Ayarları",
            description="Aşağıdaki butonları kullanarak ticket sistemini yapılandırabilirsiniz.",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="Mevcut Ayarlar",
            value=(
                "**Ticket Kategorisi:** Ayarlanmamış\n"
                "**Log Kanalı:** Ayarlanmamış\n"
                "**Yetkili Rolü:** Ayarlanmamış\n"
                "**Ticket Türleri:** Ayarlanmamış"
            ),
            inline=False
        )
        
        embed.add_field(
            name="Neler Yapabilirsiniz?",
            value=(
                "• Ticket kategorisini ayarlayın\n"
                "• Log kanalını ayarlayın\n"
                "• Yetkili rolünü belirleyin\n"
                "• Ticket türlerini ekleyin veya düzenleyin\n"
                "• Özel formlar oluşturun\n"
                "• Ticket mesajını düzenleyin"
            ),
            inline=False
        )
        
        embed.set_footer(text="Bir ayarı değiştirmek için ilgili butona tıklayın")
        
        return embed
    
    @discord.ui.button(label="Kategori Ayarla", style=discord.ButtonStyle.primary, emoji="📁", row=0)
    async def set_category(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Set the ticket category"""
        # Create a selection menu for categories
        await interaction.response.send_modal(SetCategoryModal(self.bot, self.guild_id))
    
    @discord.ui.button(label="Log Kanalı Ayarla", style=discord.ButtonStyle.primary, emoji="📋", row=0)
    async def set_log_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Set the ticket log channel"""
        # Show channel selection menu
        await interaction.response.send_message("Log kanalı seçme menüsü burada görünecek", ephemeral=True)
    
    @discord.ui.button(label="Yetkili Rolü Ayarla", style=discord.ButtonStyle.primary, emoji="👮", row=1)
    async def set_staff_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Set the staff role for tickets"""
        # Show role selection menu
        await interaction.response.send_message("Rol seçme menüsü burada görünecek", ephemeral=True)
    
    @discord.ui.button(label="Ticket Türleri", style=discord.ButtonStyle.primary, emoji="📝", row=1)
    async def manage_ticket_types(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Manage ticket types"""
        # Show ticket types management view
        await interaction.response.send_message("Ticket türleri yönetim menüsü burada görünecek", ephemeral=True)
    
    @discord.ui.button(label="Ticket Mesajı", style=discord.ButtonStyle.primary, emoji="💬", row=2)
    async def set_ticket_message(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Set the ticket message"""
        # Show message editor
        await interaction.response.send_message("Ticket mesajı düzenleme menüsü burada görünecek", ephemeral=True)
    
    @discord.ui.button(label="Gönder", style=discord.ButtonStyle.success, emoji="✅", row=3)
    async def send_ticket_panel(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Send the ticket panel to a channel"""
        # Show channel selection for sending the ticket panel
        await interaction.response.send_message("Kanal seçme menüsü burada görünecek", ephemeral=True)
    
    @discord.ui.button(label="İptal", style=discord.ButtonStyle.danger, emoji="❌", row=3)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Cancel the ticket settings view"""
        await interaction.response.defer()
        await self.message.delete()
        self.stop()


class SetCategoryModal(discord.ui.Modal, title="Ticket Kategorisi Ayarla"):
    """Modal for setting the ticket category"""
    
    category_id = discord.ui.TextInput(
        label="Kategori ID",
        placeholder="Kategori ID'sini girin",
        required=True,
        style=discord.TextStyle.short
    )
    
    def __init__(self, bot, guild_id):
        super().__init__()
        self.bot = bot
        self.guild_id = guild_id
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle the modal submission"""
        try:
            category_id = int(self.category_id.value)
            category = interaction.guild.get_channel(category_id)
            
            if not category or not isinstance(category, discord.CategoryChannel):
                return await interaction.response.send_message(
                    "❌ Geçerli bir kategori ID'si girin.",
                    ephemeral=True
                )
            
            # Save to database would go here
            
            await interaction.response.send_message(
                f"✅ Ticket kategorisi başarıyla `{category.name}` olarak ayarlandı.",
                ephemeral=True
            )
        except ValueError:
            await interaction.response.send_message(
                "❌ Geçerli bir kategori ID'si girin.",
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Error setting ticket category: {e}")
            await interaction.response.send_message(
                f"❌ Bir hata oluştu: {str(e)}",
                ephemeral=True
            )
