import discord
from discord import ui
from typing import Optional, Callable, Any
from .messages import warning_embed, success_embed, error_embed


class ConfirmationView(ui.View):
    """Common confirmation dialog view"""
    
    def __init__(
        self,
        user: discord.Member,
        timeout: int = 60,
        confirm_callback: Optional[Callable] = None,
        cancel_callback: Optional[Callable] = None,
        confirm_label: str = "Onayla",
        cancel_label: str = "İptal",
        confirm_style: discord.ButtonStyle = discord.ButtonStyle.danger,
        cancel_style: discord.ButtonStyle = discord.ButtonStyle.secondary
    ):
        super().__init__(timeout=timeout)
        self.user = user
        self.confirm_callback = confirm_callback
        self.cancel_callback = cancel_callback
        self.value = None
        
        # Add buttons
        confirm_button = ui.Button(
            label=confirm_label,
            emoji="✅",
            style=confirm_style
        )
        confirm_button.callback = self._confirm
        self.add_item(confirm_button)
        
        cancel_button = ui.Button(
            label=cancel_label,
            emoji="❌",
            style=cancel_style
        )
        cancel_button.callback = self._cancel
        self.add_item(cancel_button)
    
    async def _confirm(self, interaction: discord.Interaction):
        """Handle confirmation"""
        if interaction.user.id != self.user.id:
            await interaction.response.send_message(
                embed=error_embed("Bu onay diyaloğunu sadece komutu kullanan kişi kullanabilir."),
                ephemeral=True
            )
            return
        
        self.value = True
        self.stop()
        
        if self.confirm_callback:
            await self.confirm_callback(interaction)
        else:
            await interaction.response.edit_message(
                embed=success_embed("İşlem onaylandı."),
                view=None
            )
    
    async def _cancel(self, interaction: discord.Interaction):
        """Handle cancellation"""
        if interaction.user.id != self.user.id:
            await interaction.response.send_message(
                embed=error_embed("Bu onay diyaloğunu sadece komutu kullanan kişi kullanabilir."),
                ephemeral=True
            )
            return
        
        self.value = False
        self.stop()
        
        if self.cancel_callback:
            await self.cancel_callback(interaction)
        else:
            await interaction.response.edit_message(
                embed=error_embed("İşlem iptal edildi."),
                view=None
            )
    
    async def on_timeout(self):
        """Handle timeout"""
        self.value = None
        for item in self.children:
            item.disabled = True


class DangerConfirmationView(ConfirmationView):
    """Confirmation dialog for dangerous actions"""
    
    def __init__(
        self,
        user: discord.Member,
        action_description: str,
        confirm_callback: Optional[Callable] = None,
        cancel_callback: Optional[Callable] = None,
        timeout: int = 60
    ):
        super().__init__(
            user=user,
            timeout=timeout,
            confirm_callback=confirm_callback,
            cancel_callback=cancel_callback,
            confirm_label="Evet, Devam Et",
            cancel_label="Hayır, İptal",
            confirm_style=discord.ButtonStyle.danger,
            cancel_style=discord.ButtonStyle.secondary
        )
        self.action_description = action_description


async def confirm_action(
    interaction: discord.Interaction,
    title: str = "⚠️ Onay Gerekli",
    description: str = "Bu işlemi gerçekleştirmek istediğinizden emin misiniz?",
    confirm_callback: Optional[Callable] = None,
    cancel_callback: Optional[Callable] = None,
    danger: bool = False,
    ephemeral: bool = True
) -> Optional[bool]:
    """
    Show a confirmation dialog and wait for user response
    
    Args:
        interaction: The Discord interaction
        title: Title of the confirmation embed
        description: Description of what will happen
        confirm_callback: Optional callback for confirmation
        cancel_callback: Optional callback for cancellation
        danger: Whether this is a dangerous action (changes button style)
        ephemeral: Whether the message should be ephemeral
        
    Returns:
        True if confirmed, False if cancelled, None if timed out
    """
    embed = warning_embed(description, title)
    
    if danger:
        view = DangerConfirmationView(
            user=interaction.user,
            action_description=description,
            confirm_callback=confirm_callback,
            cancel_callback=cancel_callback
        )
    else:
        view = ConfirmationView(
            user=interaction.user,
            confirm_callback=confirm_callback,
            cancel_callback=cancel_callback
        )
    
    await interaction.response.send_message(
        embed=embed,
        view=view,
        ephemeral=ephemeral
    )
    
    # Wait for the view to finish
    await view.wait()
    return view.value 