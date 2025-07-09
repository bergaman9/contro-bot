"""UI component utility classes."""
import discord
import math
from typing import List, Optional, Any, Dict, Union

from .formatting import create_embed
from .db import async_initialize_mongodb

class Paginator(discord.ui.View):
    """
    A paginator for Discord embeds.
    
    Attributes:
        embed_list (List[discord.Embed]): The list of embeds to paginate
        current_page (int): The current page index
    """
    def __init__(self, embed_list=None, timeout=120):
        super().__init__(timeout=timeout)
        self.embed_list = embed_list or []
        self.current_page = 0
        
        # Disable buttons if not needed
        if len(self.embed_list) <= 1:
            self.first_page.disabled = True
            self.prev_page.disabled = True
            self.next_page.disabled = True
            self.last_page.disabled = True
    
    async def send_initial_message(self, ctx):
        """Send the initial message with the paginator"""
        if len(self.embed_list) > 0:
            self.update_buttons()
            await ctx.send(embed=self.embed_list[self.current_page], view=self)
        else:
            await ctx.send(embed=discord.Embed(title="No data", description="No data to display", color=discord.Color.red()))

    def update_buttons(self):
        """Update the button states based on current page"""
        self.first_page.disabled = self.current_page == 0
        self.prev_page.disabled = self.current_page == 0
        self.next_page.disabled = self.current_page == len(self.embed_list) - 1
        self.last_page.disabled = self.current_page == len(self.embed_list) - 1
        
        # Update the page counter label
        self.page_counter.label = f"Page {self.current_page + 1}/{len(self.embed_list)}"

    @discord.ui.button(emoji="⏮️", style=discord.ButtonStyle.primary)
    async def first_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Go to the first page"""
        self.current_page = 0
        self.update_buttons()
        await interaction.response.edit_message(embed=self.embed_list[self.current_page], view=self)

    @discord.ui.button(emoji="◀️", style=discord.ButtonStyle.primary)
    async def prev_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Go to the previous page"""
        if self.current_page > 0:
            self.current_page -= 1
            self.update_buttons()
            await interaction.response.edit_message(embed=self.embed_list[self.current_page], view=self)

    @discord.ui.button(label="Page", style=discord.ButtonStyle.secondary, disabled=True)
    async def page_counter(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Page counter display (non-functional button)"""
        pass

    @discord.ui.button(emoji="▶️", style=discord.ButtonStyle.primary)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Go to the next page"""
        if self.current_page < len(self.embed_list) - 1:
            self.current_page += 1
            self.update_buttons()
            await interaction.response.edit_message(embed=self.embed_list[self.current_page], view=self)

    @discord.ui.button(emoji="⏭️", style=discord.ButtonStyle.primary)
    async def last_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Go to the last page"""
        self.current_page = len(self.embed_list) - 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.embed_list[self.current_page], view=self)

    async def on_timeout(self):
        """When the view times out, disable all buttons"""
        for item in self.children:
            item.disabled = True
        
        # Try to update the message if possible
        if hasattr(self, "message") and self.message:
            try:
                await self.message.edit(view=self)
            except discord.NotFound:
                pass


class DynamicButton(discord.ui.Button):
    """A button that can execute custom callbacks"""
    
    def __init__(self, label, style=discord.ButtonStyle.primary, callback=None, **kwargs):
        super().__init__(label=label, style=style, **kwargs)
        self.custom_callback = callback
    
    async def callback(self, interaction: discord.Interaction):
        """Execute the custom callback when clicked"""
        if self.custom_callback:
            await self.custom_callback(interaction, self)
        else:
            await interaction.response.send_message("This button has no action assigned to it.", ephemeral=True)


STYLE_MAPPING = {
    "primary": discord.ButtonStyle.primary,
    "secondary": discord.ButtonStyle.secondary,
    "success": discord.ButtonStyle.success,
    "danger": discord.ButtonStyle.danger,
}


class DynamicView(discord.ui.View):
    """A view that can have buttons added to it dynamically"""
    
    def __init__(self, timeout=180):
        super().__init__(timeout=timeout)
    
    def add_button(self, label, style="primary", callback=None, row=None, **kwargs):
        """
        Add a new button to the view
        
        Parameters:
            label (str): The button label
            style (str): The button style (primary, secondary, success, danger)
            callback (callable): The function to call when the button is clicked
            row (int, optional): The row to place the button in
            **kwargs: Additional arguments to pass to the Button constructor
        """
        button_style = STYLE_MAPPING.get(style, discord.ButtonStyle.primary)
        button = DynamicButton(label=label, style=button_style, callback=callback, row=row, **kwargs)
        self.add_item(button)
        return button

    
class LinkButton(discord.ui.Button):
    """A button that opens a URL when clicked"""
    
    def __init__(self, label, url, style=discord.ButtonStyle.link, **kwargs):
        super().__init__(label=label, style=style, url=url, **kwargs)


class ReportModal(discord.ui.Modal, title='Şikayet Et'):
    """Modal for reporting messages"""
    
    reason = discord.ui.TextInput(
        label='Şikayet Sebebi',
        placeholder='Şikayet sebebinizi detaylı bir şekilde açıklayın...',
        style=discord.TextStyle.paragraph,
        min_length=10,
        max_length=1000,
    )
    
    def __init__(self, message=None):
        super().__init__()
        self.message = message
        self.mongodb = None
    
    async def on_submit(self, interaction: discord.Interaction):
        # Initialize MongoDB connection
        if not self.mongodb:
            self.mongodb = await async_initialize_mongodb()
        
        # Create a report entry
        report_data = {
            "guild_id": str(interaction.guild.id),
            "reporter_id": str(interaction.user.id),
            "reporter_name": f"{interaction.user.name}#{interaction.user.discriminator}",
            "message_id": str(self.message.id) if self.message else None,
            "message_content": self.message.content if self.message else None,
            "message_author_id": str(self.message.author.id) if self.message else None,
            "message_author_name": f"{self.message.author.name}#{self.message.author.discriminator}" if self.message else None,
            "message_channel_id": str(self.message.channel.id) if self.message else None,
            "message_channel_name": self.message.channel.name if self.message else None,
            "reason": self.reason.value,
            "timestamp": discord.utils.utcnow().isoformat(),
            "status": "pending",
        }
        
        # Save to database
        await self.mongodb.reports.insert_one(report_data)
        
        # Send confirmation to the user
        await interaction.response.send_message(
            embed=create_embed(
                "Şikayetiniz alınmıştır. Yetkili ekip en kısa sürede inceleyecektir.",
                discord.Color.green()
            ),
            ephemeral=True
        )
        
        # Try to notify staff in a designated reports channel
        try:
            # Find the reports channel (you can customize this)
            reports_channel_id = await self.mongodb.settings.find_one(
                {"guild_id": str(interaction.guild.id), "setting_type": "reports_channel"}
            )
            
            if reports_channel_id:
                reports_channel = interaction.guild.get_channel(int(reports_channel_id["value"]))
                if reports_channel:
                    # Create a detailed report embed
                    report_embed = discord.Embed(
                        title="Yeni Şikayet",
                        description=f"**Şikayet Eden:** {interaction.user.mention}\n**Sebep:** {self.reason.value}",
                        color=discord.Color.red(),
                        timestamp=discord.utils.utcnow()
                    )
                    
                    if self.message:
                        report_embed.add_field(
                            name="Şikayet Edilen Mesaj",
                            value=f"{self.message.content[:1000]}..." if len(self.message.content) > 1000 else self.message.content,
                            inline=False
                        )
                        report_embed.add_field(
                            name="Mesaj Sahibi",
                            value=f"{self.message.author.mention} ({self.message.author.id})",
                            inline=True
                        )
                        report_embed.add_field(
                            name="Kanal",
                            value=f"{self.message.channel.mention}",
                            inline=True
                        )
                        report_embed.add_field(
                            name="Bağlantı",
                            value=f"[Mesaja Git]({self.message.jump_url})",
                            inline=True
                        )
                    
                    await reports_channel.send(embed=report_embed)
        except Exception as e:
            # Log error but don't bother the user with it
            print(f"Error notifying staff about report: {e}")
    
    async def on_error(self, interaction: discord.Interaction, error: Exception):
        await interaction.response.send_message(
            embed=create_embed(
                "Şikayetiniz gönderilirken bir hata oluştu. Lütfen daha sonra tekrar deneyin.",
                discord.Color.red()
            ),
            ephemeral=True
        )
        print(f"Error handling report modal: {error}")
