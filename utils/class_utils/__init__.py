"""
Utility classes for the Contro bot.
"""
import discord
from discord.ext import commands
import asyncio
from typing import List, Optional, Any, Union, Callable, Dict

class Paginator(discord.ui.View):
    """
    A paginator view for navigating through multiple pages of content.
    """
    def __init__(
        self, 
        pages: List[Union[discord.Embed, str]], 
        timeout: int = 60, 
        author_id: Optional[int] = None,
        start_page: int = 0
    ):
        """
        Initialize the paginator.
        
        Args:
            pages: List of embeds or strings to paginate
            timeout: Seconds before the paginator times out
            author_id: User ID who can interact with the paginator
            start_page: The initial page to display
        """
        super().__init__(timeout=timeout)
        self.pages = pages
        self.author_id = author_id
        self.current_page = start_page
        self.max_pages = len(pages)
        
        # Disable buttons if needed
        self.update_buttons()
    
    def update_buttons(self):
        """Update the state of navigation buttons based on current page."""
        # First page button
        self.first_page_button.disabled = (self.current_page == 0)
        
        # Previous page button
        self.prev_button.disabled = (self.current_page == 0)
        
        # Page indicator (not a button, just for display)
        self.page_indicator.label = f"{self.current_page + 1}/{self.max_pages}"
        
        # Next page button
        self.next_button.disabled = (self.current_page == self.max_pages - 1)
        
        # Last page button
        self.last_page_button.disabled = (self.current_page == self.max_pages - 1)
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """
        Check if the user is allowed to interact with the paginator.
        
        Args:
            interaction: The interaction to check
            
        Returns:
            bool: Whether the interaction is allowed
        """
        if self.author_id is None:
            return True
            
        if interaction.user.id == self.author_id:
            return True
            
        await interaction.response.send_message(
            "You cannot control this pagination because it was not started by you.", 
            ephemeral=True
        )
        return False
    
    async def on_timeout(self) -> None:
        """Disable all buttons when the view times out."""
        for item in self.children:
            item.disabled = True
    
    @discord.ui.button(emoji="⏮️", style=discord.ButtonStyle.gray)
    async def first_page_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Go to the first page."""
        self.current_page = 0
        self.update_buttons()
        await self.show_current_page(interaction)
    
    @discord.ui.button(emoji="◀️", style=discord.ButtonStyle.blurple)
    async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Go to the previous page."""
        self.current_page = max(0, self.current_page - 1)
        self.update_buttons()
        await self.show_current_page(interaction)
    
    @discord.ui.button(label="1/1", style=discord.ButtonStyle.gray, disabled=True)
    async def page_indicator(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Page indicator, not functional as a button."""
        pass
    
    @discord.ui.button(emoji="▶️", style=discord.ButtonStyle.blurple)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Go to the next page."""
        self.current_page = min(self.max_pages - 1, self.current_page + 1)
        self.update_buttons()
        await self.show_current_page(interaction)
    
    @discord.ui.button(emoji="⏭️", style=discord.ButtonStyle.gray)
    async def last_page_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Go to the last page."""
        self.current_page = self.max_pages - 1
        self.update_buttons()
        await self.show_current_page(interaction)
    
    async def show_current_page(self, interaction: discord.Interaction):
        """
        Show the current page to the user.
        
        Args:
            interaction: The interaction to respond to
        """
        current_content = self.pages[self.current_page]
        
        kwargs = {}
        if isinstance(current_content, discord.Embed):
            kwargs["embed"] = current_content
            kwargs["content"] = None
        else:
            kwargs["content"] = str(current_content)
            kwargs["embed"] = None
        
        kwargs["view"] = self
        
        await interaction.response.edit_message(**kwargs)

    @classmethod
    async def create_paginator(
        cls, 
        ctx_or_interaction: Union[commands.Context, discord.Interaction],
        pages: List[Union[discord.Embed, str]],
        timeout: int = 60,
        author_id: Optional[int] = None,
        start_page: int = 0,
        ephemeral: bool = False
    ):
        """
        Create and start a paginator.
        
        Args:
            ctx_or_interaction: Context or Interaction to respond to
            pages: List of embeds or strings to paginate
            timeout: Seconds before the paginator times out
            author_id: User ID who can interact with the paginator
            start_page: The initial page to display
            ephemeral: Whether the response should be ephemeral (only works with interactions)
            
        Returns:
            Paginator: The created paginator instance
        """
        if not pages:
            raise ValueError("Cannot create a paginator with no pages")
            
        # Set author_id from context if not specified
        if author_id is None:
            if isinstance(ctx_or_interaction, commands.Context):
                author_id = ctx_or_interaction.author.id
            else:
                author_id = ctx_or_interaction.user.id
        
        # Create the paginator
        paginator = cls(pages, timeout=timeout, author_id=author_id, start_page=start_page)
        
        # Get current page content
        current_content = pages[start_page]
        
        # Prepare kwargs based on content type
        kwargs = {"view": paginator}
        if isinstance(current_content, discord.Embed):
            kwargs["embed"] = current_content
        else:
            kwargs["content"] = str(current_content)
        
        # Send/respond based on the context type
        if isinstance(ctx_or_interaction, commands.Context):
            await ctx_or_interaction.send(**kwargs)
        else:
            # It's an interaction
            if ctx_or_interaction.response.is_done():
                await ctx_or_interaction.followup.send(**kwargs, ephemeral=ephemeral)
            else:
                kwargs["ephemeral"] = ephemeral
                await ctx_or_interaction.response.send_message(**kwargs)
        
        return paginator
