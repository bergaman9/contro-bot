"""
Ticket system views for Discord bot.
This module has been relocated from utils/turkoyto_views/ticket_views.py.
"""
import discord
import logging
import asyncio
from typing import Optional, List, Dict, Any
from utils.database import get_async_db, ensure_async_db
from utils.core.formatting import create_embed

logger = logging.getLogger('ticket_views')

class TicketView(discord.ui.View):
    """Main ticket creation view for users to open tickets"""
    
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label="Create Ticket", style=discord.ButtonStyle.primary, emoji="📩", custom_id="create_ticket")
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Check if ticket system is enabled for this guild
        try:
            mongo_db = get_async_db()
            settings = await mongo_db.tickets.find_one({"guild_id": interaction.guild.id})
            
            if not settings:
                await interaction.response.send_message("Ticket system is not configured for this server.", ephemeral=True)
                return
            
            # Check if user already has an open ticket
            existing_ticket = await mongo_db.active_tickets.find_one({
                "guild_id": interaction.guild.id,
                "user_id": interaction.user.id
            })
            
            if existing_ticket:
                channel_id = existing_ticket.get("channel_id")
                channel = interaction.guild.get_channel(channel_id)
                
                if channel:
                    await interaction.response.send_message(
                        f"You already have an open ticket: {channel.mention}", 
                        ephemeral=True
                    )
                    return
                else:
                    # Ticket channel was deleted, remove from database
                    await mongo_db.active_tickets.delete_one({"_id": existing_ticket["_id"]})
            
            # Get ticket category
            category_id = settings.get("category_id")
            if not category_id:
                await interaction.response.send_message("Ticket system is not properly configured (no category).", ephemeral=True)
                return
            
            category = interaction.guild.get_channel(int(category_id))
            if not category:
                await interaction.response.send_message("Ticket category was not found.", ephemeral=True)
                return
            
            # Create the ticket channel
            channel_name = f"ticket-{interaction.user.name}-{interaction.user.discriminator}"
            ticket_channel = await category.create_text_channel(
                name=channel_name,
                topic=f"Support ticket for {interaction.user.mention}",
                reason=f"Support ticket created by {interaction.user}"
            )
            
            # Set permissions
            # Allow the user to see the channel
            await ticket_channel.set_permissions(interaction.user, read_messages=True, send_messages=True)
            
            # Make it private for everyone else
            await ticket_channel.set_permissions(interaction.guild.default_role, read_messages=False)
            
            # Allow access for support roles
            support_roles = settings.get("support_roles", [])
            for role_id in support_roles:
                role = interaction.guild.get_role(role_id)
                if role:
                    await ticket_channel.set_permissions(role, read_messages=True, send_messages=True)
            
            # Save to database
            await mongo_db.active_tickets.insert_one({
                "guild_id": interaction.guild.id,
                "channel_id": ticket_channel.id,
                "user_id": interaction.user.id,
                "created_at": discord.utils.utcnow().isoformat(),
                "status": "open"
            })
            
            # Send initial message in ticket channel
            embed = discord.Embed(
                title="Support Ticket",
                description=f"Thank you for creating a ticket, {interaction.user.mention}.\nSupport staff will be with you shortly.",
                color=discord.Color.green()
            )
            
            # Add ticket management buttons
            ticket_controls = TicketControlView()
            await ticket_channel.send(embed=embed, view=ticket_controls)
            
            # Notify user
            await interaction.response.send_message(
                f"Your ticket has been created: {ticket_channel.mention}", 
                ephemeral=True
            )
            
        except Exception as e:
            logger.error(f"Error creating ticket: {e}", exc_info=True)
            await interaction.response.send_message("An error occurred while creating your ticket.", ephemeral=True)

class TicketControlView(discord.ui.View):
    """View for support staff to manage an open ticket"""
    
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label="Close Ticket", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="close_ticket")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Check if user has permission (either ticket creator or support role)
        mongo_db = get_async_db()
        ticket = await mongo_db.active_tickets.find_one({"channel_id": interaction.channel.id})
        
        if not ticket:
            await interaction.response.send_message("This channel is not a valid ticket.", ephemeral=True)
            return
        
        # Check if user has permission
        settings = await mongo_db.tickets.find_one({"guild_id": interaction.guild.id})
        support_roles = settings.get("support_roles", []) if settings else []
        
        is_support = any(role.id in support_roles for role in interaction.user.roles)
        is_creator = ticket.get("user_id") == interaction.user.id
        
        if not (is_support or is_creator):
            await interaction.response.send_message("You don't have permission to close this ticket.", ephemeral=True)
            return
        
        # Ask for confirmation
        embed = discord.Embed(
            title="Close Ticket",
            description="Are you sure you want to close this ticket?",
            color=discord.Color.red()
        )
        
        confirm_view = ConfirmCloseView()
        await interaction.response.send_message(embed=embed, view=confirm_view, ephemeral=True)

class ConfirmCloseView(discord.ui.View):
    """Confirmation view for closing a ticket"""
    
    def __init__(self):
        super().__init__(timeout=60)
    
    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.danger, emoji="✅")
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        mongo_db = get_async_db()
        
        # Mark ticket as closed in database
        await mongo_db.active_tickets.update_one(
            {"channel_id": interaction.channel.id},
            {"$set": {"status": "closed", "closed_at": discord.utils.utcnow().isoformat()}}
        )
        
        # Move to closed tickets collection
        ticket = await mongo_db.active_tickets.find_one({"channel_id": interaction.channel.id})
        if ticket:
            await mongo_db.closed_tickets.insert_one(ticket)
            await mongo_db.active_tickets.delete_one({"_id": ticket["_id"]})
        
        # Inform users
        embed = discord.Embed(
            title="Ticket Closed",
            description=f"This ticket has been closed by {interaction.user.mention}.\nChannel will be deleted in 5 seconds.",
            color=discord.Color.red()
        )
        
        await interaction.response.edit_message(content="Ticket will be closed.", embed=None, view=None)
        message = await interaction.channel.send(embed=embed)
        
        # Wait and delete the channel
        await asyncio.sleep(5)
        try:
            await interaction.channel.delete(reason=f"Ticket closed by {interaction.user}")
        except Exception as e:
            logger.error(f"Error deleting ticket channel: {e}", exc_info=True)
    
    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary, emoji="❌")
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="Ticket closure cancelled.", embed=None, view=None)

# Function to setup the ticket system in a guild
async def setup_ticket_system(guild, category_id, support_role_ids):
    """Set up the ticket system for a guild"""
    mongo_db = await ensure_async_db()
    
    await mongo_db.tickets.update_one(
        {"guild_id": guild.id},
        {"$set": {
            "category_id": str(category_id),
            "support_roles": support_role_ids,
            "enabled": True
        }},
        upsert=True
    )
    
    return True 
