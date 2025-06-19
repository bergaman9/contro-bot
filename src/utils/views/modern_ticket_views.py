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

class ModernTicketFormModal(discord.ui.Modal, title="Create Support Ticket"):
    """Dynamic modal for ticket creation with custom form questions."""
    
    def __init__(self, bot, guild_id: int, questions: List[Dict[str, Any]]):
        super().__init__()
        self.bot = bot
        self.guild_id = guild_id
        self.questions = questions
        self.db = db_manager.get_database()
        
        # Add form questions to modal (Discord allows max 5 components)
        for i, question in enumerate(questions[:5]):
            style = discord.TextStyle.paragraph if question.get('type') == 'paragraph' else discord.TextStyle.short
            
            text_input = discord.ui.TextInput(
                label=question.get('question', f'Question {i+1}'),
                placeholder=question.get('placeholder', ''),
                style=style,
                required=question.get('required', True),
                max_length=1000 if style == discord.TextStyle.paragraph else 200
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
        
        # Get category
        category_id = settings.get('category_id')
        if not category_id:
            await interaction.followup.send(
                embed=error_embed("Ticket category not configured.", title="❌ Not Configured"),
                ephemeral=True
            )
            return
        
        category = interaction.guild.get_channel(int(category_id))
        if not category:
            await interaction.followup.send(
                embed=error_embed("Ticket category not found.", title="❌ Category Missing"),
                ephemeral=True
            )
            return
        
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
            
            # Add support roles
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
            
            # Create channel
            ticket_channel = await interaction.guild.create_text_channel(
                name=channel_name[:100],  # Discord limit
                category=category,
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
                "form_answers": {}
            }
            
            # Store form answers
            for i, child in enumerate(self.children):
                if isinstance(child, discord.ui.TextInput) and i < len(self.questions):
                    question = self.questions[i]
                    ticket_data["form_answers"][question.get('question', f'Question {i+1}')] = child.value
            
            result = await self.db.active_tickets.insert_one(ticket_data)
            
            # Create the main ticket embed (like in the image)
            await self._send_ticket_embed(ticket_channel, interaction, ticket_number, ticket_data)
            
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
    
    async def _send_ticket_embed(self, channel, interaction, ticket_number, ticket_data):
        """Send the main ticket embed like in the image."""
        # Check ticket settings for level card option and colors
        settings = await self.db.ticket_settings.find_one({"guild_id": self.guild_id}) or {}
        show_level_card = settings.get('show_level_card', True)  # Default enabled
        
        # Get user's level data for color scheme
        user_level = 0
        level_card_file = None
        userdata = None
        
        if show_level_card:
            try:
                # Import here to avoid circular imports
                from ...utils.community.turkoyto.card_renderer import create_level_card, get_level_scheme
                from ...utils.community.turkoyto.xp_manager import XPManager
                
                # Get database connection and initialize XP manager
                mongo_db = db_manager.get_database()
                xp_manager = XPManager(mongo_db)
                
                # Get user's level data using prepare_level_card_data
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
        
        # Get embed color - use custom color or level-based color
        embed_color = settings.get('embed_color')
        if not embed_color and user_level > 0:
            try:
                from ...utils.community.turkoyto.card_renderer import get_level_scheme, scheme_to_discord_color
                scheme = get_level_scheme(user_level)
                embed_color = scheme_to_discord_color(scheme)
            except:
                embed_color = Colors.INFO
        else:
            embed_color = embed_color or Colors.INFO
        
        # Main ticket embed
        embed = discord.Embed(
            description="Destek talebiniz oluşturuldu. Ekibimiz en kısa sürede sizinle iletişime geçecektir.",
            color=embed_color,
            timestamp=datetime.utcnow()
        )
        
        # Set author with user's name and ticket number
        embed.set_author(
            name=f"{interaction.user.display_name} - Ticket #{ticket_number}",
            icon_url=interaction.user.display_avatar.url
        )
        
        # Add user info with inline=True
        embed.add_field(
            name="Talepte bulunan kişi",
            value=f"{interaction.user.mention}",
            inline=True
        )
        
        embed.add_field(
            name="ID",
            value=str(interaction.user.id),
            inline=True
        )
        
        embed.add_field(
            name="Ticket sayısı",
            value=str(ticket_number),
            inline=True
        )
        
        # Add form answers with inline=True
        form_answers = ticket_data.get("form_answers", {})
        
        if form_answers:
            for question, answer in form_answers.items():
                # Limit answer length to fit in inline fields
                display_answer = f"```\n{answer[:200]}{'...' if len(answer) > 200 else ''}\n```"
                
                embed.add_field(
                    name=f"📝 {question}",
                    value=display_answer,
                    inline=True
                )
        
        # Add level card image if available
        if level_card_file:
            embed.set_image(url="attachment://level_card.png")
        
        # Create ticket control view (persistent)
        control_view = TicketControlView(ticket_number, interaction.user.id, channel.id)
        
        # Send main embed with level card if available
        if level_card_file:
            await channel.send(embed=embed, file=level_card_file, view=control_view)
        else:
            await channel.send(embed=embed, view=control_view)
    
    async def _get_user_level_info(self, user_id: int) -> Dict[str, Any]:
        """Get user's level information."""
        try:
            member_data = await self.db.members.find_one({
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
                "question": "Konunuz nedir?",
                "type": "short",
                "placeholder": "Ticket konunuzu kısaca açıklayın",
                "required": True,
                "order": 1
            },
            {
                "guild_id": self.guild_id,
                "question": "İletişim bilgileriniz",
                "type": "short", 
                "placeholder": "Discord kullanıcı adınız veya email",
                "required": True,
                "order": 2
            },
            {
                "guild_id": self.guild_id,
                "question": "Detaylı açıklama",
                "type": "paragraph",
                "placeholder": "Sorununuzu detaylı olarak açıklayın...",
                "required": True,
                "order": 3
            }
        ]
        
        await self.db.ticket_form_questions.insert_many(default_questions)

class TicketControlView(discord.ui.View):
    """Control view for ticket management - PERSISTENT."""
    
    def __init__(self, ticket_number: int, creator_id: int, channel_id: int):
        super().__init__(timeout=None)  # Persistent view
        self.ticket_number = ticket_number
        self.creator_id = creator_id
        self.channel_id = channel_id
    
    @discord.ui.button(
        label="Talebi Kapat",
        style=discord.ButtonStyle.danger,
        emoji="🔒",
        custom_id="ticket_close"
    )
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
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
            "Bu ticket'ı kapatmak istediğinizden emin misiniz?",
            title="🔒 Ticket Kapatma"
        )
        
        await interaction.response.send_message(embed=embed, view=close_view, ephemeral=True)

class TicketCloseConfirmView(discord.ui.View):
    """Confirmation view for closing tickets."""
    
    def __init__(self, ticket_id):
        super().__init__(timeout=60)
        self.ticket_id = ticket_id
    
    @discord.ui.button(
        label="Evet, Kapat", 
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
            f"Ticket {interaction.user.mention} tarafından kapatıldı.\nKanal 5 saniye içinde silinecek.",
            title="🔒 Ticket Kapatıldı"
        )
        
        await interaction.response.edit_message(embed=embed, view=None)
        await interaction.channel.send(embed=embed)
        
        # Wait and delete channel
        await asyncio.sleep(5)
        try:
            await interaction.channel.delete(reason=f"Ticket closed by {interaction.user}")
        except:
            pass
    
    @discord.ui.button(
        label="İptal", 
        style=discord.ButtonStyle.secondary, 
        emoji="❌"
    )
    async def cancel_close(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Cancel ticket closure."""
        embed = info_embed("Ticket kapatma işlemi iptal edildi.", title="İptal")
        await interaction.response.edit_message(embed=embed, view=None) 