"""
Ticket system cog with advanced features
"""
import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import asyncio
import random
import io
from datetime import datetime

from src.utils.core.formatting import create_embed, hex_to_int
from src.utils.database.connection import initialize_mongodb
from src.utils.core.class_utils import DynamicView, DynamicButton
from src.utils.database import get_async_db
from src.utils.views.ticket_views import (
    TicketDepartmentsView, DepartmentSelectView, TicketDepartment,
    TicketStatsView, TicketStatistics, TicketAutoClose,
    update_ticket_activity, increment_ticket_messages
)
from src.utils.common import error_embed, success_embed, info_embed

TEXT_STYLE_MAPPING = {
    "short": discord.TextStyle.short,
    "paragraph": discord.TextStyle.paragraph
}


class TicketModal(discord.ui.Modal):
    def __init__(self, data_source: str, title: str, guild_id: str):
        super().__init__(title=title, custom_id="ticket_modal")
        self.data_source = data_source
        self.guild_id = guild_id
        self.initialize_fields()

    def initialize_fields(self):
        try:
            data_list = fetch_fields_by_data_source(self.data_source, self.guild_id)

            if not data_list:
                raise ValueError("No data found")

            for index, data in enumerate(data_list):
                style_str = data.get('style', 'short')  # Varsayılan olarak 'short' kullanıldı.
                text_style = TEXT_STYLE_MAPPING.get(style_str,
                                                    discord.TextStyle.short)  # Eğer stil bulunamazsa varsayılan olarak 'short' kullanılır.

                field = discord.ui.TextInput(
                    label=data['label'],
                    placeholder=data['placeholder'],
                    custom_id=f"field_{index:02}",
                    max_length=data.get('max_length', None),
                    style=text_style,
                    required=data.get('required', True),
                    row=data.get('row', None)
                )

                setattr(self, f"field_{index:02}", field)
                dynamic_field = getattr(self, f"field_{index:02}")
                self.add_item(dynamic_field)

        except:
            self.field_01 = discord.ui.TextInput(label='Destek almak istediğiniz konu nedir?',
                                                 placeholder="Yanıtınızı giriniz.", custom_id="field_01")
            self.add_item(self.field_01)


class TicketCloseButton(discord.ui.Button):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.danger, label="Close", emoji="🔒", custom_id="ticket_close_button")

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message("This ticket will be closed in 5 seconds...", ephemeral=True)
        await asyncio.sleep(5)
        await interaction.channel.delete()


