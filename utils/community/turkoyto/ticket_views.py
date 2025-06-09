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

logger = logging.getLogger('turkoyto.ticket_views')

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
            
            # Create a ticket
            cog = interaction.client.get_cog("TurkOyto")
            if not cog:
                raise ValueError("TurkOyto cog not found. Please contact an administrator.")
                
            if not hasattr(cog, 'create_ticket'):
                raise ValueError("create_ticket method not found. Please contact an administrator.")
                
            # Defer the response to avoid timeouts during ticket creation
            await interaction.response.defer(ephemeral=True)
            
            # Add category_id to the ticket creation parameters if it's available
            kwargs = {
                "interaction": interaction,
                "subject": subject,
                "description": description,
                "contact_info": contact_info
            }
            
            # Add category_id to kwargs if available
            if hasattr(self, 'category_id') and self.category_id:
                kwargs["category_id"] = self.category_id
            
            # Create the ticket with timeout handling
            try:
                # Wrap ticket creation in wait_for to prevent indefinite hang
                ticket_creation_task = asyncio.create_task(cog.create_ticket(**kwargs))
                ticket_channel = await asyncio.wait_for(ticket_creation_task, timeout=30.0)  # 30 second timeout
                
                # Send confirmation message after ticket creation
                if ticket_channel:
                    services_embed = ServicesView.get_services_embed()
                    services_view = ServicesView()
                    
                    try:
                        await ticket_channel.send(embed=services_embed, view=services_view)
                    except Exception as e:
                        logger.error(f"Error sending services view to ticket channel: {e}")
                        # Continue anyway - the ticket is already created
                    
                    await interaction.followup.send(
                        embed=create_embed(
                            description=f"✅ Destek talebiniz oluşturuldu: {ticket_channel.mention}",
                            color=discord.Color.green()
                        ),
                        ephemeral=True
                    )
                else:
                    await interaction.followup.send(
                        embed=create_embed(
                            description="❌ Destek talebi oluşturulurken bir hata oluştu. Lütfen daha sonra tekrar deneyin.",
                            color=discord.Color.red()
                        ),
                        ephemeral=True
                    )
                    
            except asyncio.TimeoutError:
                logger.error("Ticket creation timed out after 30 seconds")
                await interaction.followup.send(
                    embed=create_embed(
                        description="⏱️ Destek talebi oluşturma işlemi zaman aşımına uğradı. Lütfen daha sonra tekrar deneyin.",
                        color=discord.Color.red()
                    ),
                    ephemeral=True
                )
                # Cancel the task to prevent it from continuing in background
                if not ticket_creation_task.done():
                    ticket_creation_task.cancel()
            
        except ValueError as ve:
            # Handle expected errors
            logger.warning(f"Ticket creation validation error: {ve}")
            try:
                await interaction.followup.send(
                    embed=create_embed(
                        description=f"❌ {str(ve)}",
                        color=discord.Color.red()
                    ),
                    ephemeral=True
                )
            except:
                logger.error("Failed to send validation error message")
        except Exception as e:
            # Handle unexpected errors
            logger.error(f"Error creating ticket: {e}", exc_info=True)
            
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
            cog = interaction.client.get_cog("TurkOyto")
            if cog and hasattr(cog, 'mongo_db'):
                try:
                    await cog.mongo_db["turkoyto_tickets"].update_one(
                        {"user_id": self.user_id, "active_tickets.channel_id": self.channel_id},
                        {"$set": {"active_tickets.$.status": "closed", "active_tickets.$.closed_at": datetime.datetime.now()}}
                    )
                except (TypeError, AttributeError):
                    cog.mongo_db["turkoyto_tickets"].update_one(
                        {"user_id": self.user_id, "active_tickets.channel_id": self.channel_id},
                        {"$set": {"active_tickets.$.status": "closed", "active_tickets.$.closed_at": datetime.datetime.now()}}
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