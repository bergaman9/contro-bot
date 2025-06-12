# Ticket Settings Views
import discord
import logging
from utils.database import get_async_db
from utils.core.formatting import create_embed

logger = logging.getLogger('ticket_settings')

class TicketSettingsView(discord.ui.View):
    """Main view for ticket system settings"""
    
    def __init__(self, bot, guild_id=None, timeout=180):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.guild_id = guild_id

    async def get_db(self):
        return get_async_db()

    @discord.ui.button(label="🏷️ Set Category", style=discord.ButtonStyle.primary, custom_id="set_ticket_category", row=0)
    async def set_category_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(SetTicketCategoryModal(self.bot))

    @discord.ui.button(label="📝 Set Log Channel", style=discord.ButtonStyle.secondary, custom_id="set_ticket_log", row=0)
    async def set_log_channel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(SetTicketLogChannelModal(self.bot))

    @discord.ui.button(label="👑 Set Support Roles", style=discord.ButtonStyle.secondary, custom_id="set_support_roles", row=0)
    async def set_support_roles_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(SetSupportRolesModal(self.bot))

    @discord.ui.button(label="🌐 Set Language", style=discord.ButtonStyle.secondary, custom_id="set_language", row=0)
    async def set_language_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(SetLanguageModal(self.bot))

    @discord.ui.button(label="🖼️ Toggle Ticket Images", style=discord.ButtonStyle.secondary, custom_id="toggle_ticket_images", row=1)
    async def toggle_ticket_images_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            mongo_db = await self.get_db()
            settings = await mongo_db.ticket_settings.find_one({"guild_id": interaction.guild.id})
            
            current_state = settings.get("enable_ticket_images", True) if settings else True
            new_state = not current_state
            
            await mongo_db.ticket_settings.update_one(
                {"guild_id": interaction.guild.id},
                {"$set": {"enable_ticket_images": new_state}},
                upsert=True
            )
            
            status = "enabled" if new_state else "disabled"
            await interaction.response.send_message(f"✅ Ticket images {status}!", ephemeral=True)
            
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)

    @discord.ui.button(label="👤 Toggle Level Cards", style=discord.ButtonStyle.secondary, custom_id="toggle_level_cards", row=1)
    async def toggle_level_cards_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            mongo_db = await self.get_db()
            settings = await mongo_db.ticket_settings.find_one({"guild_id": interaction.guild.id})
            
            current_state = settings.get("enable_level_cards", True) if settings else True
            new_state = not current_state
            
            await mongo_db.ticket_settings.update_one(
                {"guild_id": interaction.guild.id},
                {"$set": {"enable_level_cards": new_state}},
                upsert=True
            )
            
            status = "enabled" if new_state else "disabled"
            await interaction.response.send_message(f"✅ Level cards {status}!", ephemeral=True)
            
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)

    @discord.ui.button(label="📝 Edit Embed Fields", style=discord.ButtonStyle.secondary, custom_id="edit_embed_fields", row=1)
    async def edit_embed_fields_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(EditEmbedFieldsModal(self.bot))

    @discord.ui.button(label="📋 Manage Ticket Fields", style=discord.ButtonStyle.secondary, custom_id="edit_ticket_fields", row=1)
    async def edit_ticket_fields_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(EditTicketFieldsModal(self.bot))

    @discord.ui.button(label="⚙️ Advanced Settings", style=discord.ButtonStyle.secondary, custom_id="advanced_settings", row=2)
    async def advanced_settings_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(AdvancedTicketSettingsModal(self.bot))

    @discord.ui.button(label="🎫 Create Ticket Message", style=discord.ButtonStyle.success, custom_id="create_ticket_message", row=2)
    async def create_ticket_message_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(CreateTicketMessageModal(self.bot))

    @discord.ui.button(label="📊 View Current Settings", style=discord.ButtonStyle.primary, custom_id="view_settings", row=2)
    async def view_settings_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            mongo_db = await self.get_db()
            settings = await mongo_db.ticket_settings.find_one({"guild_id": interaction.guild.id})
            
            if not settings:
                await interaction.response.send_message("❌ No ticket settings found for this server!", ephemeral=True)
                return
            
            embed = discord.Embed(
                title="🎫 Current Ticket Settings",
                color=discord.Color.blue(),
                timestamp=discord.utils.utcnow()
            )
            
            # Basic Settings
            category_id = settings.get("category_id")
            category = interaction.guild.get_channel(category_id) if category_id else None
            embed.add_field(
                name="🏷️ Category",
                value=category.name if category else "Not set",
                inline=True
            )
            
            log_channel_id = settings.get("log_channel_id")
            log_channel = interaction.guild.get_channel(log_channel_id) if log_channel_id else None
            embed.add_field(
                name="📝 Log Channel",
                value=log_channel.mention if log_channel else "Not set",
                inline=True
            )
            
            language = settings.get("language", "en")
            embed.add_field(
                name="🌐 Language",
                value="🇹🇷 Turkish" if language == "tr" else "🇺🇸 English",
                inline=True
            )
            
            # Support Roles
            support_roles = settings.get("support_roles", [])
            if support_roles:
                role_mentions = []
                for role_id in support_roles:
                    role = interaction.guild.get_role(role_id)
                    if role:
                        role_mentions.append(role.mention)
                embed.add_field(
                    name="👑 Support Roles",
                    value=", ".join(role_mentions) if role_mentions else "None",
                    inline=False
                )
            
            # Feature Settings
            features = []
            if settings.get("enable_ticket_images", True):
                features.append("🖼️ Ticket Images")
            if settings.get("enable_level_cards", True):
                features.append("👤 Level Cards")
            
            embed.add_field(
                name="✨ Enabled Features",
                value="\n".join(features) if features else "None",
                inline=True
            )
            
            # Advanced Settings
            advanced_info = []
            if settings.get("max_tickets_per_user"):
                advanced_info.append(f"Max tickets per user: {settings['max_tickets_per_user']}")
            if settings.get("auto_close_days"):
                advanced_info.append(f"Auto-close after: {settings['auto_close_days']} days")
            if settings.get("ticket_naming_format"):
                advanced_info.append(f"Naming format: {settings['ticket_naming_format']}")
            
            if advanced_info:
                embed.add_field(
                    name="⚙️ Advanced Settings",
                    value="\n".join(advanced_info),
                    inline=False
                )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)

