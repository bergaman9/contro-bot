"""Settings views for server configuration."""
import discord
from discord.ext import commands
from typing import Optional, List, Dict, Any
import asyncio
from datetime import datetime
import logging

from ..core.formatting import create_embed
from ...bot.constants import Colors
from ..database.db_manager import db_manager
from .ticket_views import TicketDepartmentsView, DepartmentSelectView, TicketDepartment, TicketStatsView
from .modern_ticket_views import ModernTicketFormModal
from .settings_helper_views import (WelcomeImageView, WordFilterView, EventLoggingView, LogChannelSelectView)
from .age_role_views import AgeRoleConfigModal, AgeRoleSelectionView
from .gender_role_views import GenderRoleConfigView
from ..common import error_embed, success_embed, info_embed, warning_embed

# Modal classes are defined below in this file
# from .settings_modals import (
#     ServerFeaturesModal, WelcomeSettingsModal, GoodbyeSettingsModal,
#     AutoModSettingsModal, SpamProtectionModal, TicketBasicSettingsModal,
#     XPSettingsModal, StarboardSettingsModal, BirthdaySettingsModal,
#     AIChatSettingsModal, AIAutoModSettingsModal, BotSettingsModal,
#     SystemSettingsModal, TicketAdvancedSettingsModal
# )

# Configure logger
logger = logging.getLogger(__name__)


