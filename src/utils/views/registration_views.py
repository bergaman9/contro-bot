"""Registration panel views."""
import discord
from ..core.formatting import create_embed
from src.bot.constants import Colors


class RegistrationPanelView(discord.ui.View):
    """Registration panel view with register button."""
    
    def __init__(self, bot, guild_id: int):
        super().__init__(timeout=None)  # Persistent view
        self.bot = bot
        self.guild_id = guild_id
    
    @discord.ui.button(
        label="Kayıt Ol", 
        style=discord.ButtonStyle.primary, 
        emoji="📝",
        custom_id="registration_panel_register"
    )
    async def register_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle registration button click."""
        # Import here to avoid circular imports
        from ..community.turkoyto.registration_view import GamerRegistrationModal
        
        # Check if user is already registered
        from ..database.db_manager import db_manager
        db = db_manager.get_database()
        
        existing_member = await db.members.find_one({
            "guild_id": self.guild_id,
            "user_id": interaction.user.id,
            "registered": True
        })
        
        if existing_member:
            embed = create_embed(
                title="❌ Zaten Kayıtlısınız",
                description="Bu sunucuda zaten kayıtlısınız!",
                color=Colors.ERROR
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Show registration modal
        modal = GamerRegistrationModal(self.bot, self.guild_id)
        await interaction.response.send_modal(modal) 
