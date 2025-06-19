"""Helper views for settings configuration."""
import discord
from discord.ext import commands
from typing import Optional, List, Dict, Any
import asyncio
from datetime import datetime

from ..core.formatting import create_embed
from ...bot.constants import Colors
from ..database.db_manager import db_manager


class WelcomeImageView(discord.ui.View):
    """View for configuring welcome/goodbye images."""
    
    def __init__(self, bot, guild_id: int):
        super().__init__(timeout=300)
        self.bot = bot
        self.guild_id = guild_id
        self.db = db_manager.get_database()
        self.settings = {}
    
    async def initialize(self):
        """Initialize the view."""
        self.settings = await self.db.welcomer.find_one({"guild_id": self.guild_id}) or {}
    
    @discord.ui.select(
        placeholder="Choose background color theme",
        options=[
            discord.SelectOption(label="Blue Theme", value="blue", emoji="🔵"),
            discord.SelectOption(label="Green Theme", value="green", emoji="🟢"),
            discord.SelectOption(label="Red Theme", value="red", emoji="🔴"),
            discord.SelectOption(label="Purple Theme", value="purple", emoji="🟣"),
            discord.SelectOption(label="Dark Theme", value="dark", emoji="⚫"),
            discord.SelectOption(label="Light Theme", value="light", emoji="⚪"),
            discord.SelectOption(label="Default", value="default", emoji="🔄"),
        ]
    )
    async def select_background(self, interaction: discord.Interaction, select: discord.ui.Select):
        """Select background theme."""
        theme = select.values[0]
        
        # Update theme in database
        await self.db.welcomer.update_one(
            {"guild_id": self.guild_id},
            {"$set": {"background_theme": theme}},
            upsert=True
        )
        
        embed = create_embed(
            title="✅ Theme Updated",
            description=f"Welcome image theme changed to **{theme.title()}**",
            color=Colors.SUCCESS
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)