class CreateTicketMessageModal(discord.ui.Modal):
    """Modal for creating a ticket message with customizable fields"""
    
    def __init__(self, bot):
        super().__init__(title="Create Ticket Message")
        self.bot = bot
        
        # Define text inputs as instance variables
        self.channel_id = discord.ui.TextInput(
            label="Channel ID or #channel",
            placeholder="Enter channel ID or mention the channel",
            required=True,
            max_length=100
        )
        
        self.embed_title = discord.ui.TextInput(
            label="Embed Title",
            placeholder="Support System",
            required=False,
            max_length=256
        )
        
        self.embed_description = discord.ui.TextInput(
            label="Main Description",
            placeholder="Welcome to our support system! Click the button below to create a ticket.",
            style=discord.TextStyle.long,
            required=False,
            max_length=2000
        )
        
        self.custom_fields = discord.ui.TextInput(
            label="Custom Fields (JSON format)",
            placeholder='[{"name": "How it works", "value": "• Click Create Ticket\\n• Fill out form\\n• Get help"}]',
            style=discord.TextStyle.long,
            required=False,
            max_length=1500
        )
        
        # Add items to the modal
        self.add_item(self.channel_id)
        self.add_item(self.embed_title)
        self.add_item(self.embed_description)
        self.add_item(self.custom_fields)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Parse channel
            channel_input = self.channel_id.value.strip()
            if channel_input.startswith('<#') and channel_input.endswith('>'):
                channel_id = int(channel_input[2:-1])
            else:
                channel_id = int(channel_input)
            
            channel = interaction.guild.get_channel(channel_id)
            if not channel:
                await interaction.response.send_message("❌ Channel not found!", ephemeral=True)
                return
            
            # Get language setting
            mongo_db = get_async_db()
            settings = await mongo_db.ticket_settings.find_one({"guild_id": interaction.guild.id})
            language = settings.get("language", "en") if settings else "en"
            
            # Create embed with customizable content
            if self.embed_title.value:
                embed_title = self.embed_title.value
            else:
                embed_title = "Support System" if language == "en" else "Destek Sistemi"
            
            if self.embed_description.value:
                embed_description = self.embed_description.value
            else:
                if language == "tr":
                    embed_description = "Destek sistemimize hoş geldiniz! Ticket oluşturmak için aşağıdaki butona tıklayın."
                else:
                    embed_description = "Welcome to our support system! Click the button below to create a ticket."
            
            embed = discord.Embed(
                title=embed_title,
                description=embed_description,
                color=discord.Color.blue()
            )
            
            # Add ticket image if enabled
            file = None
            try:
                enable_ticket_images = settings.get("enable_ticket_images", True) if settings else True
                if enable_ticket_images:
                    from utils.community.turkoyto.card_renderer import create_ticket_card
                    ticket_image_path = await create_ticket_card(interaction.guild, self.bot)
                    if ticket_image_path:
                        file = discord.File(ticket_image_path, filename="ticket_image.png")
                        embed.set_image(url="attachment://ticket_image.png")
            except Exception as e:
                logger.error(f"Error creating ticket image: {e}")
            
            # Add custom fields if provided
            if self.custom_fields.value:
                try:
                    import json
                    custom_fields = json.loads(self.custom_fields.value)
                    for field in custom_fields:
                        embed.add_field(
                            name=field.get("name", "Field"),
                            value=field.get("value", "Value"),
                            inline=field.get("inline", True)
                        )
                except json.JSONDecodeError:
                    pass
            
            # Add default fields based on language
            if not self.custom_fields.value:
                if language == "tr":
                    embed.add_field(
                        name="📋 Nasıl Çalışır",
                        value=(
                            "• 'Destek Talebi' butonuna tıklayın\n"
                            "• Formu talep detaylarınızla doldurun\n"
                            "• Sizin için özel bir kanal oluşturulacak\n"
                            "• Ekibimiz en kısa sürede yardımcı olacak"
                        ),
                        inline=True
                    )
                    
                    embed.add_field(
                        name="🛠️ Mevcut Destek",
                        value=(
                            "• Teknik Sorunlar\n"
                            "• Genel Sorular\n"
                            "• Özellik İstekleri\n"
                            "• Hata Raporları"
                        ),
                        inline=True
                    )
                    
                    embed.add_field(
                        name="⏰ Yanıt Süresi",
                        value=(
                            "• Normal: 1-2 saat\n"
                            "• Öncelikli: 30 dakika\n"
                            "• Mesai dışı: 6-12 saat"
                        ),
                        inline=False
                    )
                else:
                    embed.add_field(
                        name="📋 How it works",
                        value=(
                            "• Click the 'Create Ticket' button\n"
                            "• Fill out the form with your request details\n"
                            "• A private channel will be created for you\n"
                            "• Our team will assist you as soon as possible"
                        ),
                        inline=True
                    )
                    
                    embed.add_field(
                        name="🛠️ Available Support",
                        value=(
                            "• Technical Issues\n"
                            "• General Questions\n"
                            "• Feature Requests\n"
                            "• Bug Reports"
                        ),
                        inline=True
                    )
                    
                    embed.add_field(
                        name="⏰ Response Time",
                        value=(
                            "• Normal: 1-2 hours\n"
                            "• Priority: 30 minutes\n"
                            "• Off-hours: 6-12 hours"
                        ),
                        inline=False
                    )
            
            # Create the ticket button view with language support
            from cogs.ticket import TicketButton
            view = TicketButton(language=language)
            
            # Send the message
            if file:
                await channel.send(embed=embed, view=view, file=file)
            else:
                await channel.send(embed=embed, view=view)
            
            await interaction.response.send_message(
                f"✅ Ticket message sent to {channel.mention}!", 
                ephemeral=True
            )
            
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Error: {str(e)}", 
                ephemeral=True
            )

