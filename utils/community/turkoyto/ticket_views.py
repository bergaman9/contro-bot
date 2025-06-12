import discord
import asyncio
import logging
import re
import datetime
import os
import io
from discord.ui import Button, View, Select

from utils.core.formatting import create_embed
from .card_renderer import get_level_scheme

logger = logging.getLogger(__name__)

def get_ticket_level_colors():
    """Kart renderer ile aynı 20 seviye rengini döndürür (Discord renk objesi olarak)."""
    colors = []
    for level in range(20):
        scheme = get_level_scheme(level)
        rgb = scheme["accent"][:3]
        colors.append(discord.Color.from_rgb(*rgb))
    return colors

def register_views(bot):
    """Register all persistent views for the ticket system when the bot starts"""
    logger.info("Registering persistent ticket views")
    # Register a generic ServicesView
    bot.add_view(ServicesView())
    
    # Register ticket buttons with different category IDs that might exist
    # Default ticket button with no category
    bot.add_view(TicketButton())
    
    # Register specific category IDs 
    TICKET_CATEGORY_ID = 829638666313531412  # Your ticket category ID
    bot.add_view(TicketButton(category_id=TICKET_CATEGORY_ID))
    
    logger.info("All persistent ticket views registered successfully")

# Create a services dropdown for the ticket
class ServicesDropdown(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(
                label="Discord Bot Geliştirme",
                description="Özel bot geliştirme ve entegrasyon hizmetleri",
                emoji="🤖",
                value="discord_bot"
            ),
            discord.SelectOption(
                label="Web Site Geliştirme",
                description="Kişisel ve kurumsal web siteleri, e-ticaret vb.",
                emoji="🌐",
                value="web_dev"
            ),
            discord.SelectOption(
                label="Discord Sunucu Kurulumu",
                description="Sunucunuz için kanal, rol ve bot kurulumu",
                emoji="🛠️",
                value="server_setup"
            ),
            discord.SelectOption(
                label="Sunucu İstek ve Önerileri",
                description="Sunucu ile ilgili her türlü istek ve öneri",
                emoji="💬",
                value="server_feedback"
            ),
            discord.SelectOption(
                label="Reklam ve İşbirliği",
                description="Reklam ve işbirliği teklifleri için bilgi alın",
                emoji="🤝",
                value="advertising"
            )
        ]
        
        super().__init__(
            placeholder="Hizmet seçin...",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="services_dropdown"  # Custom ID is important for persistence
        )
    
    async def callback(self, interaction: discord.Interaction):
        service_info = {
            "discord_bot": {
                "title": "🤖 Discord Bot Geliştirme",
                "description": (
                    "**Özel Discord botları geliştiriyoruz!**\n\n"
                    "- Moderasyon ve yönetim botları\n"
                    "- Eğlence ve oyun botları\n"
                    "- Ekonomi ve seviye sistemleri\n"
                    "- Özel API entegrasyonları\n"
                    "- Mevcut botlara özellik ekleme\n\n"
                    "Fiyatlar talebe göre değişiklik gösterir. Detaylı teklifler için ekibimizle iletişime geçin."
                )
            },
            "web_dev": {
                "title": "🌐 Web Site Geliştirme",
                "description": (
                    "**Profesyonel web site tasarım ve geliştirme hizmetleri!**\n\n"
                    "- Kişisel ve kurumsal web siteleri\n"
                    "- E-ticaret platformları\n"
                    "- Blog ve portal siteleri\n"
                    "- Forum ve topluluk siteleri\n"
                    "- Responsive ve modern tasarımlar\n\n"
                    "Size özel teklif için ekibimizle iletişime geçin."
                )
            },
            "server_setup": {
                "title": "🛠️ Discord Sunucu Kurulumu",
                "description": (
                    "**Discord sunucunuzun profesyonel şekilde kurulumu!**\n\n"
                    "- Kanal ve kategori düzeni\n"
                    "- Rol ve izin yapılandırması\n"
                    "- Otomasyon ve güvenlik botlarının kurulumu\n"
                    "- Hoşgeldin, kayıt, moderasyon sistemleri\n"
                    "- Sunucuya özel ayarlar ve tema\n\n"
                    "Sunucunuzun ihtiyacına göre anahtar teslim kurulum hizmeti."
                )
            },
            "server_feedback": {
                "title": "💬 Sunucu İstek ve Önerileri",
                "description": (
                    "**Sunucumuz için geri bildirimleriniz değerlidir!**\n\n"
                    "- Yeni özellik önerileri\n"
                    "- İyileştirme tavsiyeleri\n"
                    "- Etkinlik fikirleri\n"
                    "- Hata bildirimleri\n\n"
                    "Tüm geri bildirimleriniz ekibimiz tarafından dikkatle değerlendirilir."
                )
            },
            "advertising": {
                "title": "🤝 Reklam ve İşbirliği Fırsatları",
                "description": (
                    "**Reklam ve işbirliği için çeşitli fırsatlar sunuyoruz!**\n\n"
                    "- Sunucu tanıtım ortaklıkları\n"
                    "- Bot tanıtım kampanyaları\n"
                    "- İçerik üretici işbirlikleri\n"
                    "- Marka tanıtım etkinlikleri\n"
                    "- Özel pazarlama çözümleri\n\n"
                    "Markalar, içerik üreticileri ve topluluklar için özel kampanyalar hakkında bilgi alın."
                )
            }
        }
        
        selected = self.values[0]
        info = service_info.get(selected, {"title": "Hizmet Bilgisi", "description": "Bu hizmet hakkında bilgi bulunamadı."})
        
        embed = discord.Embed(
            title=info["title"],
            description=info["description"],
            color=discord.Color.blue()
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

class ServicesView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)  # Ensure timeout is None for persistence
        self.add_item(ServicesDropdown())
    
    @staticmethod
    def get_services_embed():
        return discord.Embed(
            description="Hizmetlerimiz hakkında detaylı bilgi almak için seçim yapın.",
            color=discord.Color.blue()
        )

