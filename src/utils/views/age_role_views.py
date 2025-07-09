"""Age role configuration views."""
import discord
from ..core.formatting import create_embed
from ...bot.constants import Colors
from ..database.db_manager import db_manager


class AgeRoleConfigModal(discord.ui.Modal, title="Yaş Rolleri Ayarları"):
    """Modal for configuring flexible age-based roles."""
    
    age_ranges = discord.ui.TextInput(
        label="Yaş Aralıkları",
        placeholder="13-17, 18-25, 26-35, 50+ (her satıra bir aralık)",
        style=discord.TextStyle.paragraph,
        max_length=500,
        required=False
    )
    
    def __init__(self, bot, guild_id: int):
        super().__init__()
        self.bot = bot
        self.guild_id = guild_id
        self.db = db_manager.get_database()
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle age role configuration."""
        try:
            # Parse age ranges
            age_ranges_text = self.age_ranges.value.strip()
            if not age_ranges_text:
                embed = create_embed(
                    title="ℹ️ Yaş Rolleri",
                    description="Yaş rolleri temizlendi. Artık yaşa göre rol verilmeyecek.",
                    color=Colors.SUCCESS
                )
                
                # Clear age roles
                if self.db is not None:
                    await self.db.register.update_one(
                        {"guild_id": self.guild_id},
                        {"$unset": {"age_roles": ""}},
                        upsert=True
                    )
                
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            # Show role selection for each age range
            age_ranges = [range_text.strip() for range_text in age_ranges_text.replace('\n', ',').split(',') if range_text.strip()]
            
            embed = create_embed(
                title="✅ Yaş Aralıkları Kaydedildi",
                description=f"**Aralıklar:** {', '.join(age_ranges)}\n\n"
                           "Şimdi her yaş aralığı için rol seçimi yapmanız gerekiyor.",
                color=Colors.SUCCESS
            )
            
            # Create role selection view
            view = AgeRoleSelectionView(self.bot, self.guild_id, age_ranges)
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            
        except Exception as e:
            embed = create_embed(
                title="❌ Hata",
                description=f"Yaş rolleri ayarlanırken bir hata oluştu: {str(e)}",
                color=Colors.ERROR
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)


class AgeRoleSelectionView(discord.ui.View):
    """View for selecting roles for each age range."""
    
    def __init__(self, bot, guild_id: int, age_ranges: list):
        super().__init__(timeout=300)
        self.bot = bot
        self.guild_id = guild_id
        self.age_ranges = age_ranges
        self.selected_roles = {}
        self.db = db_manager.get_database()
        
        # Add role select for first age range
        self.current_index = 0
        self.update_select()
    
    def update_select(self):
        """Update the select menu for current age range."""
        if self.current_index < len(self.age_ranges):
            current_range = self.age_ranges[self.current_index]
            
            # Remove existing select if any
            for item in self.children[:]:
                if isinstance(item, discord.ui.RoleSelect):
                    self.remove_item(item)
            
            # Add new role select
            role_select = discord.ui.RoleSelect(
                placeholder=f"{current_range} yaş aralığı için rol seçin",
                max_values=1
            )
            
            async def role_callback(interaction):
                selected_role = role_select.values[0]
                self.selected_roles[current_range] = selected_role.id
                
                self.current_index += 1
                if self.current_index < len(self.age_ranges):
                    # Continue with next age range
                    self.update_select()
                    embed = create_embed(
                        title="✅ Rol Seçildi",
                        description=f"**{current_range}:** {selected_role.mention}\n\n"
                                   f"Şimdi **{self.age_ranges[self.current_index]}** aralığı için rol seçin.",
                        color=Colors.SUCCESS
                    )
                    await interaction.response.edit_message(embed=embed, view=self)
                else:
                    # All roles selected, save to database
                    await self.save_age_roles(interaction)
            
            role_select.callback = role_callback
            self.add_item(role_select)
    
    async def save_age_roles(self, interaction):
        """Save age roles configuration to database."""
        try:
            if self.db is not None:
                await self.db.register.update_one(
                    {"guild_id": self.guild_id},
                    {"$set": {"age_roles": self.selected_roles}},
                    upsert=True
                )
            
            # Create summary
            role_summary = "\n".join([
                f"**{age_range}:** {interaction.guild.get_role(role_id).mention}"
                for age_range, role_id in self.selected_roles.items()
            ])
            
            embed = create_embed(
                title="✅ Yaş Rolleri Ayarlandı",
                description=f"Yaş rolleri başarıyla yapılandırıldı:\n\n{role_summary}",
                color=Colors.SUCCESS
            )
            
            await interaction.response.edit_message(embed=embed, view=None)
            
        except Exception as e:
            embed = create_embed(
                title="❌ Hata",
                description=f"Yaş rolleri kaydedilirken bir hata oluştu: {str(e)}",
                color=Colors.ERROR
            )
            await interaction.response.edit_message(embed=embed, view=None)


class AgeRoleConfigView(discord.ui.View):
    """Age role configuration view."""
    
    def __init__(self, bot, guild_id: int):
        super().__init__(timeout=300)
        self.bot = bot
        self.guild_id = guild_id
    
    @discord.ui.button(label="18+ Role", style=discord.ButtonStyle.primary, row=0)
    async def age_plus_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Configure 18+ role."""
        embed = create_embed(
            title="🔞 18+ Role Configuration",
            description="Please mention the role for users 18 years and older.",
            color=Colors.INFO
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @discord.ui.button(label="18- Role", style=discord.ButtonStyle.primary, row=0)
    async def age_minus_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Configure 18- role."""
        embed = create_embed(
            title="🧒 18- Role Configuration",
            description="Please mention the role for users under 18 years old.",
            color=Colors.INFO
        )
        await interaction.response.send_message(embed=embed, ephemeral=True) 