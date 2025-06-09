import discord
from discord import app_commands
from discord.ext import commands, tasks
from typing import Optional, List, Tuple, Union, Dict, Any
import traceback
import logging

from utils.database.connection import initialize_mongodb, is_db_available
from utils.core.formatting import create_embed
from utils.core.error_handler import handle_interaction_error

# Set up logging
logger = logging.getLogger('register')

class RegisterError(Exception):
    """Custom exception for registration errors"""
    pass

class RegisterButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        # Store MongoDB connection for reuse
        self.mongo_db = initialize_mongodb()
    
    @discord.ui.button(label="Kayıt Ol", style=discord.ButtonStyle.primary, custom_id="register_button")
    async def register_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            # Debug logging
            logger.info(f"Register button clicked by {interaction.user} (ID: {interaction.user.id}) in {interaction.guild.name if interaction.guild else 'DM'}")            
            
            # Show modal to collect registration info
            await interaction.response.send_modal(RegisterModal(self.mongo_db))
            
        except Exception as e:
            # Detailed error logging
            error_traceback = traceback.format_exc()
            logger.error(f"Register button error: {e}\n{error_traceback}")
            
            # Try to respond to the user
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message(
                        embed=create_embed(
                            description=f"❌ Kayıt işlemi sırasında bir hata oluştu: {str(e)}",
                            color=discord.Color.red()
                        ),
                        ephemeral=True
                    )
                else:
                    await interaction.followup.send(
                        embed=create_embed(
                            description=f"❌ Kayıt işlemi sırasında bir hata oluştu: {str(e)}",
                            color=discord.Color.red()
                        ),
                        ephemeral=True
                    )
            except Exception as respond_error:
                logger.error(f"Failed to respond to interaction error: {respond_error}")