# Update the TicketButton class to correctly respond to interactions
class TicketButton(discord.ui.View):
    def __init__(self, category_id=None):
        super().__init__(timeout=None)  # Ensure timeout is None for persistence
        
        # Store the category ID
        self.category_id = category_id
        
        # Create the button with a specific custom_id pattern
        button = discord.ui.Button(
            label="Destek Talebi", 
            style=discord.ButtonStyle.primary, 
            emoji="🎫",
            custom_id=f"create_ticket_{category_id if category_id else 'default'}"  # Ensure unique ID
        )
        
        # Add button callback
        button.callback = self.ticket_button_callback
        self.add_item(button)

    async def ticket_button_callback(self, interaction: discord.Interaction):
        """Handle button click to create a ticket"""
        logger.info(f"Ticket button clicked by {interaction.user}")
        try:
            # Open the ticket modal
            title = "Türk Oyuncu Topluluğu Destek Talebi"
            modal = TicketModal(title, self.category_id)
            await interaction.response.send_modal(modal)
        except Exception as e:
            logger.error(f"Error handling ticket button: {e}", exc_info=True)
            await interaction.response.send_message(
                embed=create_embed(
                    description="❌ Destek talebi formu açılırken bir hata oluştu.",
                    color=discord.Color.red()
                ),
                ephemeral=True
            )

