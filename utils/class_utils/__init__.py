"""
Utility classes for the Contro bot.
"""
import discord
from discord.ext import commands
import asyncio
from typing import List, Optional, Any, Union, Callable, Dict
from pathlib import Path
import json

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
        """Page indicator (not clickable)."""
        await interaction.response.defer()
    
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
            ephemeral: Whether to send the paginator as ephemeral (interactions only)
            
        Returns:
            The created Paginator instance
        """
        if not pages:
            raise ValueError("Pages list cannot be empty")
        
        # Auto-detect author if not provided
        if author_id is None:
            if hasattr(ctx_or_interaction, 'author'):
                author_id = ctx_or_interaction.author.id
            elif hasattr(ctx_or_interaction, 'user'):
                author_id = ctx_or_interaction.user.id
        
        paginator = cls(pages, timeout, author_id, start_page)
        
        # Prepare initial content
        current_content = pages[start_page]
        kwargs = {"view": paginator}
        
        if isinstance(current_content, discord.Embed):
            kwargs["embed"] = current_content
        else:
            kwargs["content"] = str(current_content)
        
        # Send the paginator
        if isinstance(ctx_or_interaction, discord.Interaction):
            kwargs["ephemeral"] = ephemeral
            await ctx_or_interaction.response.send_message(**kwargs)
        else:
            await ctx_or_interaction.send(**kwargs)
        
        return paginator


class DataManager:
    """
    A utility class for managing data storage and retrieval.
    """
    
    def __init__(self, data_dir: str = "data"):
        """
        Initialize the DataManager.
        
        Args:
            data_dir: Directory to store data files
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
    
    def save_json(self, filename: str, data: Any) -> bool:
        """
        Save data to a JSON file.
        
        Args:
            filename: Name of the file (without extension)
            data: Data to save
            
        Returns:
            True if successful, False otherwise
        """
        try:
            file_path = self.data_dir / f"{filename}.json"
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Error saving JSON file {filename}: {e}")
            return False
    
    def load_json(self, filename: str, default: Any = None) -> Any:
        """
        Load data from a JSON file.
        
        Args:
            filename: Name of the file (without extension)
            default: Default value if file doesn't exist
            
        Returns:
            Loaded data or default value
        """
        try:
            file_path = self.data_dir / f"{filename}.json"
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return default
        except Exception as e:
            print(f"Error loading JSON file {filename}: {e}")
            return default


# Export classes
__all__ = ['Paginator', 'DataManager']