class RegisterModal(discord.ui.Modal, title="Kayıt Formu"):
    """Modal for collecting registration information"""
    
    name = discord.ui.TextInput(
        label="İsminiz",
        placeholder="Gerçek isminizi girin",
        required=True,
        max_length=32
    )
    
    age = discord.ui.TextInput(
        label="Yaşınız",
        placeholder="Yaşınızı girin (Sadece sayı)",
        required=True,
        max_length=3
    )
    
    def __init__(self, mongo_db):
        super().__init__()
        self.mongo_db = mongo_db
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Validate age is a number
            try:
                age = int(self.age.value)
                if age < 10 or age > 100:
                    return await interaction.response.send_message(
                        embed=create_embed(
                            description="❌ Lütfen geçerli bir yaş girin (10-100 arası).",
                            color=discord.Color.red()
                        ),
                        ephemeral=True
                    )
            except ValueError:
                return await interaction.response.send_message(
                    embed=create_embed(
                        description="❌ Yaş sadece rakamlardan oluşmalıdır.",
                        color=discord.Color.red()
                    ),
                    ephemeral=True
                )
            
            # Get guild settings
            if is_db_available(self.mongo_db):
                settings = self.mongo_db["register"].find_one({"guild_id": interaction.guild.id})
            else:
                settings = None
                
            if not settings or "role_id" not in settings:
                return await interaction.response.send_message(
                    embed=create_embed(
                        description="❌ Kayıt sistemi henüz ayarlanmamış. Lütfen bir yetkiliyle iletişime geçin.",
                        color=discord.Color.red()
                    ),
                    ephemeral=True
                )
            
            # Get roles to assign
            roles_to_add = []
            
            # Main registration role
            main_role_id = settings.get("role_id")
            if main_role_id:
                main_role = interaction.guild.get_role(int(main_role_id))
                if main_role:
                    roles_to_add.append(main_role)
            
            # Age-based role (18+ or 18-)
            if age >= 18:
                adult_role_id = settings.get("adult_role_id")
                if adult_role_id:
                    adult_role = interaction.guild.get_role(int(adult_role_id))
                    if adult_role:
                        roles_to_add.append(adult_role)
            else:
                minor_role_id = settings.get("minor_role_id")
                if minor_role_id:
                    minor_role = interaction.guild.get_role(int(minor_role_id))
                    if minor_role:
                        roles_to_add.append(minor_role)
            
            # Bronze role
            bronze_role_id = settings.get("bronze_role_id")
            if bronze_role_id:
                bronze_role = interaction.guild.get_role(int(bronze_role_id))
                if bronze_role:
                    roles_to_add.append(bronze_role)
            
            # No roles to add
            if not roles_to_add:
                return await interaction.response.send_message(
                    embed=create_embed(
                        description="❌ Kayıt rolleri bulunamadı. Lütfen bir yetkiliyle iletişime geçin.",
                        color=discord.Color.red()
                    ),
                    ephemeral=True
                )
            
            # Update nickname
            try:
                await interaction.user.edit(nick=f"{self.name.value} | {age}")
            except discord.Forbidden:
                logger.warning(f"Missing permissions to change nickname for {interaction.user} in {interaction.guild.name}")
            
            # Add roles
            try:
                await interaction.user.add_roles(*roles_to_add)
            except discord.Forbidden:
                return await interaction.response.send_message(
                    embed=create_embed(
                        description="❌ Rolleri vermek için yetkim yok. Lütfen bir yetkiliyle iletişime geçin.",
                        color=discord.Color.red()
                    ),
                    ephemeral=True
                )
            
            # Record registration in database
            today = discord.utils.utcnow().strftime("%Y-%m-%d")
            current_time = discord.utils.utcnow().timestamp()
            
            # Update user registration record
            self.mongo_db["register_log"].update_one(
                {"guild_id": interaction.guild.id, "user_id": interaction.user.id},
                {"$set": {
                    "name": self.name.value,
                    "age": age,
                    "registered_at": current_time,
                    "registration_date": today
                }},
                upsert=True
            )
            
            # Update daily registration stats
            self.mongo_db["register_stats"].update_one(
                {"guild_id": interaction.guild.id, "date": today},
                {"$inc": {"count": 1}},
                upsert=True
            )
            
            # Update weekly and total stats
            self.mongo_db["register_stats"].update_one(
                {"guild_id": interaction.guild.id, "type": "weekly"},
                {"$inc": {"count": 1}},
                upsert=True
            )
            
            self.mongo_db["register_stats"].update_one(
                {"guild_id": interaction.guild.id, "type": "total"},
                {"$inc": {"count": 1}},
                upsert=True
            )
            
            # Send registration log to configured channel
            await self.send_registration_log(interaction, self.name.value, age, roles_to_add)
            
            # Create success message with assigned roles
            role_mentions = [role.mention for role in roles_to_add]
            roles_text = ", ".join(role_mentions)
            
            # Send success response
            await interaction.response.send_message(
                embed=create_embed(
                    description=f"✅ Kayıt işleminiz başarıyla tamamlandı!\n\n**Verilen Roller:** {roles_text}",
                    color=discord.Color.green()
                ),
                ephemeral=True
            )
            
            # Log the registration
            logger.info(f"User registered: {interaction.user} (ID: {interaction.user.id}) in {interaction.guild.name} with roles {roles_text}")
            
        except Exception as e:
            logger.error(f"Registration error: {e}\n{traceback.format_exc()}")
            await interaction.response.send_message(
                embed=create_embed(
                    description=f"❌ Kayıt işlemi sırasında bir hata oluştu: {str(e)}",
                    color=discord.Color.red()
                ),
                ephemeral=True
            )
    
    async def send_registration_log(self, interaction: discord.Interaction, name: str, age: int, roles: list):
        """Send registration log to configured channel"""
        try:
            # Get log channel from settings
            settings = self.mongo_db["register"].find_one({"guild_id": interaction.guild.id})
            if not settings or "log_channel_id" not in settings:
                logger.debug(f"No register log channel configured for guild {interaction.guild.id}")
                return
            
            log_channel_id = settings["log_channel_id"]
            log_channel = interaction.guild.get_channel(int(log_channel_id))
            
            if not log_channel:
                logger.warning(f"Register log channel {log_channel_id} not found in guild {interaction.guild.id}")
                return
            
            # Create log embed
            embed = create_embed(
                title="🎉 Yeni Kayıt",
                color=discord.Color.green()
            )
            
            embed.add_field(
                name="👤 Kullanıcı",
                value=f"{interaction.user.mention} ({interaction.user})",
                inline=False
            )
            
            embed.add_field(
                name="📝 Kayıt Bilgileri",
                value=f"**İsim:** {name}\n**Yaş:** {age}",
                inline=True
            )
            
            role_mentions = [role.mention for role in roles] if roles else ["Rol verilmedi"]
            embed.add_field(
                name="🎭 Verilen Roller",
                value="\n".join(role_mentions),
                inline=True
            )
            
            embed.add_field(
                name="📅 Kayıt Zamanı",
                value=f"<t:{int(discord.utils.utcnow().timestamp())}:F>",
                inline=False
            )
            
            embed.set_thumbnail(url=interaction.user.display_avatar.url)
            embed.set_footer(text=f"Kullanıcı ID: {interaction.user.id}")
            
            # Send log message
            await log_channel.send(embed=embed)
            logger.info(f"Registration log sent for user {interaction.user.id} to channel {log_channel.name}")
            
        except Exception as e:
            logger.error(f"Error sending registration log: {e}", exc_info=True)
    
