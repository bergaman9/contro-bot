import discord
from discord import ui
import math
from typing import List, Optional, Callable, Union

class ChannelSelector(discord.ui.Select):
    """Basic channel selector without pagination"""
    def __init__(self, 
                 channels: List[discord.abc.GuildChannel],
                 placeholder: str = "Kanal seçin...",
                 min_values: int = 1,
                 max_values: int = 1,
                 callback_func: Optional[Callable] = None):
        
        options = []
        for channel in channels[:25]:  # Discord limit is 25 options
            emoji = self._get_channel_emoji(channel)
            options.append(
                discord.SelectOption(
                    label=channel.name,
                    value=str(channel.id),
                    emoji=emoji,
                    description=f"#{channel.name}"
                )
            )
        
        super().__init__(
            placeholder=placeholder,
            min_values=min_values,
            max_values=max_values,
            options=options
        )
        self.callback_func = callback_func
        self.channels = channels
    
    def _get_channel_emoji(self, channel: discord.abc.GuildChannel) -> str:
        """Get appropriate emoji for channel type"""
        if isinstance(channel, discord.TextChannel):
            if channel.is_news():
                return "📢"
            elif channel.is_nsfw():
                return "🔞"
            else:
                return "💬"
        elif isinstance(channel, discord.VoiceChannel):
            return "🔊"
        elif isinstance(channel, discord.StageChannel):
            return "🎭"
        elif isinstance(channel, discord.ForumChannel):
            return "💭"
        elif isinstance(channel, discord.CategoryChannel):
            return "📁"
        else:
            return "📌"
    
    async def callback(self, interaction: discord.Interaction):
        if self.callback_func:
            await self.callback_func(interaction, self.values)
        else:
            selected_channels = [ch for ch in self.channels if str(ch.id) in self.values]
            channel_mentions = ", ".join([ch.mention for ch in selected_channels])
            await interaction.response.send_message(
                f"Seçilen kanal(lar): {channel_mentions}",
                ephemeral=True
            )


class RoleSelector(discord.ui.Select):
    """Basic role selector without pagination"""
    def __init__(self,
                 roles: List[discord.Role],
                 placeholder: str = "Rol seçin...",
                 min_values: int = 1,
                 max_values: int = 1,
                 callback_func: Optional[Callable] = None,
                 exclude_everyone: bool = True):
        
        # Filter roles
        if exclude_everyone:
            roles = [r for r in roles if r.name != "@everyone"]
        
        # Sort roles by position (highest first)
        roles = sorted(roles, key=lambda r: r.position, reverse=True)
        
        options = []
        for role in roles[:25]:  # Discord limit is 25 options
            options.append(
                discord.SelectOption(
                    label=role.name,
                    value=str(role.id),
                    emoji="🎭",
                    description=f"{len(role.members)} üye"
                )
            )
        
        super().__init__(
            placeholder=placeholder,
            min_values=min_values,
            max_values=max_values,
            options=options
        )
        self.callback_func = callback_func
        self.roles = roles
    
    async def callback(self, interaction: discord.Interaction):
        if self.callback_func:
            await self.callback_func(interaction, self.values)
        else:
            selected_roles = [r for r in self.roles if str(r.id) in self.values]
            role_mentions = ", ".join([r.mention for r in selected_roles])
            await interaction.response.send_message(
                f"Seçilen rol(ler): {role_mentions}",
                ephemeral=True
            )


class PaginatedChannelSelector(discord.ui.View):
    """Channel selector with pagination support"""
    def __init__(self,
                 channels: List[discord.abc.GuildChannel],
                 callback_func: Optional[Callable] = None,
                 placeholder: str = "Kanal seçin...",
                 min_values: int = 1,
                 max_values: int = 1,
                 channels_per_page: int = 20,
                 timeout: int = 300):
        
        super().__init__(timeout=timeout)
        self.channels = channels
        self.callback_func = callback_func
        self.placeholder = placeholder
        self.min_values = min_values
        self.max_values = max_values
        self.channels_per_page = channels_per_page
        self.current_page = 0
        self.total_pages = math.ceil(len(channels) / channels_per_page)
        self.selected_channels = []
        
        self._update_view()
    
    def _get_page_channels(self) -> List[discord.abc.GuildChannel]:
        """Get channels for current page"""
        start = self.current_page * self.channels_per_page
        end = start + self.channels_per_page
        return self.channels[start:end]
    
    def _update_view(self):
        """Update the view with current page items"""
        self.clear_items()
        
        # Add channel selector
        page_channels = self._get_page_channels()
        if page_channels:
            selector = ChannelSelector(
                channels=page_channels,
                placeholder=self.placeholder,
                min_values=self.min_values,
                max_values=min(self.max_values, len(page_channels)),
                callback_func=self._channel_selected
            )
            self.add_item(selector)
        
        # Add navigation buttons
        if self.total_pages > 1:
            # Previous button
            prev_button = discord.ui.Button(
                emoji="◀️",
                style=discord.ButtonStyle.secondary,
                disabled=self.current_page == 0
            )
            prev_button.callback = self._previous_page
            self.add_item(prev_button)
            
            # Page indicator
            page_button = discord.ui.Button(
                label=f"{self.current_page + 1}/{self.total_pages}",
                style=discord.ButtonStyle.secondary,
                disabled=True
            )
            self.add_item(page_button)
            
            # Next button
            next_button = discord.ui.Button(
                emoji="▶️",
                style=discord.ButtonStyle.secondary,
                disabled=self.current_page >= self.total_pages - 1
            )
            next_button.callback = self._next_page
            self.add_item(next_button)
        
        # Add confirm button if channels are selected
        if self.selected_channels:
            confirm_button = discord.ui.Button(
                label="Onayla",
                emoji="✅",
                style=discord.ButtonStyle.success
            )
            confirm_button.callback = self._confirm_selection
            self.add_item(confirm_button)
    
    async def _channel_selected(self, interaction: discord.Interaction, values: List[str]):
        """Handle channel selection"""
        # Update selected channels
        for value in values:
            if value not in [str(ch.id) for ch in self.selected_channels]:
                channel = discord.utils.get(self.channels, id=int(value))
                if channel:
                    self.selected_channels.append(channel)
        
        self._update_view()
        
        selected_names = ", ".join([f"#{ch.name}" for ch in self.selected_channels])
        embed = discord.Embed(
            title="📌 Kanal Seçimi",
            description=f"**Seçilen kanallar:** {selected_names}",
            color=discord.Color.blue()
        )
        await interaction.response.edit_message(embed=embed, view=self)
    
    async def _previous_page(self, interaction: discord.Interaction):
        """Go to previous page"""
        self.current_page -= 1
        self._update_view()
        await interaction.response.edit_message(view=self)
    
    async def _next_page(self, interaction: discord.Interaction):
        """Go to next page"""
        self.current_page += 1
        self._update_view()
        await interaction.response.edit_message(view=self)
    
    async def _confirm_selection(self, interaction: discord.Interaction):
        """Confirm the selection"""
        if self.callback_func:
            await self.callback_func(interaction, self.selected_channels)
        else:
            channel_mentions = ", ".join([ch.mention for ch in self.selected_channels])
            await interaction.response.edit_message(
                content=f"Seçilen kanallar: {channel_mentions}",
                embed=None,
                view=None
            )


