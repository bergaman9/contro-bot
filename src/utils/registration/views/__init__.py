import discord
import logging

logger = logging.getLogger('register')

class RegisterButton(discord.ui.View):
    """Persistent registration button for user registration"""
    
    def __init__(self):
        super().__init__(timeout=None)  # Set timeout to None for persistence
        
        # Create the button with a specific custom_id for persistence
        button = discord.ui.Button(
            label="Kayıt Ol", 
            style=discord.ButtonStyle.success, 
            emoji="📝",
            custom_id="kayit_ol_button"  # Custom ID is needed for persistence
        )
        
        # Add button callback
        button.callback = self.register_button_callback
        self.add_item(button)

    async def register_button_callback(self, interaction: discord.Interaction):
        """Handle button click to start registration"""
        logger.info(f"Registration button clicked by {interaction.user}")
        try:
            # Open the registration modal or redirect to registration command
            # For now, we'll just respond with a message
            await interaction.response.send_message(
                "Kayıt olmak için lütfen bir yetkili ile iletişime geçin veya /kayıt komutunu kullanın.",
                ephemeral=True
            )
            
            # Here you would normally:
            # 1. Get the Register cog
            # 2. Call the appropriate registration method
            # cog = interaction.client.get_cog("Register")
            # if cog:
            #     await cog.start_registration(interaction)
            
        except Exception as e:
            logger.error(f"Error handling registration button: {e}", exc_info=True)
            await interaction.response.send_message(
                "Kayıt işlemi başlatılırken bir hata oluştu. Lütfen daha sonra tekrar deneyin veya bir yetkili ile iletişime geçin.",
                ephemeral=True
            )

async def setup(bot):
    """Add the registration views to the bot"""
    # Register the persistent view
    bot.add_view(RegisterButton())
    logger.info("Register views loaded")
