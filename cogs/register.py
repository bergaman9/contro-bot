import discord
from discord import app_commands
from discord.ext import commands, tasks
from typing import Optional, List, Tuple, Union, Dict, Any
import traceback
import logging
import os

from utils.database.connection import get_async_db, is_db_available
from utils.core.formatting import create_embed, hex_to_int
from utils.core.error_handler import handle_interaction_error

# Set up logging
logger = logging.getLogger('register')

# Default values for settings
DEFAULT_WELCOME_MESSAGE = "Hoş geldin {mention}! Sunucumuza kayıt olduğun için teşekkürler."
DEFAULT_BUTTON_TITLE = "📝 Sunucu Kayıt Sistemi"
DEFAULT_BUTTON_DESCRIPTION = "Sunucumuza hoş geldiniz! Aşağıdaki butona tıklayarak kayıt olabilirsiniz."
DEFAULT_BUTTON_INSTRUCTIONS = "Kaydınızı tamamlamak için isminizi ve yaşınızı doğru bir şekilde girmeniz gerekmektedir."

class RegisterError(Exception):
    """Custom exception for registration errors"""
    pass

class RegisterButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        # Database connection handled via get_async_db() when needed
    
    @discord.ui.button(label="Kayıt Ol", style=discord.ButtonStyle.primary, custom_id="register_button")
    async def register_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            # Debug logging
            logger.info(f"Register button clicked by {interaction.user} (ID: {interaction.user.id}) in {interaction.guild.name if interaction.guild else 'DM'}")            
            
            # Get database connection
            mongo_db = get_async_db()
            
            # Check if user is already registered
            if is_db_available(mongo_db):
                try:
                    existing_registration = await mongo_db["register_log"].find_one({
                        "guild_id": interaction.guild.id,
                        "user_id": interaction.user.id
                    })
                    
                    if existing_registration:
                        # User is already registered, show update modal instead
                        await interaction.response.send_modal(RegisterUpdateModal(mongo_db, existing_registration))
                        return
                except Exception as db_error:
                    logger.error(f"Database query error in register button: {db_error}")
                    # Continue with new registration if DB query fails
            
            # Show modal to collect registration info for new users
            await interaction.response.send_modal(RegisterModal(mongo_db))
            
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
                settings = await self.mongo_db["register"].find_one({"guild_id": interaction.guild.id})
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
            assigned_roles_info = []
            
            # Priority 1: Age-based roles (if configured)
            age_role_assigned = False
            if age >= 18:
                adult_role_id = settings.get("adult_role_id")
                if adult_role_id:
                    adult_role = interaction.guild.get_role(int(adult_role_id))
                    if adult_role:
                        roles_to_add.append(adult_role)
                        assigned_roles_info.append(f"18+ Yaş Rolü: {adult_role.mention}")
                        age_role_assigned = True
            else:
                minor_role_id = settings.get("minor_role_id")
                if minor_role_id:
                    minor_role = interaction.guild.get_role(int(minor_role_id))
                    if minor_role:
                        roles_to_add.append(minor_role)
                        assigned_roles_info.append(f"18- Yaş Rolü: {minor_role.mention}")
                        age_role_assigned = True
            
            # Priority 2: If no age role assigned, assign member role (if configured)
            if not age_role_assigned:
                main_role_id = settings.get("role_id")
                if main_role_id:
                    main_role = interaction.guild.get_role(int(main_role_id))
                    if main_role:
                        roles_to_add.append(main_role)
                        assigned_roles_info.append(f"Üye Rolü: {main_role.mention}")
            
            # Check if we should save to database even without roles
            save_to_database = True
            
            # If no roles to assign, just save to database
            if not roles_to_add:
                logger.info(f"No roles configured for registration in guild {interaction.guild.id}, saving data only")
                assigned_roles_info.append("Henüz rol yapılandırılmamış - sadece veritabanına kaydedildi")
            
            # Update nickname
            try:
                await interaction.user.edit(nick=f"{self.name.value} | {age}")
            except discord.Forbidden:
                logger.warning(f"Missing permissions to change nickname for {interaction.user} in {interaction.guild.name}")
            
            # Add roles (if any)
            try:
                if roles_to_add:
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
            await self.mongo_db["register_log"].update_one(
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
            await self.mongo_db["register_stats"].update_one(
                {"guild_id": interaction.guild.id, "date": today},
                {"$inc": {"count": 1}},
                upsert=True
            )
            
            # Update weekly and total stats
            await self.mongo_db["register_stats"].update_one(
                {"guild_id": interaction.guild.id, "type": "weekly"},
                {"$inc": {"count": 1}},
                upsert=True
            )
            
            await self.mongo_db["register_stats"].update_one(
                {"guild_id": interaction.guild.id, "type": "total"},
                {"$inc": {"count": 1}},
                upsert=True
            )
            
            # Send registration log to configured channel
            await self.send_registration_log(interaction, self.name.value, age, roles_to_add)
            
            # Create success message with assigned roles info
            if assigned_roles_info:
                roles_text = "\n".join(assigned_roles_info)
            else:
                roles_text = "Henüz rol yapılandırılmamış - sadece veritabanına kaydedildi"
            
            # Get message format preference and welcome message
            message_format = settings.get("message_format", "embed")
            welcome_message = settings.get("welcome_message", DEFAULT_WELCOME_MESSAGE)
            
            # Format the welcome message with variables
            formatted_message = welcome_message.format(
                mention=interaction.user.mention,
                name=interaction.user.display_name,
                server=interaction.guild.name,
                member_count=interaction.guild.member_count,
                user_name=self.name.value,
                age=age
            )
            
            # Send registration success response
            if message_format == "embed":
                success_embed = create_embed(
                    title="✅ Kayıt Başarılı!",
                    description=formatted_message,
                    color=discord.Color.green()
                )
                success_embed.add_field(
                    name="📋 Verilen Roller",
                    value=roles_text,
                    inline=False
                )
                success_embed.add_field(
                    name="👤 Kayıt Bilgileri",
                    value=f"**İsim:** {self.name.value}\n**Yaş:** {age}",
                    inline=False
                )
                success_embed.set_thumbnail(url=interaction.user.display_avatar.url)
                
                await interaction.response.send_message(embed=success_embed, ephemeral=True)
            else:
                # Plain text format
                plain_message = f"✅ **Kayıt Başarılı!**\n\n{formatted_message}\n\n**Verilen Roller:**\n{roles_text}"
                await interaction.response.send_message(plain_message, ephemeral=True)
            
            # Log the registration
            logger.info(f"User registered: {interaction.user} (ID: {interaction.user.id}) in {interaction.guild.name} with roles {roles_text}")
            
            # Update the registration message in the channel
            await self.update_registration_message(interaction)
            
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
            settings = await self.mongo_db["register"].find_one({"guild_id": interaction.guild.id})
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
    
    async def update_registration_message(self, interaction: discord.Interaction):
        """Update the registration message with new statistics"""
        try:
            # Get registration channel from settings
            settings = await self.mongo_db["register"].find_one({"guild_id": interaction.guild.id})
            if not settings or "channel_id" not in settings:
                logger.debug(f"No registration channel configured for guild {interaction.guild.id}")
                return
            
            channel_id = settings["channel_id"]
            channel = interaction.guild.get_channel(int(channel_id))
            
            if not channel:
                logger.warning(f"Registration channel {channel_id} not found in guild {interaction.guild.id}")
                return
            
            # Find the registration message (look for messages with RegisterButton view)
            async for message in channel.history(limit=50):
                if (message.author == interaction.client.user and 
                    message.embeds and 
                    len(message.embeds) > 0 and
                    message.embeds[0].title and
                    "kayıt" in message.embeds[0].title.lower()):
                    
                    # Create new registration statistics card
                    try:
                        from utils.community.turkoyto.card_renderer import create_register_card
                        card_path = await create_register_card(interaction.client, interaction.guild, self.mongo_db)
                    except Exception as e:
                        logger.error(f"Error creating updated registration card: {e}")
                        return
                    
                    if not card_path:
                        logger.warning("Card path is None, skipping message update")
                        return
                    
                    # Create a new embed to avoid modifying the original
                    embed = discord.Embed(
                        title=message.embeds[0].title,
                        description=message.embeds[0].description,
                        color=message.embeds[0].color
                    )
                    
                    # Copy fields from original embed
                    for field in message.embeds[0].fields:
                        embed.add_field(name=field.name, value=field.value, inline=field.inline)
                    
                    # Set new image
                    embed.set_image(url=f"attachment://register_stats.png")
                    
                    # Update bot footer
                    bot_name = interaction.client.user.display_name
                    embed.set_footer(
                        text=f"Butona tıklayarak kayıt formunu açabilirsiniz • {bot_name}",
                        icon_url=interaction.client.user.display_avatar.url
                    )
                    
                    # Edit the message with new image and fresh button view
                    try:
                        with open(card_path, 'rb') as f:
                            file = discord.File(f, filename="register_stats.png")
                            # Create a fresh RegisterButton instance to avoid circular imports
                            button_view = RegisterButton()
                            await message.edit(embed=embed, attachments=[file], view=button_view)
                          # Clean up the temporary file
                        os.remove(card_path)
                        logger.info(f"Successfully updated registration message in {channel.name}")
                        return
                        
                    except Exception as edit_error:
                        logger.error(f"Error editing registration message: {edit_error}")
                        # Clean up file even if edit failed
                        try:
                            os.remove(card_path)
                        except Exception:
                            pass
                        return
                        
        except Exception as e:
            logger.error(f"Error updating registration message: {e}")
            # Don't re-raise the exception to prevent breaking the registration flow

class RegisterUpdateModal(discord.ui.Modal, title="Kayıt Güncelleme"):
    """Modal for updating existing registration information"""
    
    def __init__(self, mongo_db, existing_registration):
        super().__init__()
        self.mongo_db = mongo_db
        self.existing_registration = existing_registration
        
        # Pre-populate with existing data
        self.name = discord.ui.TextInput(
            label="İsminiz",
            placeholder="Gerçek isminizi girin",
            default=existing_registration.get("name", ""),
            required=True,
            max_length=32
        )
        
        self.age = discord.ui.TextInput(
            label="Yaşınız",
            placeholder="Yaşınızı girin (Sadece sayı)",
            default=str(existing_registration.get("age", "")),
            required=True,
            max_length=3
        )
        
        self.add_item(self.name)
        self.add_item(self.age)
    
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
                settings = await self.mongo_db["register"].find_one({"guild_id": interaction.guild.id})
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
            
            # Check if roles need to be updated based on age change
            old_age = self.existing_registration.get("age", 0)
            roles_to_add = []
            roles_to_remove = []
            assigned_roles_info = []
            
            # Get role objects
            main_role_id = settings.get("role_id")
            adult_role_id = settings.get("adult_role_id")
            minor_role_id = settings.get("minor_role_id")
            
            main_role = interaction.guild.get_role(int(main_role_id)) if main_role_id else None
            adult_role = interaction.guild.get_role(int(adult_role_id)) if adult_role_id else None
            minor_role = interaction.guild.get_role(int(minor_role_id)) if minor_role_id else None
            
            # Determine role changes
            age_role_assigned = False
            if age >= 18:
                if adult_role and adult_role not in interaction.user.roles:
                    roles_to_add.append(adult_role)
                    assigned_roles_info.append(f"18+ Yaş Rolü: {adult_role.mention}")
                    age_role_assigned = True
                if minor_role and minor_role in interaction.user.roles:
                    roles_to_remove.append(minor_role)
            else:
                if minor_role and minor_role not in interaction.user.roles:
                    roles_to_add.append(minor_role)
                    assigned_roles_info.append(f"18- Yaş Rolü: {minor_role.mention}")
                    age_role_assigned = True
                if adult_role and adult_role in interaction.user.roles:
                    roles_to_remove.append(adult_role)
            
            # Update nickname
            try:
                await interaction.user.edit(nick=f"{self.name.value} | {age}")
            except discord.Forbidden:
                logger.warning(f"Missing permissions to change nickname for {interaction.user} in {interaction.guild.name}")
            
            # Update roles
            try:
                if roles_to_add:
                    await interaction.user.add_roles(*roles_to_add)
                if roles_to_remove:
                    await interaction.user.remove_roles(*roles_to_remove)
            except discord.Forbidden:
                return await interaction.response.send_message(
                    embed=create_embed(
                        description="❌ Rolleri güncellemek için yetkim yok. Lütfen bir yetkiliyle iletişime geçin.",
                        color=discord.Color.red()
                    ),
                    ephemeral=True
                )
            
            # Update database record
            today = discord.utils.utcnow().strftime("%Y-%m-%d")
            current_time = discord.utils.utcnow().timestamp()
            
            await self.mongo_db["register_log"].update_one(
                {"guild_id": interaction.guild.id, "user_id": interaction.user.id},
                {"$set": {
                    "name": self.name.value,
                    "age": age,
                    "updated_at": current_time,
                    "last_update_date": today
                }}
            )
            
            # Create success message
            message_format = settings.get("message_format", "embed")
            
            if assigned_roles_info:
                roles_text = "\n".join(assigned_roles_info)
            else:
                roles_text = "Rol değişikliği yapılmadı"
            
            if message_format == "embed":
                success_embed = create_embed(
                    title="✅ Kayıt Güncellendi!",
                    description="Kayıt bilgileriniz başarıyla güncellendi.",
                    color=discord.Color.green()
                )
                success_embed.add_field(
                    name="📋 Güncellenen Roller",
                    value=roles_text,
                    inline=False
                )
                success_embed.add_field(
                    name="👤 Güncel Bilgiler",
                    value=f"**İsim:** {self.name.value}\n**Yaş:** {age}",
                    inline=False
                )
                success_embed.set_thumbnail(url=interaction.user.display_avatar.url)
                
                await interaction.response.send_message(embed=success_embed, ephemeral=True)
            else:
                # Plain text format
                plain_message = f"✅ **Kayıt Güncellendi!**\n\nKayıt bilgileriniz başarıyla güncellendi.\n\n**Rol Değişiklikleri:**\n{roles_text}"
                await interaction.response.send_message(plain_message, ephemeral=True)
            
            # Log the update
            logger.info(f"User updated registration: {interaction.user} (ID: {interaction.user.id}) in {interaction.guild.name}")
            
        except Exception as e:
            logger.error(f"Registration update error: {e}\n{traceback.format_exc()}")
            await interaction.response.send_message(
                embed=create_embed(
                    description=f"❌ Kayıt güncelleme sırasında bir hata oluştu: {str(e)}",
                    color=discord.Color.red()
                ),
                ephemeral=True
            )

class Register(commands.Cog):
    """
    Server registration system to manage new members
    """
    def __init__(self, bot):
        self.bot = bot
        # Initialize database connection - get_async_db() returns the database directly
        self.mongo_db = get_async_db()
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
            if is_db_available(self.mongo_db):
                settings = await self.mongo_db["register"].find_one({"guild_id": guild.id})
            else:
                settings = None
            if not settings:
                logger.debug(f"No registration settings found for guild: {guild.name}")
                return
                
            # Get the roles to be assigned
            main_role_id = settings.get("role_id")
            adult_role_id = settings.get("adult_role_id")
            minor_role_id = settings.get("minor_role_id")
            
            # Get role objects
            main_role = guild.get_role(int(main_role_id)) if main_role_id else None
            adult_role = guild.get_role(int(adult_role_id)) if adult_role_id else None
            minor_role = guild.get_role(int(minor_role_id)) if minor_role_id else None
            
            # Skip if no roles are configured
            if not any([main_role, adult_role, minor_role]):
                logger.debug(f"No roles configured for guild: {guild.name}")
                return
                
            # Get all registered members
            if is_db_available(self.mongo_db):
                registered_users = await self.mongo_db["register_log"].find({"guild_id": guild.id}).to_list(length=None)
            else:
                registered_users = []
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