class Register(commands.Cog):
    """
    Server registration system to manage new members
    """
    def __init__(self, bot):
        self.bot = bot
        self.mongo_db = initialize_mongodb()
        # Explicitly add a fresh instance of RegisterButton when the cog loads
        self.register_button = RegisterButton()
        self.bot.add_view(self.register_button)
        
        # Start the background task for role verification
        self.check_members_roles.start()
        logger.info(f"Register cog initialized and button view added")
        
    def cog_unload(self):
        # Stop the background task when the cog is unloaded
        self.check_members_roles.cancel()
        
    @tasks.loop(hours=6.0)
    async def check_members_roles(self):
        """Periodically check all registered members and ensure they have correct roles"""
        logger.info("Starting periodic role check for registered members")
        try:
            # Get all guilds
            for guild in self.bot.guilds:
                logger.debug(f"Checking roles for members in guild: {guild.name}")
                await self._check_guild_members_roles(guild)
            logger.info("Periodic role check completed")
        except Exception as e:
            logger.error(f"Error in periodic role check: {e}\n{traceback.format_exc()}")
            
    @check_members_roles.before_loop
    async def before_check_members_roles(self):
        """Wait until the bot is ready before starting the task"""
        await self.bot.wait_until_ready()
        logger.info("Bot is ready, role check task will start soon")
    
    async def _check_guild_members_roles(self, guild):
        """Check all registered members in a guild and ensure they have the correct roles"""
        try:
            # Get guild settings
            settings = self.mongo_db["register"].find_one({"guild_id": guild.id})
            if not settings:
                logger.debug(f"No registration settings found for guild: {guild.name}")
                return
                
            # Get the roles to be assigned
            main_role_id = settings.get("role_id")
            adult_role_id = settings.get("adult_role_id")
            minor_role_id = settings.get("minor_role_id")
            bronze_role_id = settings.get("bronze_role_id")
            
            # Get role objects
            main_role = guild.get_role(int(main_role_id)) if main_role_id else None
            adult_role = guild.get_role(int(adult_role_id)) if adult_role_id else None
            minor_role = guild.get_role(int(minor_role_id)) if minor_role_id else None
            bronze_role = guild.get_role(int(bronze_role_id)) if bronze_role_id else None
            
            # Skip if no roles are configured
            if not any([main_role, adult_role, minor_role, bronze_role]):
                logger.debug(f"No roles configured for guild: {guild.name}")
                return
                
            # Get all registered members
            registered_users = list(self.mongo_db["register_log"].find({"guild_id": guild.id}))
            logger.info(f"Found {len(registered_users)} registered users in guild: {guild.name}")
            
            # Check each registered member
            updated_count = 0
            for user_data in registered_users:
                user_id = user_data.get("user_id")
                member = guild.get_member(int(user_id))
                
                # Skip if member is not in the guild anymore
                if not member:
                    continue
                    
                roles_to_add = []
                
                # Check if main role should be added
                if main_role and main_role not in member.roles:
                    roles_to_add.append(main_role)
                
                # Check age-based roles
                age = user_data.get("age", 0)
                if age >= 18 and adult_role and adult_role not in member.roles:
                    roles_to_add.append(adult_role)
                elif age < 18 and minor_role and minor_role not in member.roles:
                    roles_to_add.append(minor_role)
                
                # Check bronze role
                if bronze_role and bronze_role not in member.roles:
                    roles_to_add.append(bronze_role)
                
                # Add missing roles
                if roles_to_add:
                    try:
                        await member.add_roles(*roles_to_add)
                        roles_text = ", ".join([role.name for role in roles_to_add])
                        logger.debug(f"Added roles to {member}: {roles_text}")
                        updated_count += 1
                    except discord.Forbidden:
                        logger.warning(f"Missing permissions to add roles to {member} in {guild.name}")
                    except Exception as e:
                        logger.error(f"Error adding roles to {member}: {e}")
            
            if updated_count > 0:
                logger.info(f"Updated roles for {updated_count} members in guild: {guild.name}")
        
        except Exception as e:
            logger.error(f"Error checking roles for guild {guild.name}: {e}\n{traceback.format_exc()}")
    
    async def _get_register_settings(self, guild_id: int) -> Dict[str, Any]:
        """
        Get registration settings for a guild
        
        Args:
            guild_id: The ID of the guild
            
        Returns:
            Dictionary with registration settings
            
        Raises:
            RegisterError: If settings are not configured
        """
        settings = self.mongo_db["register"].find_one({"guild_id": guild_id})
        if not settings:
            raise RegisterError("Kayıt sistemi henüz ayarlanmamış.")
        return settings
    
    async def _get_register_role(self, guild: discord.Guild) -> discord.Role:
        """
        Get the registration role for a guild
        
        Args:
            guild: The Discord guild object
            
        Returns:
            The registration role
            
        Raises:
            RegisterError: If role is not configured or not found
        """
        settings = await self._get_register_settings(guild.id)
        
        role_id = settings.get("role_id")
        if not role_id:
            raise RegisterError("Kayıt rolü ayarlanmamış.")
            
        role = guild.get_role(int(role_id))
        if not role:
            raise RegisterError("Kayıt rolü bulunamadı.")
            
        return role
    
    @commands.hybrid_command(name="kayıt", description="Registers a user with the given name and age.")
    @app_commands.describe(
        member="The member to register",
        name="The name of the member",
        age="The age of the member"
    )
    @commands.has_permissions(manage_roles=True)
    async def kayıt(self, ctx, member: discord.Member, name: str, age: int):
        """
        Registers a member with the specified name and age, assigning them the configured registration role.
        """
        try:
            # Get the registration role
            role = await self._get_register_role(ctx.guild)
            
            # Update member's nickname and roles
            await member.edit(nick=f"{name} | {age}")
            await member.add_roles(role)
            
            # Record the registration in the database
            self.mongo_db["register_log"].update_one(
                {"guild_id": ctx.guild.id, "user_id": member.id},
                {"$set": {
                    "name": name,
                    "age": age,
                    "registered_by": ctx.author.id,
                    "registered_at": discord.utils.utcnow().timestamp()
                }},
                upsert=True
            )
            
            await ctx.send(embed=create_embed(
                f"{member.mention} başarıyla {role.mention} rolü ile kayıt edildi.", 
                discord.Color.green()
            ))
            
        except RegisterError as e:
            await ctx.send(embed=create_embed(str(e), discord.Color.red()))
        except discord.Forbidden:
            await ctx.send(embed=create_embed(
                "Bot gerekli izinlere sahip değil. Rol yönetimi ve kullanıcı düzenleme izinleri gereklidir.",
                discord.Color.red()
            ))
        except Exception as e:
            await ctx.send(embed=create_embed(
                f"Kayıt işlemi sırasında bir hata oluştu: {str(e)}",
                discord.Color.red()
            ))
    
    @commands.hybrid_command(name="kayıt_setup", description="Sets up the registration system.")
    @app_commands.describe(
        role="The role to give to registered members"
    )
    @commands.has_permissions(administrator=True)
    async def kayıt_setup(self, ctx, role: discord.Role):
        """
        Sets up the registration system by configuring the role to be assigned to registered members.
        """
        try:
            # Store the registration role in the database
            self.mongo_db["register"].update_one(
                {"guild_id": ctx.guild.id},
                {"$set": {"role_id": str(role.id)}},
                upsert=True
            )
            
            await ctx.send(embed=create_embed(
                f"Kayıt sistemi başarıyla ayarlandı. Kayıt olan üyelere {role.mention} rolü verilecek.\n\nDaha detaylı ayarlar için ayarlar modülündeki `/register_settings` komutunu kullanabilirsiniz.",
                discord.Color.green()
            ))
            
        except Exception as e:
            await ctx.send(embed=create_embed(
                f"Kayıt sistemi ayarlanırken bir hata oluştu: {str(e)}",
                discord.Color.red()
            ))
    

    
    @commands.hybrid_command(name="kayıt_settings_show", description="Shows the current registration system settings.")
    @commands.has_permissions(manage_roles=True)
    async def kayıt_settings_show(self, ctx):
        """
        Displays the current registration system settings including the configured role.
        """
        try:
            # Get settings from database
            settings = self.mongo_db["register"].find_one({"guild_id": ctx.guild.id})
            if not settings:
                return await ctx.send(embed=create_embed(
                    "❌ Kayıt sistemi henüz ayarlanmamış.",
                    discord.Color.red()
                ))
            
            embed = discord.Embed(
                title="📋 Kayıt Sistemi Ayarları", 
                color=discord.Color.blue()
            )
            
            # Main role
            role_id = settings.get("role_id")
            if role_id:
                role = ctx.guild.get_role(int(role_id))
                role_value = f"{role.mention} ({role.id})" if role else f"Rol bulunamadı (ID: {role_id})"
                embed.add_field(name="Ana Kayıt Rolü", value=role_value, inline=True)
            else:
                embed.add_field(name="Ana Kayıt Rolü", value="❌ Ayarlanmamış", inline=True)
            
            # Adult role
            adult_role_id = settings.get("adult_role_id")
            if adult_role_id:
                adult_role = ctx.guild.get_role(int(adult_role_id))
                role_value = f"{adult_role.mention} ({adult_role.id})" if adult_role else f"Rol bulunamadı (ID: {adult_role_id})"
                embed.add_field(name="18+ Yaş Rolü", value=role_value, inline=True)
            else:
                embed.add_field(name="18+ Yaş Rolü", value="❌ Ayarlanmamış", inline=True)
            
            # Minor role
            minor_role_id = settings.get("minor_role_id")
            if minor_role_id:
                minor_role = ctx.guild.get_role(int(minor_role_id))
                role_value = f"{minor_role.mention} ({minor_role.id})" if minor_role else f"Rol bulunamadı (ID: {minor_role_id})"
                embed.add_field(name="18- Yaş Rolü", value=role_value, inline=True)
            else:
                embed.add_field(name="18- Yaş Rolü", value="❌ Ayarlanmamış", inline=True)
            
            # Bronze role
            bronze_role_id = settings.get("bronze_role_id")
            if bronze_role_id:
                bronze_role = ctx.guild.get_role(int(bronze_role_id))
                role_value = f"{bronze_role.mention} ({bronze_role.id})" if bronze_role else f"Rol bulunamadı (ID: {bronze_role_id})"
                embed.add_field(name="Bronz Rol", value=role_value, inline=True)
            else:
                embed.add_field(name="Bronz Rol", value="❌ Ayarlanmamış", inline=True)
            
            # Log channel
            log_channel_id = settings.get("log_channel_id")
            if log_channel_id:
                log_channel = ctx.guild.get_channel(int(log_channel_id))
                channel_value = f"{log_channel.mention} ({log_channel.id})" if log_channel else f"Kanal bulunamadı (ID: {log_channel_id})"
                embed.add_field(name="Log Kanalı", value=channel_value, inline=True)
            else:
                embed.add_field(name="Log Kanalı", value="❌ Ayarlanmamış", inline=True)
            
            embed.set_footer(text="Daha detaylı ayarlar için ayarlar modülündeki /register_settings komutunu kullanabilirsiniz.")
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error showing register settings: {e}")
            await ctx.send(embed=create_embed(
                f"Ayarlar gösterilirken bir hata oluştu: {str(e)}",
                discord.Color.red()
            ))
    
    @commands.command(name="debug_register", help="Check registration system status and troubleshoot issues")
    @commands.has_permissions(administrator=True)
    async def debug_register(self, ctx):
        """Command to debug registration system issues"""
        try:
            # Check MongoDB connection
            db_status = "✅ Connected" if self.mongo_db else "❌ Not connected"
            
            # Check if register button is in persistent views
            register_view_count = sum(1 for v in self.bot.persistent_views if isinstance(v, RegisterButton))
            
            # Build debug info embed
            embed = discord.Embed(
                title="Registration System Debug",
                description="Diagnostic information for the registration system",
                color=discord.Color.blue()
            )
            
            embed.add_field(name="Database Status", value=db_status, inline=False)
            embed.add_field(name="Register Button Views", value=str(register_view_count), inline=False)
            
            # Add guild settings info
            try:
                guild_settings = self.mongo_db["register"].find_one({"guild_id": str(ctx.guild.id)})
                if guild_settings:
                    settings_info = "✅ Found"
                    
                    # Check for required fields
                    for field in ["roles", "log_channel", "welcome_message"]:
                        if field in guild_settings:
                            embed.add_field(
                                name=f"{field.replace('_', ' ').title()}", 
                                value=f"✅ Configured", 
                                inline=True
                            )
                        else:
                            embed.add_field(
                                name=f"{field.replace('_', ' ').title()}", 
                                value=f"❌ Not configured", 
                                inline=True
                            )
                else:
                    settings_info = "❌ Not found - Run configuration commands first"
                
                embed.add_field(name="Guild Settings", value=settings_info, inline=False)
            except Exception as e:
                embed.add_field(name="Guild Settings", value=f"❌ Error: {str(e)}", inline=False)
            
            await ctx.send(embed=embed)
            
            # Create a fresh register button for testing
            await ctx.send(
                "New registration button for testing (temporary):", 
                view=RegisterButton()
            )
            
        except Exception as e:
            logger.error(f"Error in debug_register: {e}\n{traceback.format_exc()}")
            await ctx.send(f"Error during registration debug: {str(e)}")

    @commands.command(name="reset_register_views", help="Clear and reload registration buttons")
    @commands.has_permissions(administrator=True)
    async def reset_register_views(self, ctx):
        """Reset all registration button views"""
        try:
            # Create a new register button
            new_button = RegisterButton()
            
            # Add it to the bot
            self.bot.add_view(new_button)
            
            await ctx.send(
                embed=create_embed(
                    description="✅ Registration button views have been reset. New buttons should now work.",
                    color=discord.Color.green()
                )
            )
            
            # Send a test button
            await ctx.send("Test button:", view=new_button)
            
        except Exception as e:
            logger.error(f"Error in reset_register_views: {e}\n{traceback.format_exc()}")
            await ctx.send(f"Error resetting views: {str(e)}")

async def setup(bot):
    # Import the error_handler at setup time
    try:
        from utils.core.error_handler import setup_error_handlers
        setup_error_handlers(bot)
        logger.info("Error handlers set up")
    except Exception as e:
        logger.error(f"Failed to set up error handlers: {e}")
    
    await bot.add_cog(Register(bot))
    logger.info("Register cog loaded")