# Modal classes for ticket configuration
class SetTicketCategoryModal(discord.ui.Modal):
    """Modal for setting the ticket category"""
    
    def __init__(self, bot):
        super().__init__(title="Set Ticket Category")
        self.bot = bot
        
        self.category_id = discord.ui.TextInput(
            label="Category ID",
            placeholder="Enter the category ID for tickets",
            required=True,
            max_length=20
        )
        self.add_item(self.category_id)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            category = interaction.guild.get_channel(int(self.category_id.value))
            if not category or not isinstance(category, discord.CategoryChannel):
                await interaction.response.send_message("❌ Invalid category ID!", ephemeral=True)
                return
            
            mongo_db = get_async_db()
            await mongo_db.ticket_settings.update_one(
                {"guild_id": interaction.guild.id},
                {"$set": {"category_id": int(self.category_id.value)}},
                upsert=True
            )
            
            await interaction.response.send_message(f"✅ Ticket category set to {category.name}!", ephemeral=True)
            
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)

class SetTicketLogChannelModal(discord.ui.Modal):
    """Modal for setting the ticket log channel"""
    
    def __init__(self, bot):
        super().__init__(title="Set Ticket Log Channel")
        self.bot = bot
        
        self.channel_id = discord.ui.TextInput(
            label="Log Channel ID",
            placeholder="Enter the channel ID for ticket logs",
            required=True,
            max_length=20
        )
        self.add_item(self.channel_id)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            channel = interaction.guild.get_channel(int(self.channel_id.value))
            if not channel or not isinstance(channel, discord.TextChannel):
                await interaction.response.send_message("❌ Invalid channel ID!", ephemeral=True)
                return
            
            mongo_db = get_async_db()
            await mongo_db.ticket_settings.update_one(
                {"guild_id": interaction.guild.id},
                {"$set": {"log_channel_id": int(self.channel_id.value)}},
                upsert=True
            )
            
            await interaction.response.send_message(f"✅ Ticket log channel set to {channel.mention}!", ephemeral=True)
            
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)

