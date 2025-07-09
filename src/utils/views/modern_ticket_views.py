"""
Modern ticket system views and modals
"""
import discord
from discord.ext import commands
import asyncio
from datetime import datetime
from typing import List, Dict, Any

from ..core.formatting import create_embed
from ..database.db_manager import db_manager
from ..common import error_embed, success_embed, info_embed, warning_embed
from ...bot.constants import Colors
from ...utils.community.generic.card_renderer import create_level_card, get_level_scheme
from ...utils.community.generic.xp_manager import XPManager

class ModernTicketFormModal(discord.ui.Modal, title="Create Support Ticket"):
    """Dynamic modal for ticket creation with custom form questions."""
    
    def __init__(self, bot, guild_id: int, questions: List[Dict[str, Any]], department: Dict[str, Any] = None):
        super().__init__()
        self.bot = bot
        self.guild_id = guild_id
        self.questions = questions
        self.department = department
        self.db = db_manager.get_database()
        
        # Update modal title if department is provided
        if department:
            self.title = f"{department.get('emoji', '🎫')} {department.get('name', 'Support')} Ticket"
        
        # Add form questions to modal (Discord allows max 5 components)
        for i, question in enumerate(questions[:5]):
            # Field type mapping
            qtype = question.get('type', 'short')
            style = discord.TextStyle.paragraph if qtype in ['paragraph', 'textarea'] else discord.TextStyle.short
            
            text_input = discord.ui.TextInput(
                label=question.get('label') or question.get('question', f'Question {i+1}'),
                placeholder=question.get('placeholder', ''),
                style=style,
                required=question.get('required', True),
                max_length=question.get('max_length', 1000 if style == discord.TextStyle.paragraph else 200)
            )
            
            self.add_item(text_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle form submission and create ticket."""
        await interaction.response.defer(ephemeral=True)
        
        # Get ticket settings
        settings = await self.db.ticket_settings.find_one({"guild_id": self.guild_id}) or {"enabled": True}
        
        if not settings.get('enabled', True):  # Default to enabled if not set
            await interaction.followup.send(
                embed=error_embed("Ticket system is disabled.", title="❌ System Disabled"),
                ephemeral=True
            )
            return
        
        # Get category - check department open_category_id first, then category_id, then global
        category_id = None
        category = None
        
        if self.department:
            if self.department.get('open_category_id'):
                category_id = self.department.get('open_category_id')
            elif self.department.get('category_id'):
                category_id = self.department.get('category_id')
        
        if not category_id:
            category_id = settings.get('category_id')
        
        # If category_id exists, try to get the category
        if category_id:
            category = interaction.guild.get_channel(int(category_id))
            if not category:
                # Category ID exists but channel not found - log warning but continue without category
                print(f"Warning: Category ID {category_id} not found in guild {interaction.guild.id}")
                category = None
        
        # If no category found, ticket will be created without category (in main server directory)
        # This is the desired behavior - no new category creation
        
        try:
            # Get next ticket number
            ticket_number = await self._get_next_ticket_number()
            
            # Create ticket channel
            channel_name = f"ticket-{ticket_number}-{interaction.user.display_name.lower()}"
            
            # Set permissions
            overwrites = {
                interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                interaction.user: discord.PermissionOverwrite(
                    read_messages=True,
                    send_messages=True,
                    attach_files=True,
                    embed_links=True
                )
            }
            
            # Add support roles - check department specific first, then global
            support_roles = []
            if self.department and self.department.get('staff_roles'):
                support_roles = self.department.get('staff_roles', [])
            else:
                support_roles = settings.get('support_roles', [])
            
            for role_id in support_roles:
                role = interaction.guild.get_role(role_id)
                if role:
                    overwrites[role] = discord.PermissionOverwrite(
                        read_messages=True,
                        send_messages=True,
                        attach_files=True,
                        embed_links=True,
                        manage_messages=True
                    )
            
            # Create channel - category can be None (no category)
            ticket_channel = await interaction.guild.create_text_channel(
                name=channel_name[:100],  # Discord limit
                category=category,  # This can be None - ticket will be created without category
                overwrites=overwrites,
                topic=f"Support ticket #{ticket_number} for {interaction.user}"
            )
            
            # Save ticket to database
            ticket_data = {
                "guild_id": self.guild_id,
                "channel_id": ticket_channel.id,
                "user_id": interaction.user.id,
                "ticket_number": ticket_number,
                "created_at": datetime.utcnow(),
                "status": "open",
                "form_answers": {},
                "department_id": self.department.get('id') if self.department else None,
                "department_name": self.department.get('name') if self.department else 'General Support'
            }
            
            # Store form answers
            for i, child in enumerate(self.children):
                if isinstance(child, discord.ui.TextInput) and i < len(self.questions):
                    question = self.questions[i]
                    ticket_data["form_answers"][question.get('question', f'Question {i+1}')] = child.value
            
            await self.db.active_tickets.insert_one(ticket_data)
            
            # Create the main ticket embed (like in the image)
            await self._send_ticket_embed(ticket_channel, interaction, ticket_number, ticket_data, settings)
            
            # Confirm to user
            await interaction.followup.send(
                embed=success_embed(
                    f"Your ticket #{ticket_number} has been created: {ticket_channel.mention}",
                    title="✅ Ticket Created"
                ),
                ephemeral=True
            )
            
        except discord.Forbidden:
            await interaction.followup.send(
                embed=error_embed("I don't have permission to create ticket channels.", title="❌ Permission Error"),
                ephemeral=True
            )
        except Exception as e:
            await interaction.followup.send(
                embed=error_embed(f"An error occurred: {str(e)}", title="❌ Error"),
                ephemeral=True
            )
    
    async def _get_next_ticket_number(self) -> int:
        """Get the next ticket number for this guild."""
        # Get highest ticket number from active tickets
        last_active = await self.db.active_tickets.find_one(
            {"guild_id": self.guild_id},
            sort=[("ticket_number", -1)]
        )
        
        # Get highest ticket number from closed tickets
        last_closed = await self.db.closed_tickets.find_one(
            {"guild_id": self.guild_id},
            sort=[("ticket_number", -1)]
        )
        
        active_num = last_active.get("ticket_number", 0) if last_active else 0
        closed_num = last_closed.get("ticket_number", 0) if last_closed else 0
        
        return max(active_num, closed_num) + 1
    
    async def _send_ticket_embed(self, channel, interaction, ticket_number, ticket_data, settings):
        """Send the main ticket embed like in the image."""
        # Level kartı gösterme kontrolü
        show_level_card = True
        if self.department and isinstance(self.department, dict):
            show_level_card = self.department.get('show_level_card', True)
        
        user_level = 0
        level_card_file = None
        userdata = None
        
        # 1. Embed kaynağını belirle
        embed_json = None
        if self.department and self.department.get('ticket_embed'):
            embed_json = self.department['ticket_embed']
        elif settings.get('default_ticket_embed'):
            embed_json = settings['default_ticket_embed']
        
        # 2. Embed'i oluştur
        if embed_json:
            embed = json_to_discord_embed(embed_json)
        else:
            # Fallback: eski koddaki gibi embed oluştur
            embed_color = settings.get('embed_color') or Colors.INFO
            welcome_message = self.department.get('welcome_message') if self.department and self.department.get('welcome_message') else "Your support request has been created. Our team will contact you as soon as possible."
            embed = discord.Embed(
                description=welcome_message,
                color=embed_color,
                timestamp=datetime.utcnow()
            )
            embed.set_author(
                name=f"{interaction.user.display_name} - Ticket #{ticket_number}",
                icon_url=interaction.user.display_avatar.url
            )
        
        # 3. Ticket info ve form cevaplarını embed'e ekle
        embed.add_field(
            name="👤 User",
            value=f"{interaction.user.mention}",
            inline=True
        )
        embed.add_field(
            name="🎫 Ticket",
            value=f"#{ticket_number}",
            inline=True
        )
        if self.department:
            embed.add_field(
                name="🏢 Department",
                value=f"{self.department.get('emoji', '🎫')} {self.department.get('name', 'General Support')}",
                inline=True
            )
        else:
            embed.add_field(
                name="🏢 Department",
                value="🎫 General Support",
                inline=True
            )
        form_answers = ticket_data.get("form_answers", {})
        if form_answers:
            for question, answer in form_answers.items():
                display_answer = f"```\n{answer[:200]}{'...' if len(answer) > 200 else ''}\n```"
                embed.add_field(
                    name=f"📝 {question}",
                    value=display_answer,
                    inline=True
                )
        
        # Add level card image if available
        if show_level_card:
            try:
                mongo_db = db_manager.get_database()
                xp_manager = XPManager(mongo_db)
                userdata = await xp_manager.prepare_level_card_data(interaction.user, interaction.guild)
                
                if userdata:
                    user_level = userdata.get('level', 0)
                    
                    # Create level card
                    card_path = await create_level_card(
                        self.bot, 
                        interaction.user, 
                        userdata, 
                        interaction.guild
                    )
                    
                    if card_path:
                        level_card_file = discord.File(card_path, filename="level_card.png")
            except Exception as e:
                # If level card creation fails, just continue without it
                print(f"Level card creation failed: {e}")
        
        # Create ticket control view (persistent)
        control_view = TicketControlView(ticket_number, interaction.user.id, channel.id)
        
        # Send main embed with level card if available
        try:
            if level_card_file:
                await channel.send(embed=embed, file=level_card_file, view=control_view)
            else:
                await channel.send(embed=embed, view=control_view)
        except Exception as send_err:
            print(f"[ERROR] Ticket embed gönderilemedi: {send_err}")
            # Fallback: dosyasız sadece embed gönder
            try:
                await channel.send(embed=embed, view=control_view)
            except Exception as fallback_err:
                print(f"[ERROR] Fallback embed gönderimi de başarısız: {fallback_err}")
    
    async def _get_user_level_info(self, user_id: int) -> Dict[str, Any]:
        """Get user's level information."""
        try:
            member_data = self.db.members.find_one({
                "guild_id": self.guild_id,
                "user_id": user_id
            })
            return member_data if member_data else None
        except:
            return None
    
    def _calculate_xp_for_level(self, level: int) -> int:
        """Calculate XP required for a specific level."""
        if level <= 0:
            return 0
        return level * 1000  # Simple formula: 1000 XP per level
    
    def _create_progress_bar(self, current: int, total: int, length: int = 20) -> str:
        """Create a text-based progress bar."""
        if total <= 0:
            return "▓" * length
        
        filled = int((current / total) * length)
        filled = max(0, min(filled, length))
        
        bar = "▓" * filled + "░" * (length - filled)
        return bar
    
    async def _create_default_questions(self):
        """Create default form questions if none exist."""
        default_questions = [
            {
                "guild_id": self.guild_id,
                "question": "What is your issue about?",
                "type": "short",
                "placeholder": "Briefly describe your ticket subject",
                "required": True,
                "order": 1
            },
            {
                "guild_id": self.guild_id,
                "question": "Your contact information",
                "type": "short", 
                "placeholder": "Your Discord username or email",
                "required": True,
                "order": 2
            },
            {
                "guild_id": self.guild_id,
                "question": "Detailed description",
                "type": "paragraph",
                "placeholder": "Please describe your issue in detail...",
                "required": True,
                "order": 3
            }
        ]
        
        self.db.ticket_form_questions.insert_many(default_questions)

class TicketControlView(discord.ui.View):
    """Control view for ticket management - PERSISTENT."""
    
    def __init__(self, ticket_number: int, creator_id: int, channel_id: int):
        super().__init__(timeout=None)  # Persistent view
        self.ticket_number = ticket_number
        self.creator_id = creator_id
        self.channel_id = channel_id
        
        # Create close button with unique custom_id
        close_button = discord.ui.Button(
            label="Close Ticket",
            style=discord.ButtonStyle.danger,
            emoji="🔒",
            custom_id=f"ticket_close_{ticket_number}"
        )
        close_button.callback = self.close_ticket_callback
        self.add_item(close_button)
    
    async def close_ticket_callback(self, interaction: discord.Interaction):
        """Close the ticket."""
        db = db_manager.get_database()
        
        # Check if user has permission
        ticket = await db.active_tickets.find_one({"channel_id": interaction.channel.id})
        if not ticket:
            await interaction.response.send_message("Bu kanal geçerli bir ticket değil.", ephemeral=True)
            return
        
        # Check permission (ticket creator or staff)
        settings = await db.ticket_settings.find_one({"guild_id": interaction.guild.id})
        support_roles = settings.get('support_roles', []) if settings else []
        
        is_staff = any(role.id in support_roles for role in interaction.user.roles)
        is_creator = ticket.get('user_id') == interaction.user.id
        
        if not (is_staff or is_creator):
            await interaction.response.send_message("Bu ticket'ı kapatma yetkiniz yok.", ephemeral=True)
            return
        
        # Show close confirmation
        close_view = TicketCloseConfirmView(ticket["_id"])
        embed = warning_embed(
            "Are you sure you want to close this ticket?",
            title="🔒 Close Ticket"
        )
        
        await interaction.response.send_message(embed=embed, view=close_view, ephemeral=True)

class TicketCloseConfirmView(discord.ui.View):
    """Confirmation view for closing tickets."""
    
    def __init__(self, ticket_id):
        super().__init__(timeout=60)
        self.ticket_id = ticket_id
    
    @discord.ui.button(
        label="Yes, Close", 
        style=discord.ButtonStyle.danger, 
        emoji="✅"
    )
    async def confirm_close(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Confirm ticket closure."""
        db = db_manager.get_database()
        
        # Get ticket data
        ticket = await db.active_tickets.find_one({"_id": self.ticket_id})
        if not ticket:
            await interaction.response.send_message("Ticket bulunamadı.", ephemeral=True)
            return
        
        # Update ticket status
        close_data = {
            "status": "closed",
            "closed_at": datetime.utcnow(),
            "closed_by": interaction.user.id
        }
        
        await db.active_tickets.update_one(
            {"_id": self.ticket_id},
            {"$set": close_data}
        )
        
        # Move to closed tickets
        closed_ticket = ticket.copy()
        closed_ticket.update(close_data)
        await db.closed_tickets.insert_one(closed_ticket)
        await db.active_tickets.delete_one({"_id": self.ticket_id})
        
        # Send closing message
        embed = success_embed(
            f"Ticket closed by {interaction.user.mention}.\nThe channel will be deleted in 5 seconds.",
            title="🔒 Ticket Closed"
        )
        
        await interaction.response.edit_message(embed=embed, view=None)
        await interaction.channel.send(embed=embed)
        
        # Wait and delete channel
        await asyncio.sleep(5)
        try:
            await interaction.channel.delete(reason=f"Ticket closed by {interaction.user}")
        except:
            pass
        
        # Move channel to closed category if set
        department = None
        # Try to get department from DB using channel info
        ticket_data = await db.active_tickets.find_one({"channel_id": interaction.channel.id})
        if ticket_data and ticket_data.get("department_id"):
            department = await db.ticket_departments.find_one({"id": ticket_data["department_id"]})
        if department and department.get("closed_category_id"):
            closed_cat = interaction.guild.get_channel(int(department["closed_category_id"]))
            if closed_cat and interaction.channel.category_id != closed_cat.id:
                await interaction.channel.edit(category=closed_cat)
    
    @discord.ui.button(
        label="Cancel", 
        style=discord.ButtonStyle.secondary, 
        emoji="❌"
    )
    async def cancel_close(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Cancel ticket closure."""
        embed = info_embed("Ticket closure has been cancelled.", title="Cancelled")
        await interaction.response.edit_message(embed=embed, view=None)

# JSON embed objesini discord.Embed nesnesine çeviren yardımcı fonksiyon
def json_to_discord_embed(embed_json: dict) -> discord.Embed:
    embed = discord.Embed(
        title=embed_json.get('title', ''),
        description=embed_json.get('description', ''),
        color=int(embed_json.get('color', '#5865F2').replace('#', ''), 16) if embed_json.get('color') else Colors.INFO
    )
    for field in embed_json.get('fields', []):
        embed.add_field(
            name=field.get('name', ''),
            value=field.get('value', ''),
            inline=field.get('inline', False)
        )
    return embed 