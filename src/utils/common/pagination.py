import discord
from discord import ui
import math
from typing import List, Optional, Callable, Union, Any
from .messages import info_embed, error_embed


class Paginator(ui.View):
    """Common paginator for any type of content"""
    
    def __init__(
        self,
        items: List[Any],
        items_per_page: int = 10,
        embed_builder: Optional[Callable] = None,
        timeout: int = 300,
        user: Optional[discord.Member] = None
    ):
        super().__init__(timeout=timeout)
        self.items = items
        self.items_per_page = items_per_page
        self.embed_builder = embed_builder or self._default_embed_builder
        self.user = user
        self.current_page = 0
        self.total_pages = math.ceil(len(items) / items_per_page)
        
        self._update_buttons()
    
    def _default_embed_builder(self, items: List[Any], page: int, total_pages: int) -> discord.Embed:
        """Default embed builder for simple lists"""
        embed = info_embed(
            "\n".join([f"• {item}" for item in items]),
            title=f"📄 Liste (Sayfa {page + 1}/{total_pages})"
        )
        return embed
    
    def get_page_items(self) -> List[Any]:
        """Get items for current page"""
        start = self.current_page * self.items_per_page
        end = start + self.items_per_page
        return self.items[start:end]
    
    def _update_buttons(self):
        """Update button states based on current page"""
        # First page button
        self.first_page.disabled = self.current_page == 0
        # Previous button
        self.prev_button.disabled = self.current_page == 0
        # Next button
        self.next_button.disabled = self.current_page >= self.total_pages - 1
        # Last page button
        self.last_page.disabled = self.current_page >= self.total_pages - 1
        # Update page counter
        self.page_counter.label = f"{self.current_page + 1}/{self.total_pages}"
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Check if the user can use the buttons"""
        if self.user and interaction.user.id != self.user.id:
            await interaction.response.send_message(
                embed=error_embed("Bu sayfalama kontrollerini sadece komutu kullanan kişi kullanabilir."),
                ephemeral=True
            )
            return False
        return True
    
    @ui.button(emoji="⏮️", style=discord.ButtonStyle.secondary)
    async def first_page(self, interaction: discord.Interaction, button: ui.Button):
        """Go to first page"""
        self.current_page = 0
        self._update_buttons()
        embed = self.embed_builder(self.get_page_items(), self.current_page, self.total_pages)
        await interaction.response.edit_message(embed=embed, view=self)
    
    @ui.button(emoji="◀️", style=discord.ButtonStyle.secondary)
    async def prev_button(self, interaction: discord.Interaction, button: ui.Button):
        """Go to previous page"""
        self.current_page -= 1
        self._update_buttons()
        embed = self.embed_builder(self.get_page_items(), self.current_page, self.total_pages)
        await interaction.response.edit_message(embed=embed, view=self)
    
    @ui.button(label="1/1", style=discord.ButtonStyle.secondary, disabled=True)
    async def page_counter(self, interaction: discord.Interaction, button: ui.Button):
        """Page counter (disabled)"""
        pass
    
    @ui.button(emoji="▶️", style=discord.ButtonStyle.secondary)
    async def next_button(self, interaction: discord.Interaction, button: ui.Button):
        """Go to next page"""
        self.current_page += 1
        self._update_buttons()
        embed = self.embed_builder(self.get_page_items(), self.current_page, self.total_pages)
        await interaction.response.edit_message(embed=embed, view=self)
    
    @ui.button(emoji="⏭️", style=discord.ButtonStyle.secondary)
    async def last_page(self, interaction: discord.Interaction, button: ui.Button):
        """Go to last page"""
        self.current_page = self.total_pages - 1
        self._update_buttons()
        embed = self.embed_builder(self.get_page_items(), self.current_page, self.total_pages)
        await interaction.response.edit_message(embed=embed, view=self)


class EmbedPaginator(Paginator):
    """Paginator specifically for Discord embeds"""
    
    def __init__(
        self,
        embeds: List[discord.Embed],
        timeout: int = 300,
        user: Optional[discord.Member] = None
    ):
        super().__init__(
            items=embeds,
            items_per_page=1,
            embed_builder=self._embed_builder,
            timeout=timeout,
            user=user
        )
    
    def _embed_builder(self, items: List[discord.Embed], page: int, total_pages: int) -> discord.Embed:
        """Return the embed for the current page"""
        if items:
            embed = items[0]
            # Add page info to footer if not already present
            if not embed.footer or not embed.footer.text:
                embed.set_footer(text=f"Sayfa {page + 1}/{total_pages}")
            else:
                current_footer = embed.footer.text
                embed.set_footer(text=f"{current_footer} • Sayfa {page + 1}/{total_pages}")
            return embed
        return info_embed("Gösterilecek içerik yok.")


class FieldPaginator(Paginator):
    """Paginator for embed fields"""
    
    def __init__(
        self,
        title: str,
        description: str,
        fields: List[dict],
        fields_per_page: int = 5,
        color: discord.Color = discord.Color.blue(),
        thumbnail: Optional[str] = None,
        timeout: int = 300,
        user: Optional[discord.Member] = None
    ):
        self.title = title
        self.description = description
        self.color = color
        self.thumbnail = thumbnail
        
        super().__init__(
            items=fields,
            items_per_page=fields_per_page,
            embed_builder=self._field_embed_builder,
            timeout=timeout,
            user=user
        )
    
    def _field_embed_builder(self, fields: List[dict], page: int, total_pages: int) -> discord.Embed:
        """Build embed with fields for current page"""
        embed = discord.Embed(
            title=self.title,
            description=self.description,
            color=self.color
        )
        
        if self.thumbnail:
            embed.set_thumbnail(url=self.thumbnail)
        
        for field in fields:
            embed.add_field(
                name=field.get("name", ""),
                value=field.get("value", ""),
                inline=field.get("inline", True)
            )
        
        embed.set_footer(text=f"Sayfa {page + 1}/{total_pages}")
        return embed


async def paginate(
    interaction: discord.Interaction,
    items: List[Any],
    title: str = "📄 Liste",
    description: str = "",
    items_per_page: int = 10,
    ephemeral: bool = True
) -> None:
    """
    Quick pagination helper for simple lists
    
    Args:
        interaction: Discord interaction
        items: List of items to paginate
        title: Title for the embed
        description: Description for the embed
        items_per_page: Number of items per page
        ephemeral: Whether the message should be ephemeral
    """
    if not items:
        embed = info_embed("Gösterilecek öğe yok.", title=title)
        await interaction.response.send_message(embed=embed, ephemeral=ephemeral)
        return
    
    def embed_builder(page_items: List[Any], page: int, total_pages: int) -> discord.Embed:
        embed = discord.Embed(
            title=title,
            description=description or f"Toplam {len(items)} öğe",
            color=discord.Color.blue()
        )
        
        # Add items as a single field or multiple fields based on content
        if page_items:
            content = "\n".join([f"`{i+1 + page*items_per_page}.` {item}" for i, item in enumerate(page_items)])
            if len(content) <= 1024:
                embed.add_field(name="📋 Öğeler", value=content, inline=False)
            else:
                # Split into multiple fields if too long
                for i, item in enumerate(page_items):
                    embed.add_field(
                        name=f"#{i+1 + page*items_per_page}",
                        value=str(item)[:1024],
                        inline=False
                    )
        
        embed.set_footer(text=f"Sayfa {page + 1}/{total_pages} • Toplam {len(items)} öğe")
        return embed
    
    paginator = Paginator(
        items=items,
        items_per_page=items_per_page,
        embed_builder=embed_builder,
        user=interaction.user
    )
    
    initial_embed = embed_builder(paginator.get_page_items(), 0, paginator.total_pages)
    await interaction.response.send_message(embed=initial_embed, view=paginator, ephemeral=ephemeral) 