class SetSupportRolesModal(discord.ui.Modal):
    """Modal for setting support roles"""
    
    def __init__(self, bot):
        super().__init__(title="Set Support Roles")
        self.bot = bot
        
        self.role_ids = discord.ui.TextInput(
            label="Support Role IDs",
            placeholder="Enter role IDs separated by commas (e.g., 123456789,987654321)",
            style=discord.TextStyle.long,
            required=True,
            max_length=500
        )
        self.add_item(self.role_ids)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            role_ids = [int(role_id.strip()) for role_id in self.role_ids.value.split(",")]
            
            # Validate roles exist
            valid_roles = []
            for role_id in role_ids:
                role = interaction.guild.get_role(role_id)
                if role:
                    valid_roles.append(role_id)
            
            if not valid_roles:
                await interaction.response.send_message("❌ No valid roles found!", ephemeral=True)
                return
            
            mongo_db = get_async_db()
            await mongo_db.ticket_settings.update_one(
                {"guild_id": interaction.guild.id},
                {"$set": {"support_roles": valid_roles}},
                upsert=True
            )
            
            role_mentions = [interaction.guild.get_role(role_id).mention for role_id in valid_roles]
            await interaction.response.send_message(f"✅ Support roles set to: {', '.join(role_mentions)}!", ephemeral=True)
            
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)

