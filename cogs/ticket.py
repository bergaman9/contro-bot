import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import asyncio
import random
import io
import logging
from datetime import datetime

from utils.core.formatting import create_embed, hex_to_int
from utils.database.connection import initialize_mongodb
from utils.core.class_utils import DynamicView, DynamicButton
from utils.database import get_async_db
from utils.community.turkoyto.card_renderer import create_ticket_card, create_level_card_for_ticket

logger = logging.getLogger(__name__)

TEXT_STYLE_MAPPING = {
    "short": discord.TextStyle.short,
    "paragraph": discord.TextStyle.paragraph
}


class TicketModal(discord.ui.Modal):
    def __init__(self, data_source, guild_id, bot=None, language="en"):
        super().__init__(title="Support Ticket" if language == "en" else "Destek Talebi")
        self.data_source = data_source
        self.guild_id = guild_id
        self.bot = bot
        self.language = language
        self.initialize_fields()

    def initialize_fields(self):
        try:
            data_list = fetch_fields_by_data_source(self.data_source, self.guild_id, self.language)

            if not data_list:
                raise ValueError("No data found")

            for index, data in enumerate(data_list):
                style_str = data.get('style', 'short')
                text_style = discord.TextStyle.long if style_str == 'long' else discord.TextStyle.short

                text_input = discord.ui.TextInput(
                    label=data.get('label', f'Field {index + 1}'),
                    placeholder=data.get('placeholder', ''),
                    style=text_style,
                    required=data.get('required', False),
                    max_length=data.get('max_length', 1000)
                )

                self.add_item(text_input)

        except Exception as e:
            logger.error(f"Error initializing ticket fields: {e}")
            # Add default fields if there's an error
            self.add_item(discord.ui.TextInput(
                label="Subject" if self.language == "en" else "Konu",
                placeholder="What is your ticket about?" if self.language == "en" else "Ticket konunuz nedir?",
                style=discord.TextStyle.short,
                required=True,
                max_length=100
            ))
            self.add_item(discord.ui.TextInput(
                label="Description" if self.language == "en" else "Açıklama",
                placeholder="Please describe your issue in detail" if self.language == "en" else "Sorununuzu detaylı olarak açıklayın",
                style=discord.TextStyle.long,
                required=True,
                max_length=1000
            ))

    async def on_submit(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer(ephemeral=True)
            
            # Get ticket settings
            mongo_db = get_async_db()
            settings = await mongo_db.ticket_settings.find_one({"guild_id": interaction.guild.id})
            
            if not settings:
                await interaction.followup.send("❌ Ticket system not configured!", ephemeral=True)
                return
            
            category_id = settings.get("category_id")
            if not category_id:
                await interaction.followup.send("❌ Ticket category not set!", ephemeral=True)
                return
            
            category = interaction.guild.get_channel(category_id)
            if not category:
                await interaction.followup.send("❌ Ticket category not found!", ephemeral=True)
                return
            
            # Check max tickets per user
            max_tickets = settings.get("max_tickets_per_user", 5)
            user_tickets = [ch for ch in category.channels if str(interaction.user.id) in ch.name]
            
            if len(user_tickets) >= max_tickets:
                await interaction.followup.send(
                    f"❌ You already have {len(user_tickets)} open tickets! Maximum allowed: {max_tickets}",
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
            embed.description = "We will contact you as soon as possible." if self.language == "en" else "En kısa sürede sizinle iletişime geçeceğiz."

            # Add user info with single backticks (moved to top)
            embed.add_field(
                name="👤 User" if self.language == "en" else "👤 Kullanıcı",
                value=f"`{interaction.user.name}#{interaction.user.discriminator}`",
                inline=True
            )

            embed.add_field(
                name="🆔 User ID" if self.language == "en" else "🆔 Kullanıcı ID",
                value=f"`{interaction.user.id}`",
                inline=True
            )

            embed.add_field(
                name="🎫 Ticket Count" if self.language == "en" else "🎫 Ticket Sayısı",
                value=f"`{ticket_number}`",
                inline=True
            )
            
            # Add form fields to embed with code blocks
            for i, item in enumerate(self.children):
                if isinstance(item, discord.ui.TextInput) and item.value:
                    embed.add_field(
                        name=f"📝 {item.label}",
                        value=f"```\n{item.value}\n```",
                        inline=False
                    )
            
            # Generate images if enabled
            ticket_image_path = None
            level_card_path = None
            
            enable_level_cards = settings.get("enable_level_cards", True)
            
            if enable_level_cards:
                try:
                    level_card_path = await create_level_card_for_ticket(interaction.user, interaction.guild, self.bot)
                    if level_card_path and os.path.exists(level_card_path):
                        level_file = discord.File(level_card_path, filename="level_card.png")
                        embed.set_image(url="attachment://level_card.png")
                except Exception as e:
                    logger.error(f"Error creating level card: {e}")
            
            
            # Create ticket control view
            view = TicketControlView(self.language)
            
            # Send ticket message
            files = []
            if ticket_image_path and os.path.exists(ticket_image_path):
                files.append(discord.File(ticket_image_path, filename="ticket_image.png"))
            if level_card_path and os.path.exists(level_card_path):
                files.append(discord.File(level_card_path, filename="level_card.png"))
            
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
                        title="🎫 New Ticket Created" if self.language == "en" else "🎫 Yeni Ticket Oluşturuldu",
                        color=discord.Color.green(),
                        timestamp=discord.utils.utcnow()
                    )
                    log_embed.add_field(name="User", value=interaction.user.mention, inline=True)
                    log_embed.add_field(name="Channel", value=ticket_channel.mention, inline=True)
                    log_embed.add_field(name="Ticket #", value=str(ticket_number), inline=True)
                    await log_channel.send(embed=log_embed)
            
            await interaction.followup.send(
                f"✅ Ticket created! {ticket_channel.mention}" if self.language == "en" else f"✅ Ticket oluşturuldu! {ticket_channel.mention}",
                ephemeral=True
            )
            
        except Exception as e:
            logger.error(f"Error creating ticket: {e}")
            await interaction.followup.send(f"❌ Error creating ticket: {str(e)}", ephemeral=True)

class TicketButton(discord.ui.View):
    def __init__(self, language="en"):
        super().__init__(timeout=None)
        self.language = language
        
        # Update button label based on language
        button_label = "Create Ticket" if language == "en" else "Destek Talebi"
        self.create_ticket.label = button_label

    @discord.ui.button(label="Create Ticket", style=discord.ButtonStyle.primary, emoji="🎫", custom_id="create_ticket")
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            modal = TicketModal("default", interaction.guild.id, interaction.client, self.language)
            await interaction.response.send_modal(modal)
        except Exception as e:
            logger.error(f"Error opening ticket modal: {e}")
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)

