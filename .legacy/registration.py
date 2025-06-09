import discord
from discord.ext import commands
import datetime
import logging
from utils.database import get_async_db, ensure_async_db
from utils.core.formatting import create_embed
from utils.core.helpers import is_feature_enabled

# Set up proper logger with a dedicated file
logger = logging.getLogger('registration')

class RegistrationView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label="Register", style=discord.ButtonStyle.success, emoji="✅", custom_id="register_button")
    async def register_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Check if registration system is enabled
        if not is_feature_enabled(interaction.guild.id, "registration_system"):
            embed = create_embed(
                description="❌ Registration system is disabled for this server.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Get async database
        mongo_db = await ensure_async_db()
        
        # Check if already registered
        existing_user = await mongo_db.registrations.find_one({
            "user_id": interaction.user.id, 
            "guild_id": interaction.guild.id
        })
        
        if existing_user:
            embed = create_embed(
                title="🎮 Registration Status",
                description=f"📝 {interaction.user.mention}, you are already registered!",
                color=discord.Color.blue()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Show registration modal
        modal = RegistrationModal()
        await interaction.response.send_modal(modal)

class RegistrationModal(discord.ui.Modal, title="User Registration"):
    name = discord.ui.TextInput(
        label="Name (Optional)",
        placeholder="Your real name",
        required=False,
        max_length=50
    )
    
    age = discord.ui.TextInput(
        label="Age (Optional)",
        placeholder="Your age",
        required=False,
        max_length=3
    )
    
    games = discord.ui.TextInput(
        label="Favorite Games",
        placeholder="List your favorite games (comma separated)",
        required=True,
        style=discord.TextStyle.paragraph,
        max_length=500
    )
    
    expectations = discord.ui.TextInput(
        label="What do you expect from this server?",
        placeholder="Tell us what you're looking for...",
        required=False,
        style=discord.TextStyle.paragraph,
        max_length=1000
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Process age
            age = None
            if self.age.value.strip():
                try:
                    age = int(self.age.value.strip())
                    if age < 13 or age > 99:
                        await interaction.response.send_message(
                            embed=create_embed(
                                description="❌ Invalid age! Age must be between 13-99.",
                                color=discord.Color.red()
                            ),
                            ephemeral=True
                        )
                        return
                except ValueError:
                    await interaction.response.send_message(
                        embed=create_embed(
                            description="❌ Invalid age! Please enter a number.",
                            color=discord.Color.red()
                        ),
                        ephemeral=True
                    )
                    return
            
            # Process games
            game_list = [game.strip() for game in self.games.value.split(',') if game.strip()]
            
            # Get database
            mongo_db = await ensure_async_db()
            
            # Get registration settings
            settings = await mongo_db.registration_settings.find_one({"guild_id": interaction.guild.id}) or {}
            
            # Save registration data
            registration_data = {
                "user_id": interaction.user.id,
                "guild_id": interaction.guild.id,
                "name": self.name.value.strip() if self.name.value.strip() else None,
                "age": age,
                "games": game_list,
                "expectations": self.expectations.value.strip() if self.expectations.value.strip() else None,
                "registered_at": datetime.datetime.now(),
                "username": interaction.user.name,
                "display_name": interaction.user.display_name
            }
            
            await mongo_db.registrations.insert_one(registration_data)
            
            # Handle role management
            await self.handle_registration_roles(interaction, settings)
            
            # Send success message
            embed = create_embed(
                title="✅ Registration Successful!",
                description="Your registration has been completed successfully!",
                color=discord.Color.green()
            )
            
            # Show provided info
            info_fields = []
            if registration_data["name"]:
                info_fields.append(f"**Name:** {registration_data['name']}")
            if registration_data["age"]:
                info_fields.append(f"**Age:** {registration_data['age']}")
            info_fields.append(f"**Games:** {', '.join(game_list)}")
            
            if info_fields:
                embed.add_field(
                    name="Your Information",
                    value="\n".join(info_fields),
                    inline=False
                )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
            # Log registration
            logger.info(f"User {interaction.user.id} ({interaction.user.name}) registered in guild {interaction.guild.id}")
            
        except Exception as e:
            logger.error(f"Error during registration: {e}", exc_info=True)
            await interaction.response.send_message(
                embed=create_embed(
                    description="❌ An error occurred during registration. Please try again.",
                    color=discord.Color.red()
                ),
                ephemeral=True
            )

    async def handle_registration_roles(self, interaction, settings):
        """Handle role assignment after registration"""
        try:
            member = interaction.user
            if not isinstance(member, discord.Member):
                member = interaction.guild.get_member(interaction.user.id)
            
            if not member:
                logger.warning(f"Could not find member {interaction.user.id} in guild {interaction.guild.id}")
                return
            
            # Get role settings
            roles_to_remove = settings.get("unregistered_roles", [])
            roles_to_add = settings.get("registered_roles", [])
            
            # Remove unregistered roles
            for role_id in roles_to_remove:
                role = interaction.guild.get_role(role_id)
                if role and role in member.roles:
                    try:
                        await member.remove_roles(role, reason="User registered")
                        logger.info(f"Removed role {role.name} ({role_id}) from {member.name} ({member.id})")
                    except discord.Forbidden:
                        logger.warning(f"No permission to remove role {role.name} ({role_id}) from {member.name}")
                    except Exception as e:
                        logger.error(f"Error removing role {role.name} ({role_id}): {e}")
            
            # Add registered roles
            for role_id in roles_to_add:
                role = interaction.guild.get_role(role_id)
                if role and role not in member.roles:
                    try:
                        await member.add_roles(role, reason="User registered")
                        logger.info(f"Added role {role.name} ({role_id}) to {member.name} ({member.id})")
                    except discord.Forbidden:
                        logger.warning(f"No permission to add role {role.name} ({role_id}) to {member.name}")
                    except Exception as e:
                        logger.error(f"Error adding role {role.name} ({role_id}): {e}")
                        
        except Exception as e:
            logger.error(f"Error handling registration roles: {e}", exc_info=True)

class Registration(commands.Cog):
    """User Registration System"""
    
    def __init__(self, bot):
        self.bot = bot
        # Add persistent view
        self.bot.add_view(RegistrationView())
    
    @commands.hybrid_command(name="register_panel", description="Create a registration panel")
    @commands.has_permissions(administrator=True)
    async def register_panel(self, ctx):
        """Create a registration panel for users to register"""
        try:
            # Check if feature is enabled
            if not is_feature_enabled(ctx.guild.id, "registration_system"):
                embed = create_embed(
                    description="❌ Registration system is disabled. Enable it in settings first.",
                    color=discord.Color.red()
                )
                await ctx.send(embed=embed, ephemeral=True)
                return
            
            embed = discord.Embed(
                title="🎮 User Registration",
                description=(
                    "Welcome! Please register to access all server features.\n\n"
                    "Click the button below to start your registration."
                ),
                color=discord.Color.blue()
            )
            
            embed.add_field(
                name="What we collect:",
                value=(
                    "• Name (optional)\n"
                    "• Age (optional)\n"
                    "• Favorite games\n"
                    "• Your expectations from the server"
                ),
                inline=False
            )
            
            embed.set_footer(text="Your information is only used within this server")
            
            view = RegistrationView()
            await ctx.send(embed=embed, view=view)
            
            # Make sure the view is persistent
            self.bot.add_view(view)
            
            # Delete command if not slash command
            if hasattr(ctx, 'message') and ctx.message:
                try:
                    await ctx.message.delete()
                except:
                    pass
                    
        except Exception as e:
            logger.error(f"Error creating registration panel: {e}", exc_info=True)
            await ctx.send(
                embed=create_embed(
                    description="❌ Error creating registration panel.",
                    color=discord.Color.red()
                ),
                ephemeral=True
            )
    
    @commands.hybrid_command(name="registration_info", description="View registration information for a user")
    @commands.has_permissions(manage_guild=True)
    async def registration_info(self, ctx, member: discord.Member = None):
        """View registration information for a user"""
        try:
            if not member:
                member = ctx.author
            
            mongo_db = await ensure_async_db()
            registration = await mongo_db.registrations.find_one({
                "user_id": member.id,
                "guild_id": ctx.guild.id
            })
            
            if not registration:
                embed = create_embed(
                    description=f"❌ {member.mention} is not registered.",
                    color=discord.Color.red()
                )
                await ctx.send(embed=embed, ephemeral=True)
                return
            
            embed = discord.Embed(
                title=f"🎮 Registration Info - {member.display_name}",
                color=discord.Color.blue()
            )
            
            if registration.get("name"):
                embed.add_field(name="Name", value=registration["name"], inline=True)
            
            if registration.get("age"):
                embed.add_field(name="Age", value=str(registration["age"]), inline=True)
            
            embed.add_field(name="Registered At", value=f"<t:{int(registration['registered_at'].timestamp())}:F>", inline=True)
            
            if registration.get("games"):
                embed.add_field(
                    name="Favorite Games",
                    value=", ".join(registration["games"]),
                    inline=False
                )
            
            if registration.get("expectations"):
                embed.add_field(
                    name="Expectations",
                    value=registration["expectations"][:1000] + ("..." if len(registration["expectations"]) > 1000 else ""),
                    inline=False
                )
            
            await ctx.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error getting registration info: {e}", exc_info=True)
            await ctx.send(
                embed=create_embed(
                    description="❌ Error retrieving registration information.",
                    color=discord.Color.red()
                ),
                ephemeral=True
            )

async def setup(bot):
    await bot.add_cog(Registration(bot)) 