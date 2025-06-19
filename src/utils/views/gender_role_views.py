"""Gender role configuration views."""
import discord
from ..core.formatting import create_embed
from ...bot.constants import Colors
from ..database.db_manager import db_manager


class GenderRoleConfigView(discord.ui.View):
    """View for configuring gender roles."""
    
    def __init__(self, bot, guild_id: int):
        super().__init__(timeout=300)
        self.bot = bot
        self.guild_id = guild_id
        self.db = db_manager.get_database()
        
        # Male role select
        male_select = discord.ui.RoleSelect(
            placeholder="Erkek rolü seçin",
            max_values=1
        )
        
        # Female role select  
        female_select = discord.ui.RoleSelect(
            placeholder="Kadın rolü seçin",
            max_values=1
        )
        
        async def male_callback(interaction):
            selected_role = male_select.values[0]
            await self.save_gender_role(interaction, "male_role_id", selected_role.id, "Erkek")
        
        async def female_callback(interaction):
            selected_role = female_select.values[0]
            await self.save_gender_role(interaction, "female_role_id", selected_role.id, "Kadın")
        
        male_select.callback = male_callback
        female_select.callback = female_callback
        
        self.add_item(male_select)
        self.add_item(female_select)
    
    async def save_gender_role(self, interaction, role_type: str, role_id: int, gender_name: str):
        """Save gender role to database."""
        try:
            if self.db is not None:
                await self.db.register.update_one(
                    {"guild_id": self.guild_id},
                    {"$set": {f"gender_roles.{role_type}": role_id}},
                    upsert=True
                )
            
            role = interaction.guild.get_role(role_id)
            embed = create_embed(
                title="✅ Cinsiyet Rolü Ayarlandı",
                description=f"**{gender_name} rolü:** {role.mention}",
                color=Colors.SUCCESS
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            embed = create_embed(
                title="❌ Hata",
                description=f"Cinsiyet rolü kaydedilirken bir hata oluştu: {str(e)}",
                color=Colors.ERROR
            )
            await interaction.response.send_message(embed=embed, ephemeral=True) 