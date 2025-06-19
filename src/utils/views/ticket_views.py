"""
Ticket system views for Discord bot.
This module has been relocated from utils/turkoyto_views/ticket_views.py.
"""
import discord
import logging
import asyncio
import io
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from src.utils.database import get_async_db, ensure_async_db
from src.utils.core.formatting import create_embed
from src.utils.common import error_embed, success_embed, info_embed, warning_embed
from discord.ext import commands
from ...bot.constants import Colors
from ..database.db_manager import db_manager

logger = logging.getLogger('ticket_views')

class TicketPriority:
    """Ticket priority levels."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"
    
    COLORS = {
        LOW: discord.Color.green(),
        NORMAL: discord.Color.blue(),
        HIGH: discord.Color.orange(),
        URGENT: discord.Color.red()
    }
    
    EMOJIS = {
        LOW: "🟢",
        NORMAL: "🔵",
        HIGH: "🟠",
        URGENT: "🔴"
    }

class TicketStatus:
    """Ticket status types."""
    OPEN = "open"
    ASSIGNED = "assigned"
    PENDING = "pending"
    RESOLVED = "resolved"
    CLOSED = "closed"
    ARCHIVED = "archived"

class TicketDepartment:
    """Represents a ticket department."""
    def __init__(self, guild_id: int, name: str, description: str, staff_roles: List[int], **kwargs):
        self.guild_id = guild_id
        self.name = name
        self.description = description
        self.staff_roles = staff_roles
        self.emoji = kwargs.get("emoji", "🎫")
        self.log_channel_id = kwargs.get("log_channel_id")
        self.welcome_message = kwargs.get("welcome_message", "Welcome to your ticket! Please describe your issue.")
        self.auto_assign_staff = kwargs.get("auto_assign_staff", False)
        self.max_tickets_per_user = kwargs.get("max_tickets_per_user", 3)
        self.require_priority = kwargs.get("require_priority", False)
        self.auto_close_hours = kwargs.get("auto_close_hours", 24)
        self.category_id = kwargs.get("category_id")
        self.transcript_enabled = kwargs.get("transcript_enabled", True)
        self.rating_enabled = kwargs.get("rating_enabled", True)
        self._id = kwargs.get("_id")

    @classmethod
    async def get_all(cls, guild_id: int) -> List['TicketDepartment']:
        """Get all ticket departments for a guild."""
        departments_data = await db_manager.get_database().ticket_departments.find({"guild_id": guild_id}).to_list(None)
        return [cls(**data) for data in departments_data]

    async def save(self):
        """Save the department to the database."""
        data = self.__dict__.copy()
        if self._id:
            # Update existing department
            data.pop('_id')  # Remove _id from update data
            await db_manager.get_database().ticket_departments.update_one({"_id": self._id}, {"$set": data})
        else:
            # Insert new department
            data.pop('_id')  # Remove None _id
            result = await db_manager.get_database().ticket_departments.insert_one(data)
            self._id = result.inserted_id

    async def delete(self):
        """Delete the department from the database."""
        if self._id:
            await db_manager.get_database().ticket_departments.delete_one({"_id": self._id})

class DepartmentSelectView(discord.ui.View):
    """View with a dropdown to select a ticket department."""
    def __init__(self, departments: List[TicketDepartment]):
        super().__init__(timeout=None)
        options = []
        for d in departments:
            # Skip departments without valid _id
            if not d._id:
                logger.warning(f"Skipping department '{d.name}' with no valid _id")
                continue
                
            # Validate emoji - only use if it's a valid Unicode emoji
            emoji = None
            if d.emoji and isinstance(d.emoji, str) and len(d.emoji.strip()) > 0:
                try:
                    # Simple check for valid emoji - if it's 1-4 characters and not alphanumeric
                    emoji_clean = d.emoji.strip()
                    if len(emoji_clean) <= 4 and not emoji_clean.isalnum():
                        emoji = emoji_clean
                except:
                    pass
            
            options.append(discord.SelectOption(
                label=d.name[:100],  # Discord limit
                description=d.description[:100] if d.description else None,  # Discord limit
                emoji=emoji,
                value=str(d._id)
            ))
        
        if options:
            self.add_item(DepartmentSelect(options))

class TicketCreateModal(discord.ui.Modal, title="Create a New Ticket"):
    """Modal for creating a new ticket."""
    issue_title = discord.ui.TextInput(label="Title", placeholder="e.g., Issue with login")
    issue_description = discord.ui.TextInput(label="Description", style=discord.TextStyle.paragraph, placeholder="Please describe your issue in detail.")

    def __init__(self, department: TicketDepartment):
        super().__init__()
        self.department = department
        
        # Add priority field if required
        if department.require_priority:
            self.priority = discord.ui.TextInput(
                label="Priority (low/normal/high/urgent)",
                placeholder="normal",
                default="normal",
                min_length=3,
                max_length=6
            )

    async def on_submit(self, interaction: discord.Interaction):
        # Check ticket limits
        mongo_db = get_async_db()
        existing_tickets = await mongo_db.active_tickets.count_documents({
            "guild_id": interaction.guild.id,
            "user_id": interaction.user.id,
            "status": {"$in": [TicketStatus.OPEN, TicketStatus.ASSIGNED, TicketStatus.PENDING]}
        })
        
        if existing_tickets >= self.department.max_tickets_per_user:
            await interaction.response.send_message(
                embed=error_embed(
                    f"You already have {existing_tickets} open tickets. Maximum allowed: {self.department.max_tickets_per_user}",
                    title="❌ Ticket Limit Reached"
                ),
                ephemeral=True
            )
            return
        
        # Validate priority if required
        priority = TicketPriority.NORMAL
        if self.department.require_priority and hasattr(self, 'priority'):
            priority_input = self.priority.value.lower()
            if priority_input not in [TicketPriority.LOW, TicketPriority.NORMAL, TicketPriority.HIGH, TicketPriority.URGENT]:
                await interaction.response.send_message(
                    embed=error_embed(
                        "Invalid priority. Use: low, normal, high, or urgent",
                        title="❌ Invalid Priority"
                    ),
                    ephemeral=True
                )
                return
            priority = priority_input
        
        # Create the ticket channel
        guild = interaction.guild
        staff_roles = [guild.get_role(role_id) for role_id in self.department.staff_roles if guild.get_role(role_id)]
        
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        }
        for role in staff_roles:
            overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        try:
            # Use department category or create default
            category = None
            if self.department.category_id:
                category = guild.get_channel(self.department.category_id)
            
            if not category:
                category = discord.utils.get(guild.categories, name="Tickets")
                if not category:
                    category = await guild.create_category("Tickets")

            # Create unique channel name with priority indicator
            priority_emoji = TicketPriority.EMOJIS.get(priority, "🔵")
            ticket_number = await self._get_next_ticket_number(guild.id)
            channel_name = f"{priority_emoji}ticket-{ticket_number}-{interaction.user.display_name}"
            
            channel = await guild.create_text_channel(
                name=channel_name[:100],  # Discord channel name limit
                category=category,
                overwrites=overwrites,
                topic=f"Ticket #{ticket_number} | {self.department.name} | {interaction.user} | Priority: {priority}"
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                embed=error_embed(
                    "I don't have permissions to create channels.",
                    title="❌ Permission Error"
                ),
                ephemeral=True
            )
            return

        # Create ticket database entry
        ticket_data = {
            "ticket_number": ticket_number,
            "channel_id": channel.id,
            "guild_id": guild.id,
            "user_id": interaction.user.id,
            "department_name": self.department.name,
            "department_id": str(self.department._id) if self.department._id else None,
            "title": self.issue_title.value,
            "description": self.issue_description.value,
            "priority": priority,
            "status": TicketStatus.OPEN,
            "created_at": datetime.utcnow(),
            "assigned_staff": None,
            "messages_count": 0,
            "last_activity": datetime.utcnow()
        }
        
        result = await mongo_db.active_tickets.insert_one(ticket_data)
        
        # Send initial message to the new channel
        embed = create_embed(
            title=f"🎫 Ticket #{ticket_number}: {self.issue_title.value}",
            description=self.department.welcome_message,
            color=TicketPriority.COLORS.get(priority, Colors.INFO)
        )
        embed.add_field(name="Department", value=self.department.name, inline=True)
        embed.add_field(name="Priority", value=f"{TicketPriority.EMOJIS.get(priority)} {priority.title()}", inline=True)
        embed.add_field(name="Created by", value=interaction.user.mention, inline=True)
        embed.add_field(name="Issue Description", value=self.issue_description.value, inline=False)
        embed.set_footer(text=f"Ticket ID: {result.inserted_id}")
        
        # Add the advanced management view
        management_view = AdvancedTicketManagementView(ticket_data)
        await channel.send(f"Welcome {interaction.user.mention}! Staff will be with you shortly.", embed=embed, view=management_view)
        
        # Auto-assign staff if enabled
        if self.department.auto_assign_staff and staff_roles:
            # Simple round-robin assignment (could be enhanced with load balancing)
            assigned_staff = staff_roles[0].members[0] if staff_roles[0].members else None
            if assigned_staff:
                await self._assign_staff(channel, assigned_staff, result.inserted_id)
        
        await interaction.response.send_message(
            embed=success_embed(
                f"✅ Your ticket #{ticket_number} has been created at {channel.mention}!",
                title="Ticket Created"
            ),
            ephemeral=True
        )
    
    async def _get_next_ticket_number(self, guild_id: int) -> int:
        """Get the next ticket number for this guild."""
        mongo_db = get_async_db()
        
        # Get the highest ticket number
        last_ticket = await mongo_db.active_tickets.find_one(
            {"guild_id": guild_id},
            sort=[("ticket_number", -1)]
        )
        
        if last_ticket and "ticket_number" in last_ticket:
            return last_ticket["ticket_number"] + 1
        
        # Check closed tickets too
        last_closed = await mongo_db.closed_tickets.find_one(
            {"guild_id": guild_id},
            sort=[("ticket_number", -1)]
        )
        
        if last_closed and "ticket_number" in last_closed:
            return last_closed["ticket_number"] + 1
            
        return 1
    
    async def _assign_staff(self, channel: discord.TextChannel, staff_member: discord.Member, ticket_id):
        """Assign a staff member to the ticket."""
        mongo_db = get_async_db()
        
        await mongo_db.active_tickets.update_one(
            {"_id": ticket_id},
            {"$set": {"assigned_staff": staff_member.id, "status": TicketStatus.ASSIGNED}}
        )
        
        embed = info_embed(
            f"🎯 Ticket has been assigned to {staff_member.mention}",
            title="Staff Assigned"
        )
        await channel.send(embed=embed)

class DepartmentSelect(discord.ui.Select):
    """The select menu for ticket departments."""
    def __init__(self, options: List[discord.SelectOption]):
        super().__init__(
            placeholder="Choose a department to open a ticket...",
            options=options,
            custom_id="ticket_department_select"
        )

    async def callback(self, interaction: discord.Interaction):
        """Handle department selection."""
        department_id = self.values[0]
        db = db_manager.get_database()
        
        # Convert department_id to ObjectId
        from bson.objectid import ObjectId
        department_data = await db.ticket_departments.find_one({"_id": ObjectId(department_id)})
        
        if department_data:
            department = TicketDepartment(**department_data)
            modal = TicketCreateModal(department)
            await interaction.response.send_modal(modal)
        else:
            await interaction.response.send_message("Could not find that department.", ephemeral=True)

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
                await interaction.response.send_message(
                    embed=error_embed(
                        "Ticket sistemi bu sunucu için yapılandırılmamış.",
                        title="❌ Sistem Yapılandırılmamış"
                    ),
                    ephemeral=True
                )
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
                        embed=info_embed(
                            f"Zaten açık bir ticketınız var: {channel.mention}",
                            title="ℹ️ Mevcut Ticket"
                        ),
                        ephemeral=True
                    )
                    return
                else:
                    # Ticket channel was deleted, remove from database
                    await mongo_db.active_tickets.delete_one({"_id": existing_ticket["_id"]})
            
            # Get ticket category
            category_id = settings.get("category_id")
            if not category_id:
                await interaction.response.send_message(
                    embed=error_embed(
                        "Ticket sistemi düzgün yapılandırılmamış (kategori eksik).",
                        title="❌ Yapılandırma Hatası"
                    ),
                    ephemeral=True
                )
                return
            
            category = interaction.guild.get_channel(int(category_id))
            if not category:
                await interaction.response.send_message(
                    embed=error_embed(
                        "Ticket kategorisi bulunamadı. Lütfen yöneticiye bildirin.",
                        title="❌ Kategori Bulunamadı"
                    ),
                    ephemeral=True
                )
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
            embed = success_embed(
                f"Ticket oluşturduğunuz için teşekkür ederiz, {interaction.user.mention}.\n\nDestek ekibimiz en kısa sürede sizinle ilgilenecektir.\n\n**Lütfen sorununuzu detaylı bir şekilde açıklayın.**",
                title="🎫 Destek Ticket'ı"
            )
            
            # Add ticket management buttons
            ticket_controls = TicketControlView()
            await ticket_channel.send(embed=embed, view=ticket_controls)
            
            # Notify user
            await interaction.response.send_message(
                embed=success_embed(
                    f"Ticket'ınız başarıyla oluşturuldu: {ticket_channel.mention}\n\nLütfen ticket kanalında sorununuzu detaylı bir şekilde açıklayın.",
                    title="✅ Ticket Oluşturuldu"
                ),
                ephemeral=True
            )
            
        except Exception as e:
            logger.error(f"Error creating ticket: {e}", exc_info=True)
            await interaction.response.send_message(
                embed=error_embed(
                    "Ticket oluşturulurken bir hata oluştu. Lütfen daha sonra tekrar deneyin.",
                    title="❌ Hata"
                ),
                ephemeral=True
            )

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

class DepartmentSettingsModal(discord.ui.Modal, title="Department Settings"):
    """Modal to add or edit a ticket department."""
    department_name = discord.ui.TextInput(label="Department Name", placeholder="e.g., Technical Support")
    department_desc = discord.ui.TextInput(label="Description", placeholder="For issues related to our services.", style=discord.TextStyle.paragraph)
    staff_roles = discord.ui.TextInput(label="Staff Role IDs (comma-separated)", placeholder="e.g., 123456789, 987654321")
    emoji = discord.ui.TextInput(label="Emoji (Optional)", placeholder="e.g., 🛠️", required=False)
    
    def __init__(self, guild_id: int, department: Optional[TicketDepartment] = None):
        super().__init__()
        self.guild_id = guild_id
        self.department = department
        if department:
            self.title = f"Editing '{department.name}'"
            self.department_name.default = department.name
            self.department_desc.default = department.description
            self.staff_roles.default = ", ".join(map(str, department.staff_roles))
            self.emoji.default = department.emoji

    async def on_submit(self, interaction: discord.Interaction):
        try:
            role_ids = [int(r.strip()) for r in self.staff_roles.value.split(',') if r.strip()]
        except ValueError:
            await interaction.response.send_message("Invalid Role ID format. Please use comma-separated numbers.", ephemeral=True)
            return

        dept_data = {
            "guild_id": self.guild_id,
            "name": self.department_name.value,
            "description": self.department_desc.value,
            "staff_roles": role_ids,
            "emoji": self.emoji.value
        }
        
        if self.department:
            department_to_save = self.department
            department_to_save.name = dept_data["name"]
            department_to_save.description = dept_data["description"]
            department_to_save.staff_roles = dept_data["staff_roles"]
            department_to_save.emoji = dept_data["emoji"]
        else:
            department_to_save = TicketDepartment(**dept_data)

        await department_to_save.save()
        
        # Show advanced settings configuration
        advanced_view = DepartmentAdvancedSettingsView(department_to_save)
        embed = success_embed(
            f"✅ Department '{department_to_save.name}' saved successfully!\n\nWould you like to configure advanced settings?",
            title="Department Saved"
        )
        await interaction.response.send_message(embed=embed, view=advanced_view, ephemeral=True)

class DepartmentAdvancedSettingsView(discord.ui.View):
    """View for configuring advanced department settings."""
    
    def __init__(self, department: TicketDepartment):
        super().__init__(timeout=300)
        self.department = department
    
    @discord.ui.button(label="⚙️ Advanced Settings", style=discord.ButtonStyle.primary)
    async def advanced_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Open advanced settings modal."""
        modal = DepartmentAdvancedModal(self.department)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="✅ Done", style=discord.ButtonStyle.success)
    async def done(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Finish configuration."""
        embed = success_embed(
            "Department configuration completed!",
            title="✅ Configuration Complete"
        )
        await interaction.response.edit_message(embed=embed, view=None)

class DepartmentAdvancedModal(discord.ui.Modal, title="Advanced Department Settings"):
    """Modal for advanced department configuration."""
    
    welcome_message = discord.ui.TextInput(
        label="Welcome Message",
        style=discord.TextStyle.paragraph,
        placeholder="Welcome to your ticket! Please describe your issue.",
        required=False,
        max_length=1000
    )
    
    max_tickets = discord.ui.TextInput(
        label="Max Tickets per User",
        placeholder="3",
        required=False,
        max_length=2
    )
    
    auto_close_hours = discord.ui.TextInput(
        label="Auto-close after hours (0 = disabled)",
        placeholder="24",
        required=False,
        max_length=3
    )
    
    settings_flags = discord.ui.TextInput(
        label="Settings (comma-separated)",
        placeholder="require_priority, auto_assign_staff, transcript_enabled, rating_enabled",
        style=discord.TextStyle.paragraph,
        required=False
    )
    
    def __init__(self, department: TicketDepartment):
        super().__init__()
        self.department = department
        
        # Set defaults
        self.welcome_message.default = department.welcome_message
        self.max_tickets.default = str(department.max_tickets_per_user)
        self.auto_close_hours.default = str(department.auto_close_hours)
        
        # Create settings string
        settings = []
        if department.require_priority:
            settings.append("require_priority")
        if department.auto_assign_staff:
            settings.append("auto_assign_staff")
        if department.transcript_enabled:
            settings.append("transcript_enabled")
        if department.rating_enabled:
            settings.append("rating_enabled")
        
        self.settings_flags.default = ", ".join(settings)
    
    async def on_submit(self, interaction: discord.Interaction):
        # Parse and validate inputs
        try:
            max_tickets = int(self.max_tickets.value) if self.max_tickets.value else 3
            auto_close_hours = int(self.auto_close_hours.value) if self.auto_close_hours.value else 24
        except ValueError:
            await interaction.response.send_message(
                "Invalid number format in max tickets or auto-close hours.",
                ephemeral=True
            )
            return
        
        # Parse settings flags
        settings_list = [s.strip().lower() for s in self.settings_flags.value.split(",") if s.strip()]
        
        # Update department
        self.department.welcome_message = self.welcome_message.value or self.department.welcome_message
        self.department.max_tickets_per_user = max_tickets
        self.department.auto_close_hours = auto_close_hours
        self.department.require_priority = "require_priority" in settings_list
        self.department.auto_assign_staff = "auto_assign_staff" in settings_list
        self.department.transcript_enabled = "transcript_enabled" in settings_list
        self.department.rating_enabled = "rating_enabled" in settings_list
        
        # Save to database
        await self.department.save()
        
        # Show confirmation
        embed = success_embed(
            f"Advanced settings updated for '{self.department.name}':\n\n"
            f"**Max Tickets per User:** {max_tickets}\n"
            f"**Auto-close Hours:** {auto_close_hours}\n"
            f"**Require Priority:** {'Yes' if self.department.require_priority else 'No'}\n"
            f"**Auto-assign Staff:** {'Yes' if self.department.auto_assign_staff else 'No'}\n"
            f"**Transcript Enabled:** {'Yes' if self.department.transcript_enabled else 'No'}\n"
            f"**Rating Enabled:** {'Yes' if self.department.rating_enabled else 'No'}",
            title="⚙️ Advanced Settings Updated"
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

class TicketDepartmentsView(discord.ui.View):
    """View to manage ticket departments."""
    def __init__(self, guild_id: int):
        super().__init__(timeout=300)
        self.guild_id = guild_id

    @discord.ui.button(label="Add Department", style=discord.ButtonStyle.success)
    async def add_department(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Add a new department."""
        modal = DepartmentSettingsModal(self.guild_id)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Edit Department", style=discord.ButtonStyle.primary)
    async def edit_department(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Edit an existing department."""
        departments = await TicketDepartment.get_all(self.guild_id)
        if not departments:
            await interaction.response.send_message("No departments to edit.", ephemeral=True)
            return
        
        # Create a new view with the select menu
        edit_view = EditDepartmentView(self.guild_id, departments)
        embed = create_embed(
            title="✈️ Edit Ticket Department",
            description="Select a department to edit:",
            color=Colors.INFO
        )
        await interaction.response.send_message(embed=embed, view=edit_view, ephemeral=True)
        
class EditDepartmentView(discord.ui.View):
    """View for editing departments."""
    def __init__(self, guild_id: int, departments: List[TicketDepartment]):
        super().__init__(timeout=300)
        self.guild_id = guild_id
        
        # Create select options for departments
        options = []
        for d in departments:
            options.append(discord.SelectOption(
                label=d.name[:100],
                description=d.description[:100] if d.description else "No description",
                value=str(d._id)
            ))
        
        if options:
            self.add_item(EditDepartmentSelect(options))

class EditDepartmentSelect(discord.ui.Select):
    """Select menu to choose a department to edit."""
    def __init__(self, options: List[discord.SelectOption]):
        super().__init__(placeholder="Select a department to edit...", options=options)

    async def callback(self, interaction: discord.Interaction):
        department_id = self.values[0]
        try:
            from bson.objectid import ObjectId
            department_data = await db_manager.get_database().ticket_departments.find_one({"_id": ObjectId(department_id)})
            if department_data:
                department = TicketDepartment(**department_data)
                modal = DepartmentSettingsModal(interaction.guild_id, department)
                await interaction.response.send_modal(modal)
            else:
                await interaction.response.send_message("Could not find that department.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"Error loading department: {str(e)}", ephemeral=True)

class TicketManagementView(discord.ui.View):
    """View for managing an open ticket."""
    def __init__(self, ticket_creator_id: int):
        super().__init__(timeout=None)
        self.ticket_creator_id = ticket_creator_id

    @discord.ui.button(label="Close Ticket", style=discord.ButtonStyle.danger, custom_id="ticket_close")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Close the ticket."""
        await interaction.response.send_message("Closing this ticket in 5 seconds...")
        await asyncio.sleep(5)
        await interaction.channel.delete()

    @discord.ui.button(label="Claim Ticket", style=discord.ButtonStyle.success, custom_id="ticket_claim")
    async def claim_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Claim the ticket."""
        await interaction.channel.send(f"Ticket claimed by {interaction.user.mention}.")
        self.claim_ticket.disabled = True
        await interaction.response.edit_message(view=self)

    @discord.ui.button(label="Transcript", style=discord.ButtonStyle.secondary, custom_id="ticket_transcript")
    async def transcript(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Generate a transcript of the ticket."""
        await interaction.response.defer()
        messages = [message async for message in interaction.channel.history(limit=None, oldest_first=True)]
        transcript = "\n".join([f"{m.author} ({m.created_at.strftime('%Y-%m-%d %H:%M:%S')}): {m.content}" for m in messages])
        
        transcript_file = discord.File(io.StringIO(transcript), filename=f"transcript-{interaction.channel.name}.txt")
        await interaction.followup.send("Here is the ticket transcript:", file=transcript_file) 

class AdvancedTicketManagementView(discord.ui.View):
    """Advanced view for managing an open ticket with all features."""
    def __init__(self, ticket_data: Dict[str, Any]):
        super().__init__(timeout=None)
        self.ticket_data = ticket_data

    @discord.ui.button(label="Claim", style=discord.ButtonStyle.success, emoji="🎯", custom_id="ticket_claim", row=0)
    async def claim_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Claim the ticket."""
        mongo_db = get_async_db()
        
        # Check if user has permission
        ticket = await mongo_db.active_tickets.find_one({"channel_id": interaction.channel.id})
        if not ticket:
            await interaction.response.send_message("Ticket not found.", ephemeral=True)
            return
        
        # Check if already assigned
        if ticket.get("assigned_staff"):
            assigned_user = interaction.guild.get_member(ticket["assigned_staff"])
            await interaction.response.send_message(
                f"This ticket is already assigned to {assigned_user.mention if assigned_user else 'someone'}.",
                ephemeral=True
            )
            return
        
        # Assign to current user
        await mongo_db.active_tickets.update_one(
            {"_id": ticket["_id"]},
            {"$set": {"assigned_staff": interaction.user.id, "status": TicketStatus.ASSIGNED}}
        )
        
        embed = success_embed(
            f"🎯 Ticket has been claimed by {interaction.user.mention}",
            title="Ticket Claimed"
        )
        await interaction.response.send_message(embed=embed)
        
        # Update button to show assigned
        button.label = f"Assigned to {interaction.user.display_name}"
        button.disabled = True
        await interaction.edit_original_response(view=self)

    @discord.ui.button(label="Transfer", style=discord.ButtonStyle.primary, emoji="🔄", custom_id="ticket_transfer", row=0)
    async def transfer_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Transfer ticket to another staff member."""
        mongo_db = get_async_db()
        ticket = await mongo_db.active_tickets.find_one({"channel_id": interaction.channel.id})
        
        if not ticket:
            await interaction.response.send_message("Ticket not found.", ephemeral=True)
            return
        
        # Get department data for staff roles
        department_data = await mongo_db.ticket_departments.find_one({"_id": ticket.get("department_id")})
        if not department_data:
            await interaction.response.send_message("Department not found.", ephemeral=True)
            return
        
        # Create transfer view
        transfer_view = TicketTransferView(ticket["_id"], department_data["staff_roles"])
        embed = info_embed(
            "Select a staff member to transfer this ticket to:",
            title="Transfer Ticket"
        )
        await interaction.response.send_message(embed=embed, view=transfer_view, ephemeral=True)

    @discord.ui.button(label="Priority", style=discord.ButtonStyle.secondary, emoji="⚡", custom_id="ticket_priority", row=0)
    async def change_priority(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Change ticket priority."""
        priority_view = PrioritySelectView()
        embed = info_embed(
            "Select new priority level:",
            title="Change Priority"
        )
        await interaction.response.send_message(embed=embed, view=priority_view, ephemeral=True)

    @discord.ui.button(label="Close", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="ticket_close", row=1)
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Close the ticket with reason."""
        close_modal = TicketCloseModal()
        await interaction.response.send_modal(close_modal)

    @discord.ui.button(label="Transcript", style=discord.ButtonStyle.secondary, emoji="📋", custom_id="ticket_transcript", row=1)
    async def generate_transcript(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Generate detailed transcript."""
        await interaction.response.defer()
        
        messages = []
        async for message in interaction.channel.history(limit=None, oldest_first=True):
            messages.append({
                "author": str(message.author),
                "content": message.content,
                "timestamp": message.created_at.strftime('%Y-%m-%d %H:%M:%S UTC'),
                "attachments": [att.url for att in message.attachments]
            })
        
        # Create formatted transcript
        transcript_content = f"Ticket Transcript - {interaction.channel.name}\n"
        transcript_content += f"Generated on: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
        transcript_content += "=" * 50 + "\n\n"
        
        for msg in messages:
            transcript_content += f"[{msg['timestamp']}] {msg['author']}: {msg['content']}\n"
            if msg['attachments']:
                transcript_content += f"  Attachments: {', '.join(msg['attachments'])}\n"
            transcript_content += "\n"
        
        # Save to file
        transcript_file = discord.File(
            io.StringIO(transcript_content), 
            filename=f"transcript-{interaction.channel.name}.txt"
        )
        
        await interaction.followup.send(
            "📋 Transcript generated:",
            file=transcript_file,
            ephemeral=True
        )

class PrioritySelectView(discord.ui.View):
    """View for selecting ticket priority."""
    def __init__(self):
        super().__init__(timeout=60)
        
        options = [
            discord.SelectOption(
                label=f"{TicketPriority.EMOJIS[TicketPriority.LOW]} Low Priority",
                value=TicketPriority.LOW,
                description="Non-urgent issues"
            ),
            discord.SelectOption(
                label=f"{TicketPriority.EMOJIS[TicketPriority.NORMAL]} Normal Priority", 
                value=TicketPriority.NORMAL,
                description="Standard support requests"
            ),
            discord.SelectOption(
                label=f"{TicketPriority.EMOJIS[TicketPriority.HIGH]} High Priority",
                value=TicketPriority.HIGH, 
                description="Important issues requiring attention"
            ),
            discord.SelectOption(
                label=f"{TicketPriority.EMOJIS[TicketPriority.URGENT]} Urgent Priority",
                value=TicketPriority.URGENT,
                description="Critical issues requiring immediate attention"
            )
        ]
        
        self.add_item(PrioritySelect(options))

class PrioritySelect(discord.ui.Select):
    """Select menu for priority levels."""
    def __init__(self, options):
        super().__init__(placeholder="Select priority level...", options=options)
    
    async def callback(self, interaction: discord.Interaction):
        new_priority = self.values[0]
        mongo_db = get_async_db()
        
        # Update ticket priority
        result = await mongo_db.active_tickets.update_one(
            {"channel_id": interaction.channel.id},
            {"$set": {"priority": new_priority}}
        )
        
        if result.modified_count > 0:
            # Update channel name with new priority emoji
            priority_emoji = TicketPriority.EMOJIS.get(new_priority)
            current_name = interaction.channel.name
            
            # Remove old priority emoji and add new one
            for emoji in TicketPriority.EMOJIS.values():
                current_name = current_name.replace(emoji, "")
            
            new_name = f"{priority_emoji}{current_name}"
            await interaction.channel.edit(name=new_name[:100])
            
            embed = success_embed(
                f"Priority changed to {TicketPriority.EMOJIS.get(new_priority)} **{new_priority.title()}**",
                title="Priority Updated"
            )
            await interaction.response.edit_message(embed=embed, view=None)
        else:
            await interaction.response.send_message("Failed to update priority.", ephemeral=True)

class TicketTransferView(discord.ui.View):
    """View for transferring ticket to another staff member."""
    def __init__(self, ticket_id, staff_role_ids: List[int]):
        super().__init__(timeout=60)
        self.ticket_id = ticket_id
        self.staff_role_ids = staff_role_ids

    @discord.ui.button(label="Select Staff Member", style=discord.ButtonStyle.primary)
    async def select_staff(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Get all staff members
        staff_members = []
        for role_id in self.staff_role_ids:
            role = interaction.guild.get_role(role_id)
            if role:
                staff_members.extend(role.members)
        
        # Remove duplicates
        staff_members = list(set(staff_members))
        
        if not staff_members:
            await interaction.response.send_message("No staff members found.", ephemeral=True)
            return
        
        # Create select options (limited to 25 by Discord)
        options = []
        for member in staff_members[:25]:
            options.append(discord.SelectOption(
                label=member.display_name,
                value=str(member.id),
                description=f"Transfer to {member.display_name}"
            ))
        
        if options:
            transfer_select = StaffTransferSelect(options, self.ticket_id)
            transfer_view = discord.ui.View(timeout=60)
            transfer_view.add_item(transfer_select)
            
            await interaction.response.edit_message(
                embed=info_embed("Select a staff member:", title="Transfer Ticket"),
                view=transfer_view
            )

class StaffTransferSelect(discord.ui.Select):
    """Select menu for staff transfer."""
    def __init__(self, options, ticket_id):
        super().__init__(placeholder="Select staff member...", options=options)
        self.ticket_id = ticket_id
    
    async def callback(self, interaction: discord.Interaction):
        new_staff_id = int(self.values[0])
        new_staff = interaction.guild.get_member(new_staff_id)
        
        if not new_staff:
            await interaction.response.send_message("Staff member not found.", ephemeral=True)
            return
        
        mongo_db = get_async_db()
        await mongo_db.active_tickets.update_one(
            {"_id": self.ticket_id},
            {"$set": {"assigned_staff": new_staff_id, "status": TicketStatus.ASSIGNED}}
        )
        
        embed = success_embed(
            f"Ticket transferred to {new_staff.mention}",
            title="Ticket Transferred"
        )
        
        await interaction.response.edit_message(embed=embed, view=None)
        await interaction.channel.send(embed=embed)

class TicketCloseModal(discord.ui.Modal, title="Close Ticket"):
    """Modal for closing ticket with reason."""
    close_reason = discord.ui.TextInput(
        label="Reason for closing",
        style=discord.TextStyle.paragraph,
        placeholder="Please provide a reason for closing this ticket...",
        required=True,
        max_length=500
    )
    
    solution = discord.ui.TextInput(
        label="Solution provided (optional)",
        style=discord.TextStyle.paragraph,
        placeholder="Describe the solution or resolution...",
        required=False,
        max_length=1000
    )

    async def on_submit(self, interaction: discord.Interaction):
        mongo_db = get_async_db()
        
        # Get ticket data
        ticket = await mongo_db.active_tickets.find_one({"channel_id": interaction.channel.id})
        if not ticket:
            await interaction.response.send_message("Ticket not found.", ephemeral=True)
            return
        
        # Check if department has rating enabled
        department = None
        if ticket.get("department_id"):
            dept_data = await mongo_db.ticket_departments.find_one({"_id": ticket["department_id"]})
            if dept_data:
                department = TicketDepartment(**dept_data)
        
        # Update ticket status
        close_data = {
            "status": TicketStatus.RESOLVED,
            "closed_at": datetime.utcnow(),
            "closed_by": interaction.user.id,
            "close_reason": self.close_reason.value,
            "solution": self.solution.value
        }
        
        await mongo_db.active_tickets.update_one(
            {"_id": ticket["_id"]},
            {"$set": close_data}
        )
        
        # Send closing message
        embed = warning_embed(
            f"**Reason:** {self.close_reason.value}\n\n"
            f"**Solution:** {self.solution.value if self.solution.value else 'No solution provided'}\n\n"
            f"Closed by: {interaction.user.mention}",
            title="🔒 Ticket Resolved"
        )
        
        # Add rating system if enabled
        if department and department.rating_enabled:
            rating_view = TicketRatingView(ticket["_id"], ticket["user_id"])
            await interaction.response.send_message(embed=embed, view=rating_view)
        else:
            await interaction.response.send_message(embed=embed)
        
        # Schedule channel deletion after 10 seconds
        await asyncio.sleep(10)
        
        # Move to closed tickets
        closed_ticket = ticket.copy()
        closed_ticket.update(close_data)
        await mongo_db.closed_tickets.insert_one(closed_ticket)
        await mongo_db.active_tickets.delete_one({"_id": ticket["_id"]})
        
        try:
            await interaction.channel.delete(reason=f"Ticket closed by {interaction.user}")
        except:
            pass

class TicketRatingView(discord.ui.View):
    """View for rating ticket support."""
    def __init__(self, ticket_id, user_id: int):
        super().__init__(timeout=300)
        self.ticket_id = ticket_id
        self.user_id = user_id

    @discord.ui.button(label="⭐", style=discord.ButtonStyle.secondary, custom_id="rate_1")
    async def rate_1(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._handle_rating(interaction, 1)

    @discord.ui.button(label="⭐⭐", style=discord.ButtonStyle.secondary, custom_id="rate_2")
    async def rate_2(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._handle_rating(interaction, 2)

    @discord.ui.button(label="⭐⭐⭐", style=discord.ButtonStyle.secondary, custom_id="rate_3")
    async def rate_3(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._handle_rating(interaction, 3)

    @discord.ui.button(label="⭐⭐⭐⭐", style=discord.ButtonStyle.secondary, custom_id="rate_4")
    async def rate_4(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._handle_rating(interaction, 4)

    @discord.ui.button(label="⭐⭐⭐⭐⭐", style=discord.ButtonStyle.success, custom_id="rate_5")
    async def rate_5(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._handle_rating(interaction, 5)

    async def _handle_rating(self, interaction: discord.Interaction, rating: int):
        # Only allow ticket creator to rate
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Only the ticket creator can rate this ticket.", ephemeral=True)
            return
        
        mongo_db = get_async_db()
        
        # Save rating
        await mongo_db.ticket_ratings.insert_one({
            "ticket_id": self.ticket_id,
            "user_id": self.user_id,
            "rating": rating,
            "rated_at": datetime.utcnow(),
            "guild_id": interaction.guild.id
        })
        
        # Update closed ticket with rating
        await mongo_db.closed_tickets.update_one(
            {"_id": self.ticket_id},
            {"$set": {"rating": rating}}
        )
        
        stars = "⭐" * rating
        embed = success_embed(
            f"Thank you for rating this ticket: {stars} ({rating}/5)",
            title="Rating Submitted"
        )
        
        await interaction.response.edit_message(embed=embed, view=None) 

class TicketStatistics:
    """Class for ticket statistics and analytics."""
    
    def __init__(self, mongo_db):
        self.db = mongo_db
    
    async def get_guild_stats(self, guild_id: int) -> Dict[str, Any]:
        """Get comprehensive ticket statistics for a guild."""
        
        # Active tickets count
        active_count = await self.db.active_tickets.count_documents({"guild_id": guild_id})
        
        # Closed tickets count
        closed_count = await self.db.closed_tickets.count_documents({"guild_id": guild_id})
        
        # Total tickets
        total_tickets = active_count + closed_count
        
        # Average rating
        rating_pipeline = [
            {"$match": {"guild_id": guild_id, "rating": {"$exists": True}}},
            {"$group": {"_id": None, "avg_rating": {"$avg": "$rating"}, "total_ratings": {"$sum": 1}}}
        ]
        rating_result = await self.db.closed_tickets.aggregate(rating_pipeline).to_list(length=1)
        avg_rating = rating_result[0]["avg_rating"] if rating_result else 0
        total_ratings = rating_result[0]["total_ratings"] if rating_result else 0
        
        # Tickets by status
        status_pipeline = [
            {"$match": {"guild_id": guild_id}},
            {"$group": {"_id": "$status", "count": {"$sum": 1}}}
        ]
        status_counts = {}
        async for status_doc in self.db.active_tickets.aggregate(status_pipeline):
            status_counts[status_doc["_id"]] = status_doc["count"]
        
        # Tickets by priority
        priority_pipeline = [
            {"$match": {"guild_id": guild_id}},
            {"$group": {"_id": "$priority", "count": {"$sum": 1}}}
        ]
        priority_counts = {}
        async for priority_doc in self.db.active_tickets.aggregate(priority_pipeline):
            priority_counts[priority_doc["_id"]] = priority_doc["count"]
        
        # Average resolution time (in hours)
        resolution_pipeline = [
            {"$match": {"guild_id": guild_id, "closed_at": {"$exists": True}, "created_at": {"$exists": True}}},
            {"$project": {
                "resolution_time": {
                    "$divide": [
                        {"$subtract": ["$closed_at", "$created_at"]},
                        1000 * 60 * 60  # Convert to hours
                    ]
                }
            }},
            {"$group": {"_id": None, "avg_resolution_time": {"$avg": "$resolution_time"}}}
        ]
        resolution_result = await self.db.closed_tickets.aggregate(resolution_pipeline).to_list(length=1)
        avg_resolution_time = resolution_result[0]["avg_resolution_time"] if resolution_result else 0
        
        # Staff performance (tickets handled)
        staff_pipeline = [
            {"$match": {"guild_id": guild_id, "assigned_staff": {"$exists": True}}},
            {"$group": {"_id": "$assigned_staff", "tickets_handled": {"$sum": 1}}}
        ]
        staff_performance = {}
        async for staff_doc in self.db.closed_tickets.aggregate(staff_pipeline):
            staff_performance[staff_doc["_id"]] = staff_doc["tickets_handled"]
        
        return {
            "total_tickets": total_tickets,
            "active_tickets": active_count,
            "closed_tickets": closed_count,
            "average_rating": round(avg_rating, 2),
            "total_ratings": total_ratings,
            "status_breakdown": status_counts,
            "priority_breakdown": priority_counts,
            "avg_resolution_time_hours": round(avg_resolution_time, 2),
            "staff_performance": staff_performance
        }
    
    async def get_user_stats(self, guild_id: int, user_id: int) -> Dict[str, Any]:
        """Get ticket statistics for a specific user."""
        
        # User's tickets
        user_active = await self.db.active_tickets.count_documents({
            "guild_id": guild_id, 
            "user_id": user_id
        })
        
        user_closed = await self.db.closed_tickets.count_documents({
            "guild_id": guild_id,
            "user_id": user_id
        })
        
        # User's average rating given
        user_ratings = await self.db.ticket_ratings.find({
            "guild_id": guild_id,
            "user_id": user_id
        }).to_list(length=None)
        
        avg_user_rating = 0
        if user_ratings:
            avg_user_rating = sum(r["rating"] for r in user_ratings) / len(user_ratings)
        
        return {
            "active_tickets": user_active,
            "closed_tickets": user_closed,
            "total_tickets": user_active + user_closed,
            "average_rating_given": round(avg_user_rating, 2),
            "ratings_given": len(user_ratings)
        }

class TicketAutoClose:
    """Auto-close inactive tickets system."""
    
    def __init__(self, mongo_db):
        self.db = mongo_db
    
    async def check_inactive_tickets(self):
        """Check and auto-close inactive tickets."""
        logger.info("Checking for inactive tickets to auto-close...")
        
        # Get all departments with auto_close_hours set
        departments = await self.db.ticket_departments.find({
            "auto_close_hours": {"$gt": 0}
        }).to_list(length=None)
        
        closed_count = 0
        
        for dept in departments:
            department = TicketDepartment(**dept)
            
            # Find tickets older than auto_close_hours
            cutoff_time = datetime.utcnow() - timedelta(hours=department.auto_close_hours)
            
            inactive_tickets = await self.db.active_tickets.find({
                "department_id": str(department._id),
                "last_activity": {"$lt": cutoff_time},
                "status": {"$in": [TicketStatus.OPEN, TicketStatus.ASSIGNED]}
            }).to_list(length=None)
            
            for ticket in inactive_tickets:
                await self._auto_close_ticket(ticket, department)
                closed_count += 1
        
        logger.info(f"Auto-closed {closed_count} inactive tickets")
        return closed_count
    
    async def _auto_close_ticket(self, ticket: dict, department: TicketDepartment):
        """Auto-close a specific ticket."""
        try:
            # Update ticket status
            close_data = {
                "status": TicketStatus.CLOSED,
                "closed_at": datetime.utcnow(),
                "close_reason": f"Auto-closed due to inactivity ({department.auto_close_hours} hours)",
                "auto_closed": True
            }
            
            await self.db.active_tickets.update_one(
                {"_id": ticket["_id"]},
                {"$set": close_data}
            )
            
            # Move to closed tickets
            closed_ticket = ticket.copy()
            closed_ticket.update(close_data)
            await self.db.closed_tickets.insert_one(closed_ticket)
            await self.db.active_tickets.delete_one({"_id": ticket["_id"]})
            
            # Try to delete the channel
            from discord.utils import get
            # This would need bot instance access - implement in cog level
            
            logger.info(f"Auto-closed ticket {ticket.get('ticket_number', 'Unknown')} in guild {ticket['guild_id']}")
            
        except Exception as e:
            logger.error(f"Error auto-closing ticket {ticket.get('_id')}: {e}")

class TicketStatsView(discord.ui.View):
    """View for displaying ticket statistics."""
    
    def __init__(self, guild_id: int):
        super().__init__(timeout=300)
        self.guild_id = guild_id
    
    @discord.ui.button(label="📊 Guild Stats", style=discord.ButtonStyle.primary, row=0)
    async def guild_stats(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Show guild-wide ticket statistics."""
        await interaction.response.defer()
        
        mongo_db = get_async_db()
        stats = TicketStatistics(mongo_db)
        guild_stats = await stats.get_guild_stats(self.guild_id)
        
        embed = create_embed(
            title="📊 Guild Ticket Statistics",
            description="Comprehensive ticket analytics for this server",
            color=Colors.INFO
        )
        
        # Basic stats
        embed.add_field(
            name="📈 Overview",
            value=f"**Total Tickets:** {guild_stats['total_tickets']}\n"
                  f"**Active:** {guild_stats['active_tickets']}\n"
                  f"**Closed:** {guild_stats['closed_tickets']}\n"
                  f"**Avg Rating:** {guild_stats['average_rating']}/5 ({guild_stats['total_ratings']} ratings)",
            inline=True
        )
        
        # Status breakdown
        status_text = ""
        for status, count in guild_stats['status_breakdown'].items():
            status_text += f"**{status.title()}:** {count}\n"
        
        if status_text:
            embed.add_field(name="📋 By Status", value=status_text, inline=True)
        
        # Priority breakdown
        priority_text = ""
        for priority, count in guild_stats['priority_breakdown'].items():
            emoji = TicketPriority.EMOJIS.get(priority, "🔵")
            priority_text += f"{emoji} **{priority.title()}:** {count}\n"
        
        if priority_text:
            embed.add_field(name="⚡ By Priority", value=priority_text, inline=True)
        
        # Performance metrics
        embed.add_field(
            name="⚡ Performance",
            value=f"**Avg Resolution Time:** {guild_stats['avg_resolution_time_hours']:.1f} hours",
            inline=False
        )
        
        # Top staff performance
        if guild_stats['staff_performance']:
            staff_list = sorted(
                guild_stats['staff_performance'].items(),
                key=lambda x: x[1],
                reverse=True
            )[:5]  # Top 5
            
            staff_text = ""
            for staff_id, count in staff_list:
                member = interaction.guild.get_member(staff_id)
                name = member.display_name if member else f"User {staff_id}"
                staff_text += f"**{name}:** {count} tickets\n"
            
            if staff_text:
                embed.add_field(name="🏆 Top Staff", value=staff_text, inline=False)
        
        await interaction.followup.send(embed=embed)
    
    @discord.ui.button(label="👤 My Stats", style=discord.ButtonStyle.secondary, row=0)
    async def user_stats(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Show user's personal ticket statistics."""
        await interaction.response.defer()
        
        mongo_db = get_async_db()
        stats = TicketStatistics(mongo_db)
        user_stats = await stats.get_user_stats(self.guild_id, interaction.user.id)
        
        embed = create_embed(
            title=f"👤 {interaction.user.display_name}'s Ticket Stats",
            description="Your personal ticket statistics",
            color=Colors.INFO
        )
        
        embed.add_field(
            name="📊 Your Tickets",
            value=f"**Total:** {user_stats['total_tickets']}\n"
                  f"**Active:** {user_stats['active_tickets']}\n"
                  f"**Closed:** {user_stats['closed_tickets']}\n"
                  f"**Avg Rating Given:** {user_stats['average_rating_given']}/5",
            inline=False
        )
        
        await interaction.followup.send(embed=embed, ephemeral=True)
    
    @discord.ui.button(label="🔄 Auto-Close Check", style=discord.ButtonStyle.secondary, row=1)
    async def check_auto_close(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Manually trigger auto-close check."""
        # Check permissions
        if not any(role.permissions.manage_guild for role in interaction.user.roles):
            await interaction.response.send_message(
                "You need 'Manage Server' permission to run this check.",
                ephemeral=True
            )
            return
        
        await interaction.response.defer()
        
        mongo_db = get_async_db()
        auto_close = TicketAutoClose(mongo_db)
        closed_count = await auto_close.check_inactive_tickets()
        
        embed = success_embed(
            f"Auto-close check completed. {closed_count} inactive tickets were closed.",
            title="🔄 Auto-Close Check"
        )
        
        await interaction.followup.send(embed=embed)

# Add utility functions for ticket management
async def update_ticket_activity(channel_id: int):
    """Update last activity time for a ticket."""
    mongo_db = get_async_db()
    await mongo_db.active_tickets.update_one(
        {"channel_id": channel_id},
        {"$set": {"last_activity": datetime.utcnow()}}
    )

async def increment_ticket_messages(channel_id: int):
    """Increment message count for a ticket."""
    mongo_db = get_async_db()
    await mongo_db.active_tickets.update_one(
        {"channel_id": channel_id},
        {"$inc": {"messages_count": 1}}
    ) 