class TicketModal(discord.ui.Modal, title="Destek Talebi Formu"):
    def __init__(self, title, category_id=None):
        super().__init__(title=title)
        self.category_id = category_id
        
        # Define form fields for the ticket
        self.konu = discord.ui.TextInput(
            label="Konu",
            placeholder="Destek talebinizin konusu nedir?",
            required=True,
            max_length=100,
            style=discord.TextStyle.short
        )
        self.add_item(self.konu)
        
        self.aciklama = discord.ui.TextInput(
            label="Açıklama",
            placeholder="Detaylı açıklama...",
            required=True,
            max_length=1000,
            style=discord.TextStyle.paragraph
        )
        self.add_item(self.aciklama)
        
        self.iletisim = discord.ui.TextInput(
            label="İletişim Bilgileri",
            placeholder="Discord ID'niz veya diğer iletişim bilgileri (opsiyonel)",
            required=False,
            max_length=100,
            style=discord.TextStyle.short
        )
        self.add_item(self.iletisim)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Get the form values
            subject = self.konu.value
            description = self.aciklama.value
            contact_info = self.iletisim.value if self.iletisim.value else "Belirtilmedi"
            
            # Use the new ticket system instead of TurkOyto cog
            from cogs.ticket import TicketModal
            
            # Defer the response to avoid timeouts during ticket creation
            await interaction.response.defer(ephemeral=True)
            
            try:
                # Create a new ticket using the updated ticket system
                ticket_modal = TicketModal("default", interaction.guild.id, interaction.client, "tr")
                
                # Simulate form submission with the collected data
                # Create a mock interaction for the ticket modal
                from utils.database import get_async_db
                
                mongo_db = get_async_db()
                settings = await mongo_db.ticket_settings.find_one({"guild_id": interaction.guild.id})
                
                if not settings or not settings.get("category_id"):
                    await interaction.followup.send(
                        embed=create_embed(
                            description="❌ Ticket sistemi yapılandırılmamış. Lütfen bir yöneticiyle iletişime geçin.",
                            color=discord.Color.red()
                        ),
                        ephemeral=True
                    )
                    return
                
                category_id = settings.get("category_id")
                category = interaction.guild.get_channel(category_id)
                if not category:
                    await interaction.followup.send(
                        embed=create_embed(
                            description="❌ Ticket kategorisi bulunamadı.",
                            color=discord.Color.red()
                        ),
                        ephemeral=True
                    )
                    return
                
                # Check max tickets per user
                max_tickets = settings.get("max_tickets_per_user", 5)
                user_tickets = [ch for ch in category.channels if str(interaction.user.id) in ch.name]
                
                if len(user_tickets) >= max_tickets:
                    await interaction.followup.send(
                        embed=create_embed(
                            description=f"❌ Zaten {len(user_tickets)} açık ticket'ınız var! Maksimum izin verilen: {max_tickets}",
                            color=discord.Color.red()
                        ),
                        ephemeral=True
                    )
                    return
                
                # Get user's ticket count for numbering
                all_user_tickets = await mongo_db.tickets.count_documents({
                    "guild_id": interaction.guild.id,
                    "user_id": interaction.user.id
                })
                ticket_number = all_user_tickets + 1
                
                # Create ticket channel
                overwrites = {
                    interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                    interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                    interaction.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
                }
                
                # Add support roles
                support_roles = settings.get("support_roles", [])
                for role_id in support_roles:
                    role = interaction.guild.get_role(role_id)
                    if role:
                        overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
                
                # Create channel name
                naming_format = settings.get("ticket_naming_format", "ticket-{username}-{ticketnumber}")
                channel_name = naming_format.format(
                    username=interaction.user.name,
                    discriminator=interaction.user.discriminator,
                    userid=interaction.user.id,
                    ticketnumber=ticket_number
                ).lower().replace(" ", "-")
                
                ticket_channel = await category.create_text_channel(
                    name=channel_name,
                    overwrites=overwrites
                )
                
                # Create ticket embed
                embed = discord.Embed(
                    color=discord.Color.blue(),
                    timestamp=discord.utils.utcnow()
                )

                # Set author with member's ticket format and ticket number
                embed.set_author(
                    name=f"{interaction.user.display_name}'s Ticket #{ticket_number}",
                    icon_url=interaction.user.display_avatar.url
                )

                # Add description with contact message
                embed.description = "En kısa sürede sizinle iletişime geçeceğiz."

                # Add user info with single backticks (moved to top)
                embed.add_field(
                    name="👤 Kullanıcı",
                    value=f"`{interaction.user.name}#{interaction.user.discriminator}`",
                    inline=True
                )

                embed.add_field(
                    name="🆔 Kullanıcı ID",
                    value=f"`{interaction.user.id}`",
                    inline=True
                )

                embed.add_field(
                    name="🎫 Ticket Sayısı",
                    value=f"`{ticket_number}`",
                    inline=True
                )
                
                # Add form fields to embed with code blocks
                embed.add_field(
                    name="📝 Konu",
                    value=f"```\n{subject}\n```",
                    inline=False
                )
                
                embed.add_field(
                    name="📝 Açıklama",
                    value=f"```\n{description}\n```",
                    inline=False
                )
                
                embed.add_field(
                    name="📞 İletişim Bilgisi",
                    value=f"```\n{contact_info}\n```",
                    inline=False
                )
                
                # Generate images if enabled
                ticket_image_path = None
                level_card_path = None
                
                enable_ticket_images = settings.get("enable_ticket_images", True)
                enable_level_cards = settings.get("enable_level_cards", True)
                
                files = []
                
                if enable_level_cards:
                    try:
                        from utils.community.turkoyto.card_renderer import create_level_card_for_ticket
                        level_card_path = await create_level_card_for_ticket(interaction.user, interaction.guild, interaction.client)
                        if level_card_path and os.path.exists(level_card_path):
                            files.append(discord.File(level_card_path, filename="level_card.png"))
                            embed.set_image(url="attachment://level_card.png")
                    except Exception as e:
                        logger.error(f"Error creating level card: {e}")
                
                if enable_ticket_images:
                    try:
                        from utils.community.turkoyto.card_renderer import create_ticket_card
                        ticket_image_path = await create_ticket_card(interaction.guild, interaction.client)
                        if ticket_image_path and os.path.exists(ticket_image_path):
                            files.append(discord.File(ticket_image_path, filename="ticket_image.png"))
                            embed.set_thumbnail(url="attachment://ticket_image.png")
                    except Exception as e:
                        logger.error(f"Error creating ticket image: {e}")
                
                # Create ticket control view
                from cogs.ticket import TicketControlView
                view = TicketControlView("tr")
                
                # Send ticket message
                if files:
                    await ticket_channel.send(embed=embed, view=view, files=files)
                else:
                    await ticket_channel.send(embed=embed, view=view)
                
                # Save ticket to database
                await mongo_db.tickets.insert_one({
                    "guild_id": interaction.guild.id,
                    "user_id": interaction.user.id,
                    "channel_id": ticket_channel.id,
                    "ticket_number": ticket_number,
                    "status": "open",
                    "created_at": discord.utils.utcnow()
                })
                
                # Clean up image files
                for path in [ticket_image_path, level_card_path]:
                    if path and os.path.exists(path):
                        try:
                            os.remove(path)
                        except Exception as e:
                            logger.error(f"Error removing file {path}: {e}")
                
                # Log ticket creation
                log_channel_id = settings.get("log_channel_id")
                if log_channel_id:
                    log_channel = interaction.guild.get_channel(log_channel_id)
                    if log_channel:
                        log_embed = discord.Embed(
                            title="🎫 Yeni Ticket Oluşturuldu",
                            color=discord.Color.green(),
                            timestamp=discord.utils.utcnow()
                        )
                        log_embed.add_field(name="Kullanıcı", value=interaction.user.mention, inline=True)
                        log_embed.add_field(name="Kanal", value=ticket_channel.mention, inline=True)
                        log_embed.add_field(name="Ticket #", value=str(ticket_number), inline=True)
                        await log_channel.send(embed=log_embed)
                
                await interaction.followup.send(
                    embed=create_embed(
                        description=f"✅ Destek talebiniz oluşturuldu: {ticket_channel.mention}",
                        color=discord.Color.green()
                    ),
                    ephemeral=True
                )
                    
            except Exception as e:
                logger.error(f"Error creating ticket: {e}")
                await interaction.followup.send(
                    embed=create_embed(
                        description="❌ Destek talebi oluşturulurken bir hata oluştu. Lütfen daha sonra tekrar deneyin.",
                        color=discord.Color.red()
                    ),
                    ephemeral=True
                )
            
        except Exception as e:
            # Handle unexpected errors
            logger.error(f"Error in ticket modal submission: {e}", exc_info=True)
            
            error_message = "❌ Destek talebi oluşturulurken bir hata oluştu, lütfen daha sonra tekrar deneyin."
            
            try:
                await interaction.followup.send(
                    embed=create_embed(
                        description=error_message,
                        color=discord.Color.red()
                    ),
                    ephemeral=True
                )
            except Exception as response_error:
                logger.error(f"Failed to send error response: {response_error}")