class TicketControlView(discord.ui.View):
    def __init__(self, language="en"):
        super().__init__(timeout=None)
        self.language = language
        
        # Update button labels based on language
        if language == "tr":
            self.close_ticket.label = "Ticket'ı Kapat"
            self.claim_ticket.label = "Ticket'ı Sahiplen"
        else:
            self.close_ticket.label = "Close Ticket"
            self.claim_ticket.label = "Claim Ticket"

    @discord.ui.button(label="Close Ticket", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="close_ticket")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            # Check permissions
            mongo_db = get_async_db()
            settings = await mongo_db.ticket_settings.find_one({"guild_id": interaction.guild.id})
            
            support_roles = settings.get("support_roles", []) if settings else []
            user_roles = [role.id for role in interaction.user.roles]
            
            # Check if user is ticket owner or has support role
            ticket = await mongo_db.tickets.find_one({"channel_id": interaction.channel.id})
            is_owner = ticket and ticket.get("user_id") == interaction.user.id
            is_support = any(role_id in user_roles for role_id in support_roles)
            is_admin = interaction.user.guild_permissions.administrator
            
            if not (is_owner or is_support or is_admin):
                await interaction.response.send_message(
                    "❌ You don't have permission to close this ticket!" if self.language == "en" else "❌ Bu ticket'ı kapatma yetkiniz yok!",
                    ephemeral=True
                )
                return
            
            # Close ticket
            await interaction.response.send_message(
                "🔒 Closing ticket in 5 seconds..." if self.language == "en" else "🔒 Ticket 5 saniye içinde kapatılacak...",
                ephemeral=False
            )
            
            await asyncio.sleep(5)
            
            # Update database
            if ticket:
                await mongo_db.tickets.update_one(
                    {"channel_id": interaction.channel.id},
                    {"$set": {"status": "closed", "closed_at": discord.utils.utcnow(), "closed_by": interaction.user.id}}
                )
            
            # Delete channel
            await interaction.channel.delete()
            
        except Exception as e:
            logger.error(f"Error closing ticket: {e}")
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)

    @discord.ui.button(label="Claim Ticket", style=discord.ButtonStyle.secondary, emoji="👋", custom_id="claim_ticket")
    async def claim_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            # Check if user has support role
            mongo_db = get_async_db()
            settings = await mongo_db.ticket_settings.find_one({"guild_id": interaction.guild.id})
            
            support_roles = settings.get("support_roles", []) if settings else []
            user_roles = [role.id for role in interaction.user.roles]
            
            is_support = any(role_id in user_roles for role_id in support_roles)
            is_admin = interaction.user.guild_permissions.administrator
            
            if not (is_support or is_admin):
                await interaction.response.send_message(
                    "❌ You don't have permission to claim tickets!" if self.language == "en" else "❌ Ticket sahiplenme yetkiniz yok!",
                    ephemeral=True
                )
                return
            
            # Update database
            await mongo_db.tickets.update_one(
                {"channel_id": interaction.channel.id},
                {"$set": {"claimed_by": interaction.user.id, "claimed_at": discord.utils.utcnow()}}
            )
            
            await interaction.response.send_message(
                f"✅ {interaction.user.mention} has claimed this ticket!" if self.language == "en" else f"✅ {interaction.user.mention} bu ticket'ı sahiplendi!",
                ephemeral=False
            )
            
        except Exception as e:
            logger.error(f"Error claiming ticket: {e}")
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)