class MainSettingsView(discord.ui.View):
    """Main settings panel view."""
    
    def __init__(self, bot, guild_id: int):
        super().__init__(timeout=300)
        self.bot = bot
        self.guild_id = guild_id
    
    # Row 0: Core Features (SUCCESS - Green)
    @discord.ui.button(emoji="📝", label="Register", style=discord.ButtonStyle.success, row=0)
    async def register_system(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Open registration system settings."""
        view = RegistrationSystemView(self.bot, self.guild_id)
        await view.initialize()
        
        embed = create_embed(
        title="📝 Registration System Settings",
        description="**Core Feature:** Automated member onboarding with role assignment, age verification, and custom forms.\n"
                   "This system handles new member registration, data collection, and role management.",
        color=Colors.SUCCESS
        )
        
        # System Status (inline fields - 3 per row)
        settings_summary = view.get_settings_summary()
        
        embed.add_field(
        name="🔧 System Status",
        value=f"**Enabled:** {'🟢 Yes' if 'Enabled' in settings_summary else '🔴 No'}\n"
              f"**Method:** Button Registration\n"
              f"**Auto-assign:** Roles on register",
        inline=True
        )
        
        embed.add_field(
        name="📊 Configuration",
        value=f"**Channel:** {'Set' if 'register_channel_id' in str(view.registration_settings) else 'Not set'}\n"
              f"**Main Role:** {'Set' if view.register_settings.get('main_role_id') else 'Not set'}\n"
              f"**Verification:** {'Required' if view.registration_settings.get('age_verification_required') else 'Optional'}",
        inline=True
        )
        
        embed.add_field(
        name="🎭 Role Setup", 
        value=f"**Age Roles:** {'Configured' if view.register_settings.get('age_roles') else 'Not set'}\n"
              f"**Gender Roles:** {'Configured' if view.register_settings.get('gender_roles') else 'Not set'}\n"
              f"**Auto Roles:** {len(view.registration_settings.get('auto_roles', []))} set",
        inline=True
        )
        
        # Button Guide
        embed.add_field(
        name="🎮 Available Actions",
        value="**Row 1:** ⚙️ Basic Setup • 🎭 Role Management • 📋 Custom Forms\n"
              "**Row 2:** 🔐 Verification • 📊 Statistics & Logs • 🎨 Customization\n"
              "**Row 3:** 🛠️ Advanced Settings\n"
              "**Bottom:** ⬅️ Back to Main Settings",
        inline=False
        )
        
        embed.set_footer(text="✅ Core Feature: Essential for server management • Configure roles and verification")
        
        await interaction.response.edit_message(embed=embed, view=view)
    
    @discord.ui.button(emoji="👋", label="Welcome", style=discord.ButtonStyle.success, row=0)
    async def welcome_system(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Open welcome/goodbye settings."""
        view = WelcomeGoodbyeView(self.bot, self.guild_id)
        await view.initialize()
        
        embed = create_embed(
        title="👋 Welcome & Goodbye Settings",
        description="**Core Feature:** Automated greeting system for new and departing members.\n"
                   "Create custom welcome/goodbye messages with images and role assignments.",
        color=Colors.SUCCESS
        )
        
        # System Status (inline fields - 3 per row)
        embed.add_field(
        name="👋 Welcome System",
        value=f"**Status:** {'🟢 Active' if view.welcome_settings.get('welcome_channel_id') else '🔴 Inactive'}\n"
              f"**Channel:** {'Set' if view.welcome_settings.get('welcome_channel_id') else 'Not set'}\n"
              f"**Images:** {'Enabled' if view.welcome_settings.get('welcome_image_enabled') else 'Disabled'}",
        inline=True
        )
        
        embed.add_field(
        name="👋 Goodbye System",
        value=f"**Status:** {'🟢 Active' if view.goodbye_settings.get('channel_id') else '🔴 Inactive'}\n"
              f"**Channel:** {'Set' if view.goodbye_settings.get('channel_id') else 'Not set'}\n"
              f"**Images:** {'Enabled' if view.goodbye_settings.get('enabled') else 'Disabled'}",
        inline=True
        )
        
        embed.add_field(
        name="🎨 Customization",
        value=f"**Themes:** Multiple backgrounds\n"
              f"**Variables:** User, Guild, Mention\n"
              f"**Auto Roles:** On welcome",
        inline=True
        )
        
        # Button Guide
        embed.add_field(
        name="🎮 Available Actions",
        value="**Row 1:** 👋 Welcome Settings • 👋 Goodbye Settings\n"
              "**Row 2:** 🖼️ Image Settings (backgrounds, themes, customization)\n"
              "**Bottom:** ⬅️ Back to Main Settings",
        inline=False
        )
        
        embed.set_footer(text="✅ Core Feature: First impression matters • Create welcoming environment")
        
        await interaction.response.edit_message(embed=embed, view=view)
    
    @discord.ui.button(emoji="🎫", label="Tickets", style=discord.ButtonStyle.success, row=0)
    async def tickets(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Open ticket system settings."""
        view = TicketSystemView(self.bot, self.guild_id)
        await view.initialize()
        
        embed = create_embed(
        title="🎫 Ticket System Settings",
        description="**Core Feature:** Advanced support ticket system with categories, priorities, and automation.\n"
                   "Handle member support requests with staff assignment, transcripts, and ratings.",
        color=Colors.SUCCESS
        )
        
        # System Status (inline fields - 3 per row)
        settings_summary = view.get_settings_summary()
        
        embed.add_field(
        name="🎫 System Status",
        value=f"**Enabled:** {'🟢 Yes' if view.settings.get('enabled') else '🔴 No'}\n"
              f"**Category:** {'Set' if view.settings.get('category_id') else 'Not set'}\n"
              f"**Auto-close:** {view.settings.get('auto_close_time', 'Disabled')} hrs",
        inline=True
        )
        
        embed.add_field(
        name="👥 Staff & Access",
        value=f"**Staff Roles:** {len(view.settings.get('staff_role_ids', []))} configured\n"
              f"**Level Cards:** {'Enabled' if view.settings.get('show_level_card', True) else 'Disabled'}\n"
              f"**Transcripts:** {'Enabled' if view.settings.get('transcript_enabled', True) else 'Disabled'}",
        inline=True
        )
        
        embed.add_field(
        name="📊 Features",
        value=f"**Form Questions:** Custom fields\n"
              f"**Priority System:** Low/Normal/High/Urgent\n"
              f"**Rating System:** 5-star feedback",
        inline=True
        )
        
        # Button Guide
        embed.add_field(
        name="🎮 Available Actions",
        value="**Row 1:** 🔧 Basic Setup • 📝 Form Questions • 🎨 Send Panel\n"
              "**Row 2:** 📊 Statistics • ⚙️ Advanced Settings\n"
              "**Bottom:** ⬅️ Back to Main Settings",
        inline=False
        )
        
        embed.set_footer(text="✅ Core Feature: Professional support system • Handle member requests efficiently")
        
        await interaction.response.edit_message(embed=embed, view=view)
    
    # Row 1: Essential Features (PRIMARY - Blue)
    @discord.ui.button(emoji="📊", label="Leveling", style=discord.ButtonStyle.primary, row=1)
    async def leveling(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Open leveling settings."""
        view = LevellingSettingsView(self.bot, self.guild_id)
        await view.initialize()
        
        embed = create_embed(
        title="📊 Leveling & XP Settings",
        description="**Essential Feature:** Gamified experience system with XP tracking, level progression, and rewards.\n"
                   "Encourage member engagement through messages, voice activity, and level-based roles.",
        color=Colors.INFO
        )
        
        # System Status (inline fields - 3 per row)
        embed.add_field(
        name="📊 XP System",
        value=f"**Status:** 🟢 Active\n"
              f"**XP per Message:** 1-10 XP\n"
              f"**Voice XP:** 30 XP/minute",
        inline=True
        )
        
        embed.add_field(
        name="🏆 Level Rewards",
        value=f"**Level Roles:** {'Configured' if view.settings.get('level_roles') else 'Not set'}\n"
              f"**Notifications:** Level up alerts\n"
              f"**Leaderboard:** Server rankings",
        inline=True
        )
        
        embed.add_field(
        name="🎨 Features",
        value=f"**Rank Cards:** Custom designs\n"
              f"**Progress Bars:** Visual tracking\n"
              f"**Admin Tools:** XP management",
        inline=True
        )
        
        # Button Guide
        embed.add_field(
        name="🎮 Available Actions",
        value="**Row 1:** ⚙️ XP Settings • 🏆 Level Roles\n"
              "**Row 2:** 📊 Leaderboard Settings\n"
              "**Bottom:** ⬅️ Back to Main Settings",
        inline=False
        )
        
        embed.set_footer(text="🔵 Essential Feature: Boost engagement • Reward active members with progression")
        
        await interaction.response.edit_message(embed=embed, view=view)
    
    @discord.ui.button(emoji="📋", label="Logging", style=discord.ButtonStyle.primary, row=1)
    async def logging(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Open logging settings."""
        view = LoggingView(self.bot, self.guild_id)
        await view.initialize()
        
        embed = create_embed(
        title="📋 Event Logging & Audit System",
        description="**Essential Feature:** Comprehensive server activity tracking and audit logging.\n"
                   "Monitor member actions, message changes, and server events for security and moderation.",
        color=Colors.INFO
        )
        
        # System Status (inline fields - 3 per row)
        embed.add_field(
        name="📋 Log System",
        value=f"**Status:** {'🟢 Active' if view.logging_settings.get('channel_id') else '🔴 Inactive'}\n"
              f"**Channel:** {'Set' if view.logging_settings.get('channel_id') else 'Not set'}\n"
              f"**Auto-log:** Real-time events",
        inline=True
        )
        
        embed.add_field(
        name="📝 Event Types",
        value=f"**Messages:** Edit/Delete tracking\n"
              f"**Members:** Join/Leave logs\n"
              f"**Voice:** Channel activity",
        inline=True
        )
        
        embed.add_field(
        name="🔍 Audit Features",
        value=f"**Timestamps:** Precise timing\n"
              f"**User Details:** Full attribution\n"
              f"**Mod Actions:** Staff tracking",
        inline=True
        )
        
        # Button Guide
        embed.add_field(
        name="🎮 Available Actions",
        value="**Row 1:** 📋 Event Logging • 🎯 Log Channel\n"
              "**Bottom:** ⬅️ Back to Main Settings",
        inline=False
        )
        
        embed.set_footer(text="🔵 Essential Feature: Transparency & accountability • Track important server events")
        
        await interaction.response.edit_message(embed=embed, view=view)
    
    @discord.ui.button(emoji="⭐", label="Starboard", style=discord.ButtonStyle.primary, row=1)
    async def starboard(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Open starboard settings."""
        view = StarboardView(self.bot, self.guild_id)
        await view.initialize()
        
        embed = create_embed(
        title="⭐ Starboard & Featured Messages",
        description="**Essential Feature:** Highlight exceptional messages with community reactions.\n"
                   "Showcase popular content and create a hall of fame for your server's best moments.",
        color=Colors.INFO
        )
        
        # System Status (inline fields - 3 per row)
        embed.add_field(
        name="⭐ Starboard System",
        value=f"**Status:** {'🟢 Active' if view.settings.get('enabled', False) else '🔴 Inactive'}\n"
              f"**Channel:** {'Set' if view.settings.get('channel_id') else 'Not set'}\n"
              f"**Threshold:** {view.settings.get('threshold', 3)} ⭐ required",
        inline=True
        )
        
        embed.add_field(
        name="🎯 Configuration",
        value=f"**Star Emoji:** {view.settings.get('emoji', '⭐')}\n"
              f"**Self-star:** {'Allowed' if view.settings.get('allow_self_star', False) else 'Disabled'}\n"
              f"**Bot Messages:** {'Ignored' if view.settings.get('ignore_bots', True) else 'Included'}",
        inline=True
        )
        
        embed.add_field(
        name="📊 Analytics",
        value=f"**Featured Messages:** Track popular content\n"
              f"**Member Rankings:** Top contributors\n"
              f"**Trending Topics:** Community favorites",
        inline=True
        )
        
        # Button Guide
        embed.add_field(
        name="🎮 Available Actions",
        value="**Row 1:** ⭐ Basic Settings (threshold, channel, emoji)\n"
              "**Row 2:** 🔧 Advanced Settings (filters, permissions, automation)\n"
              "**Bottom:** ⬅️ Back to Main Settings",
        inline=False
        )
        
        embed.set_footer(text="🔵 Essential Feature: Community engagement • Highlight the best content")
        
        await interaction.response.edit_message(embed=embed, view=view)
    
    # Row 2: System Features (PRIMARY - Blue)
    @discord.ui.button(emoji="🎨", label="Roles", style=discord.ButtonStyle.primary, row=2)
    async def roles(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Open role management settings."""
        view = RoleManagementView(self.bot, self.guild_id)
        await view.initialize()
        
        embed = create_embed(
        title="🎨 Role Management & Automation",
        description="**System Feature:** Advanced role assignment and management system.\n"
                   "Automate role distribution with reaction roles, auto-roles, and dynamic role menus.",
        color=Colors.INFO
        )
        
        # System Status (inline fields - 3 per row)
        embed.add_field(
        name="🤖 Auto Roles",
        value=f"**System:** {'🟢 Active' if view.settings.get('auto_roles_enabled', False) else '🔴 Inactive'}\n"
              f"**Join Roles:** {len(view.settings.get('auto_roles', []))} configured\n"
              f"**Bot Roles:** Auto role hierarchy",
        inline=True
        )
        
        embed.add_field(
        name="⚡ Reaction Roles",
        value=f"**System:** {'🟢 Active' if view.settings.get('reaction_roles_enabled', False) else '🔴 Inactive'}\n"
              f"**Active Panels:** {len(view.settings.get('reaction_roles', []))} panels\n"
              f"**Self-assign:** User controlled",
        inline=True
        )
        
        embed.add_field(
        name="🎭 Role Menus",
        value=f"**Custom Menus:** Dynamic selection\n"
              f"**Categories:** Organized role groups\n"
              f"**Permissions:** Hierarchy protection",
        inline=True
        )
        
        # Button Guide
        embed.add_field(
        name="🎮 Available Actions",
        value="**Row 1:** 🤖 Auto Roles • ⚡ Reaction Roles\n"
              "**Row 2:** 🎭 Role Menus (custom selection panels)\n"
              "**Features:** Automated role assignment and user self-service\n"
              "**Bottom:** ⬅️ Back to Main Settings",
        inline=False
        )
        
        embed.set_footer(text="🔵 System Feature: Role automation • Streamline role management")
        
        await interaction.response.edit_message(embed=embed, view=view)
    
    @discord.ui.button(emoji="⚔️", label="Moderation", style=discord.ButtonStyle.primary, row=2)
    async def moderation(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Open moderation settings."""
        view = ModerationView(self.bot, self.guild_id)
        await view.initialize()
        
        embed = create_embed(
        title="⚔️ Moderation & AutoMod Settings",
        description="**System Feature:** Comprehensive moderation tools with AI-powered automation.\n"
                   "Protect your server with spam detection, word filtering, and intelligent moderation.",
        color=Colors.INFO
        )
        
        # System Status (inline fields - 3 per row)
        embed.add_field(
        name="🚫 AutoMod System",
        value=f"**Status:** {'🟢 Active' if view.automod_settings.get('enabled', False) else '🔴 Inactive'}\n"
              f"**Spam Filter:** {'Enabled' if view.automod_settings.get('spam_filter') else 'Disabled'}\n"
              f"**Word Filter:** {'Enabled' if view.automod_settings.get('word_filter') else 'Disabled'}",
        inline=True
        )
        
        embed.add_field(
        name="📋 Logging & Audit",
        value=f"**Mod Log:** {'Set' if view.settings.get('mod_log_channel') else 'Not set'}\n"
              f"**Action Tracking:** Real-time logs\n"
              f"**Staff Actions:** Full attribution",
        inline=True
        )
        
        embed.add_field(
        name="🛡️ Protection Features",
        value=f"**Raid Protection:** Auto-detection\n"
              f"**Link Filtering:** Malicious URLs\n"
              f"**Role Protection:** Hierarchy guard",
        inline=True
        )
        
        # Button Guide
        embed.add_field(
        name="🎮 Available Actions",
        value="**Row 1:** 🚫 AutoMod • 📝 Word Filter • 🛡️ Spam Protection\n"
              "**Features:** Configure automated moderation tools\n"
              "**Bottom:** ⬅️ Back to Main Settings",
        inline=False
        )
        
        embed.set_footer(text="🔵 System Feature: Server protection • Keep your community safe")
        
        await interaction.response.edit_message(embed=embed, view=view)
    
    @discord.ui.button(emoji="🛡️", label="Server", style=discord.ButtonStyle.primary, row=2)
    async def server_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Open server settings panel."""
        view = ServerSettingsView(self.bot, self.guild_id)
        await view.initialize()
        
        embed = create_embed(
        title="🛡️ Server Information & Configuration",
        description="**System Feature:** Comprehensive server management and information center.\n"
                   "View server statistics, configure community features, and manage server-wide settings.",
        color=Colors.INFO
        )
        
        # Get current settings
        guild = self.bot.get_guild(self.guild_id)
        
        # System Status (inline fields - 3 per row)
        embed.add_field(
        name="📊 Server Overview",
        value=f"**Name:** {guild.name}\n"
              f"**Members:** {guild.member_count}\n"
              f"**Channels:** {len(guild.channels)}",
        inline=True
        )
        
        embed.add_field(
        name="🚀 Server Features",
        value=f"**Boost Level:** {guild.premium_tier}\n"
              f"**Boosts:** {guild.premium_subscription_count}\n"
              f"**Verification:** {guild.verification_level.name.title()}",
        inline=True
        )
        
        embed.add_field(
        name="👑 Management",
        value=f"**Owner:** {guild.owner.display_name if guild.owner else 'Unknown'}\n"
              f"**Created:** {guild.created_at.strftime('%d.%m.%Y')}\n"
              f"**Bot Features:** Integrated",
        inline=True
        )
        
        # Button Guide
        embed.add_field(
        name="🎮 Available Actions",
        value="**Row 1:** 📝 Server Info • 🔧 Configure Features\n"
              "**Functions:** View detailed information and configure community settings\n"
              "**Bottom:** ⬅️ Back to Main Settings",
        inline=False
        )
        
        embed.set_footer(text="🔵 System Feature: Server management • Monitor and configure your community")
        
        await interaction.response.edit_message(embed=embed, view=view)
    
    # Row 3: Optional Features (SECONDARY - Gray)
    @discord.ui.button(emoji="🤖", label="Bot Config", style=discord.ButtonStyle.secondary, row=3)
    async def bot_config(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Open bot configuration."""
        view = BotConfigView(self.bot, self.guild_id)
        await view.initialize()
        
        embed = create_embed(
        title="🤖 Bot Configuration & Settings",
        description="**Optional Feature:** Customize bot behavior and server-specific preferences.\n"
                   "Configure command prefix, status roles, and bot-specific functionality settings.",
        color=Colors.INFO
        )
        
        # System Status (inline fields - 3 per row)
        embed.add_field(
        name="⚙️ Bot Settings",
        value=f"**Prefix:** `{view.settings.get('prefix', '>')}`\n"
              f"**Commands:** {'Enabled' if view.settings.get('commands_enabled', True) else 'Disabled'}\n"
              f"**Error Reporting:** {'On' if view.settings.get('error_reporting', True) else 'Off'}",
        inline=True
        )
        
        embed.add_field(
        name="📌 Status & Roles",
        value=f"**Status Role:** {'Set' if view.settings.get('status_role_id') else 'Not set'}\n"
              f"**Activity Status:** Online monitoring\n"
              f"**Presence:** Custom status",
        inline=True
        )
        
        embed.add_field(
        name="🔧 Customization",
        value=f"**Permissions:** Bot role hierarchy\n"
              f"**Integration:** Third-party services\n"
              f"**Performance:** Optimized settings",
        inline=True
        )
        
        # Button Guide
        embed.add_field(
        name="🎮 Available Actions",
        value="**Row 1:** 🔧 Prefix • 📌 Status Role\n"
              "**Row 2:** ⚙️ Bot Settings (commands, error handling, behavior)\n"
              "**Bottom:** ⬅️ Back to Main Settings",
        inline=False
        )
        
        embed.set_footer(text="⚫ Optional Feature: Bot customization • Tailor bot behavior to your server")
        
        await interaction.response.edit_message(embed=embed, view=view)
    
    @discord.ui.button(emoji="🎂", label="Birthday", style=discord.ButtonStyle.secondary, row=3)
    async def birthday(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Open birthday settings."""
        view = BirthdaySettingsView(self.bot, self.guild_id)
        await view.initialize()
        
        embed = create_embed(
        title="🎂 Birthday Celebration System",
        description="**Optional Feature:** Automated birthday celebrations and member recognition.\n"
                   "Create a warm community atmosphere with birthday announcements and special roles.",
        color=Colors.INFO
        )
        
        # System Status (inline fields - 3 per row)
        embed.add_field(
        name="🎂 Birthday System",
        value=f"**Status:** {'🟢 Active' if view.settings.get('enabled', False) else '🔴 Inactive'}\n"
              f"**Channel:** {'Set' if view.settings.get('channel_id') else 'Not set'}\n"
              f"**Auto Announce:** Daily check",
        inline=True
        )
        
        embed.add_field(
        name="🎉 Celebrations",
        value=f"**Birthday Role:** {'Set' if view.settings.get('birthday_role_id') else 'Not set'}\n"
              f"**Custom Messages:** Personalized\n"
              f"**Member List:** {'Available' if view.settings.get('show_list', True) else 'Private'}",
        inline=True
        )
        
        embed.add_field(
        name="📅 Management",
        value=f"**Registered:** Birthday tracking\n"
              f"**Reminders:** Automated system\n"
              f"**Privacy:** Member controlled",
        inline=True
        )
        
        # Button Guide
        embed.add_field(
        name="🎮 Available Actions",
        value="**Row 1:** 🎂 Basic Settings (channel, role, messages)\n"
              "**Row 2:** 📅 Birthday List (view registered members)\n"
              "**Bottom:** ⬅️ Back to Main Settings",
        inline=False
        )
        
        embed.set_footer(text="⚫ Optional Feature: Community building • Celebrate your members' special days")
        
        await interaction.response.edit_message(embed=embed, view=view)
    
    @discord.ui.button(emoji="🤖", label="AI", style=discord.ButtonStyle.secondary, row=3)
    async def ai_features(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Open AI settings."""
        view = AISettingsView(self.bot, self.guild_id)
        await view.initialize()
        
        embed = create_embed(
        title="🤖 AI-Powered Features & Intelligence",
        description="**Optional Feature:** Advanced artificial intelligence integration for enhanced automation.\n"
                   "Leverage AI for chat assistance, content moderation, and intelligent server management.",
        color=Colors.INFO
        )
        
        # System Status (inline fields - 3 per row)
        embed.add_field(
        name="🤖 AI Chat Assistant",
        value=f"**Status:** {'🟢 Active' if view.settings.get('ai_chat_enabled', False) else '🔴 Inactive'}\n"
              f"**Model:** {view.settings.get('ai_model', 'GPT-3.5')}\n"
              f"**Language:** {view.settings.get('response_language', 'Auto')}",
        inline=True
        )
        
        embed.add_field(
        name="🛡️ AI AutoMod",
        value=f"**Status:** {'🟢 Active' if view.settings.get('ai_automod_enabled', False) else '🔴 Inactive'}\n"
              f"**Sensitivity:** {view.settings.get('sensitivity', 'Medium')}\n"
              f"**Real-time:** Content analysis",
        inline=True
        )
        
        embed.add_field(
        name="🧠 Intelligence Features",
        value=f"**Content Analysis:** Smart detection\n"
              f"**Pattern Recognition:** Behavioral analysis\n"
              f"**Auto Learning:** Adaptive responses",
        inline=True
        )
        
        # Button Guide
        embed.add_field(
        name="🎮 Available Actions",
        value="**Row 1:** 🤖 AI Chat • 🛡️ AI AutoMod\n"
              "**Features:** Configure AI-powered assistance and automated moderation\n"
              "**Bottom:** ⬅️ Back to Main Settings",
        inline=False
        )
        
        embed.set_footer(text="⚫ Optional Feature: AI intelligence • Enhanced automation with artificial intelligence")
        
        await interaction.response.edit_message(embed=embed, view=view)
    
    # Row 4: Advanced & Close (SECONDARY/DANGER)
    @discord.ui.button(emoji="⚙️", label="Advanced", style=discord.ButtonStyle.secondary, row=4)
    async def advanced(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Open advanced settings."""
        view = AdvancedSettingsView(self.bot, self.guild_id)
        await view.initialize()
        
        embed = create_embed(
        title="⚙️ Advanced System Configuration",
        description="**Optional Feature:** Advanced system configuration and maintenance tools.\n"
                   "Access developer settings, system diagnostics, and database management features.",
        color=Colors.INFO
        )
        
        # System Status (inline fields - 3 per row)
        embed.add_field(
        name="🔧 System Settings",
        value=f"**Debug Mode:** {'🟢 On' if view.settings.get('debug_mode', False) else '🔴 Off'}\n"
              f"**Cooldowns:** {'Custom' if view.settings.get('command_cooldowns') else 'Default'}\n"
              f"**Performance:** Optimized",
        inline=True
        )
        
        embed.add_field(
        name="📊 Database Management",
        value=f"**Backup System:** Automated\n"
              f"**Data Export:** Available\n"
              f"**Cleanup:** Scheduled maintenance",
        inline=True
        )
        
        embed.add_field(
        name="🚨 Diagnostics",
        value=f"**Error Tracking:** Active monitoring\n"
              f"**Performance:** Real-time metrics\n"
              f"**Health Check:** System status",
        inline=True
        )
        
        # Button Guide
        embed.add_field(
        name="🎮 Available Actions",
        value="**Row 1:** 🔧 System Settings (debug, performance, cooldowns)\n"
              "**Row 2:** 📊 Database Backup (data management, export, cleanup)\n"
              "**Warning:** ⚠️ Advanced users only - modify with caution\n"
              "**Bottom:** ⬅️ Back to Main Settings",
        inline=False
        )
        
        embed.set_footer(text="⚫ Optional Feature: System administration • Advanced configuration for experienced users")
        
        await interaction.response.edit_message(embed=embed, view=view)
    
    @discord.ui.button(emoji="❌", label="Close", style=discord.ButtonStyle.danger, row=4)
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Close the settings panel."""
        await interaction.response.defer()
        await interaction.delete_original_response()


class BaseSettingsView(discord.ui.View):
    """Base class for all settings views."""
    
    def __init__(self, bot, guild_id: int):
        super().__init__(timeout=300)
        self.bot = bot
        self.guild_id = guild_id
        self.db = db_manager.get_database()
        self.settings = {}
    
    async def initialize(self):
        """Initialize the view with current settings."""
        await self.load_settings()
    
    async def load_settings(self):
        """Load settings from database."""
    # pass  # Override in subclasses
    
    def get_settings_summary(self) -> str:
        """Get a summary of current settings."""
        return "Settings not loaded"
    
    @discord.ui.button(label="⬅️ Back", style=discord.ButtonStyle.secondary, row=4)
    async def back(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Go back to main settings."""
        view = MainSettingsView(self.bot, self.guild_id)
        
        # Import settings cog to use its method
        from src.cogs.admin.settings import Settings
        settings_cog = Settings(self.bot)
        await settings_cog.initialize_db()
        
        # Get settings summary
        settings_summary = await settings_cog.get_settings_summary(self.guild_id)
        
        embed = discord.Embed(
            title="⚙️ Server Settings",
            description="**Configure your server settings using the organized buttons below.**\n"
                       "Features are color-coded: 🟢 Core • 🔵 Essential • ⚫ Optional",
            color=discord.Color.blue()
        )
        
        # Add core features status (inline fields - 3 per row)
        embed.add_field(
            name="📝 Registration System",
            value=f"**Status:** {'🟢 Active' if 'Registration' in settings_summary else '🔴 Inactive'}\n"
                  f"**Function:** Member onboarding\n"
                  f"**Setup:** Age/Gender/Game roles",
            inline=True
        )
        
        embed.add_field(
            name="👋 Welcome System", 
            value=f"**Status:** {'🟢 Active' if 'Welcome: Enabled' in settings_summary else '🔴 Inactive'}\n"
                  f"**Function:** Greet new members\n"
                  f"**Setup:** Messages & images",
            inline=True
        )
        
        embed.add_field(
            name="🎫 Ticket System",
            value=f"**Status:** {'🟢 Active' if 'Tickets: Enabled' in settings_summary else '🔴 Inactive'}\n"
                  f"**Function:** Support tickets\n"
                  f"**Setup:** Categories & staff",
            inline=True
        )
        
        # Add essential features status  
        embed.add_field(
            name="📊 Leveling System",
            value=f"**Status:** 🟢 Active\n"
                  f"**Function:** XP & level tracking\n"
                  f"**Setup:** Rewards & roles",
            inline=True
        )
        
        embed.add_field(
            name="📋 Logging System",
            value=f"**Status:** {'🟢 Active' if 'Logging: Enabled' in settings_summary else '🔴 Inactive'}\n"
                  f"**Function:** Event tracking\n"
                  f"**Setup:** Channels & events",
            inline=True
        )
        
        embed.add_field(
            name="⭐ Starboard",
            value=f"**Status:** 🔴 Inactive\n"
                  f"**Function:** Featured messages\n"
                  f"**Setup:** Star threshold",
            inline=True
        )
        
        # Button guide
        embed.add_field(
            name="🎮 Button Guide",
            value="**Row 1:** 📝 Register | 👋 Welcome | 🎫 Tickets\n"
                  "**Row 2:** 📊 Leveling | 📋 Logging | ⭐ Starboard\n" 
                  "**Row 3:** 🎨 Roles | ⚔️ Moderation | 🛡️ Server\n"
                  "**Row 4:** 🤖 Bot Config | 🎂 Birthday | 🤖 AI\n"
                  "**Row 5:** ⚙️ Advanced | ❌ Close",
            inline=False
        )
        
        embed.set_footer(text="🔒 Administrator permissions required • Click buttons to configure features")
        
        await interaction.response.edit_message(embed=embed, view=view)


class ServerSettingsView(BaseSettingsView):
    """Server settings view."""
    
    async def load_settings(self):
        """Load server settings from database."""
        self.settings = await self.db.server_settings.find_one({"server_id": self.guild_id}) or {}
    
    def get_settings_summary(self) -> str:
        """Get server settings summary."""
        guild = self.bot.get_guild(self.guild_id)
        return (f"**Server Name:** {guild.name}\n"
            f"**Member Count:** {guild.member_count}\n"
            f"**Boost Level:** {guild.premium_tier}\n"
            f"**Boost Count:** {guild.premium_subscription_count}")
    
    @discord.ui.button(label="📝 Server Info", style=discord.ButtonStyle.primary, row=0)
    async def server_info(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Show detailed server info."""
        guild = interaction.guild
        
        embed = create_embed(
        title=f"📝 {guild.name} - Server Information",
        description="Detailed server information",
        color=Colors.INFO
        )
        
        embed.add_field(
        name="Basic Information",
        value=f"**Owner:** {guild.owner.mention if guild.owner else 'Unknown'}\n"
              f"**Created:** {guild.created_at.strftime('%d.%m.%Y %H:%M')}\n"
              f"**Member Count:** {guild.member_count}\n"
              f"**Channel Count:** {len(guild.channels)}",
        inline=True
        )
        
        embed.add_field(
        name="Boost Information",
        value=f"**Boost Level:** {guild.premium_tier}\n"
              f"**Boost Count:** {guild.premium_subscription_count}\n"
              f"**Max Bitrate:** {guild.bitrate_limit // 1000}kbps\n"
              f"**Max File Size:** {guild.filesize_limit // 1024 // 1024}MB",
        inline=True
        )
        
        embed.add_field(
        name="Features",
        value=f"**Verification Level:** {guild.verification_level.name.title()}\n"
              f"**Content Filter:** {guild.explicit_content_filter.name.replace('_', ' ').title()}\n"
              f"**Default Notifications:** {guild.default_notifications.name.replace('_', ' ').title()}",
        inline=False
        )
        
        if guild.icon:
                    embed.set_thumbnail(url=guild.icon.url)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @discord.ui.button(label="🔧 Configure Features", style=discord.ButtonStyle.primary, row=0)
    async def configure_features(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Configure server features."""
        modal = ServerFeaturesModal(self.bot, self.guild_id, self.settings)
        await interaction.response.send_modal(modal)


class WelcomeGoodbyeView(BaseSettingsView):
    """Welcome/goodbye settings view."""
    
    async def load_settings(self):
        """Load welcome settings from database."""
        self.welcome_settings = await self.db.welcomer.find_one({"guild_id": self.guild_id}) or {}
        self.goodbye_settings = await self.db.byebye.find_one({"guild_id": self.guild_id}) or {}
    
    def get_settings_summary(self) -> str:
        """Get welcome settings summary."""
        welcome_channel = f"<#{self.welcome_settings.get('welcome_channel_id')}>" if self.welcome_settings.get('welcome_channel_id') else "Not set"
        goodbye_channel = f"<#{self.goodbye_settings.get('channel_id')}>" if self.goodbye_settings.get('channel_id') else "Not set"
        
        return (f"**Welcome Channel:** {welcome_channel}\n"
            f"**Welcome Message:** {'Enabled' if self.welcome_settings.get('welcome_message_enabled') else 'Disabled'}\n"
            f"**Goodbye Channel:** {goodbye_channel}\n"
            f"**Goodbye Message:** {'Enabled' if self.goodbye_settings.get('enabled') else 'Disabled'}")
    
    @discord.ui.button(label="👋 Welcome Settings", style=discord.ButtonStyle.primary, row=0)
    async def welcome_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Configure welcome settings."""
        modal = WelcomeSettingsModal(self.bot, self.guild_id, self.welcome_settings)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="👋 Goodbye Settings", style=discord.ButtonStyle.primary, row=0)
    async def goodbye_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Configure goodbye settings."""
        modal = GoodbyeSettingsModal(self.bot, self.guild_id, self.goodbye_settings)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="🖼️ Image Settings", style=discord.ButtonStyle.secondary, row=1)
    async def image_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Configure welcome/goodbye images."""
        view = WelcomeImageView(self.bot, self.guild_id)
        await view.initialize()
        
        embed = create_embed(
        title="🖼️ Welcome/Goodbye Image Settings",
        description="Configure welcome and goodbye card images.",
        color=Colors.INFO
        )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class ModerationView(BaseSettingsView):
    """Moderation settings view."""
    
    async def load_settings(self):
        """Load moderation settings from database."""
        self.settings = await self.db.moderation_settings.find_one({"guild_id": self.guild_id}) or {}
        self.automod_settings = await self.db.automod.find_one({"guild_id": self.guild_id}) or {}
    
    def get_settings_summary(self) -> str:
        """Get moderation settings summary."""
        automod_enabled = self.automod_settings.get('enabled', False)
        mod_log_channel = f"<#{self.settings.get('mod_log_channel')}>" if self.settings.get('mod_log_channel') else "Not set"
        
        return (f"**AutoMod:** {'Enabled' if automod_enabled else 'Disabled'}\n"
            f"**Mod Log Channel:** {mod_log_channel}\n"
            f"**Word Filter:** {'Enabled' if self.automod_settings.get('word_filter') else 'Disabled'}\n"
            f"**Spam Filter:** {'Enabled' if self.automod_settings.get('spam_filter') else 'Disabled'}")
    
    @discord.ui.button(label="🚫 AutoMod", style=discord.ButtonStyle.primary, row=0)
    async def automod_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Configure AutoMod settings."""
        modal = AutoModSettingsModal(self.bot, self.guild_id, self.automod_settings)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="📝 Word Filter", style=discord.ButtonStyle.primary, row=0)
    async def word_filter(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Configure word filter."""
        view = WordFilterView(self.bot, self.guild_id)
        await view.initialize()
        
        embed = create_embed(
        title="📝 Word Filter Settings",
        description="Configure filtered words and phrases.",
        color=Colors.INFO
        )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @discord.ui.button(label="🛡️ Spam Protection", style=discord.ButtonStyle.primary, row=0)
    async def spam_protection(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Configure spam protection."""
        modal = SpamProtectionModal(self.bot, self.guild_id, self.automod_settings)
        await interaction.response.send_modal(modal)


class LoggingView(BaseSettingsView):
    """Logging settings view."""
    
    async def load_settings(self):
        """Load logging settings from database."""
        self.settings = await self.db.server_settings.find_one({"server_id": self.guild_id}) or {}
        self.logging_settings = self.settings.get('logging', {})
    
    def get_settings_summary(self) -> str:
        """Get logging settings summary."""
        log_channel = f"<#{self.logging_settings.get('channel_id')}>" if self.logging_settings.get('channel_id') else "Not set"
        
        enabled_events = []
        for event in ['message_delete', 'message_edit', 'member_join', 'member_leave', 'voice_state']:
            if self.logging_settings.get(f'{event}_enabled'):
                enabled_events.append(event.replace('_', ' ').title())
        
        return (f"**Log Channel:** {log_channel}\n"
            f"**Enabled Events:** {', '.join(enabled_events) if enabled_events else 'None'}")
    
    @discord.ui.button(label="📋 Event Logging", style=discord.ButtonStyle.primary, row=0)
    async def event_logging(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Configure event logging."""
        view = EventLoggingView(self.bot, self.guild_id, self.logging_settings)
        
        embed = create_embed(
        title="📋 Event Logging Configuration",
        description="Select which events to log.",
        color=Colors.INFO
        )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @discord.ui.button(label="🎯 Log Channel", style=discord.ButtonStyle.primary, row=0)
    async def log_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Select log channel."""
        view = LogChannelSelectView(self.bot, self.guild_id)
        
        embed = create_embed(
        title="🎯 Select Log Channel",
        description="Choose a channel for logging events.",
        color=Colors.INFO
        )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class TicketSystemView(BaseSettingsView):
    """Modern ticket system settings view."""
    
    async def load_settings(self):
        """Load ticket settings from database."""
        self.settings = await self.db.ticket_settings.find_one({"guild_id": self.guild_id}) or {"enabled": True}
        self.form_questions = await self.db.ticket_form_questions.find({"guild_id": self.guild_id}).to_list(None) or []
    
    def get_settings_summary(self) -> str:
        """Get ticket settings summary."""
        enabled = self.settings.get('enabled', True)  # Default to enabled
        category = f"<#{self.settings.get('category_id')}>" if self.settings.get('category_id') else "Not set"
        log_channel = f"<#{self.settings.get('log_channel_id')}>" if self.settings.get('log_channel_id') else "Not set"
        support_roles = self.settings.get('support_roles', [])
        
        show_level_card = self.settings.get('show_level_card', True)
        
        return (f"**System Status:** {'🟢 Enabled' if enabled else '🔴 Disabled'}\n"
                f"**Ticket Category:** {category}\n"
                f"**Support Roles:** {len(support_roles)} configured\n"
                f"**Form Questions:** {len(self.form_questions)} configured\n"
                f"**Level Card:** {'✅ Enabled' if show_level_card else '❌ Disabled'}")
    
    @discord.ui.button(label="🔧 Basic Setup", style=discord.ButtonStyle.primary, row=0)
    async def basic_setup(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Configure basic ticket settings."""
        modal = TicketBasicSettingsModal(self.bot, self.guild_id, self.settings)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="📝 Form Questions", style=discord.ButtonStyle.primary, row=0)
    async def form_questions(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Manage ticket form questions."""
        view = TicketFormQuestionsView(self.bot, self.guild_id)
        await view.initialize()
        
        embed = create_embed(
            title="📝 Ticket Form Questions",
            description="Configure questions that users will answer when creating tickets.",
            color=Colors.INFO
        )
        
        # Show current questions
        if self.form_questions:
            questions_text = []
            for i, q in enumerate(self.form_questions[:5], 1):
                questions_text.append(f"**{i}.** {q.get('question', 'No question')[:50]}...")
            
            embed.add_field(
                name="Current Questions",
                value="\n".join(questions_text),
                inline=False
            )
        else:
            embed.add_field(
                name="Current Questions",
                value="No questions configured yet.",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @discord.ui.button(label="🎨 Send Ticket Panel", style=discord.ButtonStyle.success, row=0)
    async def send_ticket_panel(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Send the ticket creation panel."""
        if not self.settings.get('enabled', True):  # Default to enabled if not set
            await interaction.response.send_message(
                embed=error_embed("Please enable the ticket system first.", title="❌ System Disabled"),
                ephemeral=True
            )
            return
        
        # Note: No need to check form_questions anymore - default questions are auto-created
        
        modal = TicketPanelSendModal(self.bot, self.guild_id, self.settings)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="📊 Statistics", style=discord.ButtonStyle.secondary, row=1)
    async def statistics(self, interaction: discord.Interaction, button: discord.ui.Button):
        """View ticket statistics."""
        view = TicketStatsView(self.guild_id)
        embed = create_embed(
            title="📊 Ticket Statistics Dashboard",
            description="Access comprehensive ticket analytics for your server.",
        color=Colors.INFO
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @discord.ui.button(label="⚙️ Advanced Settings", style=discord.ButtonStyle.secondary, row=1)
    async def advanced_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Configure advanced ticket settings."""
        modal = TicketAdvancedSettingsModal(self.bot, self.guild_id, self.settings)
        await interaction.response.send_modal(modal)


class LevellingSettingsView(BaseSettingsView):
    """Levelling settings view."""
    
    async def load_settings(self):
        """Load leveling settings from database."""
        self.settings = await self.db.leveling_settings.find_one({"guild_id": self.guild_id}) or {}
    
    def get_settings_summary(self) -> str:
        """Get leveling settings summary."""
        enabled = self.settings.get('enabled', True)
        xp_per_message = self.settings.get('xp_per_message', 1)
        xp_cooldown = self.settings.get('xp_cooldown', 60)
        
        return (f"**Leveling System:** {'Enabled' if enabled else 'Disabled'}\n"
            f"**XP per Message:** {xp_per_message}\n"
            f"**XP Cooldown:** {xp_cooldown} seconds\n"
            f"**Level-up Notifications:** {'Enabled' if self.settings.get('levelup_notifications') else 'Disabled'}")
    
    @discord.ui.button(label="⚙️ XP Settings", style=discord.ButtonStyle.primary, row=0)
    async def xp_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Configure XP settings."""
        modal = XPSettingsModal(self.bot, self.guild_id, self.settings)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="🏆 Level Roles", style=discord.ButtonStyle.primary, row=0)
    async def level_roles(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Configure level roles."""
        view = LevelRolesView(self.bot, self.guild_id)
        await view.initialize()
        
        embed = create_embed(
        title="🏆 Level Roles Configuration",
        description="Configure roles given at certain levels.",
        color=Colors.INFO
        )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @discord.ui.button(label="📊 Leaderboard", style=discord.ButtonStyle.secondary, row=1)
    async def leaderboard_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Configure leaderboard settings."""
        modal = LeaderboardSettingsModal(self.bot, self.guild_id, self.settings)
        await interaction.response.send_modal(modal)


class RoleManagementView(BaseSettingsView):
    """Role management settings view."""
    
    async def load_settings(self):
        """Load role settings from database."""
        self.settings = await self.db.role_settings.find_one({"guild_id": self.guild_id}) or {}
        self.auto_roles = await self.db.auto_roles.find({"guild_id": self.guild_id}).to_list(None) or []
    
    def get_settings_summary(self) -> str:
        """Get role settings summary."""
        auto_role_count = len(self.auto_roles)
        reaction_roles = len(self.settings.get('reaction_roles', []))
        
        return (f"**Auto Roles:** {auto_role_count} configured\n"
            f"**Reaction Roles:** {reaction_roles} configured\n"
            f"**Role Hierarchy Check:** {'Enabled' if self.settings.get('hierarchy_check') else 'Disabled'}")
    
    @discord.ui.button(label="🤖 Auto Roles", style=discord.ButtonStyle.primary, row=0)
    async def auto_roles(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Configure auto roles."""
        view = AutoRolesView(self.bot, self.guild_id)
        await view.initialize()
        
        embed = create_embed(
        title="🤖 Auto Roles Configuration",
        description="Configure roles automatically given to new members.",
        color=Colors.INFO
        )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @discord.ui.button(label="⚡ Reaction Roles", style=discord.ButtonStyle.primary, row=0)
    async def reaction_roles(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Configure reaction roles."""
        view = ReactionRolesView(self.bot, self.guild_id)
        await view.initialize()
        
        embed = create_embed(
        title="⚡ Reaction Roles Configuration",
        description="Configure roles given by emoji reactions.",
        color=Colors.INFO
        )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @discord.ui.button(label="🎭 Role Menus", style=discord.ButtonStyle.secondary, row=1)
    async def role_menus(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Configure role selection menus."""
        view = RoleMenusView(self.bot, self.guild_id)
        await view.initialize()
        
        embed = create_embed(
        title="🎭 Role Menus Configuration",
        description="Configure dropdown role selection menus.",
        color=Colors.INFO
        )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class StarboardView(BaseSettingsView):
    """Starboard settings view."""
    
    async def load_settings(self):
        """Load starboard settings from database."""
        self.settings = await self.db.starboard.find_one({"guild_id": self.guild_id}) or {}
    
    def get_settings_summary(self) -> str:
        """Get starboard settings summary."""
        enabled = self.settings.get('enabled', False)
        channel = f"<#{self.settings.get('channel_id')}>" if self.settings.get('channel_id') else "Not set"
        threshold = self.settings.get('star_threshold', 3)
        
        return (f"**Starboard:** {'Enabled' if enabled else 'Disabled'}\n"
            f"**Channel:** {channel}\n"
            f"**Star Threshold:** {threshold}\n"
            f"**Self-Star:** {'Allowed' if self.settings.get('allow_self_star') else 'Not allowed'}")
    
    @discord.ui.button(label="⭐ Basic Settings", style=discord.ButtonStyle.primary, row=0)
    async def basic_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Configure basic starboard settings."""
        modal = StarboardSettingsModal(self.bot, self.guild_id, self.settings)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="🔧 Advanced Settings", style=discord.ButtonStyle.secondary, row=1)
    async def advanced_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Configure advanced starboard settings."""
        modal = StarboardAdvancedModal(self.bot, self.guild_id, self.settings)
        await interaction.response.send_modal(modal)


class BotConfigView(BaseSettingsView):
    """Bot configuration view."""
    
    async def load_settings(self):
        """Load bot settings from database."""
        self.settings = await self.db.settings.find_one({"guild_id": self.guild_id}) or {}
    
    def get_settings_summary(self) -> str:
        """Get bot settings summary."""
        prefix = self.settings.get('prefix', '>')
        status_role = f"<@&{self.settings.get('status_role_id')}>" if self.settings.get('status_role_id') else "Not set"
        
        return (f"**Prefix:** `{prefix}`\n"
            f"**Status Role:** {status_role}\n"
            f"**Commands Enabled:** {'Yes' if self.settings.get('commands_enabled', True) else 'No'}")
    
    @discord.ui.button(label="🔧 Prefix", style=discord.ButtonStyle.primary, row=0)
    async def prefix(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Change bot prefix."""
        modal = PrefixModal(self.bot, self.guild_id)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="📌 Status Role", style=discord.ButtonStyle.primary, row=0)
    async def status_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Configure status role."""
        view = StatusRoleView(self.bot, self.guild_id)
        
        embed = create_embed(
        title="📌 Status Role Configuration",
        description="Configure the status role for bot updates.",
        color=Colors.INFO
        )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @discord.ui.button(label="⚙️ Bot Settings", style=discord.ButtonStyle.secondary, row=1)
    async def bot_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Configure general bot settings."""
        modal = BotSettingsModal(self.bot, self.guild_id, self.settings)
        await interaction.response.send_modal(modal)


class BirthdaySettingsView(BaseSettingsView):
    """Birthday settings view."""
    
    async def load_settings(self):
        """Load birthday settings from database."""
        self.settings = await self.db.birthday.find_one({"guild_id": self.guild_id}) or {}
    
    def get_settings_summary(self) -> str:
        """Get birthday settings summary."""
        enabled = self.settings.get('enabled', False)
        channel = f"<#{self.settings.get('channel_id')}>" if self.settings.get('channel_id') else "Not set"
        role = f"<@&{self.settings.get('birthday_role_id')}>" if self.settings.get('birthday_role_id') else "Not set"
        
        return (f"**Birthday System:** {'Enabled' if enabled else 'Disabled'}\n"
            f"**Announcement Channel:** {channel}\n"
            f"**Birthday Role:** {role}\n"
            f"**Auto Remove Role:** {'Yes' if self.settings.get('auto_remove_role') else 'No'}")
    
    @discord.ui.button(label="🎂 Basic Settings", style=discord.ButtonStyle.primary, row=0)
    async def basic_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Configure basic birthday settings."""
        modal = BirthdaySettingsModal(self.bot, self.guild_id, self.settings)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="📅 Birthday List", style=discord.ButtonStyle.secondary, row=1)
    async def birthday_list(self, interaction: discord.Interaction, button: discord.ui.Button):
        """View birthday list."""
        await self.show_birthday_list(interaction)
    
    async def show_birthday_list(self, interaction):
        """Show list of registered birthdays."""
        birthdays = await self.db.user_birthdays.find({"guild_id": self.guild_id}).to_list(None)
        
        if not birthdays:
            embed = create_embed(
                title="📅 Birthday List",
                description="No birthdays registered yet.",
                color=Colors.INFO
            )
        else:
            # Sort by month and day
            sorted_birthdays = sorted(birthdays, key=lambda x: (x.get('month', 12), x.get('day', 31)))
            
            birthday_text = []
            for birthday in sorted_birthdays[:20]:  # Limit to 20
                user = self.bot.get_user(birthday['user_id'])
                if user:
                    birthday_text.append(f"**{user.display_name}** - {birthday.get('day', '?')}/{birthday.get('month', '?')}")
            
            embed = create_embed(
                title="📅 Birthday List",
                description="\n".join(birthday_text) if birthday_text else "No valid birthdays found.",
                color=Colors.INFO
            )
            
            if len(birthdays) > 20:
                embed.set_footer(text=f"Showing 20 of {len(birthdays)} birthdays")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)


class AISettingsView(BaseSettingsView):
    """AI settings view."""
    
    async def load_settings(self):
        """Load AI settings from database."""
        self.settings = await self.db.ai_settings.find_one({"guild_id": self.guild_id}) or {}
    
    def get_settings_summary(self) -> str:
        """Get AI settings summary."""
        ai_chat_enabled = self.settings.get('ai_chat_enabled', False)
        auto_mod_enabled = self.settings.get('ai_automod_enabled', False)
        
        return (f"**AI Chat:** {'Enabled' if ai_chat_enabled else 'Disabled'}\n"
            f"**AI AutoMod:** {'Enabled' if auto_mod_enabled else 'Disabled'}\n"
            f"**AI Model:** {self.settings.get('ai_model', 'GPT-3.5')}\n"
            f"**Response Language:** {self.settings.get('response_language', 'Turkish')}")
    
    @discord.ui.button(label="🤖 AI Chat", style=discord.ButtonStyle.primary, row=0)
    async def ai_chat(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Configure AI chat settings."""
        modal = AIChatSettingsModal(self.bot, self.guild_id, self.settings)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="🛡️ AI AutoMod", style=discord.ButtonStyle.primary, row=0)
    async def ai_automod(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Configure AI AutoMod settings."""
        modal = AIAutoModSettingsModal(self.bot, self.guild_id, self.settings)
        await interaction.response.send_modal(modal)


class AdvancedSettingsView(BaseSettingsView):
    """Advanced settings view."""
    
    async def load_settings(self):
        """Load advanced settings from database."""
        self.settings = await self.db.advanced_settings.find_one({"guild_id": self.guild_id}) or {}
    
    def get_settings_summary(self) -> str:
        """Get advanced settings summary."""
        return (f"**Debug Mode:** {'Enabled' if self.settings.get('debug_mode') else 'Disabled'}\n"
            f"**Command Cooldowns:** {'Enabled' if self.settings.get('command_cooldowns', True) else 'Disabled'}\n"
            f"**Error Reporting:** {'Enabled' if self.settings.get('error_reporting', True) else 'Disabled'}")
    
    @discord.ui.button(label="🔧 System Settings", style=discord.ButtonStyle.primary, row=0)
    async def system_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Configure system settings."""
        modal = SystemSettingsModal(self.bot, self.guild_id, self.settings)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="📊 Database Backup", style=discord.ButtonStyle.secondary, row=1)
    async def database_backup(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Create database backup."""
        await self.create_database_backup(interaction)
    
    async def create_database_backup(self, interaction):
        """Create a backup of guild data."""
        await interaction.response.defer(ephemeral=True)
        
        # Get all guild data
        guild_data = {
            'guild_id': self.guild_id,
            'export_date': datetime.utcnow().isoformat(),
            'settings': {},
            'members': [],
            'other_data': {}
        }
        
        # Export settings from various collections
        collections_to_export = [
        'server_settings', 'welcomer', 'byebye', 'ticket_settings',
        'leveling_settings', 'role_settings', 'starboard', 'birthday',
        'ai_settings', 'advanced_settings'
        ]
        
        for collection_name in collections_to_export:
            collection = getattr(self.db, collection_name, None)
            if collection:
                data = await collection.find_one({"guild_id": self.guild_id})
                if data:
                    guild_data['settings'][collection_name] = data
        
        # Export member data (limited)
        members = await self.db.members.find({"guild_id": self.guild_id}).limit(1000).to_list(None)
        guild_data['members'] = [
            {
                'user_id': member.get('user_id'),
                'xp': member.get('xp', 0),
                'level': member.get('level', 0),
                'messages': member.get('messages', 0)
            }
            for member in members
        ]
        
        # Create embed with backup info
        embed = create_embed(
            title="📊 Database Backup Created",
            description=f"Backup created for guild {interaction.guild.name}",
            color=Colors.SUCCESS
        )
        
        embed.add_field(
            name="Backup Contents",
            value=f"**Settings Collections:** {len(guild_data['settings'])}\n"
                  f"**Member Records:** {len(guild_data['members'])}\n"
                  f"**Export Date:** {datetime.utcnow().strftime('%d.%m.%Y %H:%M')}",
            inline=False
        )
        
        # Store backup in database
        await self.db.backups.insert_one(guild_data)
        
        try:
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            embed = create_embed(
                title="❌ Backup Failed",
                description=f"Could not create backup: {str(e)}",
                color=Colors.ERROR
            )
            await interaction.followup.send(embed=embed, ephemeral=True)


# Modal classes for settings configuration
class PrefixModal(discord.ui.Modal, title="Change Bot Prefix"):
    """Modal for changing bot prefix."""
    
    prefix = discord.ui.TextInput(
        label="New Prefix",
        placeholder="Enter new prefix (1-3 characters)",
        max_length=3,
        required=True
    )
    
    def __init__(self, bot, guild_id: int):
        super().__init__()
        self.bot = bot
        self.guild_id = guild_id
        self.db = db_manager.get_database()
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle prefix change submission."""
        new_prefix = self.prefix.value.strip()
        
        if not new_prefix or len(new_prefix) > 3:
            embed = create_embed(
                title="❌ Invalid Prefix",
                description="Prefix must be 1-3 characters long.",
                color=Colors.ERROR
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Update prefix in database
        await self.db.settings.update_one(
        {"guild_id": self.guild_id},
        {"$set": {"prefix": new_prefix}},
        upsert=True
        )
        
        embed = create_embed(
        title="✅ Prefix Updated",
        description=f"Bot prefix changed to `{new_prefix}`",
        color=Colors.SUCCESS
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)


# Additional modal classes would be implemented here...
# For brevity, I'm showing the structure - each modal would handle specific settings


class TicketAdvancedSettingsModal(discord.ui.Modal, title="Advanced Ticket Settings"):
    """Modal for advanced ticket settings."""
    
    auto_close_time = discord.ui.TextInput(
        label="Auto Close Time (hours)",
        placeholder="Auto close inactive tickets after X hours (0 to disable)",
        max_length=3,
        required=False
    )
    
    transcript_enabled = discord.ui.TextInput(
        label="Transcripts (true/false)",
        placeholder="Save ticket transcripts when closed?",
        max_length=5,
        required=False
    )
    
    def __init__(self, bot, guild_id: int, settings: dict):
        super().__init__()
        self.bot = bot
        self.guild_id = guild_id
        self.settings = settings
        self.db = db_manager.get_database()
        
        # Pre-fill current values
        if settings.get('auto_close_hours'):
            self.auto_close_time.default = str(settings['auto_close_hours'])
        if 'transcript_enabled' in settings:
            self.transcript_enabled.default = str(settings['transcript_enabled']).lower()
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle advanced ticket settings submission."""
        updates = {}
        
        if self.auto_close_time.value:
            try:
                hours = int(self.auto_close_time.value)
                if 0 <= hours <= 168:  # 0 to 7 days
                    updates['auto_close_hours'] = hours
            except ValueError:
                pass
        
        if self.transcript_enabled.value:
            updates['transcript_enabled'] = self.transcript_enabled.value.lower() == 'true'
        
        try:
            await self.db.ticket_settings.update_one(
                {"guild_id": self.guild_id},
                {"$set": updates},
                upsert=True
            )
            
            embed = create_embed(
                title="✅ Advanced Ticket Settings Updated",
                description="Advanced ticket settings have been updated.",
                color=Colors.SUCCESS
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            embed = create_embed(
                title="❌ Error",
                description=f"Failed to update advanced ticket settings: {str(e)}",
                color=Colors.ERROR
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)


class LeaderboardSettingsModal(discord.ui.Modal, title="Leaderboard Settings"):
    """Modal for leaderboard settings."""
    
    leaderboard_enabled = discord.ui.TextInput(
        label="Leaderboard Enabled (true/false)",
        placeholder="Enable leaderboard display?",
        max_length=5,
        required=False
    )
    
    show_voice_time = discord.ui.TextInput(
        label="Show Voice Time (true/false)",
        placeholder="Include voice time in leaderboard?",
        max_length=5,
        required=False
    )
    
    def __init__(self, bot, guild_id: int, settings: dict):
        super().__init__()
        self.bot = bot
        self.guild_id = guild_id
        self.settings = settings
        self.db = db_manager.get_database()
        
        # Pre-fill current values
        if 'leaderboard_enabled' in settings:
            self.leaderboard_enabled.default = str(settings['leaderboard_enabled']).lower()
        if 'show_voice_time' in settings:
            self.show_voice_time.default = str(settings['show_voice_time']).lower()
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle leaderboard settings submission."""
        updates = {}
        
        if self.leaderboard_enabled.value:
            updates['leaderboard_enabled'] = self.leaderboard_enabled.value.lower() == 'true'
        
        if self.show_voice_time.value:
            updates['show_voice_time'] = self.show_voice_time.value.lower() == 'true'
        
        try:
            await self.db.leveling_settings.update_one(
                {"guild_id": self.guild_id},
                {"$set": updates},
                upsert=True
            )
            
            embed = create_embed(
                title="✅ Leaderboard Settings Updated",
                description="Leaderboard settings have been updated.",
                color=Colors.SUCCESS
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            embed = create_embed(
                title="❌ Error",
                description=f"Failed to update leaderboard settings: {str(e)}",
                color=Colors.ERROR
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)


class StarboardAdvancedModal(discord.ui.Modal, title="Advanced Starboard Settings"):
    """Modal for advanced starboard settings."""
    
    ignore_bots = discord.ui.TextInput(
        label="Ignore Bots (true/false)",
        placeholder="Should bot messages be ignored?",
        max_length=5,
        required=False
    )
    
    star_emoji = discord.ui.TextInput(
        label="Star Emoji",
        placeholder="Custom star emoji (leave empty for ⭐)",
        max_length=50,
        required=False
    )
    
    def __init__(self, bot, guild_id: int, settings: dict):
        super().__init__()
        self.bot = bot
        self.guild_id = guild_id
        self.settings = settings
        self.db = db_manager.get_database()
        
        # Pre-fill current values
        if 'ignore_bots' in settings:
            self.ignore_bots.default = str(settings['ignore_bots']).lower()
        if settings.get('star_emoji'):
            self.star_emoji.default = settings['star_emoji']
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle advanced starboard settings submission."""
        updates = {}
        
        if self.ignore_bots.value:
            updates['ignore_bots'] = self.ignore_bots.value.lower() == 'true'
        
        if self.star_emoji.value:
            updates['star_emoji'] = self.star_emoji.value
        elif self.star_emoji.value == "":
            updates['star_emoji'] = "⭐"
        
        await self.db.starboard.update_one(
            {"guild_id": self.guild_id},
            {"$set": updates},
            upsert=True
        )
        
        embed = create_embed(
            title="✅ Advanced Starboard Settings Updated",
            description="Advanced starboard settings have been updated.",
            color=Colors.SUCCESS
        )
        
        try:
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            embed = create_embed(
                title="❌ Error",
                description=f"Failed to update advanced starboard settings: {str(e)}",
                color=Colors.ERROR
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)


class TicketPanelView(discord.ui.View):
    """Ticket panel configuration view"""
    
    def __init__(self, bot, guild_id: int):
        super().__init__(timeout=300)
        self.bot = bot
        self.guild_id = guild_id
    
    async def initialize(self):
        """Initialize the view (for compatibility)"""
        pass
    
    @discord.ui.button(label="📝 Create Panel", style=discord.ButtonStyle.primary)
    async def create_panel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🚧 Ticket panel creation coming soon!", ephemeral=True)
    
    @discord.ui.button(label="⚙️ Configure", style=discord.ButtonStyle.secondary)
    async def configure_tickets(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🚧 Ticket configuration coming soon!", ephemeral=True)


class LevelRolesView(discord.ui.View):
    """Level roles configuration view"""
    
    def __init__(self, bot, guild_id: int):
        super().__init__(timeout=300)
        self.bot = bot
        self.guild_id = guild_id
    
    async def initialize(self):
        """Initialize the view (for compatibility)"""
        pass
    
    @discord.ui.button(label="➕ Add Level Role", style=discord.ButtonStyle.green)
    async def add_level_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🚧 Level role management coming soon!", ephemeral=True)
    
    @discord.ui.button(label="📋 View Roles", style=discord.ButtonStyle.secondary)
    async def view_roles(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🚧 Level role viewing coming soon!", ephemeral=True)


class AutoRolesView(discord.ui.View):
    """Auto roles configuration view"""
    
    def __init__(self, bot, guild_id: int):
        super().__init__(timeout=300)
        self.bot = bot
        self.guild_id = guild_id
    
    async def initialize(self):
        """Initialize the view (for compatibility)"""
        pass
    
    @discord.ui.button(label="🤖 Configure Auto Roles", style=discord.ButtonStyle.primary)
    async def configure_auto_roles(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🚧 Auto roles configuration coming soon!", ephemeral=True)


class ReactionRolesView(discord.ui.View):
    """Reaction roles configuration view"""
    
    def __init__(self, bot, guild_id: int):
        super().__init__(timeout=300)
        self.bot = bot
        self.guild_id = guild_id
    
    async def initialize(self):
        """Initialize the view (for compatibility)"""
        pass
    
    @discord.ui.button(label="📝 Create Reaction Role", style=discord.ButtonStyle.green)
    async def create_reaction_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🚧 Reaction roles coming soon!", ephemeral=True)


class RoleMenusView(discord.ui.View):
    """Role menus configuration view"""
    
    def __init__(self, bot, guild_id: int):
        super().__init__(timeout=300)
        self.bot = bot
        self.guild_id = guild_id
    
    async def initialize(self):
        """Initialize the view (for compatibility)"""
        pass
    
    @discord.ui.button(label="📋 Create Role Menu", style=discord.ButtonStyle.primary)
    async def create_role_menu(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🚧 Role menus coming soon!", ephemeral=True)


class StatusRoleView(discord.ui.View):
    """Status role configuration view"""
    
    def __init__(self, bot, guild_id: int):
        super().__init__(timeout=300)
        self.bot = bot
        self.guild_id = guild_id
    
    async def initialize(self):
        """Initialize the view (for compatibility)"""
        pass
    
    @discord.ui.button(label="📊 Configure Status Roles", style=discord.ButtonStyle.secondary)
    async def configure_status_roles(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🚧 Status role configuration coming soon!", ephemeral=True)


class FeatureManagementView(discord.ui.View):
    """Feature management configuration view"""
    
    def __init__(self, bot, guild_id: int):
        super().__init__(timeout=300)
        self.bot = bot
        self.guild_id = guild_id
    
    async def initialize(self):
        """Initialize the view (for compatibility)"""
        pass
    
    @discord.ui.button(label="🚀 Enable Features", style=discord.ButtonStyle.green)
    async def enable_features(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🚧 Feature enablement coming soon!", ephemeral=True)
    
    @discord.ui.button(label="❌ Disable Features", style=discord.ButtonStyle.red)
    async def disable_features(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🚧 Feature disabling coming soon!", ephemeral=True)
    
    @discord.ui.button(label="📋 Feature Status", style=discord.ButtonStyle.secondary)
    async def feature_status(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🚧 Feature status viewing coming soon!", ephemeral=True)


class PrefixSettingsView(discord.ui.View):
    """Prefix settings configuration view"""
    
    def __init__(self, bot, guild_id: int):
        super().__init__(timeout=300)
        self.bot = bot
        self.guild_id = guild_id
    
    async def initialize(self):
        """Initialize the view (for compatibility)"""
        pass
    
    @discord.ui.button(label="🔧 Change Prefix", style=discord.ButtonStyle.primary)
    async def change_prefix(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🚧 Prefix changing coming soon!", ephemeral=True)
    
    @discord.ui.button(label="🔄 Reset Prefix", style=discord.ButtonStyle.secondary)
    async def reset_prefix(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🚧 Prefix reset coming soon!", ephemeral=True)


class StatusRoleSettingsView(discord.ui.View):
    """Status role settings configuration view"""
    
    def __init__(self, bot, guild_id: int):
        super().__init__(timeout=300)
        self.bot = bot
        self.guild_id = guild_id
    
    async def initialize(self):
        """Initialize the view (for compatibility)"""
        pass
    
    @discord.ui.button(label="📊 Configure Status Roles", style=discord.ButtonStyle.primary)
    async def configure_status_roles(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🚧 Status role configuration coming soon!", ephemeral=True)


class LegalInfoView(discord.ui.View):
    """Legal info configuration view"""
    
    def __init__(self, bot, guild_id: int):
        super().__init__(timeout=300)
        self.bot = bot
        self.guild_id = guild_id
    
    async def initialize(self):
        """Initialize the view (for compatibility)"""
        pass
    
    @discord.ui.button(label="📋 Legal Information", style=discord.ButtonStyle.secondary)
    async def legal_info(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🚧 Legal information coming soon!", ephemeral=True)


class ChannelSelectView(discord.ui.View):
    """Channel selector view"""
    
    def __init__(self, bot, guild_id: int):
        super().__init__(timeout=300)
        self.bot = bot
        self.guild_id = guild_id
    
    async def initialize(self):
        """Initialize the view (for compatibility)"""
        pass
    
    @discord.ui.button(label="📺 Select Channel", style=discord.ButtonStyle.primary)
    async def select_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🚧 Channel selection coming soon!", ephemeral=True)


class RegistrationSystemView(BaseSettingsView):
    """Registration system main settings view"""
    
    async def load_settings(self):
        """Load registration settings from database."""
        self.registration_settings = await self.db.registration_settings.find_one({"guild_id": self.guild_id}) or {}
        self.register_settings = await self.db.register.find_one({"guild_id": self.guild_id}) or {}
        self.role_settings = await self.db.role_settings.find_one({"guild_id": self.guild_id}) or {}
    
    def get_settings_summary(self) -> str:
        """Get registration settings summary."""
        is_enabled = self.registration_settings.get('enabled', False)
        register_channel = f"<#{self.registration_settings.get('register_channel_id')}>" if self.registration_settings.get('register_channel_id') else "Not set"
        verification_required = self.registration_settings.get('age_verification_required', False)
        auto_roles = len(self.registration_settings.get('auto_roles', []))
        
        main_role_id = self.register_settings.get('main_role_id')
        main_role = f"<@&{main_role_id}>" if main_role_id else "Not set"
        
        return (f"**System Status:** {'🟢 Enabled' if is_enabled else '🔴 Disabled'}\n"
            f"**Register Channel:** {register_channel}\n"
            f"**Main Role:** {main_role}\n"
            f"**Age Verification:** {'Required' if verification_required else 'Optional'}\n"
            f"**Auto Roles:** {auto_roles} configured\n"
            f"**Registration Count:** Loading...")
    
    @discord.ui.button(label="⚙️ Basic Setup", style=discord.ButtonStyle.primary, row=0)
    async def basic_setup(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Configure basic registration settings."""
        view = RegistrationBasicView(self.bot, self.guild_id)
        await view.initialize()
        
        embed = create_embed(
        title="⚙️ Basic Registration Setup",
        description="Configure essential registration system settings.",
        color=Colors.INFO
        )
        
        embed.add_field(
        name="Basic Settings",
        value=view.get_basic_summary(),
        inline=False
        )
        
        await interaction.response.edit_message(embed=embed, view=view)
    
    @discord.ui.button(label="🎭 Role Management", style=discord.ButtonStyle.primary, row=0)
    async def role_management(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Configure registration roles."""
        view = RegistrationRoleView(self.bot, self.guild_id)
        await view.initialize()
        
        embed = create_embed(
        title="🎭 Registration Role Management",
        description="Configure roles for different registration types and verification levels.",
        color=Colors.INFO
        )
        
        embed.add_field(
        name="Role Configuration",
        value=view.get_role_summary(),
        inline=False
        )
        
        await interaction.response.edit_message(embed=embed, view=view)
    
    @discord.ui.button(label="📋 Custom Forms", style=discord.ButtonStyle.primary, row=0)
    async def custom_forms(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Configure custom registration forms."""
        view = RegistrationFormView(self.bot, self.guild_id)
        await view.initialize()
        
        embed = create_embed(
        title="📋 Custom Registration Forms",
        description="Create and manage custom registration forms with validation.",
        color=Colors.INFO
        )
        
        embed.add_field(
        name="Form Settings",
        value=view.get_form_summary(),
        inline=False
        )
        
        await interaction.response.edit_message(embed=embed, view=view)
    
    @discord.ui.button(label="🔐 Verification", style=discord.ButtonStyle.primary, row=1)
    async def verification_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Configure verification settings."""
        view = RegistrationVerificationView(self.bot, self.guild_id)
        await view.initialize()
        
        embed = create_embed(
        title="🔐 Verification Settings",
        description="Configure age verification, rule acceptance, and verification requirements.",
        color=Colors.INFO
        )
        
        embed.add_field(
        name="Verification Configuration",
        value=view.get_verification_summary(),
        inline=False
        )
        
        await interaction.response.edit_message(embed=embed, view=view)
    
    @discord.ui.button(label="📊 Statistics & Logs", style=discord.ButtonStyle.secondary, row=1)
    async def statistics(self, interaction: discord.Interaction, button: discord.ui.Button):
        """View registration statistics."""
        view = RegistrationStatsView(self.bot, self.guild_id)
        await view.initialize()
        
        embed = create_embed(
        title="📊 Registration Statistics",
        description="View detailed registration statistics and logs.",
        color=Colors.INFO
        )
        
        embed.add_field(
        name="Statistics",
        value=await view.get_stats_summary(),
        inline=False
        )
        
        await interaction.response.edit_message(embed=embed, view=view)
    
    @discord.ui.button(label="🎨 Customization", style=discord.ButtonStyle.secondary, row=1)
    async def customization(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Configure registration UI customization."""
        view = RegistrationCustomizationView(self.bot, self.guild_id)
        await view.initialize()
        
        embed = create_embed(
        title="🎨 Registration Customization",
        description="Customize registration panels, messages, and UI elements.",
        color=Colors.INFO
        )
        
        embed.add_field(
        name="Customization Options",
        value=view.get_customization_summary(),
        inline=False
        )
        
        await interaction.response.edit_message(embed=embed, view=view)
    
    @discord.ui.button(label="🛠️ Advanced Settings", style=discord.ButtonStyle.secondary, row=2)
    async def advanced_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Configure advanced registration settings."""
        view = RegistrationAdvancedView(self.bot, self.guild_id)
        await view.initialize()
        
        embed = create_embed(
        title="🛠️ Advanced Registration Settings",
        description="Configure advanced features like automation, webhooks, and integrations.",
        color=Colors.INFO
        )
        
        embed.add_field(
        name="Advanced Configuration",
        value=view.get_advanced_summary(),
        inline=False
        )
        
        await interaction.response.edit_message(embed=embed, view=view)


class RegistrationBasicView(BaseSettingsView):
    """Basic registration settings view"""
    
    async def load_settings(self):
        """Load basic registration settings."""
        self.settings = await self.db.registration_settings.find_one({"guild_id": self.guild_id}) or {}
        self.register_settings = await self.db.register.find_one({"guild_id": self.guild_id}) or {}
    
    def get_basic_summary(self) -> str:
        """Get basic settings summary."""
        enabled = self.settings.get('enabled', False)
        channel = f"<#{self.settings.get('register_channel_id')}>" if self.settings.get('register_channel_id') else "Not set"
        welcome_message = "Enabled" if self.settings.get('welcome_message_enabled') else "Disabled"
        
        return (f"**Status:** {'🟢 Enabled' if enabled else '🔴 Disabled'}\n"
            f"**Register Channel:** {channel}\n"
            f"**Welcome Message:** {welcome_message}\n"
            f"**Registration Method:** {self.settings.get('registration_method', 'Button')}")
    
    @discord.ui.button(label="🔧 Enable/Disable System", style=discord.ButtonStyle.success, row=0)
    async def toggle_system(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Toggle registration system on/off."""
        current_status = self.settings.get('enabled', False)
        new_status = not current_status
        
        await self.db.registration_settings.update_one(
        {"guild_id": self.guild_id},
        {"$set": {"enabled": new_status}},
        upsert=True
        )
        
        status_text = "enabled" if new_status else "disabled"
        embed = create_embed(
        title="✅ Registration System Updated",
        description=f"Registration system has been **{status_text}**.",
        color=Colors.SUCCESS if new_status else Colors.WARNING
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
        # Refresh view
        await self.load_settings()
        view = RegistrationBasicView(self.bot, self.guild_id)
        await view.initialize()
    
    @discord.ui.button(label="📺 Set Register Channel", style=discord.ButtonStyle.primary, row=0)
    async def set_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Set registration channel."""
        view = ChannelSelectView(self.bot, self.guild_id)
        
        embed = create_embed(
        title="📺 Select Registration Channel",
        description="Choose the channel where users will register.",
        color=Colors.INFO
        )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @discord.ui.button(label="💬 Configure Messages", style=discord.ButtonStyle.primary, row=0)
    async def configure_messages(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Configure registration messages."""
        modal = RegistrationMessagesModal(self.bot, self.guild_id, self.settings)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="🎛️ Registration Method", style=discord.ButtonStyle.secondary, row=1)
    async def registration_method(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Choose registration method."""
        view = RegistrationMethodView(self.bot, self.guild_id)
        
        embed = create_embed(
        title="🎛️ Registration Method",
        description="Choose how users will register (Button, Command, Form, etc.)",
        color=Colors.INFO
        )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @discord.ui.button(label="📋 Send Registration Panel", style=discord.ButtonStyle.success, row=2)
    async def send_registration_panel(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Send the registration panel to current or selected channel."""
        modal = RegistrationPanelModal(self.bot, self.guild_id, self.settings)
        await interaction.response.send_modal(modal)


class RegistrationRoleView(BaseSettingsView):
    """Registration role management view"""
    
    async def load_settings(self):
        """Load role settings."""
        self.register_settings = await self.db.register.find_one({"guild_id": self.guild_id}) or {}
        self.role_settings = await self.db.role_settings.find_one({"guild_id": self.guild_id}) or {}
    
    def get_role_summary(self) -> str:
        """Get role configuration summary."""
        main_role = f"<@&{self.register_settings.get('main_role_id')}>" if self.register_settings.get('main_role_id') else "Not set"
        
        # Age roles (flexible)
        age_roles = self.register_settings.get('age_roles', {})
        age_roles_text = ", ".join([f"{age_range}: <@&{role_id}>" for age_range, role_id in age_roles.items()]) if age_roles else "Not set"
        
        # Gender roles
        gender_roles = self.register_settings.get('gender_roles', {})
        male_role = f"<@&{gender_roles.get('male_role_id')}>" if gender_roles.get('male_role_id') else "Not set"
        female_role = f"<@&{gender_roles.get('female_role_id')}>" if gender_roles.get('female_role_id') else "Not set"

        return (f"**Main Role:** {main_role}\n"
            f"**Age Roles:** {age_roles_text}\n"
            f"**Male Role:** {male_role}\n"
            f"**Female Role:** {female_role}\n"
            f"**Auto Roles:** {len(self.role_settings.get('auto_roles', []))} configured")
    
    @discord.ui.button(label="👤 Main Role", style=discord.ButtonStyle.primary, row=0)
    async def main_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Set main registration role."""
        view = RoleSelectView(self.bot, self.guild_id, "main_role", "Main registration role for all registered users")
        
        embed = create_embed(
        title="👤 Select Main Registration Role",
        description="This role will be given to all registered users.",
        color=Colors.INFO
        )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @discord.ui.button(label="🔢 Age Roles", style=discord.ButtonStyle.primary, row=0)
    async def age_roles(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Configure flexible age-based roles."""
        modal = AgeRoleConfigModal(self.bot, self.guild_id)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="⚧️ Gender Roles", style=discord.ButtonStyle.primary, row=0)
    async def gender_roles(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Configure gender-based roles."""
        view = GenderRoleConfigView(self.bot, self.guild_id)
        embed = create_embed(
        title="⚧️ Gender Role Configuration",
        description="Configure roles for male and female members.",
        color=Colors.INFO
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @discord.ui.button(label="🎮 Game Roles", style=discord.ButtonStyle.secondary, row=1, disabled=True)
    async def game_roles(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Configure game selection roles (disabled)."""
        embed = create_embed(
        title="🎮 Game Roles - Coming Soon",
        description="This feature is currently in development and will be available in a future update.",
        color=Colors.WARNING
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @discord.ui.button(label="🤖 Auto Roles", style=discord.ButtonStyle.secondary, row=1)
    async def auto_roles(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Configure automatic role assignment."""
        view = AutoRoleConfigView(self.bot, self.guild_id)
        await view.initialize()

        embed = create_embed(
        title="🤖 Automatic Role Assignment",
        description="Configure roles that are automatically assigned upon registration.",
        color=Colors.INFO
        )

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @discord.ui.button(label="🎨 Color Roles", style=discord.ButtonStyle.secondary, row=1, disabled=True)
    async def color_roles(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Configure color selection roles (disabled)."""
        embed = create_embed(
        title="🎨 Color Roles - Coming Soon",
        description="This feature is currently in development and will be available in a future update.",
        color=Colors.WARNING
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


class RegistrationFormView(BaseSettingsView):
    """Custom registration form view"""
    
    async def load_settings(self):
        """Load form settings."""
        self.form_settings = await self.db.registration_forms.find_one({"guild_id": self.guild_id}) or {}
        self.custom_fields = await self.db.registration_fields.find({"guild_id": self.guild_id}).to_list(None)
    
    def get_form_summary(self) -> str:
        """Get form configuration summary."""
        forms_enabled = self.form_settings.get('enabled', False)
        custom_fields_count = len(self.custom_fields)
        required_fields = len([f for f in self.custom_fields if f.get('required', False)])
        
        return (f"**Custom Forms:** {'🟢 Enabled' if forms_enabled else '🔴 Disabled'}\n"
            f"**Custom Fields:** {custom_fields_count} configured\n"
            f"**Required Fields:** {required_fields}\n"
            f"**Form Validation:** {'Enabled' if self.form_settings.get('validation_enabled') else 'Disabled'}")
    
    @discord.ui.button(label="📝 Create Form Field", style=discord.ButtonStyle.success, row=0)
    async def create_field(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Create a new form field."""
        modal = CreateFormFieldModal(self.bot, self.guild_id)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="📋 Manage Fields", style=discord.ButtonStyle.primary, row=0)
    async def manage_fields(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Manage existing form fields."""
        view = FormFieldManagerView(self.bot, self.guild_id, self.custom_fields)
        
        embed = create_embed(
        title="📋 Form Field Manager",
        description="Manage, edit, and delete custom registration form fields.",
        color=Colors.INFO
        )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @discord.ui.button(label="🔍 Form Preview", style=discord.ButtonStyle.secondary, row=0)
    async def form_preview(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Preview the registration form."""
        embed = create_embed(
        title="🔍 Registration Form Preview",
        description="This is how your registration form will look:",
        color=Colors.INFO
        )
        
        # Show form preview
        if self.custom_fields:
            field_list = "\n".join([f"**{field['name']}**{' (Required)' if field.get('required') else ''}: {field['description']}" for field in self.custom_fields])
            embed.add_field(name="Form Fields", value=field_list, inline=False)
        else:
            embed.add_field(name="Form Fields", value="No custom fields configured", inline=False)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)


class RegistrationVerificationView(BaseSettingsView):
    """Registration verification settings view"""
    
    async def load_settings(self):
        """Load verification settings."""
        self.verification_settings = await self.db.registration_verification.find_one({"guild_id": self.guild_id}) or {}
    
    def get_verification_summary(self) -> str:
        """Get verification settings summary."""
        age_verification = self.verification_settings.get('age_verification_required', False)
        rule_acceptance = self.verification_settings.get('rule_acceptance_required', True)
        email_verification = self.verification_settings.get('email_verification', False)
        phone_verification = self.verification_settings.get('phone_verification', False)
        
        return (f"**Age Verification:** {'Required' if age_verification else 'Optional'}\n"
            f"**Rule Acceptance:** {'Required' if rule_acceptance else 'Optional'}\n"
            f"**Email Verification:** {'Enabled' if email_verification else 'Disabled'}\n"
            f"**Phone Verification:** {'Enabled' if phone_verification else 'Disabled'}")
    
    @discord.ui.button(label="🔞 Age Verification", style=discord.ButtonStyle.primary, row=0)
    async def age_verification(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Configure age verification."""
        modal = AgeVerificationModal(self.bot, self.guild_id, self.verification_settings)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="📜 Rule Acceptance", style=discord.ButtonStyle.primary, row=0)
    async def rule_acceptance(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Configure rule acceptance."""
        modal = RuleAcceptanceModal(self.bot, self.guild_id, self.verification_settings)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="📧 Contact Verification", style=discord.ButtonStyle.secondary, row=1)
    async def contact_verification(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Configure email/phone verification."""
        view = ContactVerificationView(self.bot, self.guild_id)
        await view.initialize()
        
        embed = create_embed(
        title="📧 Contact Verification Settings",
        description="Configure email and phone number verification.",
        color=Colors.INFO
        )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class RegistrationStatsView(BaseSettingsView):
    """Registration statistics view"""
    
    async def load_settings(self):
        """Load statistics."""
        # Load will be handled by get_stats_summary
    # pass
    
    async def get_stats_summary(self) -> str:
        """Get registration statistics."""
        total_members = await self.db.members.count_documents({"guild_id": self.guild_id})
        registered_members = await self.db.members.count_documents({"guild_id": self.guild_id, "registered": True})
        age_plus_members = await self.db.members.count_documents({"guild_id": self.guild_id, "age_verified": True, "age_18_plus": True})
        
        # Recent registrations (last 7 days)
        from datetime import datetime, timedelta
        week_ago = datetime.utcnow() - timedelta(days=7)
        recent_registrations = await self.db.members.count_documents({
            "guild_id": self.guild_id, 
            "registered": True,
            "registration_date": {"$gte": week_ago}
        })
        
        registration_rate = (registered_members / total_members * 100) if total_members > 0 else 0
        
        try:
            return (f"**Total Members:** {total_members}\n"
                    f"**Registered Members:** {registered_members}\n"
                    f"**Registration Rate:** {registration_rate:.1f}%\n"
                    f"**18+ Members:** {age_plus_members}\n"
                    f"**Recent (7 days):** {recent_registrations}")
        except:
            return "**Statistics:** Could not load data"
    
    @discord.ui.button(label="📊 Detailed Stats", style=discord.ButtonStyle.primary, row=0)
    async def detailed_stats(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Show detailed statistics."""
        await interaction.response.defer(ephemeral=True)
        
        # Generate detailed stats embed
        embed = create_embed(
        title="📊 Detailed Registration Statistics",
        description="Comprehensive registration system analytics",
        color=Colors.INFO
        )
        
        # Add various statistics
        total_members = await self.db.members.count_documents({"guild_id": self.guild_id})
        registered_members = await self.db.members.count_documents({"guild_id": self.guild_id, "registered": True})
        
        # Age statistics
        age_plus = await self.db.members.count_documents({"guild_id": self.guild_id, "age_18_plus": True})
        age_minus = await self.db.members.count_documents({"guild_id": self.guild_id, "age_18_plus": False})
        
        try:
            embed.add_field(
                name="Member Statistics",
                value=f"**Total:** {total_members}\n**Registered:** {registered_members}\n**Unregistered:** {total_members - registered_members}",
                inline=True
            )
            
            embed.add_field(
                name="Age Distribution",
                value=f"**18+ Members:** {age_plus}\n**18- Members:** {age_minus}\n**Unknown:** {registered_members - age_plus - age_minus}",
                inline=True
            )
            
        except Exception as e:
            embed.add_field(name="Error", value=f"Could not load statistics: {str(e)}", inline=False)
        
        await interaction.followup.send(embed=embed, ephemeral=True)
    
    @discord.ui.button(label="📝 Export Data", style=discord.ButtonStyle.secondary, row=0)
    async def export_data(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Export registration data."""
        await interaction.response.send_message("🚧 Data export feature coming soon!", ephemeral=True)


class RegistrationCustomizationView(BaseSettingsView):
    """Registration UI customization view"""
    
    async def load_settings(self):
        """Load customization settings."""
        self.customization_settings = await self.db.registration_customization.find_one({"guild_id": self.guild_id}) or {}
    
    def get_customization_summary(self) -> str:
        """Get customization summary."""
        custom_embed = self.customization_settings.get('custom_embed_enabled', False)
        custom_buttons = self.customization_settings.get('custom_buttons_enabled', False)
        custom_colors = self.customization_settings.get('custom_colors_enabled', False)
        
        return (f"**Custom Embeds:** {'Enabled' if custom_embed else 'Disabled'}\n"
            f"**Custom Buttons:** {'Enabled' if custom_buttons else 'Disabled'}\n"
            f"**Custom Colors:** {'Enabled' if custom_colors else 'Disabled'}\n"
            f"**Theme:** {self.customization_settings.get('theme', 'Default')}")
    
    @discord.ui.button(label="🎨 Embed Customization", style=discord.ButtonStyle.primary, row=0)
    async def embed_customization(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Customize registration embeds."""
        modal = EmbedCustomizationModal(self.bot, self.guild_id, self.customization_settings)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="🔘 Button Customization", style=discord.ButtonStyle.primary, row=0)
    async def button_customization(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Customize registration buttons."""
        modal = ButtonCustomizationModal(self.bot, self.guild_id, self.customization_settings)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="🌈 Color Themes", style=discord.ButtonStyle.secondary, row=1)
    async def color_themes(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Choose color themes."""
        view = ColorThemeView(self.bot, self.guild_id)
        
        embed = create_embed(
        title="🌈 Registration Color Themes",
        description="Choose a color theme for your registration system.",
        color=Colors.INFO
        )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class RegistrationAdvancedView(BaseSettingsView):
    """Advanced registration settings view"""
    
    async def load_settings(self):
        """Load advanced settings."""
        self.advanced_settings = await self.db.registration_advanced.find_one({"guild_id": self.guild_id}) or {}
    
    def get_advanced_summary(self) -> str:
        """Get advanced settings summary."""
        automation = self.advanced_settings.get('automation_enabled', False)
        webhooks = self.advanced_settings.get('webhooks_enabled', False)
        api_access = self.advanced_settings.get('api_access_enabled', False)
        
        return (f"**Automation:** {'Enabled' if automation else 'Disabled'}\n"
            f"**Webhooks:** {'Enabled' if webhooks else 'Disabled'}\n"
            f"**API Access:** {'Enabled' if api_access else 'Disabled'}\n"
            f"**Auto Cleanup:** {'Enabled' if self.advanced_settings.get('auto_cleanup') else 'Disabled'}")
    
    @discord.ui.button(label="🤖 Automation", style=discord.ButtonStyle.primary, row=0)
    async def automation_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Configure automation settings."""
        modal = AutomationSettingsModal(self.bot, self.guild_id, self.advanced_settings)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="🔗 Webhooks", style=discord.ButtonStyle.primary, row=0)
    async def webhook_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Configure webhook integrations."""
        view = WebhookConfigView(self.bot, self.guild_id)
        await view.initialize()
        
        embed = create_embed(
        title="🔗 Webhook Configuration",
        description="Configure webhooks for registration events.",
        color=Colors.INFO
        )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @discord.ui.button(label="🔧 Maintenance", style=discord.ButtonStyle.secondary, row=1)
    async def maintenance_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Configure maintenance and cleanup."""
        view = MaintenanceConfigView(self.bot, self.guild_id)
        await view.initialize()
        
        embed = create_embed(
        title="🔧 Maintenance Configuration",
        description="Configure automatic cleanup and maintenance tasks.",
        color=Colors.INFO
        )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


# Missing Modal Classes - Placeholder Implementations

class RegistrationMessagesModal(discord.ui.Modal, title="Registration Messages"):
    """Modal for configuring registration messages."""
    
    welcome_message = discord.ui.TextInput(
        label="Welcome Message",
        placeholder="Welcome message for new registrants",
        style=discord.TextStyle.paragraph,
        max_length=1000,
        required=False
    )
    
    def __init__(self, bot, guild_id: int, settings: dict):
        super().__init__()
        self.bot = bot
        self.guild_id = guild_id
        self.settings = settings
        self.db = db_manager.get_database()
        
        if settings.get('welcome_message'):
            self.welcome_message.default = settings['welcome_message']
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle message configuration submission."""
        updates = {}
        if self.welcome_message.value:
            updates['welcome_message'] = self.welcome_message.value
            updates['welcome_message_enabled'] = True
        
        try:
            await self.db.registration_settings.update_one(
                {"guild_id": self.guild_id},
                {"$set": updates},
                upsert=True
            )
            
            embed = create_embed(
                title="✅ Registration Messages Updated",
                description="Registration messages have been configured.",
                color=Colors.SUCCESS
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            embed = create_embed(
                title="❌ Error",
                description=f"Failed to update messages: {str(e)}",
                color=Colors.ERROR
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)


class CreateFormFieldModal(discord.ui.Modal, title="Create Form Field"):
    """Modal for creating custom form fields."""
    
    field_name = discord.ui.TextInput(
        label="Field Name",
        placeholder="Name of the form field",
        max_length=50,
        required=True
    )
    
    field_description = discord.ui.TextInput(
        label="Field Description",
        placeholder="Description or prompt for users",
        style=discord.TextStyle.paragraph,
        max_length=500,
        required=True
    )
    
    def __init__(self, bot, guild_id: int):
        super().__init__()
        self.bot = bot
        self.guild_id = guild_id
        self.db = db_manager.get_database()
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle form field creation."""
        field_data = {
            "guild_id": self.guild_id,
            "name": self.field_name.value,
            "description": self.field_description.value,
            "required": False,
            "field_type": "text",
            "created_at": datetime.utcnow()
        }
        
        try:
            await self.db.registration_fields.insert_one(field_data)
            
            embed = create_embed(
                title="✅ Form Field Created",
                description=f"Custom field '{self.field_name.value}' has been created.",
                color=Colors.SUCCESS
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            embed = create_embed(
                title="❌ Error",
                description=f"Failed to create form field: {str(e)}",
                color=Colors.ERROR
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)


class AgeVerificationModal(discord.ui.Modal, title="Age Verification Settings"):
    """Modal for age verification configuration."""
    
    age_verification_required = discord.ui.TextInput(
        label="Age Verification Required (true/false)",
        placeholder="true veya false",
        max_length=5,
        required=True,
        default="false"
    )
    
    minimum_age = discord.ui.TextInput(
        label="Minimum Age",
        placeholder="18",
        max_length=2,
        required=False,
        default="18"
    )
    
    def __init__(self, bot, guild_id: int, settings: dict):
        super().__init__()
        self.bot = bot
        self.guild_id = guild_id
        self.settings = settings
        self.db = db_manager.get_database()
        
        # Set current values
        if settings.get('age_verification_required'):
            self.age_verification_required.default = str(settings['age_verification_required']).lower()
        if settings.get('minimum_age'):
            self.minimum_age.default = str(settings['minimum_age'])
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle age verification settings."""
        age_required = self.age_verification_required.value.lower() == 'true'
        min_age = int(self.minimum_age.value) if self.minimum_age.value else 18
        
        try:
            await self.db.registration_verification.update_one(
                {"guild_id": self.guild_id},
                {"$set": {
                    "age_verification_required": age_required,
                    "minimum_age": min_age
                }},
                upsert=True
            )
            
            embed = create_embed(
                title="✅ Age Verification Updated",
                description=f"Age verification is now {'required' if age_required else 'optional'} (minimum age: {min_age})",
                color=Colors.SUCCESS
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            embed = create_embed(
                title="❌ Error",
                description=f"Failed to update age verification: {str(e)}",
                color=Colors.ERROR
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)


class RuleAcceptanceModal(discord.ui.Modal, title="Rule Acceptance Settings"):
    """Modal for rule acceptance configuration."""
    
    rule_acceptance_required = discord.ui.TextInput(
        label="Rule Acceptance Required (true/false)",
        placeholder="true veya false",
        max_length=5,
        required=True,
        default="true"
    )
    
    rules_channel = discord.ui.TextInput(
        label="Rules Channel ID",
        placeholder="Kurallar kanalının ID'si",
        max_length=20,
        required=False
    )
    
    def __init__(self, bot, guild_id: int, settings: dict):
        super().__init__()
        self.bot = bot
        self.guild_id = guild_id
        self.settings = settings
        self.db = db_manager.get_database()
        
        # Set current values
        if settings.get('rule_acceptance_required') is not None:
            self.rule_acceptance_required.default = str(settings['rule_acceptance_required']).lower()
        if settings.get('rules_channel_id'):
            self.rules_channel.default = str(settings['rules_channel_id'])
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle rule acceptance settings."""
        rule_required = self.rule_acceptance_required.value.lower() == 'true'
        rules_channel_id = None
        
        try:
            if self.rules_channel.value:
                try:
                    rules_channel_id = int(self.rules_channel.value)
                except ValueError:
                    pass
            
            await self.db.registration_verification.update_one(
                {"guild_id": self.guild_id},
                {"$set": {
                    "rule_acceptance_required": rule_required,
                    "rules_channel_id": rules_channel_id
                }},
                upsert=True
            )
            
            embed = create_embed(
                title="✅ Rule Acceptance Updated",
                description=f"Rule acceptance is now {'required' if rule_required else 'optional'}",
                color=Colors.SUCCESS
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            embed = create_embed(
                title="❌ Error",
                description=f"Failed to update rule acceptance: {str(e)}",
                color=Colors.ERROR
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)


class EmbedCustomizationModal(discord.ui.Modal, title="Embed Customization"):
    """Modal for embed customization."""
    
    def __init__(self, bot, guild_id: int, settings: dict):
        super().__init__()
        self.bot = bot
        self.guild_id = guild_id
        self.settings = settings
        self.db = db_manager.get_database()
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle embed customization."""
        embed = create_embed(
        title="🚧 Coming Soon",
        description="Embed customization will be available soon!",
        color=Colors.INFO
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


class ButtonCustomizationModal(discord.ui.Modal, title="Button Customization"):
    """Modal for button customization."""
    
    def __init__(self, bot, guild_id: int, settings: dict):
        super().__init__()
        self.bot = bot
        self.guild_id = guild_id
        self.settings = settings
        self.db = db_manager.get_database()
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle button customization."""
        embed = create_embed(
        title="🚧 Coming Soon",
        description="Button customization will be available soon!",
        color=Colors.INFO
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


class AutomationSettingsModal(discord.ui.Modal, title="Automation Settings"):
    """Modal for automation configuration."""
    
    def __init__(self, bot, guild_id: int, settings: dict):
        super().__init__()
        self.bot = bot
        self.guild_id = guild_id
        self.settings = settings
        self.db = db_manager.get_database()
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle automation settings."""
        embed = create_embed(
        title="🚧 Coming Soon",
        description="Automation configuration will be available soon!",
        color=Colors.INFO
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


# Missing View Classes - Placeholder Implementations

class RegistrationMethodView(discord.ui.View):
    """Registration method selection view"""
    
    def __init__(self, bot, guild_id: int):
        super().__init__(timeout=300)
        self.bot = bot
        self.guild_id = guild_id
    
    @discord.ui.button(label="🔘 Button Registration", style=discord.ButtonStyle.primary)
    async def button_method(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🚧 Button registration setup coming soon!", ephemeral=True)
    
    @discord.ui.button(label="📝 Form Registration", style=discord.ButtonStyle.secondary)
    async def form_method(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🚧 Form registration setup coming soon!", ephemeral=True)


class RoleSelectView(discord.ui.View):
    """Role selection view"""
    
    def __init__(self, bot, guild_id: int, role_type: str, description: str):
        super().__init__(timeout=300)
        self.bot = bot
        self.guild_id = guild_id
        self.role_type = role_type
        self.description = description
    
    @discord.ui.button(label="🎭 Select Role", style=discord.ButtonStyle.primary)
    async def select_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🚧 Role selection coming soon!", ephemeral=True)


class AgeRoleConfigView(discord.ui.View):
    """Age role configuration view"""
    
    def __init__(self, bot, guild_id: int):
        super().__init__(timeout=300)
        self.bot = bot
        self.guild_id = guild_id
    
    async def initialize(self):
        pass
    
    @discord.ui.button(label="🔞 18+ Role", style=discord.ButtonStyle.primary)
    async def age_plus_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🚧 Age role configuration coming soon!", ephemeral=True)


class GameRoleConfigView(discord.ui.View):
    """Game role configuration view"""
    
    def __init__(self, bot, guild_id: int):
        super().__init__(timeout=300)
        self.bot = bot
        self.guild_id = guild_id
    
    async def initialize(self):
        pass
    
    @discord.ui.button(label="🎮 Add Game Role", style=discord.ButtonStyle.success)
    async def add_game_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🚧 Game role configuration coming soon!", ephemeral=True)


class AutoRoleConfigView(discord.ui.View):
    """Auto role configuration view"""
    
    def __init__(self, bot, guild_id: int):
        super().__init__(timeout=300)
        self.bot = bot
        self.guild_id = guild_id
    
    async def initialize(self):
        pass
    
    @discord.ui.button(label="🤖 Configure Auto Roles", style=discord.ButtonStyle.primary)
    async def configure_auto_roles(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🚧 Auto role configuration coming soon!", ephemeral=True)


class ColorRoleConfigView(discord.ui.View):
    """Color role configuration view"""
    
    def __init__(self, bot, guild_id: int):
        super().__init__(timeout=300)
        self.bot = bot
        self.guild_id = guild_id
    
    async def initialize(self):
        pass
    
    @discord.ui.button(label="🎨 Add Color Role", style=discord.ButtonStyle.success)
    async def add_color_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🚧 Color role configuration coming soon!", ephemeral=True)


class FormFieldManagerView(discord.ui.View):
    """Form field manager view"""
    
    def __init__(self, bot, guild_id: int, fields: list):
        super().__init__(timeout=300)
        self.bot = bot
        self.guild_id = guild_id
        self.fields = fields
    
    @discord.ui.button(label="📝 Edit Fields", style=discord.ButtonStyle.primary)
    async def edit_fields(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🚧 Field editing coming soon!", ephemeral=True)


class ContactVerificationView(discord.ui.View):
    """Contact verification view"""
    
    def __init__(self, bot, guild_id: int):
        super().__init__(timeout=300)
        self.bot = bot
        self.guild_id = guild_id
    
    async def initialize(self):
        pass
    
    @discord.ui.button(label="📧 Email Verification", style=discord.ButtonStyle.primary)
    async def email_verification(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🚧 Email verification coming soon!", ephemeral=True)


class ColorThemeView(discord.ui.View):
    """Color theme selection view"""
    
    def __init__(self, bot, guild_id: int):
        super().__init__(timeout=300)
        self.bot = bot
        self.guild_id = guild_id
    
    @discord.ui.button(label="🔵 Blue Theme", style=discord.ButtonStyle.primary)
    async def blue_theme(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🚧 Theme selection coming soon!", ephemeral=True)


class WebhookConfigView(discord.ui.View):
    """Webhook configuration view"""
    
    def __init__(self, bot, guild_id: int):
        super().__init__(timeout=300)
        self.bot = bot
        self.guild_id = guild_id
    
    async def initialize(self):
        pass
    
    @discord.ui.button(label="🔗 Add Webhook", style=discord.ButtonStyle.success)
    async def add_webhook(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🚧 Webhook configuration coming soon!", ephemeral=True)


class MaintenanceConfigView(discord.ui.View):
    """Maintenance configuration view"""
    
    def __init__(self, bot, guild_id: int):
        super().__init__(timeout=300)
        self.bot = bot
        self.guild_id = guild_id
    
    async def initialize(self):
        pass
    
    @discord.ui.button(label="🔧 Configure Cleanup", style=discord.ButtonStyle.primary)
    async def configure_cleanup(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🚧 Maintenance configuration coming soon!", ephemeral=True)


class RegistrationPanelModal(discord.ui.Modal, title="Kayıt Paneli Gönder"):
    """Modal for sending registration panel."""
    
    channel_id = discord.ui.TextInput(
        label="Kanal ID (Boş bırakırsanız mevcut kanal)",
        placeholder="Kayıt panelinin gönderileceği kanalın ID'si",
        max_length=20,
        required=False
    )
    
    panel_title = discord.ui.TextInput(
        label="Panel Başlığı",
        placeholder="Sunucu Kayıt Sistemi",
        default="📝 Sunucu Kayıt Sistemi",
        max_length=100,
        required=False
    )
    
    panel_description = discord.ui.TextInput(
        label="Panel Açıklaması",
        placeholder="Sunucumuza hoş geldiniz! Aşağıdaki butona tıklayarak kayıt olabilirsiniz.",
        style=discord.TextStyle.paragraph,
        max_length=1000,
        required=False,
        default="Sunucumuza hoş geldiniz! Aşağıdaki butona tıklayarak kayıt olabilirsiniz."
    )
    
    def __init__(self, bot, guild_id: int, settings: dict):
        super().__init__()
        self.bot = bot
        self.guild_id = guild_id
        self.settings = settings
        self.db = db_manager.get_database()
    
    async def on_submit(self, interaction: discord.Interaction):
        """Send the registration panel."""
        try:
            if self.channel_id.value:
                try:
                    target_channel = self.bot.get_channel(int(self.channel_id.value))
                    if not target_channel:
                        raise ValueError("Channel not found")
                except (ValueError, TypeError):
                    await interaction.response.send_message("❌ Geçersiz kanal ID'si!", ephemeral=True)
                    return
            else:
                target_channel = interaction.channel
            
            if not target_channel.permissions_for(interaction.guild.me).send_messages:
                await interaction.response.send_message("❌ Bu kanala mesaj gönderme iznim yok!", ephemeral=True)
                return
            
            await self.send_registration_panel(target_channel, interaction)
            
        except Exception as e:
            embed = create_embed(
                title="❌ Hata",
                description=f"Kayıt paneli gönderilirken hata oluştu: {str(e)}",
                color=Colors.ERROR
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
    
    async def send_registration_panel(self, channel, interaction):
        """Send the actual registration panel."""
        # Import create_register_card
        from src.utils.community.turkoyto.card_renderer import create_register_card
        
        # Get current registration stats
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        try:
            today_registrations = await self.db.members.count_documents({
                "guild_id": self.guild_id,
                "registered": True,
                "registration_date": {"$gte": today}
            }) if self.db is not None else 0
        except:
            today_registrations = 0

        # Create registration statistics card
        stats_card_path = None
        # Get Register cog's MongoDB connection
        bot_register_cog = self.bot.get_cog("Register")
        try:
            mongo_db = bot_register_cog.mongo_db if bot_register_cog else None
            stats_card_path = await create_register_card(self.bot, interaction.guild, mongo_db)
        except Exception as card_error:
            logger.error(f"Error creating registration statistics card: {card_error}")
            stats_card_path = None

        # Create main embed
        embed = create_embed(
        title=self.panel_title.value or "📝 Sunucu Kayıt Sistemi",
        description=self.panel_description.value or "Sunucumuza hoş geldiniz! Aşağıdaki butona tıklayarak kayıt olabilirsiniz.",
        color=0x5865F2  # Discord Blurple
        )

        # Add instructions field
        embed.add_field(
        name="📋 Nasıl Kayıt Olursunuz?",
        value="Kaydınızı tamamlamak için aşağıdaki adımları takip edin:\n"
              "• **Kayıt Ol** butonuna tıklayın\n"
              "• İsminizi ve yaşınızı girin\n"
              "• Cinsiyet bilginizi seçin (Erkek/Kadın)\n"
              "• Formu göndererek kaydınızı tamamlayın",
        inline=False
        )

        # Set image if stats card was created successfully
        if stats_card_path:
            embed.set_image(url="attachment://register_stats.png")

        # Add footer
        embed.set_footer(
        text="Butona tıklayarak kayıt formunu açabilirsiniz • Contro",
        icon_url=self.bot.user.avatar.url if self.bot.user.avatar else None
        )

        # Create registration view
        view = RegistrationPanelView(self.bot, self.guild_id)

        # Send panel with or without file attachment
        if stats_card_path:
            try:
                import os
                file = discord.File(stats_card_path, filename="register_stats.png")
                await channel.send(embed=embed, file=file, view=view)
                
                # Clean up temporary file
                os.remove(stats_card_path)
            except Exception as file_error:
                logger.error(f"Error sending file attachment: {file_error}")
                # Send without file if there's an error
                await channel.send(embed=embed, view=view)
        else:
            await channel.send(embed=embed, view=view)

        # Mark panel as sent in database
        await self.db.registration_settings.update_one(
            {"guild_id": self.guild_id},
            {"$set": {"panel_sent": True, "enabled": True}},
            upsert=True
        )

        # Confirm to admin
        success_embed = create_embed(
        title="✅ Kayıt Paneli Gönderildi",
        description=f"Kayıt paneli {channel.mention} kanalına başarıyla gönderildi.",
        color=Colors.SUCCESS
        )
        await interaction.response.send_message(embed=success_embed, ephemeral=True)


class RegistrationPanelView(discord.ui.View):
    """The actual registration panel with button."""
    
    def __init__(self, bot, guild_id: int):
        super().__init__(timeout=None)  # Persistent view
        self.bot = bot
        self.guild_id = guild_id
        self.db = db_manager.get_database()
    
    @discord.ui.button(
        label="Kayıt Ol", 
        style=discord.ButtonStyle.primary, 
        emoji="📝",
        custom_id="registration_panel_register"
    )
    async def register_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle registration button click."""
        logger.info(f"Registration button clicked by {interaction.user} (ID: {interaction.user.id}) in guild {interaction.guild.name}")
        
        # Check if user is already registered
        if self.db is not None:
            existing_member = await self.db.members.find_one({
                "guild_id": self.guild_id,
                "user_id": interaction.user.id,
                "registered": True
            })
            
            if existing_member:
                embed = create_embed(
                    title="⚠️ Zaten Kayıtlısınız",
                    description="Bu sunucuda zaten kayıtlı durumdasınız!",
                    color=Colors.WARNING
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
        
        # Open registration modal
        modal = UserRegistrationModal(self.bot, self.guild_id)
        await interaction.response.send_modal(modal)
        try:
            logger.info(f"Registration modal sent to user {interaction.user.id}")
        except Exception as e:
            import traceback
            error_traceback = traceback.format_exc()
            logger.error(f"Registration panel error for user {interaction.user.id}: {e}\n{error_traceback}")
        
        error_msg = f"Kayıt işlemi başlatılırken bir hata oluştu.\n\n**Hata Detayı:** {str(e)[:100]}...\n\nLütfen bir yetkiliyle iletişime geçin."
        
        embed = create_embed(
            title="❌ Hata",
            description=error_msg,
            color=Colors.ERROR
        )
        
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as respond_error:
            logger.error(f"Failed to respond to registration error: {respond_error}")


class UserRegistrationModal(discord.ui.Modal, title="Sunucu Kaydı"):
    """Modal for user registration with configurable fields."""
    
    name = discord.ui.TextInput(
        label="İsim",
        placeholder="Örnek: Ahmet",
        max_length=30,
        required=True
    )
    
    age = discord.ui.TextInput(
        label="Yaş",
        placeholder="Örnek: 20",
        max_length=2,
        required=True
    )
    
    gender = discord.ui.TextInput(
        label="Cinsiyet (Erkek/Kadın)",
        placeholder="Erkek veya Kadın",
        max_length=10,
        required=True
    )
    
    games = discord.ui.TextInput(
        label="Oynadığınız Oyunlar (İsteğe bağlı)",
        placeholder="CS2, Valorant, LOL, vb...",
        style=discord.TextStyle.paragraph,
        max_length=200,
        required=False
    )
    
    extra_field = discord.ui.TextInput(
        label="Ek Bilgi (İsteğe bağlı)",
        placeholder="Diğer bilgiler...",
        style=discord.TextStyle.paragraph,
        max_length=100,
        required=False
    )
    
    def __init__(self, bot, guild_id: int):
        super().__init__()
        self.bot = bot
        self.guild_id = guild_id
        self.db = db_manager.get_database()
        
        # TODO: Load custom field configuration from database
        # For now using default fields, will be configurable later
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle registration submission."""
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Validate name
            name = self.name.value.strip()
            if len(name) < 2:
                embed = create_embed(
                    title="❌ Geçersiz İsim",
                    description="İsim en az 2 karakter olmalıdır!",
                    color=Colors.ERROR
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Validate age
            try:
                age = int(self.age.value.strip())
                if age < 13 or age > 99:
                    raise ValueError()
            except ValueError:
                embed = create_embed(
                    title="❌ Geçersiz Yaş",
                    description="Yaş 13-99 arasında bir sayı olmalıdır!",
                    color=Colors.ERROR
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Validate gender
            gender_input = self.gender.value.lower().strip()
            if gender_input not in ['erkek', 'kadın', 'erkek', 'kadin']:
                embed = create_embed(
                    title="❌ Geçersiz Cinsiyet",
                    description="Cinsiyet 'Erkek' veya 'Kadın' olmalıdır!",
                    color=Colors.ERROR
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            gender = "Erkek" if gender_input in ['erkek'] else "Kadın"
            is_18_plus = age >= 18
            
            # Save to database
            if self.db is not None:
                registration_data = {
                    "guild_id": self.guild_id,
                    "user_id": interaction.user.id,
                    "registered": True,
                    "registration_date": datetime.utcnow(),
                    "name": name,
                    "age": age,
                    "age_18_plus": is_18_plus,
                    "gender": gender,
                    "games": self.games.value.strip() if self.games.value else None,
                    "extra_info": self.extra_field.value.strip() if self.extra_field.value else None,
                    "discord_tag": str(interaction.user),
                    "nickname": f"{name} | {age}"
                }
                
                await self.db.members.update_one(
                    {"guild_id": self.guild_id, "user_id": interaction.user.id},
                    {"$set": registration_data},
                    upsert=True
                )
            
            # Apply roles and get them for logging
            applied_roles = await self.apply_registration_roles(interaction, age, gender)
            
            # Update nickname
            try:
                new_nickname = f"{name} | {age}"
                await interaction.user.edit(nick=new_nickname)
            except discord.Forbidden:
                pass
            
            # Send registration log
            await self.send_registration_log(interaction, name, age, gender, applied_roles)
            
            # Success message
            embed = create_embed(
                title="✅ Kayıt Başarılı!",
                description=f"Hoş geldin **{name}**!\n\n"
                           f"**Yaş:** {age}\n"
                           f"**Cinsiyet:** {gender}",
                color=Colors.SUCCESS
            )
            
            if self.games.value:
                embed.add_field(name="🎮 Oyunlar", value=self.games.value, inline=False)
                
            if self.extra_field.value:
                embed.add_field(name="ℹ️ Ek Bilgi", value=self.extra_field.value, inline=False)
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            embed = create_embed(
                title="❌ Kayıt Hatası",
                description=f"Kayıt işlemi sırasında bir hata oluştu: {str(e)}",
                color=Colors.ERROR
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    async def apply_registration_roles(self, interaction, age: int, gender: str):
        """Apply registration roles to user with flexible age configuration."""
        applied_roles = []
        try:
            # Get role settings
            register_settings = await self.db.register.find_one({"guild_id": self.guild_id}) if self.db is not None else {}
            
            guild = interaction.guild
            member = interaction.user
            
            # Main registration role
            main_role_id = register_settings.get('main_role_id')
            if main_role_id:
                main_role = guild.get_role(main_role_id)
                if main_role:
                    await member.add_roles(main_role, reason="Registration completed")
                    applied_roles.append(main_role)
            
            # Flexible age-based roles
            age_roles = register_settings.get('age_roles', {})
            for age_range, role_id in age_roles.items():
                if self._check_age_range(age, age_range):
                    age_role = guild.get_role(role_id)
                    if age_role:
                        await member.add_roles(age_role, reason=f"Age {age} matches range {age_range}")
                        applied_roles.append(age_role)
            
            # Gender-based roles (if configured)
            gender_roles = register_settings.get('gender_roles', {})
            if gender == "Erkek" and gender_roles.get('male_role_id'):
                male_role = guild.get_role(gender_roles['male_role_id'])
                if male_role:
                    await member.add_roles(male_role, reason="Male gender role")
                    applied_roles.append(male_role)
            elif gender == "Kadın" and gender_roles.get('female_role_id'):
                female_role = guild.get_role(gender_roles['female_role_id'])
                if female_role:
                    await member.add_roles(female_role, reason="Female gender role")
                    applied_roles.append(female_role)
                
        except Exception as e:
            logger.error(f"Error applying registration roles: {e}")  # Log error but don't fail registration
        
        return applied_roles
    
    async def send_registration_log(self, interaction, name: str, age: int, gender: str, applied_roles: list):
        """Send registration log to configured channel"""
        # Get log channel from settings
        register_settings = await self.db.register.find_one({"guild_id": self.guild_id}) if self.db is not None else {}
        if not register_settings or "log_channel_id" not in register_settings:
            logger.debug(f"No register log channel configured for guild {self.guild_id}")
            return
        
        log_channel_id = register_settings["log_channel_id"]
        log_channel = interaction.guild.get_channel(int(log_channel_id))
        
        if not log_channel:
            logger.warning(f"Register log channel {log_channel_id} not found in guild {self.guild_id}")
            return
        
        # Create log embed
        embed = create_embed(
            title="🎉 Yeni Kayıt",
            color=Colors.SUCCESS
        )
        
        embed.add_field(
            name="👤 Kullanıcı",
            value=f"{interaction.user.mention} ({interaction.user})",
            inline=False
        )
        
        embed.add_field(
            name="📝 Kayıt Bilgileri",
            value=f"**İsim:** {name}\n**Yaş:** {age}\n**Cinsiyet:** {gender}",
            inline=True
        )
        
        role_mentions = [role.mention for role in applied_roles] if applied_roles else ["Rol verilmedi"]
        embed.add_field(
            name="🎭 Verilen Roller",
            value="\n".join(role_mentions),
            inline=True
        )
        
        embed.add_field(
            name="📅 Kayıt Zamanı",
            value=f"<t:{int(datetime.utcnow().timestamp())}:F>",
            inline=False
        )
        
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.set_footer(text=f"Kullanıcı ID: {interaction.user.id}")
        
        # Send log message
        try:
            await log_channel.send(embed=embed)
            logger.info(f"Registration log sent for user {interaction.user.id} to channel {log_channel.name}")
        except Exception as e:
            logger.error(f"Error sending registration log: {e}")
    
    def _check_age_range(self, age: int, age_range: str) -> bool:
        """Check if age falls within the specified range."""
        try:
            if '-' in age_range:
                # Range like "18-25"
                min_age, max_age = map(int, age_range.split('-'))
                return min_age <= age <= max_age
            elif age_range.endswith('+'):
                # Range like "18+"
                min_age = int(age_range[:-1])
                return age >= min_age
            elif age_range.endswith('-'):
                # Range like "18-" (under 18)
                max_age = int(age_range[:-1])
                return age < max_age
            else:
                # Exact age
                return age == int(age_range)
        except ValueError:
            return False




class RegistrationLogChannelView(discord.ui.View):
    """View for selecting registration log channel."""
    
    def __init__(self, bot, guild_id: int):
        super().__init__(timeout=300)
        self.bot = bot
        self.guild_id = guild_id
        self.db = db_manager.get_database()
        
        # Channel select
        channel_select = discord.ui.ChannelSelect(
        placeholder="Kayıt logları için kanal seçin",
        channel_types=[discord.ChannelType.text],
        max_values=1
        )
        
        async def channel_callback(interaction: discord.Interaction):
            selected_channel = channel_select.values[0]
            await self.save_log_channel(interaction, selected_channel.id)
        
        channel_select.callback = channel_callback
        self.add_item(channel_select)
    
    async def save_log_channel(self, interaction, channel_id: int):
        """Save log channel to database."""
        try:
            if self.db is not None:
                await self.db.register.update_one(
                    {"guild_id": self.guild_id},
                    {"$set": {"log_channel_id": channel_id}},
                    upsert=True
                )
            
            channel = interaction.guild.get_channel(channel_id)
            embed = create_embed(
                title="✅ Log Kanalı Ayarlandı",
                description=f"Kayıt logları artık {channel.mention} kanalına gönderilecek.",
                color=Colors.SUCCESS
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            embed = create_embed(
                title="❌ Hata",
                description=f"Log kanalı kaydedilirken bir hata oluştu: {str(e)}",
                color=Colors.ERROR
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)


# Missing Modal Classes Implementation

class TicketBasicSettingsModal(discord.ui.Modal, title="Basic Ticket Settings"):
    """Modal for basic ticket settings."""
    
    enabled = discord.ui.TextInput(
        label="Enable Ticket System (true/false)",
        placeholder="true or false",
        max_length=5,
        required=True,
        default="true"
    )
    
    category_id = discord.ui.TextInput(
        label="Ticket Category ID",
        placeholder="ID of the category for tickets",
        max_length=20,
        required=True
    )
    
    staff_role_ids = discord.ui.TextInput(
        label="Staff Role IDs (comma-separated)",
        placeholder="Role IDs that can manage tickets",
        style=discord.TextStyle.paragraph,
        max_length=500,
        required=False
    )
    
    show_level_card = discord.ui.TextInput(
        label="Show Level Card (true/false)",
        placeholder="Show user's level card in tickets (default: true)",
        max_length=5,
        required=False,
        default="true"
    )
    
    embed_color = discord.ui.TextInput(
        label="Embed Color (hex code, optional)",
        placeholder="e.g., #5865F2 (leave empty for level-based color)",
        max_length=7,
        required=False
    )
    
    def __init__(self, bot, guild_id: int, settings: dict):
        super().__init__()
        self.bot = bot
        self.guild_id = guild_id
        self.settings = settings
        self.db = db_manager.get_database()
        
        # Pre-fill current values
        if 'enabled' in settings:
            self.enabled.default = str(settings['enabled']).lower()
        else:
            self.enabled.default = "true"  # Default to enabled
            
        if settings.get('category_id'):
            self.category_id.default = str(settings['category_id'])
        if settings.get('support_roles'):
            self.staff_role_ids.default = ', '.join(map(str, settings['support_roles']))
        if 'show_level_card' in settings:
            self.show_level_card.default = str(settings['show_level_card']).lower()
        else:
            self.show_level_card.default = "true"  # Default to enabled
        if settings.get('embed_color'):
            self.embed_color.default = settings['embed_color']
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle basic ticket settings submission."""
        try:
            # Validate enabled setting
            enabled_value = self.enabled.value.lower().strip()
            if enabled_value not in ['true', 'false']:
                embed = create_embed(
                    title="❌ Invalid Input",
                    description="Enabled must be 'true' or 'false'.",
                    color=Colors.ERROR
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            enabled = enabled_value == 'true'
            
            # Validate category
            try:
                category_id = int(self.category_id.value)
                category = interaction.guild.get_channel(category_id)
                if not category or not isinstance(category, discord.CategoryChannel):
                    raise ValueError("Invalid category")
            except (ValueError, TypeError):
                embed = create_embed(
                    title="❌ Invalid Category",
                    description="Please provide a valid category channel ID.",
                    color=Colors.ERROR
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            # Validate show level card setting
            show_level_card_value = self.show_level_card.value.lower().strip()
            if show_level_card_value not in ['true', 'false']:
                embed = create_embed(
                    title="❌ Invalid Input",
                    description="Show Level Card must be 'true' or 'false'.",
                    color=Colors.ERROR
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            show_level_card = show_level_card_value == 'true'
            
            # Validate embed color (optional)
            embed_color = None
            if self.embed_color.value:
                color_value = self.embed_color.value.strip()
                if color_value.startswith('#') and len(color_value) == 7:
                    try:
                        # Try to convert hex to int to validate
                        int(color_value[1:], 16)
                        embed_color = int(color_value[1:], 16)
                    except ValueError:
                        embed = create_embed(
                            title="❌ Invalid Color",
                            description="Please provide a valid hex color code (e.g., #5865F2).",
                            color=Colors.ERROR
                        )
                        await interaction.response.send_message(embed=embed, ephemeral=True)
                        return
                else:
                    embed = create_embed(
                        title="❌ Invalid Color Format",
                        description="Color must be in hex format with # (e.g., #5865F2).",
                        color=Colors.ERROR
                    )
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                    return
            
            # Validate staff roles
            support_roles = []
            if self.staff_role_ids.value:
                role_ids = [r.strip() for r in self.staff_role_ids.value.split(',') if r.strip()]
                for role_id in role_ids:
                    try:
                        role = interaction.guild.get_role(int(role_id))
                        if role:
                            support_roles.append(int(role_id))
                        else:
                            embed = create_embed(
                                title="❌ Invalid Role",
                                description=f"Role with ID {role_id} not found.",
                                color=Colors.ERROR
                            )
                            await interaction.response.send_message(embed=embed, ephemeral=True)
                            return
                    except ValueError:
                        embed = create_embed(
                            title="❌ Invalid Role ID",
                            description=f"'{role_id}' is not a valid role ID.",
                            color=Colors.ERROR
                        )
                        await interaction.response.send_message(embed=embed, ephemeral=True)
                        return
            
            # Update settings
            settings_data = {
                "guild_id": self.guild_id,
                "enabled": enabled,
                "category_id": str(category_id),
                "support_roles": support_roles,
                "show_level_card": show_level_card
            }
            
            # Add embed color if provided
            if embed_color is not None:
                settings_data["embed_color"] = embed_color
            
            await self.db.ticket_settings.update_one(
                {"guild_id": self.guild_id},
                {"$set": settings_data},
                upsert=True
            )
            
            status = "enabled" if enabled else "disabled"
            embed = create_embed(
                title="✅ Settings Updated",
                description=f"Ticket system has been {status} and settings updated successfully!",
                color=Colors.SUCCESS
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            embed = create_embed(
                title="❌ Error",
                description=f"An error occurred: {str(e)}",
                color=Colors.ERROR
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)


class WelcomeSettingsModal(discord.ui.Modal, title="Welcome Settings"):
    """Modal for welcome message settings."""
    
    welcome_message = discord.ui.TextInput(
        label="Welcome Message",
        placeholder="Welcome {user} to {guild}! Variables: {user}, {guild}, {mention}",
        style=discord.TextStyle.paragraph,
        max_length=1000,
        required=False
    )
    
    welcome_channel = discord.ui.TextInput(
        label="Welcome Channel ID",
        placeholder="Channel ID for welcome messages",
        max_length=20,
        required=False
    )
    
    enable_images = discord.ui.TextInput(
        label="Enable Welcome Images (true/false)",
        placeholder="true or false",
        max_length=5,
        required=False,
        default="true"
    )
    
    def __init__(self, bot, guild_id: int, settings: dict):
        super().__init__()
        self.bot = bot
        self.guild_id = guild_id
        self.settings = settings
        self.db = db_manager.get_database()
        
        # Pre-fill current values
        if settings.get('welcome_message'):
            self.welcome_message.default = settings['welcome_message']
        if settings.get('welcome_channel_id'):
            self.welcome_channel.default = str(settings['welcome_channel_id'])
        if 'welcome_image_enabled' in settings:
            self.enable_images.default = str(settings['welcome_image_enabled']).lower()
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle welcome settings submission."""
        try:
            updates = {}
            
            if self.welcome_message.value:
                updates['welcome_message'] = self.welcome_message.value
                updates['welcome_message_enabled'] = True
            
            if self.welcome_channel.value:
                try:
                    channel_id = int(self.welcome_channel.value)
                    channel = interaction.guild.get_channel(channel_id)
                    if channel and isinstance(channel, discord.TextChannel):
                        updates['welcome_channel_id'] = channel_id
                except (ValueError, TypeError):
                    pass
            
            if self.enable_images.value:
                updates['welcome_image_enabled'] = self.enable_images.value.lower() == 'true'
            
            if updates:
                await self.db.welcomer.update_one(
                    {"guild_id": self.guild_id},
                    {"$set": updates},
                    upsert=True
                )
            
            embed = create_embed(
                title="✅ Welcome Settings Updated",
                description="Welcome message settings have been updated.",
                color=Colors.SUCCESS
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            embed = create_embed(
                title="❌ Error",
                description=f"Failed to update welcome settings: {str(e)}",
                color=Colors.ERROR
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)


class GoodbyeSettingsModal(discord.ui.Modal, title="Goodbye Settings"):
    """Modal for goodbye message settings."""
    
    goodbye_message = discord.ui.TextInput(
        label="Goodbye Message",
        placeholder="Goodbye {user}! Variables: {user}, {guild}, {mention}",
        style=discord.TextStyle.paragraph,
        max_length=1000,
        required=False
    )
    
    goodbye_channel = discord.ui.TextInput(
        label="Goodbye Channel ID",
        placeholder="Channel ID for goodbye messages",
        max_length=20,
        required=False
    )
    
    enable_images = discord.ui.TextInput(
        label="Enable Goodbye Images (true/false)",
        placeholder="true or false",
        max_length=5,
        required=False,
        default="true"
    )
    
    def __init__(self, bot, guild_id: int, settings: dict):
        super().__init__()
        self.bot = bot
        self.guild_id = guild_id
        self.settings = settings
        self.db = db_manager.get_database()
        
        # Pre-fill current values
        if settings.get('goodbye_message'):
            self.goodbye_message.default = settings['goodbye_message']
        if settings.get('channel_id'):
            self.goodbye_channel.default = str(settings['channel_id'])
        if 'image_enabled' in settings:
            self.enable_images.default = str(settings['image_enabled']).lower()
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle goodbye settings submission."""
        try:
            updates = {}
            
            if self.goodbye_message.value:
                updates['goodbye_message'] = self.goodbye_message.value
                updates['enabled'] = True
            
            if self.goodbye_channel.value:
                try:
                    channel_id = int(self.goodbye_channel.value)
                    channel = interaction.guild.get_channel(channel_id)
                    if channel and isinstance(channel, discord.TextChannel):
                        updates['channel_id'] = channel_id
                except (ValueError, TypeError):
                    pass
            
            if self.enable_images.value:
                updates['image_enabled'] = self.enable_images.value.lower() == 'true'
            
            if updates:
                await self.db.byebye.update_one(
                    {"guild_id": self.guild_id},
                    {"$set": updates},
                    upsert=True
                )
            
            embed = create_embed(
                title="✅ Goodbye Settings Updated",
                description="Goodbye message settings have been updated.",
                color=Colors.SUCCESS
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            embed = create_embed(
                title="❌ Error",
                description=f"Failed to update goodbye settings: {str(e)}",
                color=Colors.ERROR
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)


# Additional Missing Modal Classes

class XPSettingsModal(discord.ui.Modal, title="XP System Settings"):
    """Modal for XP system configuration."""
    
    xp_enabled = discord.ui.TextInput(
        label="Enable XP System (true/false)",
        placeholder="true or false",
        max_length=5,
        required=False,
        default="true"
    )
    
    xp_per_message = discord.ui.TextInput(
        label="XP per Message",
        placeholder="1-10 XP per message (default: 1)",
        max_length=2,
        required=False,
        default="1"
    )
    
    xp_cooldown = discord.ui.TextInput(
        label="XP Cooldown (seconds)",
        placeholder="Cooldown between XP gains (default: 60)",
        max_length=3,
        required=False,
        default="60"
    )
    
    def __init__(self, bot, guild_id: int, settings: dict):
        super().__init__()
        self.bot = bot
        self.guild_id = guild_id
        self.settings = settings
        self.db = db_manager.get_database()
        
        # Pre-fill current values
        if 'enabled' in settings:
            self.xp_enabled.default = str(settings['enabled']).lower()
        if settings.get('xp_per_message'):
            self.xp_per_message.default = str(settings['xp_per_message'])
        if settings.get('xp_cooldown'):
            self.xp_cooldown.default = str(settings['xp_cooldown'])
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle XP settings submission."""
        try:
            updates = {}
            
            if self.xp_enabled.value:
                updates['enabled'] = self.xp_enabled.value.lower() == 'true'
            
            if self.xp_per_message.value:
                try:
                    xp_amount = int(self.xp_per_message.value)
                    if 1 <= xp_amount <= 10:
                        updates['xp_per_message'] = xp_amount
                except (ValueError, TypeError):
                    pass
            
            if self.xp_cooldown.value:
                try:
                    cooldown = int(self.xp_cooldown.value)
                    if 0 <= cooldown <= 300:
                        updates['xp_cooldown'] = cooldown
                except (ValueError, TypeError):
                    pass
            
            if updates:
                await self.db.leveling_settings.update_one(
                    {"guild_id": self.guild_id},
                    {"$set": updates},
                    upsert=True
                )
            
            embed = create_embed(
                title="✅ XP Settings Updated",
                description="XP system settings have been updated.",
                color=Colors.SUCCESS
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            embed = create_embed(
                title="❌ Error",
                description=f"Failed to update XP settings: {str(e)}",
                color=Colors.ERROR
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)


class AutoModSettingsModal(discord.ui.Modal, title="AutoMod Settings"):
    """Modal for automod configuration."""
    
    automod_enabled = discord.ui.TextInput(
        label="Enable AutoMod (true/false)",
        placeholder="true or false",
        max_length=5,
        required=False,
        default="true"
    )
    
    spam_filter = discord.ui.TextInput(
        label="Spam Filter (true/false)",
        placeholder="Enable spam detection",
        max_length=5,
        required=False,
        default="true"
    )
    
    word_filter = discord.ui.TextInput(
        label="Word Filter (true/false)",
        placeholder="Enable bad word filtering",
        max_length=5,
        required=False,
        default="true"
    )
    
    def __init__(self, bot, guild_id: int, settings: dict):
        super().__init__()
        self.bot = bot
        self.guild_id = guild_id
        self.settings = settings
        self.db = db_manager.get_database()
        
        # Pre-fill current values
        if 'enabled' in settings:
            self.automod_enabled.default = str(settings['enabled']).lower()
        if 'spam_filter' in settings:
            self.spam_filter.default = str(settings['spam_filter']).lower()
        if 'word_filter' in settings:
            self.word_filter.default = str(settings['word_filter']).lower()
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle automod settings submission."""
        try:
            updates = {}
            
            if self.automod_enabled.value:
                updates['enabled'] = self.automod_enabled.value.lower() == 'true'
            
            if self.spam_filter.value:
                updates['spam_filter'] = self.spam_filter.value.lower() == 'true'
            
            if self.word_filter.value:
                updates['word_filter'] = self.word_filter.value.lower() == 'true'
            
            if updates:
                await self.db.automod.update_one(
                    {"guild_id": self.guild_id},
                    {"$set": updates},
                    upsert=True
                )
            
            embed = create_embed(
                title="✅ AutoMod Settings Updated",
                description="AutoMod settings have been updated.",
                color=Colors.SUCCESS
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            embed = create_embed(
                title="❌ Error",
                description=f"Failed to update AutoMod settings: {str(e)}",
                color=Colors.ERROR
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)


class SpamProtectionModal(discord.ui.Modal, title="Spam Protection"):
    """Modal for spam protection settings."""
    
    spam_enabled = discord.ui.TextInput(
        label="Enable Spam Protection (true/false)",
        placeholder="true or false",
        max_length=5,
        required=False,
        default="true"
    )
    
    message_limit = discord.ui.TextInput(
        label="Message Limit",
        placeholder="Max messages per time window (default: 5)",
        max_length=2,
        required=False,
        default="5"
    )
    
    time_window = discord.ui.TextInput(
        label="Time Window (seconds)",
        placeholder="Time window in seconds (default: 10)",
        max_length=3,
        required=False,
        default="10"
    )
    
    def __init__(self, bot, guild_id: int, settings: dict):
        super().__init__()
        self.bot = bot
        self.guild_id = guild_id
        self.settings = settings
        self.db = db_manager.get_database()
        
        # Pre-fill current values
        if 'spam_filter' in settings:
            self.spam_enabled.default = str(settings['spam_filter']).lower()
        if settings.get('spam_message_limit'):
            self.message_limit.default = str(settings['spam_message_limit'])
        if settings.get('spam_time_window'):
            self.time_window.default = str(settings['spam_time_window'])
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle spam protection settings submission."""
        try:
            updates = {}
            
            if self.spam_enabled.value:
                updates['spam_filter'] = self.spam_enabled.value.lower() == 'true'
            
            if self.message_limit.value:
                try:
                    limit = int(self.message_limit.value)
                    if 1 <= limit <= 20:
                        updates['spam_message_limit'] = limit
                except (ValueError, TypeError):
                    pass
            
            if self.time_window.value:
                try:
                    window = int(self.time_window.value)
                    if 1 <= window <= 300:
                        updates['spam_time_window'] = window
                except (ValueError, TypeError):
                    pass
            
            if updates:
                await self.db.automod.update_one(
                    {"guild_id": self.guild_id},
                    {"$set": updates},
                    upsert=True
                )
            
            embed = create_embed(
                title="✅ Spam Protection Updated",
                description="Spam protection settings have been updated.",
                color=Colors.SUCCESS
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            embed = create_embed(
                title="❌ Error",
                description=f"Failed to update spam protection: {str(e)}",
                color=Colors.ERROR
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)


class StarboardSettingsModal(discord.ui.Modal, title="Starboard Settings"):
    """Modal for starboard configuration."""
    
    starboard_enabled = discord.ui.TextInput(
        label="Enable Starboard (true/false)",
        placeholder="true or false",
        max_length=5,
        required=False,
        default="false"
    )
    
    star_threshold = discord.ui.TextInput(
        label="Star Threshold",
        placeholder="Minimum stars needed (default: 3)",
        max_length=2,
        required=False,
        default="3"
    )
    
    starboard_channel = discord.ui.TextInput(
        label="Starboard Channel ID",
        placeholder="Channel ID for starboard",
        max_length=20,
        required=False
    )
    
    def __init__(self, bot, guild_id: int, settings: dict):
        super().__init__()
        self.bot = bot
        self.guild_id = guild_id
        self.settings = settings
        self.db = db_manager.get_database()
        
        # Pre-fill current values
        if 'enabled' in settings:
            self.starboard_enabled.default = str(settings['enabled']).lower()
        if settings.get('star_threshold'):
            self.star_threshold.default = str(settings['star_threshold'])
        if settings.get('channel_id'):
            self.starboard_channel.default = str(settings['channel_id'])
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle starboard settings submission."""
        try:
            updates = {}
            
            if self.starboard_enabled.value:
                updates['enabled'] = self.starboard_enabled.value.lower() == 'true'
            
            if self.star_threshold.value:
                try:
                    threshold = int(self.star_threshold.value)
                    if 1 <= threshold <= 50:
                        updates['star_threshold'] = threshold
                except (ValueError, TypeError):
                    pass
            
            if self.starboard_channel.value:
                try:
                    channel_id = int(self.starboard_channel.value)
                    channel = interaction.guild.get_channel(channel_id)
                    if channel and isinstance(channel, discord.TextChannel):
                        updates['channel_id'] = channel_id
                except (ValueError, TypeError):
                    pass
            
            if updates:
                await self.db.starboard.update_one(
                    {"guild_id": self.guild_id},
                    {"$set": updates},
                    upsert=True
                )
            
            embed = create_embed(
                title="✅ Starboard Settings Updated",
                description="Starboard settings have been updated.",
                color=Colors.SUCCESS
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            embed = create_embed(
                title="❌ Error",
                description=f"Failed to update starboard settings: {str(e)}",
                color=Colors.ERROR
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)


class BirthdaySettingsModal(discord.ui.Modal, title="Birthday Settings"):
    """Modal for birthday system configuration."""
    
    birthday_enabled = discord.ui.TextInput(
        label="Enable Birthday System (true/false)",
        placeholder="true or false",
        max_length=5,
        required=False,
        default="false"
    )
    
    birthday_channel = discord.ui.TextInput(
        label="Birthday Channel ID",
        placeholder="Channel ID for birthday announcements",
        max_length=20,
        required=False
    )
    
    birthday_role = discord.ui.TextInput(
        label="Birthday Role ID",
        placeholder="Role ID for birthday celebrants",
        max_length=20,
        required=False
    )
    
    def __init__(self, bot, guild_id: int, settings: dict):
        super().__init__()
        self.bot = bot
        self.guild_id = guild_id
        self.settings = settings
        self.db = db_manager.get_database()
        
        # Pre-fill current values
        if 'enabled' in settings:
            self.birthday_enabled.default = str(settings['enabled']).lower()
        if settings.get('channel_id'):
            self.birthday_channel.default = str(settings['channel_id'])
        if settings.get('birthday_role_id'):
            self.birthday_role.default = str(settings['birthday_role_id'])
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle birthday settings submission."""
        try:
            updates = {}
            
            if self.birthday_enabled.value:
                updates['enabled'] = self.birthday_enabled.value.lower() == 'true'
            
            if self.birthday_channel.value:
                try:
                    channel_id = int(self.birthday_channel.value)
                    channel = interaction.guild.get_channel(channel_id)
                    if channel and isinstance(channel, discord.TextChannel):
                        updates['channel_id'] = channel_id
                except (ValueError, TypeError):
                    pass
            
            if self.birthday_role.value:
                try:
                    role_id = int(self.birthday_role.value)
                    role = interaction.guild.get_role(role_id)
                    if role:
                        updates['birthday_role_id'] = role_id
                except (ValueError, TypeError):
                    pass
            
            if updates:
                await self.db.birthday.update_one(
                    {"guild_id": self.guild_id},
                    {"$set": updates},
                    upsert=True
                )
            
            embed = create_embed(
                title="✅ Birthday Settings Updated",
                description="Birthday system settings have been updated.",
                color=Colors.SUCCESS
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            embed = create_embed(
                title="❌ Error",
                description=f"Failed to update birthday settings: {str(e)}",
                color=Colors.ERROR
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)


class AIChatSettingsModal(discord.ui.Modal, title="AI Chat Settings"):
    """Modal for AI chat configuration."""
    
    ai_chat_enabled = discord.ui.TextInput(
        label="Enable AI Chat (true/false)",
        placeholder="true or false",
        max_length=5,
        required=False,
        default="false"
    )
    
    ai_model = discord.ui.TextInput(
        label="AI Model",
        placeholder="AI model to use (default: GPT-3.5)",
        max_length=50,
        required=False,
        default="GPT-3.5"
    )
    
    response_language = discord.ui.TextInput(
        label="Response Language",
        placeholder="Language for AI responses (default: Turkish)",
        max_length=20,
        required=False,
        default="Turkish"
    )
    
    def __init__(self, bot, guild_id: int, settings: dict):
        super().__init__()
        self.bot = bot
        self.guild_id = guild_id
        self.settings = settings
        self.db = db_manager.get_database()
        
        # Pre-fill current values
        if 'ai_chat_enabled' in settings:
            self.ai_chat_enabled.default = str(settings['ai_chat_enabled']).lower()
        if settings.get('ai_model'):
            self.ai_model.default = settings['ai_model']
        if settings.get('response_language'):
            self.response_language.default = settings['response_language']
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle AI chat settings submission."""
        try:
            updates = {}
            
            if self.ai_chat_enabled.value:
                updates['ai_chat_enabled'] = self.ai_chat_enabled.value.lower() == 'true'
            
            if self.ai_model.value:
                updates['ai_model'] = self.ai_model.value
            
            if self.response_language.value:
                updates['response_language'] = self.response_language.value
            
            if updates:
                await self.db.ai_settings.update_one(
                    {"guild_id": self.guild_id},
                    {"$set": updates},
                    upsert=True
                )
            
            embed = create_embed(
                title="✅ AI Chat Settings Updated",
                description="AI chat settings have been updated.",
                color=Colors.SUCCESS
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            embed = create_embed(
                title="❌ Error",
                description=f"Failed to update AI chat settings: {str(e)}",
                color=Colors.ERROR
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)


class AIAutoModSettingsModal(discord.ui.Modal, title="AI AutoMod Settings"):
    """Modal for AI automod configuration."""
    
    ai_automod_enabled = discord.ui.TextInput(
        label="Enable AI AutoMod (true/false)",
        placeholder="true or false",
        max_length=5,
        required=False,
        default="false"
    )
    
    sensitivity = discord.ui.TextInput(
        label="Sensitivity Level (1-10)",
        placeholder="AI detection sensitivity (default: 5)",
        max_length=2,
        required=False,
        default="5"
    )
    
    def __init__(self, bot, guild_id: int, settings: dict):
        super().__init__()
        self.bot = bot
        self.guild_id = guild_id
        self.settings = settings
        self.db = db_manager.get_database()
        
        # Pre-fill current values
        if 'ai_automod_enabled' in settings:
            self.ai_automod_enabled.default = str(settings['ai_automod_enabled']).lower()
        if settings.get('ai_sensitivity'):
            self.sensitivity.default = str(settings['ai_sensitivity'])
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle AI automod settings submission."""
        try:
            updates = {}
            
            if self.ai_automod_enabled.value:
                updates['ai_automod_enabled'] = self.ai_automod_enabled.value.lower() == 'true'
            
            if self.sensitivity.value:
                try:
                    sens = int(self.sensitivity.value)
                    if 1 <= sens <= 10:
                        updates['ai_sensitivity'] = sens
                except (ValueError, TypeError):
                    pass
            
            if updates:
                await self.db.ai_settings.update_one(
                    {"guild_id": self.guild_id},
                    {"$set": updates},
                    upsert=True
                )
            
            embed = create_embed(
                title="✅ AI AutoMod Settings Updated",
                description="AI AutoMod settings have been updated.",
                color=Colors.SUCCESS
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            embed = create_embed(
                title="❌ Error",
                description=f"Failed to update AI AutoMod settings: {str(e)}",
                color=Colors.ERROR
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)


class BotSettingsModal(discord.ui.Modal, title="Bot Settings"):
    """Modal for general bot configuration."""
    
    commands_enabled = discord.ui.TextInput(
        label="Enable Commands (true/false)",
        placeholder="true or false",
        max_length=5,
        required=False,
        default="true"
    )
    
    error_reporting = discord.ui.TextInput(
        label="Error Reporting (true/false)",
        placeholder="Enable error reporting",
        max_length=5,
        required=False,
        default="true"
    )
    
    def __init__(self, bot, guild_id: int, settings: dict):
        super().__init__()
        self.bot = bot
        self.guild_id = guild_id
        self.settings = settings
        self.db = db_manager.get_database()
        
        # Pre-fill current values
        if 'commands_enabled' in settings:
            self.commands_enabled.default = str(settings['commands_enabled']).lower()
        if 'error_reporting' in settings:
            self.error_reporting.default = str(settings['error_reporting']).lower()
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle bot settings submission."""
        try:
            updates = {}
            
            if self.commands_enabled.value:
                updates['commands_enabled'] = self.commands_enabled.value.lower() == 'true'
            
            if self.error_reporting.value:
                updates['error_reporting'] = self.error_reporting.value.lower() == 'true'
            
            if updates:
                await self.db.settings.update_one(
                    {"guild_id": self.guild_id},
                    {"$set": updates},
                    upsert=True
                )
            
            embed = create_embed(
                title="✅ Bot Settings Updated",
                description="Bot settings have been updated.",
                color=Colors.SUCCESS
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            embed = create_embed(
                title="❌ Error",
                description=f"Failed to update bot settings: {str(e)}",
                color=Colors.ERROR
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)


class SystemSettingsModal(discord.ui.Modal, title="System Settings"):
    """Modal for advanced system configuration."""
    
    debug_mode = discord.ui.TextInput(
        label="Debug Mode (true/false)",
        placeholder="Enable debug mode",
        max_length=5,
        required=False,
        default="false"
    )
    
    command_cooldowns = discord.ui.TextInput(
        label="Command Cooldowns (true/false)",
        placeholder="Enable command cooldowns",
        max_length=5,
        required=False,
        default="true"
    )
    
    def __init__(self, bot, guild_id: int, settings: dict):
        super().__init__()
        self.bot = bot
        self.guild_id = guild_id
        self.settings = settings
        self.db = db_manager.get_database()
        
        # Pre-fill current values
        if 'debug_mode' in settings:
            self.debug_mode.default = str(settings['debug_mode']).lower()
        if 'command_cooldowns' in settings:
            self.command_cooldowns.default = str(settings['command_cooldowns']).lower()
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle system settings submission."""
        try:
            updates = {}
            
            if self.debug_mode.value:
                updates['debug_mode'] = self.debug_mode.value.lower() == 'true'
            
            if self.command_cooldowns.value:
                updates['command_cooldowns'] = self.command_cooldowns.value.lower() == 'true'
            
            if updates:
                await self.db.advanced_settings.update_one(
                    {"guild_id": self.guild_id},
                    {"$set": updates},
                    upsert=True
                )
            
            embed = create_embed(
                title="✅ System Settings Updated",
                description="Advanced system settings have been updated.",
                color=Colors.SUCCESS
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            embed = create_embed(
                title="❌ Error",
                description=f"Failed to update system settings: {str(e)}",
                color=Colors.ERROR
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)


class ServerFeaturesModal(discord.ui.Modal, title="Server Features Configuration"):
    """Modal for configuring server features."""
    
    community_features = discord.ui.TextInput(
        label="Community Features (true/false)",
        placeholder="Enable community features",
        max_length=5,
        required=False,
        default="true"
    )
    
    discovery = discord.ui.TextInput(
        label="Server Discovery (true/false)",
        placeholder="Enable in server discovery",
        max_length=5,
        required=False,
        default="false"
    )
    
    welcome_screen = discord.ui.TextInput(
        label="Welcome Screen (true/false)",
        placeholder="Enable welcome screen",
        max_length=5,
        required=False,
        default="true"
    )
    
    def __init__(self, bot, guild_id: int, settings: dict):
        super().__init__()
        self.bot = bot
        self.guild_id = guild_id
        self.settings = settings
        self.db = db_manager.get_database()
        
        # Pre-fill current values
        if 'community_features' in settings:
            self.community_features.default = str(settings['community_features']).lower()
        if 'discovery_enabled' in settings:
            self.discovery.default = str(settings['discovery_enabled']).lower()
        if 'welcome_screen_enabled' in settings:
            self.welcome_screen.default = str(settings['welcome_screen_enabled']).lower()
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle server features submission."""
        try:
            updates = {}
            
            if self.community_features.value:
                updates['community_features'] = self.community_features.value.lower() == 'true'
            
            if self.discovery.value:
                updates['discovery_enabled'] = self.discovery.value.lower() == 'true'
            
            if self.welcome_screen.value:
                updates['welcome_screen_enabled'] = self.welcome_screen.value.lower() == 'true'
            
            if updates:
                await self.db.server_settings.update_one(
                    {"server_id": self.guild_id},
                    {"$set": updates},
                    upsert=True
                )
            
            embed = create_embed(
                title="✅ Server Features Updated",
                description="Server feature settings have been updated.",
                color=Colors.SUCCESS
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            embed = create_embed(
                title="❌ Error",
                description=f"Failed to update server features: {str(e)}",
                color=Colors.ERROR
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)


class TicketFormQuestionsView(discord.ui.View):
    """View for managing ticket form questions."""
    
    def __init__(self, bot, guild_id: int):
        super().__init__(timeout=300)
        self.bot = bot
        self.guild_id = guild_id
        self.db = db_manager.get_database()
    
    async def initialize(self):
        """Initialize the view with current data."""
        pass
    
    @discord.ui.button(label="➕ Add Question", style=discord.ButtonStyle.success, row=0)
    async def add_question(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Add a new form question."""
        modal = TicketQuestionModal(self.bot, self.guild_id)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="📋 Manage Questions", style=discord.ButtonStyle.primary, row=0)
    async def manage_questions(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Manage existing questions."""
        questions = await self.db.ticket_form_questions.find({"guild_id": self.guild_id}).to_list(None)
        
        if not questions:
            await interaction.response.send_message(
                embed=error_embed("No questions configured yet.", title="❌ No Questions"),
                ephemeral=True
            )
            return
        
        view = TicketQuestionManagerView(self.bot, self.guild_id, questions)
        embed = create_embed(
            title="📋 Manage Form Questions",
            description="Select a question to edit or delete.",
            color=Colors.INFO
        )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

class TicketQuestionModal(discord.ui.Modal, title="Add Form Question"):
    """Modal for adding ticket form questions."""
    
    question = discord.ui.TextInput(
        label="Question",
        placeholder="What is the reason for your ticket?",
        max_length=200,
        required=True
    )
    
    question_type = discord.ui.TextInput(
        label="Question Type (short/paragraph)",
        placeholder="short or paragraph",
        max_length=10,
        required=True,
        default="short"
    )
    
    placeholder = discord.ui.TextInput(
        label="Placeholder Text",
        placeholder="Enter placeholder text for the input...",
        max_length=100,
        required=False
    )
    
    required = discord.ui.TextInput(
        label="Required (true/false)",
        placeholder="true or false",
        max_length=5,
        required=False,
        default="true"
    )
    
    def __init__(self, bot, guild_id: int, question_data: dict = None):
        super().__init__()
        self.bot = bot
        self.guild_id = guild_id
        self.db = db_manager.get_database()
        self.question_data = question_data
        
        if question_data:
            self.title = "Edit Form Question"
            self.question.default = question_data.get('question', '')
            self.question_type.default = question_data.get('type', 'short')
            self.placeholder.default = question_data.get('placeholder', '')
            self.required.default = str(question_data.get('required', True)).lower()
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle question submission."""
        # Validate inputs
        q_type = self.question_type.value.lower().strip()
        if q_type not in ['short', 'paragraph']:
            await interaction.response.send_message(
                embed=error_embed("Question type must be 'short' or 'paragraph'.", title="❌ Invalid Type"),
                ephemeral=True
            )
            return
        
        is_required = self.required.value.lower().strip() == 'true'
        
        question_data = {
            "guild_id": self.guild_id,
            "question": self.question.value,
            "type": q_type,
            "placeholder": self.placeholder.value or None,
            "required": is_required,
            "order": await self._get_next_order()
        }
        
        if self.question_data:
            # Update existing
            await self.db.ticket_form_questions.update_one(
                {"_id": self.question_data["_id"]},
                {"$set": question_data}
            )
            action = "updated"
        else:
            # Insert new
            await self.db.ticket_form_questions.insert_one(question_data)
            action = "added"
        
        embed = success_embed(
            f"Form question {action} successfully!",
            title="✅ Question Saved"
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    async def _get_next_order(self) -> int:
        """Get the next order number for questions."""
        if self.question_data:
            return self.question_data.get('order', 1)
        
        last_question = await self.db.ticket_form_questions.find_one(
            {"guild_id": self.guild_id},
            sort=[("order", -1)]
        )
        return (last_question.get('order', 0) + 1) if last_question else 1

class TicketQuestionManagerView(discord.ui.View):
    """View for managing existing questions."""
    
    def __init__(self, bot, guild_id: int, questions: list):
        super().__init__(timeout=300)
        self.bot = bot
        self.guild_id = guild_id
        self.questions = questions
        
        if questions:
            options = []
            for q in questions[:25]:  # Discord limit
                question_text = q.get('question', 'No question')[:100]
                options.append(discord.SelectOption(
                    label=question_text,
                    description=f"Type: {q.get('type', 'short')} | Required: {q.get('required', True)}",
                    value=str(q['_id'])
                ))
            
            self.add_item(TicketQuestionSelect(self.bot, self.guild_id, options, questions))

class TicketQuestionSelect(discord.ui.Select):
    """Select menu for choosing questions to edit."""
    
    def __init__(self, bot, guild_id: int, options: list, questions: list):
        super().__init__(placeholder="Select a question to edit...", options=options)
        self.bot = bot
        self.guild_id = guild_id
        self.questions = questions
    
    async def callback(self, interaction: discord.Interaction):
        """Handle question selection."""
        question_id = self.values[0]
        question = next((q for q in self.questions if str(q['_id']) == question_id), None)
        
        if not question:
            await interaction.response.send_message("Question not found.", ephemeral=True)
            return
        
        view = TicketQuestionEditView(self.bot, self.guild_id, question)
        embed = create_embed(
            title=f"Edit Question: {question.get('question', '')[:50]}...",
            description="Choose an action for this question.",
            color=Colors.INFO
        )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

class TicketQuestionEditView(discord.ui.View):
    """View for editing individual questions."""
    
    def __init__(self, bot, guild_id: int, question: dict):
        super().__init__(timeout=300)
        self.bot = bot
        self.guild_id = guild_id
        self.question = question
        self.db = db_manager.get_database()
    
    @discord.ui.button(label="✏️ Edit", style=discord.ButtonStyle.primary)
    async def edit_question(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Edit the question."""
        modal = TicketQuestionModal(self.bot, self.guild_id, self.question)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="🗑️ Delete", style=discord.ButtonStyle.danger)
    async def delete_question(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Delete the question."""
        await self.db.ticket_form_questions.delete_one({"_id": self.question["_id"]})
        
        embed = success_embed(
            f"Question '{self.question.get('question', '')[:50]}...' deleted successfully!",
            title="✅ Question Deleted"
        )
        await interaction.response.edit_message(embed=embed, view=None)

class TicketPanelSendModal(discord.ui.Modal, title="Send Ticket Panel"):
    """Modal for sending ticket panel."""
    
    channel_id = discord.ui.TextInput(
        label="Channel ID (leave empty for current channel)",
        placeholder="Channel ID where to send the panel",
        max_length=20,
        required=False
    )
    
    panel_title = discord.ui.TextInput(
        label="Panel Title",
        placeholder="Support Tickets",
        default="🎫 Support Tickets",
        max_length=100,
        required=False
    )
    
    panel_description = discord.ui.TextInput(
        label="Panel Description",
        placeholder="Click the button below to create a support ticket...",
        style=discord.TextStyle.paragraph,
        max_length=1000,
        required=False
    )
    
    def __init__(self, bot, guild_id: int, settings: dict):
        super().__init__()
        self.bot = bot
        self.guild_id = guild_id
        self.settings = settings
    
    async def on_submit(self, interaction: discord.Interaction):
        """Send the ticket panel."""
        # Determine target channel
        if self.channel_id.value:
            try:
                channel = interaction.guild.get_channel(int(self.channel_id.value))
                if not channel:
                    await interaction.response.send_message(
                        embed=error_embed("Channel not found.", title="❌ Invalid Channel"),
                        ephemeral=True
                    )
                    return
            except ValueError:
                await interaction.response.send_message(
                    embed=error_embed("Invalid channel ID.", title="❌ Invalid ID"),
                    ephemeral=True
                )
                return
        else:
            channel = interaction.channel
        
        # Create panel embed
        title = self.panel_title.value or "🎫 Support Tickets"
        description = self.panel_description.value or "Click the button below to create a support ticket and get help from our support team."
        
        embed = create_embed(
            title=title,
            description=description,
            color=Colors.INFO
        )
        embed.add_field(
            name="📋 How to create a ticket:",
            value="1️⃣ Click the button below\n2️⃣ Fill out the form\n3️⃣ Wait for staff assistance",
            inline=False
        )
        embed.set_footer(text="Our support team will respond as soon as possible!")
        
        # Create view with ticket button
        view = ModernTicketPanelView(self.bot, self.guild_id)
        
        try:
            await channel.send(embed=embed, view=view)
            
            # Mark panel as sent in database
            db = db_manager.get_database()
            await db.ticket_settings.update_one(
                {"guild_id": self.guild_id},
                {"$set": {"panel_sent": True}},
                upsert=True
            )
            
            await interaction.response.send_message(
                embed=success_embed(
                    f"Ticket panel sent to {channel.mention}!",
                    title="✅ Panel Sent"
                ),
                ephemeral=True
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                embed=error_embed("I don't have permission to send messages in that channel.", title="❌ Permission Error"),
                ephemeral=True
            )

class ModernTicketPanelView(discord.ui.View):
    """Modern ticket panel with form-based ticket creation."""
    
    def __init__(self, bot, guild_id: int):
        super().__init__(timeout=None)
        self.bot = bot
        self.guild_id = guild_id
    
    @discord.ui.button(
        label="Create Ticket",
        style=discord.ButtonStyle.primary,
        emoji="🎫",
        custom_id="modern_ticket_create"
    )
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Create a ticket with form questions."""
        # Get form questions
        db = db_manager.get_database()
        
        # Check if ticket system is enabled
        settings = await db.ticket_settings.find_one({"guild_id": self.guild_id}) or {"enabled": True}
        if not settings.get('enabled', True):
            await interaction.response.send_message(
                embed=error_embed("Ticket system is disabled.", title="❌ System Disabled"),
                ephemeral=True
            )
            return
        
        questions = await db.ticket_form_questions.find(
            {"guild_id": self.guild_id}
        ).sort("order", 1).to_list(None)
        
        # If no questions exist, create default ones
        if not questions:
            await self._create_default_questions(db)
            questions = await db.ticket_form_questions.find(
                {"guild_id": self.guild_id}
            ).sort("order", 1).to_list(None)
        
        # Check for existing ticket
        existing_ticket = await db.active_tickets.find_one({
            "guild_id": self.guild_id,
            "user_id": interaction.user.id
        })
        
        if existing_ticket:
            channel = interaction.guild.get_channel(existing_ticket.get('channel_id'))
            if channel:
                await interaction.response.send_message(
                    embed=info_embed(
                        f"You already have an open ticket: {channel.mention}",
                        title="ℹ️ Existing Ticket"
                    ),
                    ephemeral=True
                )
                return
            else:
                # Clean up orphaned ticket
                await db.active_tickets.delete_one({"_id": existing_ticket["_id"]})
        
        # Create and show form modal
        modal = ModernTicketFormModal(self.bot, self.guild_id, questions)
        await interaction.response.send_modal(modal)
    
    async def _create_default_questions(self, db):
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
        
        await db.ticket_form_questions.insert_many(default_questions)