class TicketManagementView(discord.ui.View):
    def __init__(self, channel_id, user_id, ticket_number):
        super().__init__(timeout=None)  # Ensure timeout is None for persistence
        self.channel_id = channel_id
        self.user_id = user_id
        self.ticket_number = ticket_number
        
        # Create the button with a unique custom_id for persistence
        close_button = discord.ui.Button(
            label="Talebi Kapat", 
            style=discord.ButtonStyle.danger, 
            emoji="🔒", 
            custom_id=f"close_ticket_{channel_id}"  # Ensure unique ID
        )
        
        # Attach the callback manually
        close_button.callback = self.close_ticket_callback
        
        # Add the button to the view
        self.add_item(close_button)
    
    # Define the callback method - no decorator to avoid conflicts
    async def close_ticket_callback(self, interaction: discord.Interaction):
        # Defer the response immediately to prevent timeout
        await interaction.response.defer(ephemeral=True)
        
        # Check permissions (staff or ticket creator)
        if not await self.check_permissions(interaction):
            return
        
        # Update ticket status in database
        try:
            from utils.database import get_async_db
            mongo_db = get_async_db()
            
            # Update ticket status
            await mongo_db.tickets.update_one(
                {"channel_id": self.channel_id},
                {"$set": {"status": "closed", "closed_at": discord.utils.utcnow()}}
            )
        except Exception as e:
            logger.error(f"Error updating ticket status: {e}")
            
        # Change channel permissions - remove user's ability to send messages
        channel = interaction.channel
        member = interaction.guild.get_member(self.user_id)
        if member:
            try:
                await channel.set_permissions(member, read_messages=True, send_messages=False)
                
                # Create new management view with additional buttons - simplified approach
                closed_view = TicketClosedView(self.channel_id, self.user_id, self.ticket_number)
                
                # Add a message indicating ticket is closed with management buttons
                await channel.send(
                    embed=create_embed(
                        description=f"🔒 Bu destek talebi {interaction.user.mention} tarafından kapatıldı. Sadece yetkililer mesaj gönderebilir.",
                        color=discord.Color.orange()
                    ),
                    view=closed_view
                )
                
                # Register the view
                try:
                    # Ensure the view is registered with the bot for persistence
                    interaction.client.add_view(closed_view, message_id=None)  # message_id=None to register for any message
                    logger.info(f"Successfully registered closed ticket view for channel {self.channel_id}")
                except Exception as e:
                    logger.error(f"Error registering closed ticket view: {e}")
                
                # Confirm to the user that the ticket was closed
                await interaction.followup.send(
                    embed=create_embed(
                        description=f"✅ Destek talebi başarıyla kapatıldı.",
                        color=discord.Color.green()
                    ),
                    ephemeral=True
                )
                
            except Exception as e:
                logger.error(f"Error updating channel permissions: {e}")
                await interaction.followup.send(
                    embed=create_embed(
                        description="❌ Talebi kapatırken bir hata oluştu.",
                        color=discord.Color.red()
                    ),
                    ephemeral=True
                )

    # Add this method to check permissions
    async def check_permissions(self, interaction):
        member = interaction.user
        
        # Check if user is staff
        is_staff = member.guild_permissions.manage_channels or any(
            role.name.lower() in ["mod", "admin", "moderator", "administrator"] 
            for role in member.roles
        )
        
        # Check if user is ticket creator
        is_creator = member.id == self.user_id
        
        if not (is_creator or is_staff):
            await interaction.response.send_message(
                embed=create_embed(
                    description="❌ Bu işlemi gerçekleştirmek için talep sahibi veya yetkili olmanız gerekiyor.",
                    color=discord.Color.red()
                ),
                ephemeral=True
            )
            return False
            
        return True

