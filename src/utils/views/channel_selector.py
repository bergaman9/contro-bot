import discord
from discord.ext import commands
from typing import List, Optional, Callable
import math

class ChannelSelectView(discord.ui.View):
    """Channel selection view with pagination support"""
    
    def __init__(self, channels: List[discord.TextChannel], callback: Callable, per_page: int = 20, timeout: int = 300):
        super().__init__(timeout=timeout)
        self.channels = channels
        self.callback = callback
        self.per_page = per_page
        self.current_page = 0
        self.max_pages = math.ceil(len(channels) / per_page)
        self.selected_channel = None
        
        # Add the channel select dropdown
        self.add_item(ChannelSelect(self.get_current_page_channels()))
        
        # Add pagination buttons if needed
        if self.max_pages > 1:
            self.add_pagination_buttons()
    
    def get_current_page_channels(self) -> List[discord.TextChannel]:
        """Get channels for current page"""
        start = self.current_page * self.per_page
        end = start + self.per_page
        return self.channels[start:end]
    
    def add_pagination_buttons(self):
        """Add pagination buttons"""
        # Previous button
        self.previous_button = discord.ui.Button(
            label="Previous",
            emoji="◀️",
            style=discord.ButtonStyle.secondary,
            disabled=self.current_page == 0,
            row=1
        )
        self.previous_button.callback = self.go_previous
        self.add_item(self.previous_button)
        
        # Page indicator
        self.page_button = discord.ui.Button(
            label=f"Page {self.current_page + 1}/{self.max_pages}",
            style=discord.ButtonStyle.secondary,
            disabled=True,
            row=1
        )
        self.add_item(self.page_button)
        
        # Next button
        self.next_button = discord.ui.Button(
            label="Next",
            emoji="▶️",
            style=discord.ButtonStyle.secondary,
            disabled=self.current_page >= self.max_pages - 1,
            row=1
        )
        self.next_button.callback = self.go_next
        self.add_item(self.next_button)
    
    async def go_previous(self, interaction: discord.Interaction):
        """Go to previous page"""
        self.current_page -= 1
        await self.update_view(interaction)
    
    async def go_next(self, interaction: discord.Interaction):
        """Go to next page"""
        self.current_page += 1
        await self.update_view(interaction)
    
    async def update_view(self, interaction: discord.Interaction):
        """Update the view with new page"""
        # Remove old select
        self.remove_item(self.children[0])
        
        # Add new select with current page channels
        select = ChannelSelect(self.get_current_page_channels())
        self.add_item(select)
        
        # Update pagination buttons
        if self.max_pages > 1:
            self.previous_button.disabled = self.current_page == 0
            self.next_button.disabled = self.current_page >= self.max_pages - 1
            self.page_button.label = f"Page {self.current_page + 1}/{self.max_pages}"
        
        await interaction.response.edit_message(view=self)


class ChannelSelect(discord.ui.Select):
    """Channel selection dropdown"""
    
    def __init__(self, channels: List[discord.TextChannel]):
        options = []
        for channel in channels[:25]:  # Discord limit
            options.append(
                discord.SelectOption(
                    label=channel.name,
                    value=str(channel.id),
                    description=f"#{channel.name} in {channel.category.name if channel.category else 'No Category'}",
                    emoji="📝"
                )
            )
        
        super().__init__(
            placeholder="Select a channel...",
            options=options,
            min_values=1,
            max_values=1
        )
    
    async def callback(self, interaction: discord.Interaction):
        """Handle channel selection"""
        channel_id = int(self.values[0])
        channel = interaction.guild.get_channel(channel_id)
        
        if channel:
            self.view.selected_channel = channel
            await self.view.callback(interaction, channel)
        else:
            await interaction.response.send_message(
                "❌ Channel not found!",
                ephemeral=True
            ) 