class TicketCloseButtonView(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.add_item(TicketCloseButton())


class TicketButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(discord.ui.Button(label="Create Ticket", style=discord.ButtonStyle.primary, custom_id="create_ticket"))


class TicketClose(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(discord.ui.Button(label="Close Ticket", style=discord.ButtonStyle.danger, custom_id="close_ticket"))


class Ticket(commands.Cog):
    """
    Create and manage support tickets with advanced features
    """
    
    def __init__(self, bot):
        self.bot = bot
        self.mongodb = initialize_mongodb()
        
    @app_commands.command(
        name="ticket_panel",
        description="Create an advanced ticket panel with departments"
    )
    @app_commands.describe(
        channel="Channel to send the ticket panel to (defaults to current channel)"
    )
    @commands.has_permissions(manage_guild=True)
    async def ticket_panel(self, interaction: discord.Interaction, channel: discord.TextChannel = None):
        """Create an advanced ticket panel."""
        target_channel = channel or interaction.channel
        
        # Get departments for this guild
        departments = await TicketDepartment.get_all(interaction.guild.id)
        
        if not departments:
            await interaction.response.send_message(
                embed=error_embed(
                    "No ticket departments found. Please create departments first using `/ticket departments`.",
                    title="❌ No Departments"
                ),
                ephemeral=True
            )
            return
        
        # Create the panel
        view = DepartmentSelectView(departments)
        embed = create_embed(
            title="🎫 Support Tickets",
            description=(
                "Welcome to our support system!\n\n"
                "**How to create a ticket:**\n"
                "1️⃣ Select a department below\n"
                "2️⃣ Fill out the ticket form\n"
                "3️⃣ Wait for staff assistance\n\n"
                "Our support team will respond as soon as possible."
            ),
            color=discord.Color.blue()
        )
        embed.set_footer(text="Click the dropdown below to get started")
        
        await target_channel.send(embed=embed, view=view)
        
        await interaction.response.send_message(
            embed=success_embed(
                f"✅ Advanced ticket panel created in {target_channel.mention}",
                title="Panel Created"
            ),
            ephemeral=True
        )
    
    @app_commands.command(
        name="ticket_departments",
        description="Manage ticket departments"
    )
    @commands.has_permissions(manage_guild=True)
    async def ticket_departments(self, interaction: discord.Interaction):
        """Manage ticket departments."""
        view = TicketDepartmentsView(interaction.guild.id)
        embed = create_embed(
            title="✈️ Ticket Departments Management",
            description="Create and manage ticket departments for your server.",
            color=discord.Color.blue()
        )
        
        # Show existing departments
        departments = await TicketDepartment.get_all(interaction.guild.id)
        if departments:
            dept_list = []
            for dept in departments[:10]:  # Limit to first 10
                staff_roles = [f"<@&{role_id}>" for role_id in dept.staff_roles[:3]]  # First 3 roles
                dept_list.append(
                    f"**{dept.emoji} {dept.name}**\n"
                    f"Staff: {', '.join(staff_roles) if staff_roles else 'None'}\n"
                    f"Max tickets per user: {dept.max_tickets_per_user}"
                )
            
            embed.add_field(
                name="📋 Existing Departments",
                value="\n\n".join(dept_list),
                inline=False
            )
        else:
            embed.add_field(
                name="📋 Existing Departments",
                value="No departments created yet.",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @app_commands.command(
        name="ticket_stats",
        description="View ticket statistics and analytics"
    )
    @commands.has_permissions(manage_guild=True)
    async def ticket_stats(self, interaction: discord.Interaction):
        """View comprehensive ticket statistics."""
        view = TicketStatsView(interaction.guild.id)
        embed = create_embed(
            title="📊 Ticket Statistics Dashboard",
            description="Access comprehensive ticket analytics for your server.",
            color=discord.Color.blue()
        )
        embed.add_field(
            name="📈 Available Statistics",
            value=(
                "• **Guild Stats** - Overall server ticket metrics\n"
                "• **My Stats** - Your personal ticket history\n"
                "• **Auto-Close Check** - Manual inactive ticket cleanup"
            ),
            inline=False
        )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @app_commands.command(
        name="ticket_autoclose",
        description="Configure automatic closing of inactive tickets"
    )
    @app_commands.describe(
        hours="Hours of inactivity before auto-closing (0 to disable)"
    )
    @commands.has_permissions(manage_guild=True)
    async def ticket_autoclose(self, interaction: discord.Interaction, hours: int):
        """Configure auto-close for all departments."""
        if hours < 0:
            await interaction.response.send_message(
                embed=error_embed("Hours must be 0 or positive.", title="❌ Invalid Input"),
                ephemeral=True
            )
            return
        
        # Update all departments in this guild
        mongo_db = get_async_db()
        result = await mongo_db.ticket_departments.update_many(
            {"guild_id": interaction.guild.id},
            {"$set": {"auto_close_hours": hours}}
        )
        
        if result.modified_count > 0:
            status = f"enabled (after {hours} hours)" if hours > 0 else "disabled"
            await interaction.response.send_message(
                embed=success_embed(
                    f"Auto-close has been {status} for {result.modified_count} departments.",
                    title="✅ Auto-Close Updated"
                ),
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                embed=info_embed(
                    "No departments found to update. Create departments first.",
                    title="ℹ️ No Changes"
                ),
                ephemeral=True
            )
    
    @commands.Cog.listener()
    async def on_message(self, message):
        """Track ticket activity."""
        if message.author.bot or not message.guild:
            return
        
        # Check if this is a ticket channel
        if message.channel.name.startswith(("ticket-", "🔵ticket-", "🟢ticket-", "🟠ticket-", "🔴ticket-")):
            await update_ticket_activity(message.channel.id)
            await increment_ticket_messages(message.channel.id)
    
    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if interaction.type == discord.InteractionType.component:
            custom_id = interaction.data.get("custom_id", "")
            
            if custom_id == "create_ticket":
                await self.create_ticket(interaction)
            elif custom_id == "close_ticket":
                await self.close_ticket(interaction)
    
    async def create_ticket(self, interaction: discord.Interaction):
        # Get ticket configuration
        ticket_config = self.mongodb["tickets"].find_one({"guild_id": interaction.guild_id})
        if not ticket_config:
            await interaction.response.send_message(
                embed=create_embed("The ticket system is not set up yet.", discord.Color.red()),
                ephemeral=True
            )
            return
            
        # Check if user already has an open ticket
        existing_ticket = discord.utils.get(
            interaction.guild.channels,
            name=f"ticket-{interaction.user.name.lower()}",
            type=discord.ChannelType.text
        )
        
        if existing_ticket:
            await interaction.response.send_message(
                embed=create_embed(f"You already have an open ticket: {existing_ticket.mention}", discord.Color.yellow()),
                ephemeral=True
            )
            return
            
        # Get category and support roles
        category_id = ticket_config.get("category_id")
        if not category_id:
            await interaction.response.send_message(
                embed=create_embed("Ticket category not configured.", discord.Color.red()),
                ephemeral=True
            )
            return
            
        category = interaction.guild.get_channel(int(category_id))
        if not category:
            await interaction.response.send_message(
                embed=create_embed("Ticket category not found.", discord.Color.red()),
                ephemeral=True
            )
            return
            
        support_role_ids = ticket_config.get("support_roles", [])
        
        # Create permissions for the channel
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(
                read_messages=True, 
                send_messages=True,
                attach_files=True,
                embed_links=True
            )
        }
        
        # Add permissions for support roles
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
        
        # Create the ticket channel
        channel_name = f"ticket-{interaction.user.name.lower()}"
        try:
            channel = await interaction.guild.create_text_channel(
                name=channel_name,
                category=category,
                overwrites=overwrites,
                topic=f"Support ticket for {interaction.user.name}"
            )
            
            # Send initial ticket message
            embed = discord.Embed(
                title=f"Ticket: {interaction.user.name}",
                description="Thank you for creating a ticket. Support staff will assist you shortly.",
                color=discord.Color.blue()
            )
            embed.add_field(name="User", value=f"{interaction.user.mention}", inline=True)
            embed.add_field(name="Created", value=discord.utils.format_dt(discord.utils.utcnow()), inline=True)
            
            await channel.send(embed=embed, view=TicketClose())
            
            # Ping support roles if configured
            support_pings = []
            for role_id in support_role_ids:
                role = interaction.guild.get_role(int(role_id))
                if role:
                    support_pings.append(role.mention)
            
            if support_pings:
                await channel.send(", ".join(support_pings))
            
            # Confirm ticket creation to user
            await interaction.response.send_message(
                embed=create_embed(f"Your ticket has been created: {channel.mention}", discord.Color.green()),
                ephemeral=True
            )
            
        except discord.Forbidden:
            await interaction.response.send_message(
                embed=create_embed("I don't have permission to create ticket channels.", discord.Color.red()),
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                embed=create_embed(f"An error occurred: {str(e)}", discord.Color.red()),
                ephemeral=True
            )
    
    async def close_ticket(self, interaction: discord.Interaction):
        # Check if channel is a ticket
        if not interaction.channel.name.startswith("ticket-"):
            await interaction.response.send_message(
                embed=create_embed("This command can only be used in ticket channels.", discord.Color.red()),
                ephemeral=True
            )
            return
        
        # Check if user has permission (ticket creator or support role)
        is_support = False
        ticket_config = self.mongodb["tickets"].find_one({"guild_id": interaction.guild_id})
        if ticket_config:
            support_role_ids = ticket_config.get("support_roles", [])
            for role_id in support_role_ids:
                role = interaction.guild.get_role(int(role_id))
                if role and role in interaction.user.roles:
                    is_support = True
                    break
        
        is_author = interaction.channel.name.endswith(interaction.user.name.lower())
        
        if not (is_support or is_author):
            await interaction.response.send_message(
                embed=create_embed("You don't have permission to close this ticket.", discord.Color.red()),
                ephemeral=True
            )
            return
        
        # Log ticket content if configured
        log_channel_id = ticket_config.get("log_channel_id") if ticket_config else None
        if log_channel_id:
            log_channel = interaction.guild.get_channel(int(log_channel_id))
            if log_channel:
                # Create transcript of ticket
                messages = []
                async for message in interaction.channel.history(limit=100, oldest_first=True):
                    content = message.content if message.content else "No content"
                    timestamp = message.created_at.strftime("%Y-%m-%d %H:%M:%S")
                    messages.append(f"[{timestamp}] {message.author.name}: {content}")
                
                transcript = "\n".join(messages)
                
                # If transcript is too long, truncate it and add to a file
                if len(transcript) > 2000:
                    embed = create_embed(f"Ticket {interaction.channel.name} was closed by {interaction.user.mention}. Transcript is too long and attached as file.", discord.Color.red())
                    transcript_file = discord.File(io.StringIO(transcript), filename=f"transcript-{interaction.channel.name}.txt")
                    await log_channel.send(embed=embed, file=transcript_file)
                else:
                    embed = create_embed(f"Ticket {interaction.channel.name} was closed by {interaction.user.mention}.\n\n```\n{transcript}\n```", discord.Color.red())
                    await log_channel.send(embed=embed)
        
        # Close the ticket channel
        await interaction.response.send_message(
            embed=create_embed("This ticket is now being closed...", discord.Color.orange())
        )
        
        # Archive or delete based on configuration
        delete_tickets = ticket_config.get("delete_tickets", False) if ticket_config else False
        
        try:
            if delete_tickets:
                await interaction.channel.delete()
            else:
                # Archive the ticket by removing permissions
                await interaction.channel.set_permissions(interaction.guild.default_role, read_messages=False)
                await interaction.channel.edit(name=f"closed-{interaction.channel.name}")
        except discord.Forbidden:
            await interaction.followup.send(embed=create_embed("I don't have permission to close this ticket.", discord.Color.red()))
        except Exception as e:
            await interaction.followup.send(embed=create_embed(f"An error occurred while closing the ticket: {str(e)}", discord.Color.red()))


async def setup(bot):
    await bot.add_cog(Ticket(bot))


def fetch_fields_by_data_source(data_source: str, guild_id: str):
    """Fetch form fields for ticket modal from database"""
    # Initialize MongoDB connection
    mongo_db = initialize_mongodb()
    
    if not mongo_db:
        logger.error(f"Failed to connect to MongoDB when fetching ticket fields for guild {guild_id}")
        return get_default_ticket_fields()
    
    try:
        # Get ticket configuration from database
        ticket_config = mongo_db.ticket_config.find_one({"guild_id": guild_id})
        
        if not ticket_config or "fields" not in ticket_config:
            logger.info(f"No custom ticket fields found for guild {guild_id}, using defaults")
            return get_default_ticket_fields()
        
        fields = ticket_config["fields"]
        
        # Validate fields
        for field in fields:
            if "label" not in field or "placeholder" not in field:
                logger.warning(f"Invalid field configuration in guild {guild_id}: {field}")
                return get_default_ticket_fields()
        
        return fields
        
    except Exception as e:
        logger.error(f"Error fetching ticket fields for guild {guild_id}: {e}")
        return get_default_ticket_fields()


def get_default_ticket_fields():
    """Return default ticket form fields"""
    return [
        {
            "label": "Konu",
            "placeholder": "Sorununuzu kısaca açıklayın",
            "style": "short",
            "max_length": 100,
            "required": True,
            "row": 0
        },
        {
            "label": "Açıklama", 
            "placeholder": "Sorununuzu detaylı olarak açıklayın",
            "style": "paragraph",
            "max_length": 1000,
            "required": True,
            "row": 1
        }
    ]