class TicketClosedView(discord.ui.View):
    def __init__(self, channel_id, user_id, ticket_number):
        super().__init__(timeout=None)  # Ensure timeout is None for persistence
        self.channel_id = channel_id
        self.user_id = user_id
        self.ticket_number = ticket_number

        # Add buttons with unique IDs for persistence
        delete_button = discord.ui.Button(
            label="Sil",
            style=discord.ButtonStyle.danger,
            emoji="🗑️",
            custom_id=f"delete_ticket_{channel_id}",
            row=0
        )
        delete_button.callback = self.delete_ticket_callback

        reopen_button = discord.ui.Button(
            label="Yeniden Aç",
            style=discord.ButtonStyle.success,
            emoji="🔓",
            custom_id=f"reopen_ticket_{channel_id}",
            row=0
        )
        reopen_button.callback = self.reopen_ticket_callback

        transcript_button = discord.ui.Button(
            label="Döküman",
            style=discord.ButtonStyle.primary,
            emoji="📝",
            custom_id=f"transcript_ticket_{channel_id}",
            row=0
        )
        transcript_button.callback = self.transcript_ticket_callback

        self.add_item(delete_button)
        self.add_item(reopen_button)
        self.add_item(transcript_button)

    async def delete_ticket_callback(self, interaction: discord.Interaction):
        # Defer the response immediately to prevent timeout
        await interaction.response.defer(ephemeral=True)
        
        if not interaction.user.guild_permissions.manage_channels:
            await interaction.followup.send(
                embed=create_embed(
                    description="❌ Talep kanalını silme yetkiniz yok.",
                    color=discord.Color.red()
                ),
                ephemeral=True
            )
            return

        await interaction.followup.send(
            embed=create_embed(
                description="⚠️ Bu talebi silmek üzeresiniz. Bu işlem geri alınamaz.",
                color=discord.Color.red()
            ),
            ephemeral=True
        )
        await asyncio.sleep(2)
        try:
            await self.create_transcript(interaction, delete_after=True)
        except Exception as e:
            logger.error(f"Error deleting ticket: {e}")
            await interaction.followup.send(
                embed=create_embed(
                    description="❌ Talep silinirken bir hata oluştu.",
                    color=discord.Color.red()
                ),
                ephemeral=True
            )

    async def reopen_ticket_callback(self, interaction: discord.Interaction):
        # Defer the response immediately to prevent timeout
        await interaction.response.defer(ephemeral=True)
        
        if not await self.check_permissions(interaction, staff_only=True):
            return

        channel = interaction.channel
        member = interaction.guild.get_member(self.user_id)
        if member:
            try:
                await channel.set_permissions(member, read_messages=True, send_messages=True)
                cog = interaction.client.get_cog("TurkOyto")
                if cog and hasattr(cog, 'mongo_db'):
                    try:
                        await cog.mongo_db["turkoyto_tickets"].update_one(
                            {"user_id": self.user_id, "active_tickets.channel_id": self.channel_id},
                            {"$set": {"active_tickets.$.status": "open", "active_tickets.$.reopened_at": datetime.datetime.now()}}
                        )
                    except (TypeError, AttributeError):
                        cog.mongo_db["turkoyto_tickets"].update_one(
                            {"user_id": self.user_id, "active_tickets.channel_id": self.channel_id},
                            {"$set": {"active_tickets.$.status": "open", "active_tickets.$.reopened_at": datetime.datetime.now()}}
                        )
                management_view = TicketManagementView(self.channel_id, self.user_id, self.ticket_number)
                await channel.send(
                    embed=create_embed(
                        description=f"🔓 Bu destek talebi {interaction.user.mention} tarafından yeniden açıldı.",
                        color=discord.Color.green()
                    ),
                    view=management_view
                )
                interaction.client.add_view(management_view)
                
                # Confirm to the user that the ticket was reopened
                await interaction.followup.send(
                    embed=create_embed(
                        description=f"✅ Destek talebi başarıyla yeniden açıldı.",
                        color=discord.Color.green()
                    ),
                    ephemeral=True
                )
            except Exception as e:
                logger.error(f"Error reopening ticket: {e}")
                await interaction.followup.send(
                    embed=create_embed(
                        description="❌ Talebi yeniden açarken bir hata oluştu.",
                        color=discord.Color.red()
                    ),
                    ephemeral=True
                )

    async def transcript_ticket_callback(self, interaction: discord.Interaction):
        # Defer the response immediately to prevent timeout
        await interaction.response.defer(ephemeral=True)
        
        if not await self.check_permissions(interaction):
            return
        await self.create_transcript(interaction)

    async def check_permissions(self, interaction, staff_only=False):
        member = interaction.user
        is_staff = member.guild_permissions.manage_channels or any(
            role.name.lower() in ["mod", "admin", "moderator", "administrator"]
            for role in member.roles
        )
        if staff_only and not is_staff:
            await interaction.followup.send(
                embed=create_embed(
                    description="❌ Bu işlemi gerçekleştirmek için yetkili olmanız gerekiyor.",
                    color=discord.Color.red()
                ),
                ephemeral=True
            )
            return False
        is_creator = member.id == self.user_id
        if not (is_creator or is_staff):
            await interaction.followup.send(
                embed=create_embed(
                    description="❌ Bu işlemi gerçekleştirmek için talep sahibi veya yetkili olmanız gerekiyor.",
                    color=discord.Color.red()
                ),
                ephemeral=True
            )
            return False
        return True

    async def create_transcript(self, interaction, delete_after=False):
        channel = interaction.channel
        try:
            messages = []
            async for message in channel.history(limit=500, oldest_first=True):
                timestamp = message.created_at.strftime("%Y-%m-%d %H:%M:%S")
                author = message.author.name
                content = message.content or "*[No text content]*"
                attachments = [f"[Attachment: {a.filename}]({a.url})" for a in message.attachments]
                embeds = [f"[Embed: {e.title}]" for e in message.embeds if e.title]
                formatted_message = f"**{timestamp}** - **{author}**:\n{content}"
                if attachments:
                    formatted_message += "\n" + "\n".join(attachments)
                if embeds:
                    formatted_message += "\n" + "\n".join(embeds)
                messages.append(formatted_message)
            transcript_content = f"# Ticket Transcript: {channel.name}\n"
            transcript_content += f"Created: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            transcript_content += "\n\n---\n\n".join(messages)
            transcript_file = discord.File(
                io.StringIO(transcript_content),
                filename=f"{channel.name}-transcript.md"
            )
            logs_channel = None
            for ch in interaction.guild.text_channels:
                if ch.name in ["ticket-logs", "ticket-transcripts", "logs"]:
                    logs_channel = ch
                    break
            if not logs_channel and interaction.user.guild_permissions.manage_channels:
                logs_channel = await interaction.guild.create_text_channel(
                    name="ticket-logs",
                    topic="Ticket system logs and transcripts",
                    overwrites={
                        interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                        interaction.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
                    }
                )
            if logs_channel:
                member = interaction.guild.get_member(self.user_id)
                member_mention = member.mention if member else f"ID: {self.user_id}"
                embed = discord.Embed(
                    title=f"📝 Ticket Transcript",
                    description=(
                        f"**Kanal:** {channel.name}\n"
                        f"**Kullanıcı:** {member_mention}\n"
                        f"**Ticket Numarası:** {self.ticket_number}\n"
                        f"**Tarih:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                    ),
                    color=discord.Color.blue()
                )
                await logs_channel.send(embed=embed, file=transcript_file)
                if not delete_after:
                    await interaction.followup.send(
                        embed=create_embed(
                            description=f"✅ Ticket dökümü oluşturuldu ve {logs_channel.mention} kanalına gönderildi.",
                            color=discord.Color.green()
                        ),
                        ephemeral=True
                    )
            elif not delete_after:
                await interaction.followup.send(
                    embed=create_embed(
                        description="📝 Ticket dökümü oluşturuldu:",
                        color=discord.Color.blue()
                    ),
                    file=transcript_file,
                    ephemeral=True
                )
            try:
                cog = interaction.client.get_cog("TurkOyto")
                if cog and hasattr(cog, 'mongo_db'):
                    try:
                        await cog.mongo_db["turkoyto_tickets"].update_one(
                            {"user_id": self.user_id, "active_tickets.channel_id": self.channel_id},
                            {"$set": {"active_tickets.$.status": "archived", "active_tickets.$.archived_at": datetime.datetime.now()}}
                        )
                    except (TypeError, AttributeError):
                        cog.mongo_db["turkoyto_tickets"].update_one(
                            {"user_id": self.user_id, "active_tickets.channel_id": self.channel_id},
                            {"$set": {"active_tickets.$.status": "archived", "active_tickets.$.archived_at": datetime.datetime.now()}}
                        )
            except Exception as db_error:
                logger.error(f"Database error during ticket operation: {db_error}")
            if delete_after:
                await channel.delete(reason=f"Destek talebi {interaction.user.name} tarafından silindi")
        except Exception as e:
            logger.error(f"Error creating transcript: {e}", exc_info=True)
            if not delete_after:
                await interaction.followup.send(
                    embed=create_embed(
                        description="❌ Döküm oluşturulurken bir hata oluştu.",
                        color=discord.Color.red()
                    ),
                    ephemeral=True
                )

# For backwards compatibility
class TicketCloseView(TicketClosedView):
    def __init__(self, channel_id, user_id, ticket_number):
        super().__init__(channel_id, user_id, ticket_number)