class SetLanguageModal(discord.ui.Modal):
    """Modal for setting the ticket system language"""
    
    def __init__(self, bot):
        super().__init__(title="Set Ticket Language")
        self.bot = bot
        
        self.language = discord.ui.TextInput(
            label="Language (en/tr)",
            placeholder="Enter 'en' for English or 'tr' for Turkish",
            required=True,
            max_length=2
        )
        self.add_item(self.language)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            lang = self.language.value.lower().strip()
            if lang not in ["en", "tr"]:
                await interaction.response.send_message("❌ Invalid language! Use 'en' for English or 'tr' for Turkish.", ephemeral=True)
                return
            
            mongo_db = get_async_db()
            await mongo_db.ticket_settings.update_one(
                {"guild_id": interaction.guild.id},
                {"$set": {"language": lang}},
                upsert=True
            )
            
            lang_name = "English" if lang == "en" else "Turkish"
            await interaction.response.send_message(f"✅ Ticket language set to {lang_name}!", ephemeral=True)
            
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)

class EditEmbedFieldsModal(discord.ui.Modal):
    """Modal for editing ticket embed fields"""
    
    def __init__(self, bot):
        super().__init__(title="Edit Embed Fields")
        self.bot = bot
        
        self.embed_fields = discord.ui.TextInput(
            label="Embed Fields (JSON format)",
            placeholder='[{"name": "Field Name", "value": "Field Value", "inline": true}]',
            style=discord.TextStyle.long,
            required=True,
            max_length=1500
        )
        self.add_item(self.embed_fields)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            import json
            fields = json.loads(self.embed_fields.value)
            
            # Validate fields
            for field in fields:
                if not isinstance(field, dict) or "name" not in field or "value" not in field:
                    await interaction.response.send_message("❌ Invalid field format! Each field must have 'name' and 'value'.", ephemeral=True)
                    return
            
            mongo_db = get_async_db()
            await mongo_db.ticket_settings.update_one(
                {"guild_id": interaction.guild.id},
                {"$set": {"embed_fields": fields}},
                upsert=True
            )
            
            await interaction.response.send_message(f"✅ Embed fields updated! ({len(fields)} fields saved)", ephemeral=True)
            
        except json.JSONDecodeError:
            await interaction.response.send_message("❌ Invalid JSON format! Please check your syntax.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)

class EditTicketFieldsModal(discord.ui.Modal):
    """Modal for editing ticket form fields"""
    
    def __init__(self, bot):
        super().__init__(title="Edit Ticket Fields")
        self.bot = bot
        
        self.fields = discord.ui.TextInput(
            label="Ticket Form Fields",
            placeholder="Enter field names separated by commas",
            style=discord.TextStyle.long,
            required=False,
            max_length=1000
        )
        self.add_item(self.fields)
    
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.send_message("✅ Ticket fields updated!", ephemeral=True)

class AdvancedTicketSettingsModal(discord.ui.Modal):
    """Modal for configuring advanced ticket settings"""
    
    def __init__(self, bot):
        super().__init__(title="Advanced Ticket Settings")
        self.bot = bot
        
        self.auto_close_days = discord.ui.TextInput(
            label="Auto-close after (days)",
            placeholder="Enter the number of days before a ticket auto-closes",
            required=False,
            max_length=3
        )
        
        self.max_tickets_per_user = discord.ui.TextInput(
            label="Max tickets per user",
            placeholder="Enter the maximum number of tickets a user can have",
            required=False,
            max_length=3
        )
        
        self.ticket_naming_format = discord.ui.TextInput(
            label="Ticket naming format",
            placeholder="Enter the format for ticket naming",
            required=False,
            max_length=256
        )
        
        # Add items to the modal
        self.add_item(self.auto_close_days)
        self.add_item(self.max_tickets_per_user)
        self.add_item(self.ticket_naming_format)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            mongo_db = get_async_db()
            update_data = {}
            
            if self.auto_close_days.value:
                try:
                    days = int(self.auto_close_days.value)
                    if days > 0:
                        update_data["auto_close_days"] = days
                except ValueError:
                    await interaction.response.send_message("❌ Invalid auto-close days value!", ephemeral=True)
                    return
            
            if self.max_tickets_per_user.value:
                try:
                    max_tickets = int(self.max_tickets_per_user.value)
                    if max_tickets > 0:
                        update_data["max_tickets_per_user"] = max_tickets
                except ValueError:
                    await interaction.response.send_message("❌ Invalid max tickets value!", ephemeral=True)
                    return
            
            if self.ticket_naming_format.value:
                update_data["ticket_naming_format"] = self.ticket_naming_format.value
            
            if update_data:
                await mongo_db.ticket_settings.update_one(
                    {"guild_id": interaction.guild.id},
                    {"$set": update_data},
                    upsert=True
                )
            
            await interaction.response.send_message("✅ Advanced ticket settings updated!", ephemeral=True)
            
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)

