import discord
from discord.ext import commands
import asyncio
import logging
import re
import datetime
import os
import json
import io
from discord.ui import Button, View, Select

from src.utils.core.formatting import create_embed
from src.utils.database.connection import initialize_mongodb
from .card_renderer import get_level_scheme

logger = logging.getLogger('community.ticket_views')

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
                label="Discord Bot Development",
                description="Custom bot development and integration services",
                emoji="🤖",
                value="discord_bot"
            ),
            discord.SelectOption(
                label="Website Development",
                description="Personal and corporate websites, e-commerce, etc.",
                emoji="🌐",
                value="web_dev"
            ),
            discord.SelectOption(
                label="Discord Server Setup",
                description="Channel, role and bot setup for your server",
                emoji="🛠️",
                value="server_setup"
            ),
            discord.SelectOption(
                label="Server Requests & Suggestions",
                description="All kinds of requests and suggestions for the server",
                emoji="💬",
                value="server_feedback"
            ),
            discord.SelectOption(
                label="Advertising & Partnership",
                description="Get information about advertising and partnership offers",
                emoji="🤝",
                value="advertising"
            )
        ]
        
        super().__init__(
            placeholder="Select a service...",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="services_dropdown"  # Custom ID is important for persistence
        )
    
    async def callback(self, interaction: discord.Interaction):
        service_info = {
            "discord_bot": {
                "title": "🤖 Discord Bot Development",
                "description": (
                    "**We develop custom Discord bots!**\n\n"
                    "- Moderation and management bots\n"
                    "- Fun and gaming bots\n"
                    "- Economy and leveling systems\n"
                    "- Custom API integrations\n"
                    "- Adding features to existing bots\n\n"
                    "Prices vary according to demand. Contact our team for detailed offers."
                )
            },
            "web_dev": {
                "title": "🌐 Website Development",
                "description": (
                    "**Professional website design and development services!**\n\n"
                    "- Personal and corporate websites\n"
                    "- E-commerce platforms\n"
                    "- Blog and portal sites\n"
                    "- Forum and community sites\n"
                    "- Responsive and modern designs\n\n"
                    "Contact our team for a custom offer tailored to you."
                )
            },
            "server_setup": {
                "title": "🛠️ Discord Server Setup",
                "description": (
                    "**Professional setup of your Discord server!**\n\n"
                    "- Channel and category layout\n"
                    "- Role and permission configuration\n"
                    "- Automation and security bot installation\n"
                    "- Welcome, registration, moderation systems\n"
                    "- Server-specific settings and themes\n\n"
                    "Turnkey installation service according to your server's needs."
                )
            },
            "server_feedback": {
                "title": "💬 Server Requests & Suggestions",
                "description": (
                    "**Your feedback is valuable to our server!**\n\n"
                    "- New feature suggestions\n"
                    "- Improvement recommendations\n"
                    "- Event ideas\n"
                    "- Bug reports\n\n"
                    "All your feedback is carefully evaluated by our team."
                )
            },
            "advertising": {
                "title": "🤝 Advertising & Partnership Opportunities",
                "description": (
                    "**We offer various opportunities for advertising and partnerships!**\n\n"
                    "- Server promotion partnerships\n"
                    "- Bot promotion campaigns\n"
                    "- Content creator collaborations\n"
                    "- Brand promotion events\n"
                    "- Custom marketing solutions\n\n"
                    "Get information about special campaigns for brands, content creators and communities."
                )
            }
        }
        
        selected = self.values[0]
        info = service_info.get(selected, {"title": "Service Information", "description": "No information found for this service."})
        
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
            description="Select an option to get detailed information about our services.",
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
            label="Support Request", 
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
            title = "Support Request Form"
            modal = TicketModal(title, self.category_id)
            await interaction.response.send_modal(modal)
        except Exception as e:
            logger.error(f"Error handling ticket button: {e}", exc_info=True)
            await interaction.response.send_message(
                embed=create_embed(
                    description="❌ An error occurred while opening the support request form.",
                    color=discord.Color.red()
                ),
                ephemeral=True
            )

