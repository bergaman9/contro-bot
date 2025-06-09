import discord
from discord.ext import commands
from utils.core.formatting import create_embed
from utils.database.connection import initialize_mongodb

class TicketSettingsView(discord.ui.View):
    """View for configuring ticket system settings"""
    
    def __init__(self, bot, timeout=180):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.mongo_db = initialize_mongodb()
    
    @discord.ui.button(label="Kategori Ayarla", style=discord.ButtonStyle.primary, custom_id="set_ticket_category", row=0)
    async def set_category_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Set the category where ticket channels will be created"""
        await interaction.response.send_modal(SetTicketCategoryModal(self.bot))
    
    @discord.ui.button(label="Log Kanalı Ayarla", style=discord.ButtonStyle.primary, custom_id="set_ticket_log", row=0)
    async def set_log_channel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Set the channel where ticket actions will be logged"""
        await interaction.response.send_modal(SetTicketLogChannelModal(self.bot))
    
    @discord.ui.button(label="Destek Rollerini Ayarla", style=discord.ButtonStyle.primary, custom_id="set_support_roles", row=1)
    async def set_support_roles_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Set the roles that will have access to tickets"""
        await interaction.response.send_modal(SetSupportRolesModal(self.bot))
    
    @discord.ui.button(label="Bilet Alanlarını Düzenle", style=discord.ButtonStyle.primary, custom_id="edit_ticket_fields", row=1)
    async def edit_ticket_fields_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Edit the form fields for the ticket creation modal"""
        await interaction.response.send_modal(EditTicketFieldsModal(self.bot))
    
    @discord.ui.button(label="Otomatik Arşivlemeyi Ayarla", style=discord.ButtonStyle.primary, custom_id="set_ticket_archiving", row=2)
    async def set_ticket_archiving_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Configure automatic ticket archiving settings"""
        await interaction.response.defer(ephemeral=True)
        
        # Toggle auto-archiving setting
        guild_id = str(interaction.guild.id)
        ticket_config = self.mongo_db.ticket_config.find_one({"guild_id": guild_id})
        
        auto_archive = not ticket_config.get("auto_archive", False) if ticket_config else True
        
        # Update or create config
        if ticket_config:
            self.mongo_db.ticket_config.update_one(
                {"guild_id": guild_id},
                {"$set": {"auto_archive": auto_archive}}
            )
        else:
            self.mongo_db.ticket_config.insert_one({
                "guild_id": guild_id,
                "auto_archive": auto_archive
            })
        
        status = "etkinleştirildi" if auto_archive else "devre dışı bırakıldı"
        await interaction.followup.send(
            embed=create_embed(f"Otomatik bilet arşivleme {status}.", discord.Color.green()),
            ephemeral=True
        )
    
    @discord.ui.button(label="Silme/Arşivleme Seçenekleri", style=discord.ButtonStyle.primary, custom_id="delete_or_archive", row=2)
    async def delete_or_archive_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Choose whether to delete or archive closed tickets"""
        await interaction.response.defer(ephemeral=True)
        
        # Toggle delete tickets setting
        guild_id = str(interaction.guild.id)
        ticket_config = self.mongo_db.ticket_config.find_one({"guild_id": guild_id})
        
        delete_tickets = not ticket_config.get("delete_tickets", False) if ticket_config else True
        
        # Update or create config
        if ticket_config:
            self.mongo_db.ticket_config.update_one(
                {"guild_id": guild_id},
                {"$set": {"delete_tickets": delete_tickets}}
            )
        else:
            self.mongo_db.ticket_config.insert_one({
                "guild_id": guild_id,
                "delete_tickets": delete_tickets
            })
        
        action = "silinecek" if delete_tickets else "arşivlenecek"
        await interaction.followup.send(
            embed=create_embed(f"Kapatılan biletler artık {action}.", discord.Color.green()),
            ephemeral=True
        )
    
    @discord.ui.button(label="Geri", style=discord.ButtonStyle.danger, custom_id="back_to_settings", row=3)
    async def back_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Return to main settings panel"""
        # This will be handled by the settings cog
        await interaction.response.defer(ephemeral=True)


class SetTicketCategoryModal(discord.ui.Modal, title="Bilet Kategorisi Ayarla"):
    """Modal for setting the ticket category"""
    
    category_id = discord.ui.TextInput(
        label="Kategori ID",
        placeholder="Biletlerin oluşturulacağı kategorinin ID'sini girin",
        required=True,
        style=discord.TextStyle.short
    )
    
    def __init__(self, bot):
        super().__init__()
        self.bot = bot
        self.mongo_db = initialize_mongodb()
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            category_id = int(self.category_id.value.strip())
            category = interaction.guild.get_channel(category_id)
            
            if not category or not isinstance(category, discord.CategoryChannel):
                return await interaction.response.send_message(
                    embed=create_embed("Geçerli bir kategori ID'si girmelisiniz.", discord.Color.red()),
                    ephemeral=True
                )
            
            # Save to database
            guild_id = str(interaction.guild.id)
            ticket_config = self.mongo_db.ticket_config.find_one({"guild_id": guild_id})
            
            if ticket_config:
                self.mongo_db.ticket_config.update_one(
                    {"guild_id": guild_id},
                    {"$set": {"category_id": category_id}}
                )
            else:
                self.mongo_db.ticket_config.insert_one({
                    "guild_id": guild_id,
                    "category_id": category_id
                })
            
            await interaction.response.send_message(
                embed=create_embed(f"Bilet kategorisi başarıyla {category.name} olarak ayarlandı.", discord.Color.green()),
                ephemeral=True
            )
            
        except ValueError:
            await interaction.response.send_message(
                embed=create_embed("Geçerli bir kategori ID'si girmelisiniz.", discord.Color.red()),
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                embed=create_embed(f"Bir hata oluştu: {str(e)}", discord.Color.red()),
                ephemeral=True
            )


class SetTicketLogChannelModal(discord.ui.Modal, title="Bilet Log Kanalı Ayarla"):
    """Modal for setting the ticket log channel"""
    
    channel_id = discord.ui.TextInput(
        label="Kanal ID",
        placeholder="Bilet işlemlerinin loglanacağı kanalın ID'sini girin",
        required=True,
        style=discord.TextStyle.short
    )
    
    def __init__(self, bot):
        super().__init__()
        self.bot = bot
        self.mongo_db = initialize_mongodb()
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            channel_id = int(self.channel_id.value.strip())
            channel = interaction.guild.get_channel(channel_id)
            
            if not channel or not isinstance(channel, discord.TextChannel):
                return await interaction.response.send_message(
                    embed=create_embed("Geçerli bir metin kanalı ID'si girmelisiniz.", discord.Color.red()),
                    ephemeral=True
                )
            
            # Save to database
            guild_id = str(interaction.guild.id)
            ticket_config = self.mongo_db.ticket_config.find_one({"guild_id": guild_id})
            
            if ticket_config:
                self.mongo_db.ticket_config.update_one(
                    {"guild_id": guild_id},
                    {"$set": {"log_channel_id": channel_id}}
                )
            else:
                self.mongo_db.ticket_config.insert_one({
                    "guild_id": guild_id,
                    "log_channel_id": channel_id
                })
            
            await interaction.response.send_message(
                embed=create_embed(f"Bilet log kanalı başarıyla {channel.mention} olarak ayarlandı.", discord.Color.green()),
                ephemeral=True
            )
            
        except ValueError:
            await interaction.response.send_message(
                embed=create_embed("Geçerli bir kanal ID'si girmelisiniz.", discord.Color.red()),
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                embed=create_embed(f"Bir hata oluştu: {str(e)}", discord.Color.red()),
                ephemeral=True
            )


class SetSupportRolesModal(discord.ui.Modal, title="Destek Rollerini Ayarla"):
    """Modal for setting support roles"""
    
    role_ids = discord.ui.TextInput(
        label="Rol ID'leri",
        placeholder="Destek rollerinin ID'lerini virgülle ayırarak girin",
        required=True,
        style=discord.TextStyle.paragraph
    )
    
    def __init__(self, bot):
        super().__init__()
        self.bot = bot
        self.mongo_db = initialize_mongodb()
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Parse role IDs
            role_id_strings = self.role_ids.value.split(',')
            role_ids = []
            invalid_ids = []
            
            for id_str in role_id_strings:
                id_str = id_str.strip()
                if not id_str:
                    continue
                    
                try:
                    role_id = int(id_str)
                    role = interaction.guild.get_role(role_id)
                    
                    if role:
                        role_ids.append(role_id)
                    else:
                        invalid_ids.append(id_str)
                except ValueError:
                    invalid_ids.append(id_str)
            
            if not role_ids:
                return await interaction.response.send_message(
                    embed=create_embed("En az bir geçerli rol ID'si girmelisiniz.", discord.Color.red()),
                    ephemeral=True
                )
            
            # Save to database
            guild_id = str(interaction.guild.id)
            ticket_config = self.mongo_db.ticket_config.find_one({"guild_id": guild_id})
            
            if ticket_config:
                self.mongo_db.ticket_config.update_one(
                    {"guild_id": guild_id},
                    {"$set": {"support_role_ids": role_ids}}
                )
            else:
                self.mongo_db.ticket_config.insert_one({
                    "guild_id": guild_id,
                    "support_role_ids": role_ids
                })
            
            # Construct response message
            role_mentions = [f"<@&{role_id}>" for role_id in role_ids]
            roles_text = ", ".join(role_mentions)
            
            response = f"Destek rolleri başarıyla ayarlandı: {roles_text}"
            if invalid_ids:
                response += f"\n\nGeçersiz ID'ler: {', '.join(invalid_ids)}"
            
            await interaction.response.send_message(
                embed=create_embed(response, discord.Color.green()),
                ephemeral=True
            )
            
        except Exception as e:
            await interaction.response.send_message(
                embed=create_embed(f"Bir hata oluştu: {str(e)}", discord.Color.red()),
                ephemeral=True
            )


class EditTicketFieldsModal(discord.ui.Modal, title="Bilet Alanlarını Düzenle"):
    """Modal for editing ticket form fields"""
    
    field_config = discord.ui.TextInput(
        label="Alan Yapılandırması (JSON)",
        placeholder='[{"label": "Konu", "placeholder": "Sorununuzu kısaca açıklayın"}]',
        required=True,
        style=discord.TextStyle.paragraph
    )
    
    def __init__(self, bot):
        super().__init__()
        self.bot = bot
        self.mongo_db = initialize_mongodb()
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            import json
            
            # Parse JSON config
            fields_config = json.loads(self.field_config.value)
            
            if not isinstance(fields_config, list):
                return await interaction.response.send_message(
                    embed=create_embed("Alan yapılandırması bir liste olmalıdır.", discord.Color.red()),
                    ephemeral=True
                )
            
            # Validate each field has required properties
            for field in fields_config:
                if not isinstance(field, dict) or "label" not in field or "placeholder" not in field:
                    return await interaction.response.send_message(
                        embed=create_embed("Her alan için 'label' ve 'placeholder' özellikleri gereklidir.", discord.Color.red()),
                        ephemeral=True
                    )
            
            # Save to database
            guild_id = str(interaction.guild.id)
            ticket_config = self.mongo_db.ticket_config.find_one({"guild_id": guild_id})
            
            if ticket_config:
                self.mongo_db.ticket_config.update_one(
                    {"guild_id": guild_id},
                    {"$set": {"fields": fields_config}}
                )
            else:
                self.mongo_db.ticket_config.insert_one({
                    "guild_id": guild_id,
                    "fields": fields_config
                })
            
            await interaction.response.send_message(
                embed=create_embed(f"{len(fields_config)} bilet alanı başarıyla yapılandırıldı.", discord.Color.green()),
                ephemeral=True
            )
            
        except json.JSONDecodeError:
            await interaction.response.send_message(
                embed=create_embed("Geçerli bir JSON yapısı girmelisiniz.", discord.Color.red()),
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                embed=create_embed(f"Bir hata oluştu: {str(e)}", discord.Color.red()),
                ephemeral=True
            )
