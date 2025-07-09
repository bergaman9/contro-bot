import discord
from discord import ui
from discord.ext import commands
import asyncio
from typing import Optional, List, Dict
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class DepartmentSettingsView(discord.ui.View):
    """Departman ayarları için ana view"""
    
    def __init__(self, bot, guild_id: int):
        super().__init__(timeout=300)
        self.bot = bot
        self.guild_id = guild_id
        self.current_page = 0
        self.departments = []
        
    async def initialize(self):
        """Departmanları yükle"""
        try:
            db = self.bot.async_db
            settings = await db.ticket_settings.find_one({'guild_id': self.guild_id})
            
            if settings and 'departments' in settings:
                self.departments = settings['departments']
            else:
                # Default departmanlar
                self.departments = [
                    {
                        'id': 'general_support',
                        'name': 'General Support',
                        'description': 'General questions and assistance',
                        'emoji': '🎫',
                        'category_id': None,
                        'staff_roles': [],
                        'auto_assign_staff': False,
                        'welcome_message': 'Welcome to General Support!\nA staff member will assist you shortly.',
                        'button_style': 'primary',
                        'form_fields': []
                    },
                    {
                        'id': 'technical_issues',
                        'name': 'Technical Issues',
                        'description': 'Technical problems and bug reports',
                        'emoji': '🔧',
                        'category_id': None,
                        'staff_roles': [],
                        'auto_assign_staff': False,
                        'welcome_message': 'Welcome to Technical Support!\nPlease describe your issue in detail.',
                        'button_style': 'danger',
                        'form_fields': []
                    }
                ]
                # Save default departments
                await db.ticket_settings.update_one(
                    {'guild_id': self.guild_id},
                    {'$set': {'departments': self.departments}},
                    upsert=True
                )
        except Exception as e:
            logger.error(f"Error loading departments: {e}")
    
    @discord.ui.button(label="➕ Create Department", style=discord.ButtonStyle.success, row=0)
    async def create_department(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Yeni departman oluştur"""
        modal = CreateDepartmentModal(self)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="📝 Edit Department", style=discord.ButtonStyle.primary, row=0)
    async def edit_department(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Departman düzenle"""
        if not self.departments:
            await interaction.response.send_message("No departments to edit!", ephemeral=True)
            return
        
        view = DepartmentSelectView(self, "edit")
        embed = discord.Embed(
            title="Select Department to Edit",
            description="Choose a department from the dropdown below:",
            color=discord.Color.blue()
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @discord.ui.button(label="🗑️ Delete Department", style=discord.ButtonStyle.danger, row=0)
    async def delete_department(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Departman sil"""
        if not self.departments:
            await interaction.response.send_message("No departments to delete!", ephemeral=True)
            return
        
        view = DepartmentSelectView(self, "delete")
        embed = discord.Embed(
            title="Select Department to Delete",
            description="⚠️ This action cannot be undone!",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @discord.ui.button(label="🔧 Configure Forms", style=discord.ButtonStyle.secondary, row=1)
    async def configure_forms(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Form field'larını yapılandır"""
        if not self.departments:
            await interaction.response.send_message("No departments to configure!", ephemeral=True)
            return
        
        view = DepartmentSelectView(self, "forms")
        embed = discord.Embed(
            title="Select Department for Form Configuration",
            description="Choose a department to configure its form fields:",
            color=discord.Color.blue()
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @discord.ui.button(label="📋 View Departments", style=discord.ButtonStyle.secondary, row=1)
    async def view_departments(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Tüm departmanları görüntüle"""
        embed = self.create_departments_embed()
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @discord.ui.button(label="❌ Close", style=discord.ButtonStyle.danger, row=2)
    async def close_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Menüyü kapat"""
        await interaction.response.defer()
        await interaction.delete_original_response()
    
    def create_departments_embed(self):
        """Departmanlar için embed oluştur"""
        embed = discord.Embed(
            title="🎫 Ticket Departments",
            description=f"Total Departments: {len(self.departments)}",
            color=discord.Color.blue()
        )
        
        for dept in self.departments[:25]:  # Discord limit
            category_text = f"<#{dept.get('category_id')}>" if dept.get('category_id') else "Not Set"
            staff_count = len(dept.get('staff_roles', []))
            form_count = len(dept.get('form_fields', []))
            
            embed.add_field(
                name=f"{dept.get('emoji', '🎫')} {dept['name']}",
                value=f"**Category:** {category_text}\n"
                      f"**Staff Roles:** {staff_count} roles\n"
                      f"**Form Fields:** {form_count} fields\n"
                      f"**Auto-assign:** {'Yes' if dept.get('auto_assign_staff') else 'No'}",
                inline=True
            )
        
        return embed
    
    async def save_departments(self):
        """Departmanları veritabanına kaydet"""
        try:
            db = self.bot.async_db
            await db.ticket_settings.update_one(
                {'guild_id': self.guild_id},
                {'$set': {'departments': self.departments}},
                upsert=True
            )
            return True
        except Exception as e:
            logger.error(f"Error saving departments: {e}")
            return False


class CreateDepartmentModal(discord.ui.Modal, title="Create New Department"):
    """Yeni departman oluşturma modalı"""
    
    name = discord.ui.TextInput(
        label="Department Name",
        placeholder="e.g., Technical Support",
        max_length=50,
        required=True
    )
    
    description = discord.ui.TextInput(
        label="Description",
        placeholder="Brief description of this department",
        max_length=200,
        required=True,
        style=discord.TextStyle.long
    )
    
    emoji = discord.ui.TextInput(
        label="Emoji",
        placeholder="e.g., 🎫",
        max_length=2,
        required=True,
        default="🎫"
    )
    
    welcome_message = discord.ui.TextInput(
        label="Welcome Message",
        placeholder="Message shown when ticket is created",
        max_length=1000,
        required=True,
        style=discord.TextStyle.long,
        default="Welcome! A staff member will assist you shortly."
    )
    
    def __init__(self, parent_view):
        super().__init__()
        self.parent_view = parent_view
    
    async def on_submit(self, interaction: discord.Interaction):
        # Create new department
        import uuid
        new_dept = {
            'id': str(uuid.uuid4()),
            'name': self.name.value,
            'description': self.description.value,
            'emoji': self.emoji.value,
            'category_id': None,
            'staff_roles': [],
            'auto_assign_staff': False,
            'welcome_message': self.welcome_message.value,
            'button_style': 'primary',
            'form_fields': [],
            'created_at': datetime.utcnow().isoformat()
        }
        
        self.parent_view.departments.append(new_dept)
        
        if await self.parent_view.save_departments():
            embed = discord.Embed(
                title="✅ Department Created",
                description=f"**{new_dept['emoji']} {new_dept['name']}** has been created successfully!",
                color=discord.Color.green()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message("Failed to create department!", ephemeral=True)


class DepartmentSelectView(discord.ui.View):
    """Departman seçimi için view"""
    
    def __init__(self, parent_view, action: str):
        super().__init__(timeout=180)
        self.parent_view = parent_view
        self.action = action
        
        # Create dropdown
        options = []
        for dept in parent_view.departments[:25]:
            options.append(
                discord.SelectOption(
                    label=dept['name'],
                    value=dept['id'],
                    description=dept['description'][:50],
                    emoji=dept.get('emoji', '🎫')
                )
            )
        
        self.select = discord.ui.Select(
            placeholder="Choose a department...",
            options=options
        )
        
        if action == "edit":
            self.select.callback = self.edit_callback
        elif action == "delete":
            self.select.callback = self.delete_callback
        elif action == "forms":
            self.select.callback = self.forms_callback
        
        self.add_item(self.select)
    
    async def edit_callback(self, interaction: discord.Interaction):
        """Departman düzenleme callback'i"""
        dept_id = self.select.values[0]
        dept = next((d for d in self.parent_view.departments if d['id'] == dept_id), None)
        
        if dept:
            view = EditDepartmentView(self.parent_view, dept)
            embed = view.create_edit_embed()
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    async def delete_callback(self, interaction: discord.Interaction):
        """Departman silme callback'i"""
        dept_id = self.select.values[0]
        dept = next((d for d in self.parent_view.departments if d['id'] == dept_id), None)
        
        if dept:
            # Confirm deletion
            confirm_view = ConfirmDeletionView(self.parent_view, dept)
            embed = discord.Embed(
                title="⚠️ Confirm Deletion",
                description=f"Are you sure you want to delete **{dept['emoji']} {dept['name']}**?\n\n"
                           "This action cannot be undone!",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, view=confirm_view, ephemeral=True)
    
    async def forms_callback(self, interaction: discord.Interaction):
        """Form yapılandırma callback'i"""
        dept_id = self.select.values[0]
        dept = next((d for d in self.parent_view.departments if d['id'] == dept_id), None)
        
        if dept:
            view = FormFieldsView(self.parent_view, dept)
            embed = view.create_forms_embed()
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class EditDepartmentView(discord.ui.View):
    """Departman düzenleme view'i"""
    
    def __init__(self, parent_view, department: dict):
        super().__init__(timeout=300)
        self.parent_view = parent_view
        self.department = department
        self.guild_id = parent_view.guild_id
    
    def create_edit_embed(self):
        """Düzenleme embed'i oluştur"""
        embed = discord.Embed(
            title=f"Edit Department: {self.department['emoji']} {self.department['name']}",
            color=discord.Color.blue()
        )
        
        category_text = f"<#{self.department.get('category_id')}>" if self.department.get('category_id') else "Not Set"
        staff_roles = [f"<@&{role_id}>" for role_id in self.department.get('staff_roles', [])]
        staff_text = ", ".join(staff_roles) if staff_roles else "None"
        
        embed.add_field(
            name="Current Settings",
            value=f"**Category:** {category_text}\n"
                  f"**Staff Roles:** {staff_text}\n"
                  f"**Auto-assign:** {'Yes' if self.department.get('auto_assign_staff') else 'No'}\n"
                  f"**Button Style:** {self.department.get('button_style', 'primary')}",
            inline=False
        )
        
        embed.add_field(
            name="Welcome Message",
            value=self.department.get('welcome_message', 'Not set'),
            inline=False
        )
        
        return embed
    
    @discord.ui.button(label="📝 Edit Basic Info", style=discord.ButtonStyle.primary, row=0)
    async def edit_basic_info(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Temel bilgileri düzenle"""
        modal = EditDepartmentModal(self.parent_view, self.department)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="📁 Set Category", style=discord.ButtonStyle.secondary, row=0)
    async def set_category(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Kategori ayarla"""
        view = CategorySelectView(self.parent_view, self.department)
        embed = discord.Embed(
            title="Select Category",
            description="Choose a category for this department's tickets:",
            color=discord.Color.blue()
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @discord.ui.button(label="👥 Set Staff Roles", style=discord.ButtonStyle.secondary, row=1)
    async def set_staff_roles(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Staff rollerini ayarla"""
        view = StaffRoleSelectView(self.parent_view, self.department)
        embed = discord.Embed(
            title="Select Staff Roles",
            description="Choose roles that can manage tickets in this department:",
            color=discord.Color.blue()
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @discord.ui.button(label="🎨 Button Style", style=discord.ButtonStyle.secondary, row=1)
    async def set_button_style(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Buton stilini ayarla"""
        view = ButtonStyleView(self.parent_view, self.department)
        embed = discord.Embed(
            title="Select Button Style",
            description="Choose how the department button will appear:",
            color=discord.Color.blue()
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @discord.ui.button(label="🔄 Toggle Auto-assign", style=discord.ButtonStyle.secondary, row=2)
    async def toggle_auto_assign(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Auto-assign toggle"""
        self.department['auto_assign_staff'] = not self.department.get('auto_assign_staff', False)
        
        if await self.parent_view.save_departments():
            status = "enabled" if self.department['auto_assign_staff'] else "disabled"
            await interaction.response.send_message(f"Auto-assign {status}!", ephemeral=True)
        else:
            await interaction.response.send_message("Failed to update setting!", ephemeral=True)
    
    @discord.ui.button(label="✅ Done", style=discord.ButtonStyle.success, row=2)
    async def done_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Tamamla"""
        embed = self.parent_view.create_departments_embed()
        await interaction.response.send_message("Department updated successfully!", embed=embed, ephemeral=True)


class EditDepartmentModal(discord.ui.Modal):
    """Departman düzenleme modalı"""
    
    def __init__(self, parent_view, department: dict):
        super().__init__(title=f"Edit {department['name']}")
        self.parent_view = parent_view
        self.department = department
        
        # Add fields with current values
        self.name = discord.ui.TextInput(
            label="Department Name",
            default=department['name'],
            max_length=50,
            required=True
        )
        
        self.description = discord.ui.TextInput(
            label="Description",
            default=department.get('description', ''),
            max_length=200,
            required=True,
            style=discord.TextStyle.long
        )
        
        self.emoji = discord.ui.TextInput(
            label="Emoji",
            default=department.get('emoji', '🎫'),
            max_length=2,
            required=True
        )
        
        self.welcome_message = discord.ui.TextInput(
            label="Welcome Message",
            default=department.get('welcome_message', ''),
            max_length=1000,
            required=True,
            style=discord.TextStyle.long
        )
        
        self.add_item(self.name)
        self.add_item(self.description)
        self.add_item(self.emoji)
        self.add_item(self.welcome_message)
    
    async def on_submit(self, interaction: discord.Interaction):
        # Update department
        self.department['name'] = self.name.value
        self.department['description'] = self.description.value
        self.department['emoji'] = self.emoji.value
        self.department['welcome_message'] = self.welcome_message.value
        self.department['updated_at'] = datetime.utcnow().isoformat()
        
        if await self.parent_view.save_departments():
            embed = discord.Embed(
                title="✅ Department Updated",
                description=f"**{self.department['emoji']} {self.department['name']}** has been updated!",
                color=discord.Color.green()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message("Failed to update department!", ephemeral=True)


class FormFieldsView(discord.ui.View):
    """Form field'ları yönetimi için view"""
    
    def __init__(self, parent_view, department: dict):
        super().__init__(timeout=300)
        self.parent_view = parent_view
        self.department = department
        self.form_fields = department.get('form_fields', [])
    
    def create_forms_embed(self):
        """Form field'ları embed'i"""
        embed = discord.Embed(
            title=f"Form Fields: {self.department['emoji']} {self.department['name']}",
            description=f"Configure form fields for this department\n"
                       f"Current fields: {len(self.form_fields)}",
            color=discord.Color.blue()
        )
        
        for i, field in enumerate(self.form_fields[:10]):  # Show first 10
            embed.add_field(
                name=f"{i+1}. {field['label']}",
                value=f"**Type:** {field['type']}\n"
                      f"**Required:** {'Yes' if field.get('required') else 'No'}\n"
                      f"**Placeholder:** {field.get('placeholder', 'None')}",
                inline=True
            )
        
        if len(self.form_fields) > 10:
            embed.add_field(
                name="...",
                value=f"And {len(self.form_fields) - 10} more fields",
                inline=False
            )
        
        return embed
    
    @discord.ui.button(label="➕ Add Field", style=discord.ButtonStyle.success, row=0)
    async def add_field(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Form field ekle"""
        if len(self.form_fields) >= 25:
            await interaction.response.send_message("Maximum 25 fields allowed!", ephemeral=True)
            return
        
        modal = AddFormFieldModal(self)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="📝 Edit Field", style=discord.ButtonStyle.primary, row=0)
    async def edit_field(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Form field düzenle"""
        if not self.form_fields:
            await interaction.response.send_message("No fields to edit!", ephemeral=True)
            return
        
        view = FieldSelectView(self, "edit")
        embed = discord.Embed(
            title="Select Field to Edit",
            description="Choose a field from the dropdown:",
            color=discord.Color.blue()
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @discord.ui.button(label="🗑️ Remove Field", style=discord.ButtonStyle.danger, row=0)
    async def remove_field(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Form field sil"""
        if not self.form_fields:
            await interaction.response.send_message("No fields to remove!", ephemeral=True)
            return
        
        view = FieldSelectView(self, "delete")
        embed = discord.Embed(
            title="Select Field to Remove",
            description="Choose a field to remove:",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @discord.ui.button(label="↕️ Reorder Fields", style=discord.ButtonStyle.secondary, row=1)
    async def reorder_fields(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Field'ları yeniden sırala"""
        await interaction.response.send_message(
            "Field reordering coming soon! For now, remove and re-add fields in desired order.",
            ephemeral=True
        )
    
    @discord.ui.button(label="✅ Save", style=discord.ButtonStyle.success, row=2)
    async def save_fields(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Field'ları kaydet"""
        self.department['form_fields'] = self.form_fields
        
        if await self.parent_view.save_departments():
            embed = discord.Embed(
                title="✅ Form Fields Saved",
                description=f"Saved {len(self.form_fields)} fields for **{self.department['name']}**",
                color=discord.Color.green()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message("Failed to save fields!", ephemeral=True)


class AddFormFieldModal(discord.ui.Modal, title="Add Form Field"):
    """Form field ekleme modalı"""
    
    label = discord.ui.TextInput(
        label="Field Label",
        placeholder="e.g., What is your issue?",
        max_length=100,
        required=True
    )
    
    placeholder = discord.ui.TextInput(
        label="Placeholder Text",
        placeholder="e.g., Describe your issue in detail...",
        max_length=100,
        required=False
    )
    
    def __init__(self, parent_view):
        super().__init__()
        self.parent_view = parent_view
    
    async def on_submit(self, interaction: discord.Interaction):
        import uuid
        new_field = {
            'id': str(uuid.uuid4()),
            'label': self.label.value,
            'placeholder': self.placeholder.value or f"Enter {self.label.value.lower()}...",
            'type': 'paragraph',  # Default type
            'required': True,
            'max_length': 1000
        }
        
        self.parent_view.form_fields.append(new_field)
        
        # Update embed
        embed = self.parent_view.create_forms_embed()
        await interaction.response.send_message(
            "Field added! Don't forget to save your changes.",
            embed=embed,
            ephemeral=True
        )


class CategorySelectView(discord.ui.View):
    """Kategori seçimi view'i"""
    
    def __init__(self, parent_view, department: dict):
        super().__init__(timeout=180)
        self.parent_view = parent_view
        self.department = department
        
        # Get guild categories
        guild = parent_view.bot.get_guild(parent_view.guild_id)
        if guild:
            categories = [ch for ch in guild.channels if isinstance(ch, discord.CategoryChannel)]
            
            if categories:
                options = []
                for category in categories[:25]:  # Discord limit
                    options.append(
                        discord.SelectOption(
                            label=category.name,
                            value=str(category.id),
                            description=f"Category • {len(category.channels)} channels"
                        )
                    )
                
                select = discord.ui.Select(
                    placeholder="Select a category for tickets...",
                    options=options
                )
                select.callback = self.category_callback
                self.add_item(select)
            else:
                # No categories found
                button = discord.ui.Button(
                    label="No Categories Found",
                    style=discord.ButtonStyle.secondary,
                    disabled=True
                )
                self.add_item(button)
    
    async def category_callback(self, interaction: discord.Interaction):
        """Kategori seç callback"""
        category_id = int(interaction.data['values'][0])
        guild = interaction.guild
        category = guild.get_channel(category_id)
        
        if category:
            self.department['category_id'] = category_id
            
            if await self.parent_view.save_departments():
                await interaction.response.send_message(
                    f"Category set to **{category.name}**!",
                    ephemeral=True
                )
            else:
                await interaction.response.send_message("Failed to set category!", ephemeral=True)
        else:
            await interaction.response.send_message("Category not found!", ephemeral=True)


class StaffRoleSelectView(discord.ui.View):
    """Staff rol seçimi view'i"""
    
    def __init__(self, parent_view, department: dict):
        super().__init__(timeout=180)
        self.parent_view = parent_view
        self.department = department
        
        # Get guild roles (excluding @everyone)
        guild = parent_view.bot.get_guild(parent_view.guild_id)
        if guild:
            roles = [role for role in guild.roles if role.name != "@everyone"][:25]  # Discord limit
            
            if roles:
                options = []
                for role in roles:
                    options.append(
                        discord.SelectOption(
                            label=role.name,
                            value=str(role.id),
                            description=f"Role • {len(role.members)} members"
                        )
                    )
                
                select = discord.ui.Select(
                    placeholder="Select staff roles (multi-select)...",
                    options=options,
                    min_values=0,
                    max_values=min(len(options), 10)
                )
                select.callback = self.role_callback
                self.add_item(select)
            else:
                # No roles found
                button = discord.ui.Button(
                    label="No Roles Found",
                    style=discord.ButtonStyle.secondary,
                    disabled=True
                )
                self.add_item(button)
    
    async def role_callback(self, interaction: discord.Interaction):
        """Staff rolleri seç callback"""
        selected_role_ids = [int(value) for value in interaction.data['values']]
        self.department['staff_roles'] = selected_role_ids
        
        if await self.parent_view.save_departments():
            if selected_role_ids:
                role_mentions = [f"<@&{role_id}>" for role_id in selected_role_ids]
                await interaction.response.send_message(
                    f"Staff roles updated: {', '.join(role_mentions)}",
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    "Staff roles cleared (no roles selected)",
                    ephemeral=True
                )
        else:
            await interaction.response.send_message("Failed to update staff roles!", ephemeral=True)


class ButtonStyleView(discord.ui.View):
    """Buton stili seçimi view'i"""
    
    def __init__(self, parent_view, department: dict):
        super().__init__(timeout=180)
        self.parent_view = parent_view
        self.department = department
        
        # Add style buttons
        styles = [
            ("Primary (Blue)", "primary", discord.ButtonStyle.primary),
            ("Secondary (Gray)", "secondary", discord.ButtonStyle.secondary),
            ("Success (Green)", "success", discord.ButtonStyle.success),
            ("Danger (Red)", "danger", discord.ButtonStyle.danger)
        ]
        
        for label, value, style in styles:
            button = discord.ui.Button(label=label, style=style)
            button.callback = self.create_callback(value)
            self.add_item(button)
    
    def create_callback(self, style_value: str):
        async def callback(interaction: discord.Interaction):
            self.department['button_style'] = style_value
            
            if await self.parent_view.save_departments():
                await interaction.response.send_message(
                    f"Button style set to **{style_value}**!",
                    ephemeral=True
                )
            else:
                await interaction.response.send_message("Failed to update button style!", ephemeral=True)
        
        return callback


class ConfirmDeletionView(discord.ui.View):
    """Silme onayı view'i"""
    
    def __init__(self, parent_view, department: dict):
        super().__init__(timeout=60)
        self.parent_view = parent_view
        self.department = department
    
    @discord.ui.button(label="✅ Confirm Delete", style=discord.ButtonStyle.danger)
    async def confirm_delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Silmeyi onayla"""
        # Remove department
        self.parent_view.departments = [
            d for d in self.parent_view.departments 
            if d['id'] != self.department['id']
        ]
        
        if await self.parent_view.save_departments():
            embed = discord.Embed(
                title="🗑️ Department Deleted",
                description=f"**{self.department['emoji']} {self.department['name']}** has been deleted.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message("Failed to delete department!", ephemeral=True)
    
    @discord.ui.button(label="❌ Cancel", style=discord.ButtonStyle.secondary)
    async def cancel_delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        """İptal et"""
        await interaction.response.send_message("Deletion cancelled.", ephemeral=True)


class FieldSelectView(discord.ui.View):
    """Field seçimi için view"""
    
    def __init__(self, parent_view, action: str):
        super().__init__(timeout=180)
        self.parent_view = parent_view
        self.action = action
        
        # Create dropdown
        options = []
        for i, field in enumerate(parent_view.form_fields[:25]):
            options.append(
                discord.SelectOption(
                    label=field['label'][:50],
                    value=field['id'],
                    description=f"Type: {field['type']} | Required: {'Yes' if field.get('required') else 'No'}"
                )
            )
        
        self.select = discord.ui.Select(
            placeholder="Choose a field...",
            options=options
        )
        
        if action == "edit":
            self.select.callback = self.edit_callback
        elif action == "delete":
            self.select.callback = self.delete_callback
        
        self.add_item(self.select)
    
    async def edit_callback(self, interaction: discord.Interaction):
        """Field düzenleme callback'i"""
        field_id = self.select.values[0]
        field = next((f for f in self.parent_view.form_fields if f['id'] == field_id), None)
        
        if field:
            modal = EditFormFieldModal(self.parent_view, field)
            await interaction.response.send_modal(modal)
    
    async def delete_callback(self, interaction: discord.Interaction):
        """Field silme callback'i"""
        field_id = self.select.values[0]
        
        # Remove field
        self.parent_view.form_fields = [
            f for f in self.parent_view.form_fields 
            if f['id'] != field_id
        ]
        
        # Update embed
        embed = self.parent_view.create_forms_embed()
        await interaction.response.send_message(
            "Field removed! Don't forget to save your changes.",
            embed=embed,
            ephemeral=True
        )


class EditFormFieldModal(discord.ui.Modal):
    """Form field düzenleme modalı"""
    
    def __init__(self, parent_view, field: dict):
        super().__init__(title=f"Edit Field: {field['label'][:30]}")
        self.parent_view = parent_view
        self.field = field
        
        # Add fields with current values
        self.label = discord.ui.TextInput(
            label="Field Label",
            default=field['label'],
            max_length=100,
            required=True
        )
        
        self.placeholder = discord.ui.TextInput(
            label="Placeholder Text",
            default=field.get('placeholder', ''),
            max_length=100,
            required=False
        )
        
        self.add_item(self.label)
        self.add_item(self.placeholder)
    
    async def on_submit(self, interaction: discord.Interaction):
        # Update field
        self.field['label'] = self.label.value
        self.field['placeholder'] = self.placeholder.value or f"Enter {self.label.value.lower()}..."
        
        # Update embed
        embed = self.parent_view.create_forms_embed()
        await interaction.response.send_message(
            "Field updated! Don't forget to save your changes.",
            embed=embed,
            ephemeral=True
        ) 