class CreateTicketPanelView(discord.ui.View):
    """View for creating ticket panels in channels"""
    
    def __init__(self, bot, language="en"):
        super().__init__(timeout=300)
        self.bot = bot
        self.language = language

    @discord.ui.select(
        cls=discord.ui.ChannelSelect,
        channel_types=[discord.ChannelType.text, discord.ChannelType.news],
        placeholder="Select a channel to create ticket panel...",
        min_values=1,
        max_values=1
    )
    async def channel_select(self, interaction: discord.Interaction, select: discord.ui.ChannelSelect):
        channel = select.values[0]
        
        try:
            # Get the actual channel object if it's an AppCommandChannel
            if hasattr(channel, 'id'):
                actual_channel = interaction.guild.get_channel(channel.id)
                if not actual_channel:
                    await interaction.response.send_message(
                        "❌ Channel not found!" if self.language == "en" else "❌ Kanal bulunamadı!",
                        ephemeral=True
                    )
                    return
                channel = actual_channel
            
            # Create ticket embed
            embed = discord.Embed(
                title="🎫 Support System" if self.language == "en" else "🎫 Destek Sistemi",
                description=(
                    "Need help? Create a support ticket and our team will assist you!\n\n"
                    "**What you can get help with:**\n"
                    "• Technical issues\n"
                    "• Account problems\n"
                    "• General questions\n"
                    "• Bug reports\n"
                    "• Feature requests\n\n"
                    "Click the button below to create a private support ticket."
                ) if self.language == "en" else (
                    "Yardıma mı ihtiyacın var? Bir destek bileti oluştur ve ekibimiz sana yardımcı olsun!\n\n"
                    "**Hangi konularda yardım alabilirsin:**\n"
                    "• Teknik sorunlar\n"
                    "• Hesap problemleri\n"
                    "• Genel sorular\n"
                    "• Hata raporları\n"
                    "• Özellik istekleri\n\n"
                    "Özel bir destek bileti oluşturmak için aşağıdaki butona tıkla."
                ),
                color=discord.Color.blue()
            )
            
            # Add footer
            embed.set_footer(
                text="Click the button to create a ticket • Support Team" if self.language == "en" else "Bilet oluşturmak için butona tıklayın • Destek Ekibi",
                icon_url=self.bot.user.display_avatar.url
            )
            
            # Import ticket button from ticket cog
            try:
                from cogs.ticket import CreateTicketView
                view = CreateTicketView()
            except ImportError:
                # Fallback: create a simple button
                view = discord.ui.View(timeout=None)
                button = discord.ui.Button(
                    label="🎫 Create Ticket" if self.language == "en" else "🎫 Bilet Oluştur",
                    style=discord.ButtonStyle.primary,
                    custom_id="create_ticket_button"
                )
                view.add_item(button)
            
            # Send the ticket panel
            await channel.send(embed=embed, view=view)
            
            # Confirm success
            await interaction.response.send_message(
                f"✅ Ticket panel created in {channel.mention}!" if self.language == "en" else f"✅ Bilet paneli {channel.mention} kanalında oluşturuldu!",
                ephemeral=True
            )
            
        except Exception as e:
            logger.error(f"Error creating ticket panel: {e}")
            await interaction.response.send_message(
                f"❌ Error creating ticket panel: {str(e)}" if self.language == "en" else f"❌ Bilet paneli oluşturulurken hata: {str(e)}",
                ephemeral=True
            ) 