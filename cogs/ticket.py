import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import asyncio
import random
import io
from datetime import datetime

from utils.core.formatting import create_embed, hex_to_int
from utils.database.connection import initialize_mongodb
from utils.core.class_utils import DynamicView, DynamicButton

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
    def __init__(self, **kwargs):
        self.mongo_db = initialize_mongodb()
        super().__init__(
            style=discord.ButtonStyle.green,
            label="Kapat",
            emoji="<:lock:1147769998866133022>",
            custom_id="close_ticket",
            **kwargs
        )

    async def close_ticket(self, interaction: discord.Interaction):
        support_roles_data = self.mongo_db['settings'].find_one({"guild_id": interaction.guild.id})
        user_has_permission = False

        if support_roles_data and 'support_roles' in support_roles_data:
            support_roles = support_roles_data['support_roles']

            for role_id in support_roles:
                role = discord.utils.get(interaction.guild.roles, id=role_id)
                if role and role in interaction.user.roles:
                    user_has_permission = True
                    break

        if not user_has_permission:
            default_support_role = discord.utils.get(interaction.guild.roles, name='Destek')
            if default_support_role and default_support_role in interaction.user.roles:
                user_has_permission = True

        if user_has_permission:
            channel = interaction.channel
            channel_id = channel.id

            record = self.mongo_db["logger"].find_one({"guild_id": interaction.guild.id})

            if not record:
                print("Veritabanından kayıt bulunamadı!")
                return

            logs_channel_id = record.get("channel_id")
            print(f"Logs Channel ID: {logs_channel_id}")

            logs_channel = interaction.guild.get_channel(logs_channel_id)

            if not logs_channel:
                print(f"{logs_channel_id} ID'sine sahip bir kanal bulunamadı!")
                return

            print(logs_channel)

            closing_time = datetime.now().strftime("%Y-%m-%d %H-%M-%S")

            transcript = ""
            async for message in channel.history(limit=100):  # Adjust limit as needed
                transcript += f"{message.author}: {message.content}\n"

            transcript_file = discord.File(io.StringIO(transcript),
                                           filename=f"transcript{channel.name}-{closing_time}.txt")

            if logs_channel:
                embed = discord.Embed(title="Ticket Silindi",
                                      description=f"Ticket kanalı {interaction.user.mention} tarafından silindi.",
                                      color=discord.Color.red())
                await logs_channel.send(embed=embed, file=transcript_file)

            self.mongo_db["tickets"].delete_one({"_id": channel_id})

            await interaction.channel.delete()
            return
        else:
            await interaction.response.send_message(
                embed=create_embed(description="Bu işlemi gerçekleştirmek için yetkiniz yok.",
                                   color=discord.Color.red()), ephemeral=True)


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
    Create and manage support tickets with customizable settings
    """
    
    def __init__(self, bot):
        self.bot = bot
        self.mongodb = initialize_mongodb()
        
    @commands.hybrid_command(
        name="send_ticket_message",
        description="Sends a message with a button for users to create support tickets"
    )
    @app_commands.describe(
        title="The title for the ticket message",
        description="The description text for the ticket message"
    )
    @commands.has_permissions(manage_channels=True)
    async def send_ticket_message(self, ctx, title: str = "Support Tickets", *, description: str = "Click the button below to create a support ticket"):
        """
        Sends a message with a button that users can click to create support tickets.
        
        You can customize the title and description of the message to fit your server's needs.
        Users clicking the button will create private support ticket channels.
        """
        embed = discord.Embed(title=title, description=description, color=discord.Color.blue())
        await ctx.send(embed=embed, view=TicketButton())
        await ctx.send(embed=create_embed("Ticket message sent successfully!", discord.Color.green()), ephemeral=True)
    
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