class PaginatedRoleSelector(discord.ui.View):
    """Role selector with pagination support"""
    def __init__(self,
                 roles: List[discord.Role],
                 callback_func: Optional[Callable] = None,
                 placeholder: str = "Rol seçin...",
                 min_values: int = 1,
                 max_values: int = 1,
                 roles_per_page: int = 20,
                 exclude_everyone: bool = True,
                 timeout: int = 300):
        
        super().__init__(timeout=timeout)
        
        # Filter and sort roles
        if exclude_everyone:
            roles = [r for r in roles if r.name != "@everyone"]
        self.roles = sorted(roles, key=lambda r: r.position, reverse=True)
        
        self.callback_func = callback_func
        self.placeholder = placeholder
        self.min_values = min_values
        self.max_values = max_values
        self.roles_per_page = roles_per_page
        self.current_page = 0
        self.total_pages = math.ceil(len(self.roles) / roles_per_page)
        self.selected_roles = []
        
        self._update_view()
    
    def _get_page_roles(self) -> List[discord.Role]:
        """Get roles for current page"""
        start = self.current_page * self.roles_per_page
        end = start + self.roles_per_page
        return self.roles[start:end]
    
    def _update_view(self):
        """Update the view with current page items"""
        self.clear_items()
        
        # Add role selector
        page_roles = self._get_page_roles()
        if page_roles:
            selector = RoleSelector(
                roles=page_roles,
                placeholder=self.placeholder,
                min_values=self.min_values,
                max_values=min(self.max_values, len(page_roles)),
                callback_func=self._role_selected,
                exclude_everyone=False  # Already filtered
            )
            self.add_item(selector)
        
        # Add navigation buttons
        if self.total_pages > 1:
            # Previous button
            prev_button = discord.ui.Button(
                emoji="◀️",
                style=discord.ButtonStyle.secondary,
                disabled=self.current_page == 0
            )
            prev_button.callback = self._previous_page
            self.add_item(prev_button)
            
            # Page indicator
            page_button = discord.ui.Button(
                label=f"{self.current_page + 1}/{self.total_pages}",
                style=discord.ButtonStyle.secondary,
                disabled=True
            )
            self.add_item(page_button)
            
            # Next button
            next_button = discord.ui.Button(
                emoji="▶️",
                style=discord.ButtonStyle.secondary,
                disabled=self.current_page >= self.total_pages - 1
            )
            next_button.callback = self._next_page
            self.add_item(next_button)
        
        # Add confirm button if roles are selected
        if self.selected_roles:
            confirm_button = discord.ui.Button(
                label="Onayla",
                emoji="✅",
                style=discord.ButtonStyle.success
            )
            confirm_button.callback = self._confirm_selection
            self.add_item(confirm_button)
    
    async def _role_selected(self, interaction: discord.Interaction, values: List[str]):
        """Handle role selection"""
        # Update selected roles
        for value in values:
            if value not in [str(r.id) for r in self.selected_roles]:
                role = discord.utils.get(self.roles, id=int(value))
                if role:
                    self.selected_roles.append(role)
        
        self._update_view()
        
        selected_names = ", ".join([r.name for r in self.selected_roles])
        embed = discord.Embed(
            title="🎭 Rol Seçimi",
            description=f"**Seçilen roller:** {selected_names}",
            color=discord.Color.blue()
        )
        await interaction.response.edit_message(embed=embed, view=self)
    
    async def _previous_page(self, interaction: discord.Interaction):
        """Go to previous page"""
        self.current_page -= 1
        self._update_view()
        await interaction.response.edit_message(view=self)
    
    async def _next_page(self, interaction: discord.Interaction):
        """Go to next page"""
        self.current_page += 1
        self._update_view()
        await interaction.response.edit_message(view=self)
    
    async def _confirm_selection(self, interaction: discord.Interaction):
        """Confirm the selection"""
        if self.callback_func:
            await self.callback_func(interaction, self.selected_roles)
        else:
            role_mentions = ", ".join([r.mention for r in self.selected_roles])
            await interaction.response.edit_message(
                content=f"Seçilen roller: {role_mentions}",
                embed=None,
                view=None
            ) 