class TicketModal(discord.ui.Modal, title="Support Request Form"):
    def __init__(self, title, category_id=None):
        super().__init__(title=title)
        self.category_id = category_id
        
        # Define form fields for the ticket
        self.subject = discord.ui.TextInput(
            label="Subject",
            placeholder="What is the subject of your support request?",
            required=True,
            max_length=100,
            style=discord.TextStyle.short
        )
        self.add_item(self.subject)
        
        self.description = discord.ui.TextInput(
            label="Description",
            placeholder="Detailed description...",
            required=True,
            max_length=1000,
            style=discord.TextStyle.paragraph
        )
        self.add_item(self.description)
        
        self.contact = discord.ui.TextInput(
            label="Contact Information",
            placeholder="Your Discord ID or other contact information (optional)",
            required=False,
            max_length=100,
            style=discord.TextStyle.short
        )
        self.add_item(self.contact)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Get the form values
            subject = self.subject.value
            description = self.description.value
            contact_info = self.contact.value if self.contact.value else "Not specified"
            
            # Create a ticket
            cog = interaction.client.get_cog("Community")
            if not cog:
                raise ValueError("Community cog not found. Please contact an administrator.")
                
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
                            description=f"✅ Your support request has been created: {ticket_channel.mention}",
                            color=discord.Color.green()
                        ),
                        ephemeral=True
                    )
                else:
                    await interaction.followup.send(
                        embed=create_embed(
                            description="❌ An error occurred while creating the support request. Please try again later.",
                            color=discord.Color.red()
                        ),
                        ephemeral=True
                    )
                    
            except asyncio.TimeoutError:
                logger.error("Ticket creation timed out after 30 seconds")
                await interaction.followup.send(
                    embed=create_embed(
                        description="⏱️ Support request creation has timed out. Please try again later.",
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
            
            error_message = "❌ An error occurred while creating the support request, please try again later."
            
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
            label="Close Ticket", 
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
            cog = interaction.client.get_cog("Community")
            if cog and hasattr(cog, 'mongo_db'):
                try:
                    await cog.mongo_db["tickets"].update_one(
                        {"user_id": self.user_id, "active_tickets.channel_id": self.channel_id},
                        {"$set": {"active_tickets.$.status": "closed", "active_tickets.$.closed_at": datetime.datetime.now()}}
                    )
                except (TypeError, AttributeError):
                    cog.mongo_db["tickets"].update_one(
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
                        description=f"🔒 This support ticket was closed by {interaction.user.mention}. Only staff can send messages.",
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
                        description=f"✅ Support ticket has been successfully closed.",
                        color=discord.Color.green()
                    ),
                    ephemeral=True
                )
                
            except Exception as e:
                logger.error(f"Error updating channel permissions: {e}")
                await interaction.followup.send(
                    embed=create_embed(
                        description="❌ An error occurred while closing the ticket.",
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
                    description="❌ You must be the ticket creator or staff to perform this action.",
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
            label="Delete",
            style=discord.ButtonStyle.danger,
            emoji="🗑️",
            custom_id=f"delete_ticket_{channel_id}",
            row=0
        )
        delete_button.callback = self.delete_ticket_callback

        reopen_button = discord.ui.Button(
            label="Reopen",
            style=discord.ButtonStyle.success,
            emoji="🔓",
            custom_id=f"reopen_ticket_{channel_id}",
            row=0
        )
        reopen_button.callback = self.reopen_ticket_callback

        transcript_button = discord.ui.Button(
            label="Transcript",
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
                    description="❌ You don't have permission to delete ticket channels.",
                    color=discord.Color.red()
                ),
                ephemeral=True
            )
            return

        await interaction.followup.send(
            embed=create_embed(
                description="⚠️ You are about to delete this ticket. This action cannot be undone.",
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
                    description="❌ An error occurred while deleting the ticket.",
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
                cog = interaction.client.get_cog("Community")
                if cog and hasattr(cog, 'mongo_db'):
                    try:
                        await cog.mongo_db["tickets"].update_one(
                            {"user_id": self.user_id, "active_tickets.channel_id": self.channel_id},
                            {"$set": {"active_tickets.$.status": "open", "active_tickets.$.reopened_at": datetime.datetime.now()}}
                        )
                    except (TypeError, AttributeError):
                        cog.mongo_db["tickets"].update_one(
                            {"user_id": self.user_id, "active_tickets.channel_id": self.channel_id},
                            {"$set": {"active_tickets.$.status": "open", "active_tickets.$.reopened_at": datetime.datetime.now()}}
                        )
                management_view = TicketManagementView(self.channel_id, self.user_id, self.ticket_number)
                await channel.send(
                    embed=create_embed(
                        description=f"🔓 This support ticket was reopened by {interaction.user.mention}.",
                        color=discord.Color.green()
                    ),
                    view=management_view
                )
                interaction.client.add_view(management_view)
                
                # Confirm to the user that the ticket was reopened
                await interaction.followup.send(
                    embed=create_embed(
                        description=f"✅ Support ticket has been successfully reopened.",
                        color=discord.Color.green()
                    ),
                    ephemeral=True
                )
            except Exception as e:
                logger.error(f"Error reopening ticket: {e}")
                await interaction.followup.send(
                    embed=create_embed(
                        description="❌ An error occurred while reopening the ticket.",
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
                    description="❌ You must be staff to perform this action.",
                    color=discord.Color.red()
                ),
                ephemeral=True
            )
            return False
        is_creator = member.id == self.user_id
        if not (is_creator or is_staff):
            await interaction.followup.send(
                embed=create_embed(
                    description="❌ You must be the ticket creator or staff to perform this action.",
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
                        f"**Channel:** {channel.name}\n"
                        f"**User:** {member_mention}\n"
                        f"**Ticket Number:** {self.ticket_number}\n"
                        f"**Date:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                    ),
                    color=discord.Color.blue()
                )
                await logs_channel.send(embed=embed, file=transcript_file)
                if not delete_after:
                    await interaction.followup.send(
                        embed=create_embed(
                            description=f"✅ Ticket transcript has been created and sent to {logs_channel.mention}.",
                            color=discord.Color.green()
                        ),
                        ephemeral=True
                    )
            elif not delete_after:
                await interaction.followup.send(
                    embed=create_embed(
                        description="📝 Ticket transcript has been created:",
                        color=discord.Color.blue()
                    ),
                    file=transcript_file,
                    ephemeral=True
                )
            try:
                cog = interaction.client.get_cog("Community")
                if cog and hasattr(cog, 'mongo_db'):
                    try:
                        await cog.mongo_db["tickets"].update_one(
                            {"user_id": self.user_id, "active_tickets.channel_id": self.channel_id},
                            {"$set": {"active_tickets.$.status": "archived", "active_tickets.$.archived_at": datetime.datetime.now()}}
                        )
                    except (TypeError, AttributeError):
                        cog.mongo_db["tickets"].update_one(
                            {"user_id": self.user_id, "active_tickets.channel_id": self.channel_id},
                            {"$set": {"active_tickets.$.status": "archived", "active_tickets.$.archived_at": datetime.datetime.now()}}
                        )
            except Exception as db_error:
                logger.error(f"Database error during ticket operation: {db_error}")
            if delete_after:
                await channel.delete(reason=f"Support ticket deleted by {interaction.user.name}")
        except Exception as e:
            logger.error(f"Error creating transcript: {e}", exc_info=True)
            if not delete_after:
                await interaction.followup.send(
                    embed=create_embed(
                        description="❌ An error occurred while creating the transcript.",
                        color=discord.Color.red()
                    ),
                    ephemeral=True
                )

# For backwards compatibility
class TicketCloseView(TicketClosedView):
    def __init__(self, channel_id, user_id, ticket_number):
        super().__init__(channel_id, user_id, ticket_number)

    async def get_user_data(self):
        """Get user data for the ticket"""
        return {}


class TicketCreateView(discord.ui.View):
    """View for creating tickets with a button"""
    
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot
        
    @discord.ui.button(label="Create Ticket", emoji="🎫", style=discord.ButtonStyle.primary, custom_id="create_ticket_new")
    async def create_ticket_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle ticket creation button click"""
        await interaction.response.send_modal(TicketCreationModal(self.bot, interaction.guild.id))


class TicketCreationModal(discord.ui.Modal, title="Create Support Ticket"):
    """Modal for ticket creation with form fields"""
    
    def __init__(self, bot, guild_id=None):
        super().__init__()
        self.bot = bot
        self.mongo_db = initialize_mongodb()
        self.guild_id = guild_id
        
        # Add default fields first
        self.add_default_fields()
    
    def add_default_fields(self):
        """Add default or custom fields to the modal"""
        # If we have guild_id, try to get custom questions
        questions = self.get_default_questions()
        
        if self.guild_id:
            try:
                settings = self.mongo_db["tickets"].find_one({"guild_id": str(self.guild_id)}) or {}
                custom_questions = settings.get("form_questions")
                if custom_questions:
                    questions = custom_questions
            except Exception as e:
                logger.error(f"Error loading custom questions: {e}")
        
        # Add fields based on questions (limit to 5 due to Discord limits)
        for i, question in enumerate(questions[:5]):
            style = discord.TextStyle.short if question.get("type") == "short" else discord.TextStyle.paragraph
            field = discord.ui.TextInput(
                label=question["question"],
                placeholder=question.get("placeholder", "Type your answer here..."),
                required=question.get("required", True),
                style=style,
                max_length=1000 if style == discord.TextStyle.paragraph else 200
            )
            self.add_item(field)
    
    def get_default_questions(self):
        """Get default questions if none configured"""
        return [
            {
                "question": "What is the reason for your ticket?",
                "type": "short",
                "required": True,
                "placeholder": "Briefly describe your issue"
            },
            {
                "question": "Please provide detailed information:",
                "type": "paragraph", 
                "required": True,
                "placeholder": "Explain your issue in detail..."
            }
        ]
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle form submission"""
        try:
            # Defer to prevent timeout
            await interaction.response.defer(ephemeral=True)
            
            # Get ticket settings
            ticket_config = self.mongo_db["tickets"].find_one({"guild_id": str(interaction.guild.id)})
            if not ticket_config:
                await interaction.followup.send(
                    embed=create_embed("❌ Ticket system is not configured!", discord.Color.red()),
                    ephemeral=True
                )
                return
            
            # Check for existing ticket
            existing_ticket = discord.utils.get(
                interaction.guild.channels,
                name=f"ticket-{interaction.user.name.lower().replace(' ', '-')}",
                type=discord.ChannelType.text
            )
            
            if existing_ticket:
                await interaction.followup.send(
                    embed=create_embed(f"❌ You already have an open ticket: {existing_ticket.mention}", discord.Color.yellow()),
                    ephemeral=True
                )
                return
            
            # Get category
            category_id = ticket_config.get("category_id")
            if not category_id:
                await interaction.followup.send(
                    embed=create_embed("❌ Ticket category not configured.", discord.Color.red()),
                    ephemeral=True
                )
                return
            
            category = interaction.guild.get_channel(int(category_id))
            if not category:
                await interaction.followup.send(
                    embed=create_embed("❌ Ticket category not found.", discord.Color.red()),
                    ephemeral=True
                )
                return
            
            # Create channel with permissions
            support_role_ids = ticket_config.get("support_roles", [])
            overwrites = {
                interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                interaction.user: discord.PermissionOverwrite(
                    read_messages=True,
                    send_messages=True,
                    attach_files=True,
                    embed_links=True
                ),
                interaction.guild.me: discord.PermissionOverwrite(
                    read_messages=True,
                    send_messages=True,
                    attach_files=True,
                    embed_links=True,
                    manage_messages=True,
                    manage_channels=True
                )
            }
            
            # Add support roles
            for role_id in support_role_ids:
                role = interaction.guild.get_role(int(role_id))
                if role:
                    overwrites[role] = discord.PermissionOverwrite(
                        read_messages=True,
                        send_messages=True,
                        attach_files=True,
                        embed_links=True,
                        manage_messages=True
                    )
            
            # Create ticket channel
            channel_name = f"ticket-{interaction.user.name.lower().replace(' ', '-')}"
            ticket_channel = await interaction.guild.create_text_channel(
                name=channel_name,
                category=category,
                overwrites=overwrites,
                topic=f"Support ticket for {interaction.user.name} ({interaction.user.id})"
            )
            
            # Create initial embed with form responses
            embed = discord.Embed(
                title=f"🎫 New Support Ticket",
                description=f"Ticket created by {interaction.user.mention}",
                color=discord.Color.blue(),
                timestamp=datetime.datetime.now()
            )
            
            # Add form responses to embed
            for i, child in enumerate(self.children):
                if isinstance(child, discord.ui.TextInput):
                    embed.add_field(
                        name=child.label,
                        value=child.value[:1024],  # Limit to embed field limit
                        inline=False
                    )
            
            embed.set_footer(text=f"User ID: {interaction.user.id}")
            
            # Send initial message
            await ticket_channel.send(embed=embed)
            
            # Generate and send level card
            try:
                from src.utils.community.generic.card_renderer import render_level_card
                from src.utils.community.generic.xp_manager import XPManager
                
                xp_manager = XPManager()
                user_data = await xp_manager.get_user_data(interaction.guild.id, interaction.user.id)
                
                if user_data:
                    # Generate level card
                    card_buffer = await render_level_card(
                        user=interaction.user,
                        guild=interaction.guild,
                        xp_data=user_data,
                        rank=user_data.get('rank', 0),
                        background_type='dark'
                    )
                    
                    if card_buffer:
                        card_embed = discord.Embed(
                            title="📊 User Level Information",
                            description=f"Level card for {interaction.user.mention}",
                            color=discord.Color.blue()
                        )
                        card_file = discord.File(card_buffer, filename=f"level_card_{interaction.user.id}.png")
                        card_embed.set_image(url=f"attachment://level_card_{interaction.user.id}.png")
                        
                        await ticket_channel.send(embed=card_embed, file=card_file)
            except Exception as e:
                logger.error(f"Error generating level card for ticket: {e}")
                # Continue even if level card fails
            
            # Add management buttons
            management_view = TicketManagementView(
                channel_id=ticket_channel.id,
                user_id=interaction.user.id,
                ticket_number=ticket_channel.name
            )
            
            await ticket_channel.send(
                embed=discord.Embed(
                    description="🎫 **Ticket Controls**\nUse the button below to close this ticket when your issue is resolved.",
                    color=discord.Color.blue()
                ),
                view=management_view
            )
            
            # Ping support roles
            if support_role_ids:
                mentions = []
                for role_id in support_role_ids:
                    role = interaction.guild.get_role(int(role_id))
                    if role:
                        mentions.append(role.mention)
                
                if mentions:
                    await ticket_channel.send(f"Support team: {', '.join(mentions)}")
            
            # Confirm to user
            await interaction.followup.send(
                embed=create_embed(f"✅ Your ticket has been created: {ticket_channel.mention}", discord.Color.green()),
                ephemeral=True
            )
            
            # Save ticket to database
            ticket_data = {
                "channel_id": ticket_channel.id,
                "user_id": interaction.user.id,
                "guild_id": interaction.guild.id,
                "created_at": datetime.datetime.now(),
                "status": "open",
                "answers": {child.label: child.value for i, child in enumerate(self.children) if isinstance(child, discord.ui.TextInput)}
            }
            
            self.mongo_db["active_tickets"].insert_one(ticket_data)
            
        except discord.Forbidden:
            await interaction.followup.send(
                embed=create_embed("❌ I don't have permission to create ticket channels.", discord.Color.red()),
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Error creating ticket: {e}", exc_info=True)
            await interaction.followup.send(
                embed=create_embed(f"❌ An error occurred: {str(e)}", discord.Color.red()),
                ephemeral=True
            )