class WordFilterView(discord.ui.View):
    """View for managing word filters."""
    
    def __init__(self, bot, guild_id: int):
        super().__init__(timeout=300)
        self.bot = bot
        self.guild_id = guild_id
        self.db = db_manager.get_database()
        self.filtered_words = []
    
    async def initialize(self):
        """Initialize the view."""
        automod_settings = await self.db.automod.find_one({"guild_id": self.guild_id}) or {}
        self.filtered_words = automod_settings.get('filtered_words', [])
    
    @discord.ui.button(label="➕ Add Word", style=discord.ButtonStyle.primary)
    async def add_word(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Add a word to filter."""
        modal = AddWordModal(self.bot, self.guild_id)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="➖ Remove Word", style=discord.ButtonStyle.secondary)
    async def remove_word(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Remove a word from filter."""
        if not self.filtered_words:
            embed = create_embed(
                title="ℹ️ No Words",
                description="No words are currently filtered.",
                color=Colors.INFO
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        view = RemoveWordView(self.bot, self.guild_id, self.filtered_words)
        embed = create_embed(
            title="➖ Remove Filtered Word",
            description="Select a word to remove from the filter:",
            color=Colors.INFO
        )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @discord.ui.button(label="📋 View Words", style=discord.ButtonStyle.secondary)
    async def view_words(self, interaction: discord.Interaction, button: discord.ui.Button):
        """View current filtered words."""
        if not self.filtered_words:
            embed = create_embed(
                title="📋 Filtered Words",
                description="No words are currently filtered.",
                color=Colors.INFO
            )
        else:
            words_text = "\n".join([f"• `{word}`" for word in self.filtered_words[:20]])
            if len(self.filtered_words) > 20:
                words_text += f"\n... and {len(self.filtered_words) - 20} more"
            
            embed = create_embed(
                title="📋 Filtered Words",
                description=words_text,
                color=Colors.INFO
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)


class EventLoggingView(discord.ui.View):
    """View for configuring event logging."""
    
    def __init__(self, bot, guild_id: int, logging_settings: dict):
        super().__init__(timeout=300)
        self.bot = bot
        self.guild_id = guild_id
        self.logging_settings = logging_settings
        self.db = db_manager.get_database()
    
    @discord.ui.button(label="✅ Message Delete", style=discord.ButtonStyle.success, row=0)
    async def toggle_message_delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Toggle message delete logging."""
        await self.toggle_event(interaction, "message_delete", button)
    
    @discord.ui.button(label="✅ Message Edit", style=discord.ButtonStyle.success, row=0)
    async def toggle_message_edit(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Toggle message edit logging."""
        await self.toggle_event(interaction, "message_edit", button)
    
    @discord.ui.button(label="✅ Member Join", style=discord.ButtonStyle.success, row=1)
    async def toggle_member_join(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Toggle member join logging."""
        await self.toggle_event(interaction, "member_join", button)
    
    @discord.ui.button(label="✅ Member Leave", style=discord.ButtonStyle.success, row=1)
    async def toggle_member_leave(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Toggle member leave logging."""
        await self.toggle_event(interaction, "member_leave", button)
    
    @discord.ui.button(label="✅ Voice State", style=discord.ButtonStyle.success, row=2)
    async def toggle_voice_state(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Toggle voice state logging."""
        await self.toggle_event(interaction, "voice_state", button)
    
    async def toggle_event(self, interaction: discord.Interaction, event_name: str, button: discord.ui.Button):
        """Toggle an event logging setting."""
        current_state = self.logging_settings.get(f'{event_name}_enabled', False)
        new_state = not current_state
        
        # Update in database
        await self.db.server_settings.update_one(
            {"server_id": self.guild_id},
            {"$set": {f"logging.{event_name}_enabled": new_state}},
            upsert=True
        )
        
        # Update button appearance
        if new_state:
            button.style = discord.ButtonStyle.success
            button.label = f"✅ {event_name.replace('_', ' ').title()}"
        else:
            button.style = discord.ButtonStyle.secondary
            button.label = f"❌ {event_name.replace('_', ' ').title()}"
        
        self.logging_settings[f'{event_name}_enabled'] = new_state
        
        embed = create_embed(
            title="✅ Event Logging Updated",
            description=f"{event_name.replace('_', ' ').title()} logging {'enabled' if new_state else 'disabled'}",
            color=Colors.SUCCESS
        )
        
        await interaction.response.edit_message(view=self, embed=embed)


class LogChannelSelect(discord.ui.ChannelSelect):
    def __init__(self, db, guild_id: int):
        self.db = db
        self.guild_id = guild_id
        super().__init__(
            channel_types=[discord.ChannelType.text],
            placeholder="Select a channel for logging"
        )
    
    async def callback(self, interaction: discord.Interaction):
        channel = self.values[0]
        
        await self.db.server_settings.update_one(
            {"server_id": self.guild_id},
            {"$set": {"logging.channel_id": channel.id}},
            upsert=True
        )
        
        embed = create_embed(
            title="✅ Log Channel Set",
            description=f"Log channel set to {channel.mention}",
            color=Colors.SUCCESS
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)


class LogChannelSelectView(discord.ui.View):
    """View for selecting log channel."""
    
    def __init__(self, bot, guild_id: int):
        super().__init__(timeout=300)
        self.bot = bot
        self.guild_id = guild_id
        self.db = db_manager.get_database()
        self.add_item(LogChannelSelect(self.db, self.guild_id))


class TicketPanelView(discord.ui.View):
    """View for creating ticket panel."""
    
    def __init__(self, bot, guild_id: int):
        super().__init__(timeout=300)
        self.bot = bot
        self.guild_id = guild_id
        self.db = db_manager.get_database()
    
    @discord.ui.button(label="🎨 Create Panel", style=discord.ButtonStyle.primary)
    async def create_panel(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Create ticket panel in current channel."""
        settings = await self.db.ticket_settings.find_one({"guild_id": self.guild_id}) or {}
        
        title = settings.get('panel_title', '🎫 Support Tickets')
        description = settings.get('panel_description', 'Click the button below to create a support ticket.')
        
        embed = create_embed(
            title=title,
            description=description,
            color=Colors.INFO
        )
        
        # Create persistent ticket button view
        ticket_view = TicketCreateView()
        
        await interaction.response.send_message(embed=embed, view=ticket_view)


class LevelRolesView(discord.ui.View):
    """View for managing level roles."""
    
    def __init__(self, bot, guild_id: int):
        super().__init__(timeout=300)
        self.bot = bot
        self.guild_id = guild_id
        self.db = db_manager.get_database()
        self.level_roles = []
    
    async def initialize(self):
        """Initialize the view."""
        level_roles_data = await self.db.level_roles.find({"guild_id": self.guild_id}).to_list(None)
        self.level_roles = level_roles_data or []
    
    @discord.ui.button(label="➕ Add Level Role", style=discord.ButtonStyle.primary)
    async def add_level_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Add a new level role."""
        modal = AddLevelRoleModal(self.bot, self.guild_id)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="📋 View Level Roles", style=discord.ButtonStyle.secondary)
    async def view_level_roles(self, interaction: discord.Interaction, button: discord.ui.Button):
        """View current level roles."""
        if not self.level_roles:
            embed = create_embed(
                title="📋 Level Roles",
                description="No level roles configured.",
                color=Colors.INFO
            )
        else:
            roles_text = []
            for role_data in self.level_roles[:10]:
                level = role_data.get('level', 0)
                role_id = role_data.get('role_id')
                if role_id:
                    roles_text.append(f"Level {level}: <@&{role_id}>")
            
            embed = create_embed(
                title="📋 Level Roles",
                description="\n".join(roles_text) if roles_text else "No valid level roles found.",
                color=Colors.INFO
            )
            
            if len(self.level_roles) > 10:
                embed.set_footer(text=f"Showing 10 of {len(self.level_roles)} level roles")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)


class AutoRoleSelect(discord.ui.RoleSelect):
    def __init__(self, db, guild_id):
        self.db = db
        self.guild_id = guild_id
        super().__init__(placeholder="Select roles to auto-assign to new members", max_values=5)

    async def callback(self, interaction: discord.Interaction):
        selected_roles = self.values
        
        await self.db.auto_roles.delete_many({"guild_id": self.guild_id})
        
        if selected_roles:
            await self.db.auto_roles.insert_many([{
                "guild_id": self.guild_id,
                "role_id": role.id,
                "created_at": datetime.utcnow()
            } for role in selected_roles])
        
        role_mentions = [role.mention for role in selected_roles]
        embed = create_embed(
            title="✅ Auto Roles Updated",
            description=f"Auto roles set to: {', '.join(role_mentions) if role_mentions else 'None'}",
            color=Colors.SUCCESS
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)


class AutoRolesView(discord.ui.View):
    """View for managing auto roles."""
    
    def __init__(self, bot, guild_id: int):
        super().__init__(timeout=300)
        self.bot = bot
        self.guild_id = guild_id
        self.db = db_manager.get_database()
        self.auto_roles = []
        self.add_item(AutoRoleSelect(self.db, self.guild_id))
    
    async def initialize(self):
        """Initialize the view."""
        self.auto_roles = await self.db.auto_roles.find({"guild_id": self.guild_id}).to_list(None) or []


class ReactionRolesView(discord.ui.View):
    """View for managing reaction roles."""
    
    def __init__(self, bot, guild_id: int):
        super().__init__(timeout=300)
        self.bot = bot
        self.guild_id = guild_id
        self.db = db_manager.get_database()
    
    async def initialize(self):
        """Initialize the view."""
        pass
    
    @discord.ui.button(label="➕ Create Reaction Role", style=discord.ButtonStyle.primary)
    async def create_reaction_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Create a new reaction role setup."""
        modal = ReactionRoleModal(self.bot, self.guild_id)
        await interaction.response.send_modal(modal)


class RoleMenusView(discord.ui.View):
    """View for managing role menus."""
    
    def __init__(self, bot, guild_id: int):
        super().__init__(timeout=300)
        self.bot = bot
        self.guild_id = guild_id
        self.db = db_manager.get_database()
    
    async def initialize(self):
        """Initialize the view."""
        pass
    
    @discord.ui.button(label="🎭 Create Role Menu", style=discord.ButtonStyle.primary)
    async def create_role_menu(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Create a new role menu."""
        modal = RoleMenuModal(self.bot, self.guild_id)
        await interaction.response.send_modal(modal)


class StatusRoleSelect(discord.ui.RoleSelect):
    def __init__(self, db, guild_id):
        self.db = db
        self.guild_id = guild_id
        super().__init__(placeholder="Select status role")

    async def callback(self, interaction: discord.Interaction):
        role = self.values[0]
        
        await self.db.settings.update_one(
            {"guild_id": self.guild_id},
            {"$set": {"status_role_id": role.id}},
            upsert=True
        )
        
        embed = create_embed(
            title="✅ Status Role Set",
            description=f"Status role set to {role.mention}",
            color=Colors.SUCCESS
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)


class StatusRoleView(discord.ui.View):
    """View for configuring status role."""
    
    def __init__(self, bot, guild_id: int):
        super().__init__(timeout=300)
        self.bot = bot
        self.guild_id = guild_id
        self.db = db_manager.get_database()
        self.add_item(StatusRoleSelect(self.db, self.guild_id))


# Persistent ticket creation view
class TicketCreateView(discord.ui.View):
    """Persistent view for creating tickets."""
    
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label="🎫 Create Ticket", style=discord.ButtonStyle.primary, custom_id="create_ticket")
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Create a new ticket."""
        # This would be implemented in the ticket system
        embed = create_embed(
            title="🎫 Ticket Creation",
            description="Ticket system is being set up...",
            color=Colors.INFO
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


# Modal classes for helper views
class AddWordModal(discord.ui.Modal, title="Add Filtered Word"):
    """Modal for adding a word to filter."""
    
    word = discord.ui.TextInput(
        label="Word to Filter",
        placeholder="Enter the word or phrase to filter",
        max_length=100,
        required=True
    )
    
    def __init__(self, bot, guild_id: int):
        super().__init__()
        self.bot = bot
        self.guild_id = guild_id
        self.db = db_manager.get_database()
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle word addition."""
        new_word = self.word.value.strip().lower()
        
        # Add word to filter list
        await self.db.automod.update_one(
            {"guild_id": self.guild_id},
            {"$addToSet": {"filtered_words": new_word}},
            upsert=True
        )
        
        embed = create_embed(
            title="✅ Word Added",
            description=f"Added `{new_word}` to the word filter.",
            color=Colors.SUCCESS
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)


class AddLevelRoleModal(discord.ui.Modal, title="Add Level Role"):
    """Modal for adding a level role."""
    
    level = discord.ui.TextInput(
        label="Level",
        placeholder="Level number (e.g., 10)",
        max_length=3,
        required=True
    )
    
    def __init__(self, bot, guild_id: int):
        super().__init__()
        self.bot = bot
        self.guild_id = guild_id
        self.db = db_manager.get_database()
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle level role addition."""
        try:
            level_num = int(self.level.value)
            if level_num < 1 or level_num > 999:
                raise ValueError("Level must be between 1 and 999")
            
            # This would open a role selection view
            embed = create_embed(
                title="🏆 Select Role",
                description=f"Now select the role for level {level_num}:",
                color=Colors.INFO
            )
            
            view = LevelRoleSelectView(self.bot, self.guild_id, level_num)
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            
        except ValueError:
            embed = create_embed(
                title="❌ Invalid Level",
                description="Please enter a valid level number (1-999).",
                color=Colors.ERROR
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)


class LevelRoleSelect(discord.ui.RoleSelect):
    def __init__(self, db, guild_id, level):
        self.db = db
        self.guild_id = guild_id
        self.level = level
        super().__init__(placeholder="Select role for this level")

    async def callback(self, interaction: discord.Interaction):
        role = self.values[0]
        
        await self.db.level_roles.update_one(
            {"guild_id": self.guild_id, "level": self.level},
            {"$set": {"role_id": role.id}},
            upsert=True
        )
        
        embed = create_embed(
            title="✅ Level Role Set",
            description=f"Role for Level {self.level} set to {role.mention}",
            color=Colors.SUCCESS
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)


class LevelRoleSelectView(discord.ui.View):
    """View for selecting a role for a specific level."""
    
    def __init__(self, bot, guild_id: int, level: int):
        super().__init__(timeout=300)
        self.bot = bot
        self.guild_id = guild_id
        self.level = level
        self.db = db_manager.get_database()
        self.add_item(LevelRoleSelect(self.db, self.guild_id, self.level))


class RemoveWordView(discord.ui.View):
    """View for removing filtered words."""
    
    def __init__(self, bot, guild_id: int, words: List[str]):
        super().__init__(timeout=300)
        self.bot = bot
        self.guild_id = guild_id
        self.db = db_manager.get_database()
        
        # Create select menu with words (limit to 25 due to Discord limit)
        options = []
        for word in words[:25]:
            # Truncate long words for display
            display_word = word[:100] if len(word) > 100 else word
            options.append(discord.SelectOption(label=display_word, value=word))
        
        # Add the select menu to the view
        self.add_item(WordSelectMenu(options, self.db, self.guild_id))


class WordSelectMenu(discord.ui.Select):
    """Select menu for choosing words to remove."""
    
    def __init__(self, options: List[discord.SelectOption], db, guild_id: int):
        super().__init__(placeholder="Select word to remove", options=options)
        self.db = db
        self.guild_id = guild_id
    
    async def callback(self, interaction: discord.Interaction):
        """Handle word selection for removal."""
        word_to_remove = self.values[0]
        
        # Remove word from filter
        await self.db.automod.update_one(
            {"guild_id": self.guild_id},
            {"$pull": {"filtered_words": word_to_remove}}
        )
        
        embed = create_embed(
            title="✅ Word Removed",
            description=f"Removed `{word_to_remove}` from the word filter.",
            color=Colors.SUCCESS
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)


class ReactionRoleModal(discord.ui.Modal, title="Create Reaction Role"):
    """Modal for creating reaction role."""
    
    emoji = discord.ui.TextInput(
        label="Emoji",
        placeholder="Enter emoji (e.g., 😀, :custom_emoji:)",
        max_length=50,
        required=True
    )
    
    message_id = discord.ui.TextInput(
        label="Message ID",
        placeholder="ID of message to add reaction to",
        max_length=20,
        required=True
    )
    
    def __init__(self, bot, guild_id: int):
        super().__init__()
        self.bot = bot
        self.guild_id = guild_id
        self.db = db_manager.get_database()
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle reaction role creation."""
        # This would implement the reaction role logic
        embed = create_embed(
            title="🎭 Reaction Role Setup",
            description="Reaction role system is being configured...",
            color=Colors.INFO
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


class RoleMenuModal(discord.ui.Modal, title="Create Role Menu"):
    """Modal for creating role menu."""
    
    title = discord.ui.TextInput(
        label="Menu Title",
        placeholder="Title for the role menu",
        max_length=100,
        required=True
    )
    
    description = discord.ui.TextInput(
        label="Menu Description",
        placeholder="Description for the role menu",
        style=discord.TextStyle.paragraph,
        max_length=500,
        required=False
    )
    
    def __init__(self, bot, guild_id: int):
        super().__init__()
        self.bot = bot
        self.guild_id = guild_id
        self.db = db_manager.get_database()
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle role menu creation."""
        # This would implement the role menu logic
        embed = create_embed(
            title="🎭 Role Menu Setup",
            description="Role menu system is being configured...",
            color=Colors.INFO
        )
        await interaction.response.send_message(embed=embed, ephemeral=True) 