class Ticket(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    @commands.Cog.listener()
    async def on_ready(self):
        # Add persistent views
        self.bot.add_view(TicketButton())
        self.bot.add_view(TicketControlView())
        logger.info("Ticket cog loaded and persistent views added")
    
    async def create_ticket_interaction(self, interaction: discord.Interaction):
        """Handle ticket creation from external views"""
        try:
            # Determine language based on guild locale or default to Turkish
            language = "tr"
            if hasattr(interaction.guild, 'preferred_locale'):
                if interaction.guild.preferred_locale and 'en' in str(interaction.guild.preferred_locale):
                    language = "en"
            
            # Create and send the ticket modal
            modal = TicketModal("default", interaction.guild.id, self.bot, language)
            await interaction.response.send_modal(modal)
            
        except Exception as e:
            logger.error(f"Error in create_ticket_interaction: {e}")
            error_msg = f"❌ Ticket oluşturulurken hata: {str(e)}" if language == "tr" else f"❌ Error creating ticket: {str(e)}"
            await interaction.response.send_message(error_msg, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Ticket(bot))

def fetch_fields_by_data_source(data_source, guild_id, language="en"):
    """Fetch ticket fields from database"""
    # This is a placeholder - implement based on your database structure
    if language == "tr":
        return [
            {
                'label': 'Konu',
                'placeholder': 'Ticket konunuz nedir?',
                'style': 'short',
                'required': True,
                'max_length': 100
            },
            {
                'label': 'Açıklama',
                'placeholder': 'Sorununuzu detaylı olarak açıklayın',
                'style': 'long',
                'required': True,
                'max_length': 1000
            }
        ]
    else:
        return [
            {
                'label': 'Subject',
                'placeholder': 'What is your ticket about?',
                'style': 'short',
                'required': True,
                'max_length': 100
            },
            {
                'label': 'Description',
                'placeholder': 'Please describe your issue in detail',
                'style': 'long',
                'required': True,
                'max_length': 1000
            }
        ]
