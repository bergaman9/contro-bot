import discord
from discord import app_commands
from discord.ext import commands, tasks
from typing import Optional, List, Tuple, Union, Dict, Any
import traceback
import logging
import os

from src.utils.database.connection import is_db_available
from src.utils.core.formatting import create_embed
from src.utils.core.error_handler import handle_interaction_error
from src.utils.community.generic.card_renderer import create_register_card
from src.utils.database.db_manager import db_manager
from src.cogs.base import BaseCog

# Set up logging
logger = logging.getLogger('register')

class RegisterError(Exception):
    """Custom exception for registration errors"""
    pass

class RegisterButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label="Kayıt Ol", style=discord.ButtonStyle.primary, custom_id="register_button_persistent")
    async def register_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            # Debug logging
            logger.info(f"Register button clicked by {interaction.user} (ID: {interaction.user.id}) in {interaction.guild.name if interaction.guild else 'DM'}")            
            
            # Get MongoDB connection from central manager
            mongo_db = await get_async_database()
            if not mongo_db:
                await interaction.response.send_message(
                    embed=create_embed(
                        description="❌ Veritabanı bağlantısı kurulamadı. Lütfen daha sonra tekrar deneyin.",
                        color=discord.Color.red()
                    ),
                    ephemeral=True
                )
                return
            
            # Create and setup modal with dynamic fields
            modal = RegisterModal(mongo_db)
            await modal.setup_fields(interaction.guild.id)
            
            # Show modal to collect registration info
            await interaction.response.send_modal(modal)
            
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
    
    def __init__(self, mongo_db):
        super().__init__()
        self.mongo_db = mongo_db
        self._custom_fields = {}
        
    async def setup_fields(self, guild_id: int):
        """Setup dynamic fields based on guild configuration"""
        try:
            # Get guild settings with field configuration
            settings = await self.mongo_db.get_collection("register").find_one({"guild_id": guild_id})
            if not settings:
                settings = {}
            
            # Default fields (name and age are always present unless disabled)
            if settings.get("name_field_enabled", True):
                self.name = discord.ui.TextInput(
                    label="İsminiz",
                    placeholder="Gerçek isminizi girin",
                    required=True,
                    max_length=32
                )
                self.add_item(self.name)
            
            if settings.get("age_field_enabled", True):
                self.age = discord.ui.TextInput(
                    label="Yaşınız",
                    placeholder="Yaşınızı girin (Sadece sayı)",
                    required=True,
                    max_length=3
                )
                self.add_item(self.age)
            
            # Add custom fields from Advanced settings
            custom_fields = settings.get("custom_fields", [])
            for field in custom_fields:
                if not field.get("enabled", False):
                    continue
                    
                field_name = field.get("name", "")
                field_label = field.get("label", field_name)
                field_type = field.get("type", "text")
                field_required = field.get("required", False)
                field_placeholder = field.get("placeholder", "")
                max_length = field.get("max_length", 100)
                
                # Skip if no name provided
                if not field_name:
                    continue
                
                # Create the text input based on field type
                if field_type == "paragraph":
                    text_input = discord.ui.TextInput(
                        label=field_label,
                        style=discord.TextStyle.paragraph,
                        placeholder=field_placeholder,
                        required=field_required,
                        max_length=min(max_length, 1024)  # Discord limit
                    )
                else:
                    text_input = discord.ui.TextInput(
                        label=field_label,
                        style=discord.TextStyle.short,
                        placeholder=field_placeholder,
                        required=field_required,
                        max_length=min(max_length, 100)  # Discord limit for short fields
                    )
                
                # Store field mapping for later retrieval
                self._custom_fields[field_name] = text_input
                self.add_item(text_input)
                
                # Discord modal limit is 5 fields
                if len(self.children) >= 5:
                    break
                    
        except Exception as e:
            logger.error(f"Error setting up modal fields: {e}")
            # Fallback to default fields if configuration fails
            if not hasattr(self, 'name'):
                self.name = discord.ui.TextInput(
                    label="İsminiz",
                    placeholder="Gerçek isminizi girin",
                    required=True,
                    max_length=32
                )
                self.add_item(self.name)
            
            if not hasattr(self, 'age'):
                self.age = discord.ui.TextInput(
                    label="Yaşınız",
                    placeholder="Yaşınızı girin (Sadece sayı)",
                    required=True,
                    max_length=3
                )
                self.add_item(self.age)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Validate age if age field is present
            age = None
            if hasattr(self, 'age'):
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
                settings = await self.mongo_db.get_collection("register").find_one({"guild_id": interaction.guild.id})
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
            
            # Collect all field values including custom fields
            user_data = {}
            if hasattr(self, 'name'):
                user_data['name'] = self.name.value
            if hasattr(self, 'age'):
                user_data['age'] = age
                
            # Collect custom field values
            for field_name, text_input in self._custom_fields.items():
                user_data[field_name] = text_input.value
            
            # Get roles to assign
            roles_to_add = []
            
            # Given roles (roles to add)
            given_roles = settings.get("given_roles", [])
            if isinstance(given_roles, list):
                for role_id in given_roles:
                    if role_id:  # Skip empty role IDs
                        role = interaction.guild.get_role(int(role_id))
                        if role:
                            roles_to_add.append(role)
            
            # Fallback to legacy role_id if no given_roles
            if not roles_to_add:
                main_role_id = settings.get("role_id")
                if main_role_id:
                    main_role = interaction.guild.get_role(int(main_role_id))
                    if main_role:
                        roles_to_add.append(main_role)
            
            # Age-based role (18+ or 18-)
            if age is not None:
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
            
            # Remove taken roles (roles to remove)
            roles_to_remove = []
            taken_roles = settings.get("taken_roles", [])
            if isinstance(taken_roles, list):
                for role_id in taken_roles:
                    if role_id:  # Skip empty role IDs
                        role = interaction.guild.get_role(int(role_id))
                        if role and role in interaction.user.roles:
                            roles_to_remove.append(role)
            
            # No roles to add
            if not roles_to_add:
                return await interaction.response.send_message(
                    embed=create_embed(
                        description="❌ Kayıt rolleri bulunamadı. Lütfen bir yetkiliyle iletişime geçin.",
                        color=discord.Color.red()
                    ),
                    ephemeral=True
                )
            
            # Update nickname with dynamic formatting
            await self._update_nickname(interaction, user_data, settings)
            
            # Remove roles first, then add new ones
            try:
                if roles_to_remove:
                    await interaction.user.remove_roles(*roles_to_remove)
                    logger.info(f"Removed roles from {interaction.user}: {[r.name for r in roles_to_remove]}")
                
                await interaction.user.add_roles(*roles_to_add)
                logger.info(f"Added roles to {interaction.user}: {[r.name for r in roles_to_add]}")
            except discord.Forbidden:
                return await interaction.response.send_message(
                    embed=create_embed(
                        description="❌ Rolleri vermek için yetkim yok. Lütfen bir yetkiliyle iletişime geçin.",
                        color=discord.Color.red()
                    ),
                    ephemeral=True
                )
            
            # Record registration in database with all custom fields
            today = discord.utils.utcnow().strftime("%Y-%m-%d")
            current_time = discord.utils.utcnow().timestamp()
            
            # Prepare registration data
            registration_data = {
                "guild_id": interaction.guild.id,
                "user_id": interaction.user.id,
                "username": interaction.user.name,
                "registered_at": current_time,
                "registration_date": today,
                **user_data  # Include all collected user data
            }
            
            # Update user registration record
            await self.mongo_db.get_collection("register_log").update_one(
                {"guild_id": interaction.guild.id, "user_id": interaction.user.id},
                {"$set": registration_data},
                upsert=True
            )
            
            # Update daily registration stats
            await self.mongo_db.get_collection("register_stats").update_one(
                {"guild_id": interaction.guild.id, "date": today},
                {"$inc": {"count": 1}},
                upsert=True
            )
            
            # Update weekly and total stats
            await self.mongo_db.get_collection("register_stats").update_one(
                {"guild_id": interaction.guild.id, "type": "weekly"},
                {"$inc": {"count": 1}},
                upsert=True
            )
            
            await self.mongo_db.get_collection("register_stats").update_one(
                {"guild_id": interaction.guild.id, "type": "total"},
                {"$inc": {"count": 1}},
                upsert=True
            )
            
            # Send registration log to configured channel
            await self.send_registration_log(interaction, user_data, roles_to_add)
            
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
            
            # Create and send registration statistics card
            try:
                card_path = await create_register_card(interaction.client, interaction.guild, self.mongo_db)
                if card_path:
                    # Send the card to the channel where registration panel was sent (if configured)
                    settings = await self.mongo_db.get_collection("register").find_one({"guild_id": interaction.guild.id})
                    panel_channel_id = settings.get("panel_channel_id")
                    if panel_channel_id:
                        panel_channel = interaction.guild.get_channel(int(panel_channel_id))
                        if panel_channel:
                            # Create embed with updated statistics
                            stats_embed = create_embed(
                                title="📊 Kayıt İstatistikleri Güncellendi",
                                description="Kayıt sayıları güncellenmiştir.",
                                color=discord.Color.blue()
                            )
                            
                            # Send updated card to the panel channel
                            await panel_channel.send(
                                embed=stats_embed,
                                file=discord.File(card_path, filename="register_stats.png")
                            )
                            
                            # Clean up the image file
                            try:
                                os.remove(card_path)
                            except Exception:
                                pass
                            
                            logger.info(f"Registration statistics card sent to channel {panel_channel.name}")
                        else:
                            logger.warning(f"Panel channel {panel_channel_id} not found for guild {interaction.guild.id}")
                    else:
                        logger.debug(f"No panel channel configured for registration stats in guild {interaction.guild.id}")
                else:
                    logger.warning("Failed to create registration statistics card")
            except Exception as card_error:
                logger.error(f"Error creating/sending registration card: {card_error}", exc_info=True)
            
        except Exception as e:
            logger.error(f"Registration error: {e}\n{traceback.format_exc()}")
            await interaction.response.send_message(
                embed=create_embed(
                    description=f"❌ Kayıt işlemi sırasında bir hata oluştu: {str(e)}",
                    color=discord.Color.red()
                ),
                ephemeral=True
            )
    
    async def _update_nickname(self, interaction: discord.Interaction, user_data: dict, settings: dict):
        """Update user nickname with dynamic formatting"""
        try:
            nickname_enabled = settings.get("nickname_edit", True)
            if not nickname_enabled:
                return
                
            nickname_format = settings.get("nickname_format", "{name} | {age}")
            
            # Replace variables in nickname format
            formatted_nickname = nickname_format
            
            # Replace built-in variables
            formatted_nickname = formatted_nickname.replace("{username}", interaction.user.name)
            formatted_nickname = formatted_nickname.replace("{display_name}", interaction.user.display_name)
            formatted_nickname = formatted_nickname.replace("{user_id}", str(interaction.user.id))
            
            # Replace user data variables (name, age, custom fields)
            for key, value in user_data.items():
                placeholder = "{" + key + "}"
                formatted_nickname = formatted_nickname.replace(placeholder, str(value))
            
            # Apply nickname formatting settings
            max_length = settings.get("nickname_max_length", 32)
            capitalize_names = settings.get("nickname_capitalize_names", False)
            remove_special_chars = settings.get("nickname_remove_special_chars", False)
            
            if capitalize_names:
                formatted_nickname = formatted_nickname.title()
                
            if remove_special_chars:
                import re
                formatted_nickname = re.sub(r'[^\w\s\|\-]', '', formatted_nickname)
            
            # Truncate if too long
            if len(formatted_nickname) > max_length:
                formatted_nickname = formatted_nickname[:max_length]
            
            # Update nickname
            await interaction.user.edit(nick=formatted_nickname)
            logger.info(f"Updated nickname for {interaction.user} to: {formatted_nickname}")
            
        except discord.Forbidden:
            logger.warning(f"Missing permissions to change nickname for {interaction.user} in {interaction.guild.name}")
        except Exception as e:
            logger.error(f"Error updating nickname: {e}")
    
    async def send_registration_log(self, interaction: discord.Interaction, user_data: dict, roles: list):
        """Send registration log to configured channel"""
        try:
            # Get log channel from settings
            settings = await self.mongo_db.get_collection("register").find_one({"guild_id": interaction.guild.id})
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
            
            # Format registration info
            registration_info = []
            for key, value in user_data.items():
                if key in ['name', 'age']:
                    display_key = {'name': 'İsim', 'age': 'Yaş'}.get(key, key.title())
                    registration_info.append(f"**{display_key}:** {value}")
                elif value:  # Only show non-empty custom fields
                    registration_info.append(f"**{key.title()}:** {value}")
            
            embed.add_field(
                name="📝 Kayıt Bilgileri",
                value="\n".join(registration_info) if registration_info else "Bilgi yok",
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

class Register(BaseCog):
    """
    Server registration system to manage new members
    """
    def __init__(self, bot):
        super().__init__(bot)
        self.mongo_db = None
        
        # Start the background task for role verification
        self.check_members_roles.start()
        logger.info(f"Register cog initialized")
        
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
            # Get MongoDB connection from central manager
            mongo_db = db_manager.get_database()
            if mongo_db is None:
                logger.warning(f"No database connection available for guild {guild.name}")
                return
            
            # Get guild settings
            settings = await mongo_db["register"].find_one({"guild_id": guild.id})
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
            registered_users = []
            async for user_doc in mongo_db["register_log"].find({"guild_id": guild.id}):
                registered_users.append(user_doc)
            
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
        mongo_db = db_manager.get_database()
        if not mongo_db:
            raise RegisterError("Veritabanı bağlantısı kurulamadı.")
            
        settings = await mongo_db["register"].find_one({"guild_id": guild_id})
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

async def setup(bot):
    # Import the error_handler at setup time
    try:
        from src.utils.core.error_handler import setup_error_handlers
        setup_error_handlers(bot)
        logger.info("Error handlers set up")
    except Exception as e:
        logger.error(f"Failed to set up error handlers: {e}")
    
    await bot.add_cog(Register(bot))
    logger.info("Register cog loaded")
