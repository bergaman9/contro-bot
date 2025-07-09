import discord
from discord.ui import View, Button, Select, Modal, TextInput
from src.utils.formatting import create_embed
import base64
import os
import asyncio
import logging
from io import BytesIO  # Add missing import for BytesIO

logger = logging.getLogger('welcomer_views')

class BaseConfigView(View):
    def __init__(self, bot, mongo_db, author, guild, channel, config_type):
        super().__init__(timeout=None)
        self.bot = bot
        self.mongo_db = mongo_db
        self.author = author
        self.guild = guild
        self.channel = channel
        self.config_type = config_type
        self.config = {
            "guild_id": str(guild.id),
            "channel_id": str(channel.id),
            "color": discord.Color.blue().value,
            "description": "{mention} sunucumuza hoş geldin!",
            "welcome_text": "HOŞ GELDİN!",
            "text_outline": False,
            "text_shadow": False,
            "blur_background": False,
            "background_url": "data/Backgrounds/welcome_default.png",
            "background_data": None
        }
        self.steps = [
            self.step_select_background,
            self.step_customize_text,
            self.step_select_color,
            self.step_customize_description,
            self.step_confirm_settings
        ]
        self.current_step = 0
        self.message = None
        self.backgrounds = self.get_predefined_backgrounds()

    def process_uploaded_image(self, image_data):
        """Process uploaded image data for welcome/byebye backgrounds"""
        try:
            # Try to import the function from image_utils
            from src.utils.greeting.welcomer.image_utils import process_uploaded_image
            return process_uploaded_image(image_data)
        except Exception as e:
            logger.error(f"Failed to process uploaded image: {e}")
            try:
                # Fallback processing if image_utils is not available
                from PIL import Image
                from io import BytesIO
                
                # Open the image data
                image = Image.open(BytesIO(image_data))
                
                # Resize to standard dimensions
                target_size = (1024, 500)
                
                # Calculate new dimensions while maintaining aspect ratio
                width, height = image.size
                ratio = min(target_size[0] / width, target_size[1] / height)
                new_size = (int(width * ratio), int(height * ratio))
                
                # Resize the image
                image = image.resize(new_size, Image.LANCZOS)
                
                # Create a new image with the target dimensions
                new_image = Image.new("RGB", target_size)
                
                # Paste the resized image centered on the new image
                paste_x = (target_size[0] - new_size[0]) // 2
                paste_y = (target_size[1] - new_size[1]) // 2
                new_image.paste(image, (paste_x, paste_y))
                
                # Save the processed image to a BytesIO object
                output = BytesIO()
                new_image.save(output, format="PNG")
                return output.getvalue()
            except Exception as fallback_error:
                logger.error(f"Fallback image processing also failed: {fallback_error}")
                return None
    
    def get_predefined_backgrounds(self):
        """Get background options from image_utils or use fallback options"""
        try:
            # Try to import the function from image_utils
            from src.utils.greeting.welcomer.image_utils import get_predefined_backgrounds
            return get_predefined_backgrounds(category=self.config_type)
        except Exception as e:
            logger.error(f"Failed to get backgrounds from image_utils: {e}")
            # Return a basic fallback dictionary with default background
            backgrounds_dir = os.path.join("data", "Backgrounds")
            os.makedirs(backgrounds_dir, exist_ok=True)
            
            # Create a fallback file path
            fallback_path = os.path.join(backgrounds_dir, f"{self.config_type}_default.png")
            
            # Create a basic background if it doesn't exist
            if not os.path.exists(fallback_path):
                try:
                    # Create a simple colored background as fallback
                    from PIL import Image, ImageDraw
                    img = Image.new("RGB", (1024, 500), (65, 105, 225))  # Royal blue
                    img.save(fallback_path)
                    logger.info(f"Created fallback background: {fallback_path}")
                except Exception as img_error:
                    logger.error(f"Failed to create fallback background: {img_error}")
            
            return {"Default": fallback_path}

    async def initialize_view(self):
        await self.steps[self.current_step]()

    async def step_select_background(self):
        self.clear_items()
        select = Select(
            placeholder="📝 Hazır arkaplan seçin...",
            custom_id="background_select"
        )
        for name, path in self.backgrounds.items():
            select.add_option(label=name, value=path, description=f"{name} arkaplanı seçin")
        select.callback = self.on_background_select
        self.add_item(select)
        upload_button = Button(style=discord.ButtonStyle.primary, label="📤 Kendi Resminizi Yükleyin", custom_id="upload_background")
        upload_button.callback = self.on_upload_background
        self.add_item(upload_button)
        next_button = Button(style=discord.ButtonStyle.green, label="İleri ➡️", custom_id="next_step", disabled=True)
        next_button.callback = self.on_next_step
        self.add_item(next_button)
        await self.message.edit(
            embed=create_embed(
                title="🖼️ Arkaplan Seçimi",
                description="Hoş geldin mesajı için bir arka plan resmi seçin veya kendi resminizi yükleyin.\n\n"
                           "**Not:** Yüklenen resimler 1024x500 piksel boyutuna otomatik olarak yeniden boyutlandırılacaktır.",
                color=discord.Color.blue()
            ),
            view=self
        )

    async def on_background_select(self, interaction):
        selected_background = interaction.data['values'][0]
        self.config["background_url"] = selected_background
        self.config["background_data"] = None
        
        # Check if the selected background is a URL
        if selected_background.startswith(('http://', 'https://')):
            try:
                # Import here to avoid circular imports
                from .image_utils import download_image_from_url
                
                # Try to download the image to verify it works
                image = download_image_from_url(selected_background)
                if image is None:
                    await interaction.response.send_message(
                        embed=create_embed(
                            "URL'den resim indirilirken hata oluştu. Lütfen başka bir resim seçin.",
                            discord.Color.red()
                        ),
                        ephemeral=True
                    )
                    return
            except Exception as e:
                logger.error(f"Error downloading background from URL: {e}")
                await interaction.response.send_message(
                    embed=create_embed(
                        "Belirtilen URL'den resim yüklenemedi. Lütfen başka bir resim seçin.",
                        discord.Color.red()
                    ),
                    ephemeral=True
                )
                return
                
        for item in self.children:
            if isinstance(item, Button) and item.custom_id == "next_step":
                item.disabled = False
        await interaction.response.edit_message(
            embed=create_embed(
                title="🖼️ Arkaplan Seçildi",
                description=f"Seçilen arkaplan: **{os.path.basename(selected_background) if not selected_background.startswith(('http://', 'https://')) else 'Web URL'}**\n\n"
                           f"İlerlemek için 'İleri' butonuna tıklayın.",
                color=self.config["color"]
            ),
            view=self
        )

    async def on_upload_background(self, interaction):
        await interaction.response.send_message(
            "Lütfen kullanmak istediğiniz arkaplan resmini yükleyin. "
            "Resim otomatik olarak 1024x500 piksel boyutuna ayarlanacaktır.",
            ephemeral=True
        )
        try:
            def check(msg):
                return msg.author.id == self.author.id and msg.channel.id == interaction.channel.id and msg.attachments
            message = await self.bot.wait_for('message', check=check, timeout=60.0)
            if message.attachments:
                attachment = message.attachments[0]
                if not attachment.content_type or not attachment.content_type.startswith('image/'):
                    await interaction.followup.send(
                        "❌ Lütfen geçerli bir resim dosyası yükleyin (jpg, png, vb).",
                        ephemeral=True
                    )
                    return
                image_data = await attachment.read()
                processed_data = self.process_uploaded_image(image_data)
                if processed_data:
                    self.config["background_data"] = base64.b64encode(processed_data).decode('utf-8')
                    self.config["background_url"] = "custom_upload"
                    for item in self.children:
                        if isinstance(item, Button) and item.custom_id == "next_step":
                            item.disabled = False
                    try:
                        await message.delete()
                    except:
                        pass
                    await interaction.followup.send(
                        "✅ Arkaplan başarıyla yüklendi ve işlendi!",
                        ephemeral=True
                    )
                    await self.message.edit(
                        embed=create_embed(
                            title="🖼️ Özel Arkaplan Yüklendi",
                            description="Kendi arkaplanınız başarıyla yüklendi ve işlendi.\n\n"
                                       "İlerlemek için 'İleri' butonuna tıklayın.",
                            color=self.config["color"]
                        ),
                        view=self
                    )
                else:
                    await interaction.followup.send(
                        "❌ Resim işlenirken bir hata oluştu. Lütfen başka bir resim deneyin.",
                        ephemeral=True
                    )
        except asyncio.TimeoutError:
            await interaction.followup.send(
                "⏱️ Zaman aşımı. Resim yükleme işlemi iptal edildi.",
                ephemeral=True
            )

    async def on_next_step(self, interaction):
        self.current_step += 1
        if self.current_step < len(self.steps):
            await interaction.response.defer()
            await self.steps[self.current_step]()
        else:
            await interaction.response.edit_message(
                embed=create_embed(
                    title="✅ Yapılandırma Tamamlandı",
                    description="Hoş geldin sistemi başarıyla yapılandırıldı!",
                    color=discord.Color.green()
                ),
                view=None
            )

    async def step_customize_text(self):
        self.clear_items()
        class WelcomeTextModal(Modal, title="Hoş Geldin Metni"):
            welcome_text = TextInput(
                label="Hoş Geldin Metni",
                placeholder="HOŞ GELDİN!",
                default=self.config.get("welcome_text", "HOŞ GELDİN!"),
                required=True,
                max_length=50
            )
            async def on_submit(self, interaction):
                self.view.config["welcome_text"] = self.welcome_text.value
                self.view.clear_items()
                outline_button = Button(
                    style=discord.ButtonStyle.secondary, 
                    label="✏️ Metin Dış Çizgisi", 
                    custom_id="toggle_outline"
                )
                outline_button.callback = self.view.toggle_text_outline
                self.view.add_item(outline_button)
                shadow_button = Button(
                    style=discord.ButtonStyle.secondary, 
                    label="🌑 Metin Gölgesi", 
                    custom_id="toggle_shadow"
                )
                shadow_button.callback = self.view.toggle_text_shadow
                self.view.add_item(shadow_button)
                blur_button = Button(
                    style=discord.ButtonStyle.secondary, 
                    label="🌫️ Arkaplan Bulanıklığı", 
                    custom_id="toggle_blur"
                )
                blur_button.callback = self.view.toggle_background_blur
                self.view.add_item(blur_button)
                next_button = Button(style=discord.ButtonStyle.green, label="İleri ➡️", custom_id="next_step")
                next_button.callback = self.view.on_next_step
                self.view.add_item(next_button)
                await interaction.response.edit_message(
                    embed=create_embed(
                        title="✏️ Metin Özelleştirme",
                        description=f"Hoş geldin metni: **{self.welcome_text.value}**\n\n"
                                   f"İsterseniz metin stilini özelleştirebilirsiniz:\n"
                                   f"- Metin dış çizgisi: **{'Açık' if self.view.config['text_outline'] else 'Kapalı'}**\n"
                                   f"- Metin gölgesi: **{'Açık' if self.view.config['text_shadow'] else 'Kapalı'}**\n"
                                   f"- Arkaplan bulanıklığı: **{'Açık' if self.view.config['blur_background'] else 'Kapalı'}**\n\n"
                                   f"İlerlemek için 'İleri' butonuna tıklayın.",
                        color=self.config["color"]
                    ),
                    view=self.view
                )
        modal = WelcomeTextModal()
        modal.view = self
        customize_button = Button(style=discord.ButtonStyle.primary, label="✏️ Metni Düzenle", custom_id="customize_text")
        async def open_modal(interaction):
            await interaction.response.send_modal(modal)
        customize_button.callback = open_modal
        self.add_item(customize_button)
        skip_button = Button(style=discord.ButtonStyle.secondary, label="Atla ⏩", custom_id="skip_customization")
        async def skip_customization(interaction):
            await self.on_next_step(interaction)
        skip_button.callback = skip_customization
        self.add_item(skip_button)
        await self.message.edit(
            embed=create_embed(
                title="✏️ Metin Özelleştirme",
                description="Hoş geldin mesajındaki metni özelleştirin.\n\n"
                           f"Şu anki metin: **{self.config.get('welcome_text', 'HOŞ GELDİN!')}**\n\n"
                           "Metni değiştirmek için 'Metni Düzenle' butonuna tıklayın veya "
                           "bu adımı atlamak için 'Atla' butonuna tıklayın.",
                color=self.config["color"]
            ),
            view=self
        )

    async def toggle_text_outline(self, interaction):
        self.config["text_outline"] = not self.config["text_outline"]
        await interaction.response.edit_message(
            embed=create_embed(
                title="✏️ Metin Özelleştirme",
                description=f"Hoş geldin metni: **{self.config.get('welcome_text', 'HOŞ GELDİN!')}**\n\n"
                           f"İsterseniz metin stilini özelleştirebilirsiniz:\n"
                           f"- Metin dış çizgisi: **{'Açık' if self.config['text_outline'] else 'Kapalı'}**\n"
                           f"- Metin gölgesi: **{'Açık' if self.config['text_shadow'] else 'Kapalı'}**\n"
                           f"- Arkaplan bulanıklığı: **{'Açık' if self.config['blur_background'] else 'Kapalı'}**\n\n"
                           f"İlerlemek için 'İleri' butonuna tıklayın.",
                color=self.config["color"]
            ),
            view=self
        )

    async def toggle_text_shadow(self, interaction):
        self.config["text_shadow"] = not self.config["text_shadow"]
        await interaction.response.edit_message(
            embed=create_embed(
                title="✏️ Metin Özelleştirme",
                description=f"Hoş geldin metni: **{self.config.get('welcome_text', 'HOŞ GELDİN!')}**\n\n"
                           f"İsterseniz metin stilini özelleştirebilirsiniz:\n"
                           f"- Metin dış çizgisi: **{'Açık' if self.config['text_outline'] else 'Kapalı'}**\n"
                           f"- Metin gölgesi: **{'Açık' if self.config['text_shadow'] else 'Kapalı'}**\n"
                           f"- Arkaplan bulanıklığı: **{'Açık' if self.config['blur_background'] else 'Kapalı'}**\n\n"
                           f"İlerlemek için 'İleri' butonuna tıklayın.",
                color=self.config["color"]
            ),
            view=self
        )

    async def toggle_background_blur(self, interaction):
        self.config["blur_background"] = not self.config["blur_background"]
        await interaction.response.edit_message(
            embed=create_embed(
                title="✏️ Metin Özelleştirme",
                description=f"Hoş geldin metni: **{self.config.get('welcome_text', 'HOŞ GELDİN!')}**\n\n"
                           f"İsterseniz metin stilini özelleştirebilirsiniz:\n"
                           f"- Metin dış çizgisi: **{'Açık' if self.config['text_outline'] else 'Kapalı'}**\n"
                           f"- Metin gölgesi: **{'Açık' if self.config['text_shadow'] else 'Kapalı'}**\n"
                           f"- Arkaplan bulanıklığı: **{'Açık' if self.config['blur_background'] else 'Kapalı'}**\n\n"
                           f"İlerlemek için 'İleri' butonuna tıklayın.",
                color=self.config["color"]
            ),
            view=self
        )

    async def step_select_color(self):
        self.clear_items()
        color_button = Button(style=discord.ButtonStyle.primary, label="🎨 Renk Seç", custom_id="select_color")
        async def select_color(interaction):
            await interaction.response.send_message(
                embed=create_embed(
                    title="🎨 Renk Seçimi",
                    description="Renk seçimi özelliği henüz eklenmedi.",
                    color=discord.Color.blue()
                ),
                ephemeral=True
            )
        color_button.callback = select_color
        self.add_item(color_button)
        next_button = Button(style=discord.ButtonStyle.green, label="İleri ➡️", custom_id="next_step")
        next_button.callback = self.on_next_step
        self.add_item(next_button)
        await self.message.edit(
            embed=create_embed(
                title="🎨 Renk Seçimi",
                description="Hoş geldin mesajı için bir renk seçin.\n\n"
                           "Renk seçimi özelliği henüz eklenmedi.",
                color=discord.Color.blue()
            ),
            view=self
        )

    async def step_customize_description(self):
        self.clear_items()
        class DescriptionModal(Modal, title="Hoş Geldin Açıklaması"):
            description = TextInput(
                label="Açıklama",
                placeholder="{mention} sunucumuza hoş geldin!",
                default=self.config["description"],
                required=True,
                style=discord.TextStyle.paragraph,
                max_length=1000
            )
            async def on_submit(self, interaction):
                self.view.config["description"] = self.description.value
                self.view.clear_items()
                next_button = Button(style=discord.ButtonStyle.green, label="İleri ➡️", custom_id="next_step")
                next_button.callback = self.view.on_next_step
                self.view.add_item(next_button)
                await interaction.response.edit_message(
                    embed=create_embed(
                        title="✏️ Açıklama Özelleştirme",
                        description=f"Hoş geldin açıklaması başarıyla güncellendi!\n\n"
                                   f"Yeni açıklama:\n{self.description.value}\n\n"
                                   f"İlerlemek için 'İleri' butonuna tıklayın.",
                        color=self.view.config["color"]
                    ),
                    view=self.view
                )
        modal = DescriptionModal()
        modal.view = self
        customize_button = Button(style=discord.ButtonStyle.primary, label="✏️ Açıklamayı Düzenle", custom_id="customize_description")
        async def open_modal(interaction):
            await interaction.response.send_modal(modal)
        customize_button.callback = open_modal
        self.add_item(customize_button)
        variables_button = Button(style=discord.ButtonStyle.secondary, label="ℹ️ Değişkenler", custom_id="variables_info")
        async def show_variables(interaction):
            await interaction.response.send_message(
                embed=create_embed(
                    title="📝 Kullanılabilir Değişkenler",
                    description="Açıklamanızda aşağıdaki değişkenleri kullanabilirsiniz:\n\n"
                               "`{mention}` - Kullanıcının etiketini ekler\n"
                               "`{name}` - Kullanıcının adını ekler\n"
                               "`{member_count}` - Sunucunun üye sayısını ekler\n"
                               "`{server}` - Sunucu adını ekler",
                    color=self.config["color"]
                ),
                ephemeral=True
            )
        variables_button.callback = show_variables
        self.add_item(variables_button)
        skip_button = Button(style=discord.ButtonStyle.secondary, label="Atla ⏩", custom_id="skip_description")
        async def skip_description(interaction):
            await self.on_next_step(interaction)
        skip_button.callback = skip_description
        self.add_item(skip_button)
        await self.message.edit(
            embed=create_embed(
                title="✏️ Açıklama Özelleştirme",
                description="Hoş geldin mesajının açıklamasını özelleştirin.\n\n"
                           f"Şu anki açıklama:\n{self.config['description']}\n\n"
                           "Açıklamayı değiştirmek için 'Açıklamayı Düzenle' butonuna tıklayın veya "
                           "bu adımı atlamak için 'Atla' butonuna tıklayın.",
                color=self.config["color"]
            ),
            view=self
        )

    async def step_confirm_settings(self):
        self.clear_items()
        preview_button = Button(style=discord.ButtonStyle.primary, label="🔍 Önizleme", custom_id="preview")
        async def show_preview(interaction):
            await interaction.response.defer()
            try:
                welcomer_cog = self.bot.get_cog("Welcomer")
                if not welcomer_cog:
                    await interaction.followup.send(
                        embed=create_embed(
                            description="❌ Önizleme oluşturulamıyor, Welcomer modülü bulunamadı.",
                            color=discord.Color.red()
                        ),
                        ephemeral=True
                    )
                    return
                background = None
                if "background_data" in self.config and self.config["background_data"]:
                    try:
                        background = base64.b64decode(self.config["background_data"])
                    except:
                        background = self.config["background_url"]
                else:
                    background = self.config["background_url"]
                filename = await welcomer_cog.create_welcome_image(self.author, background, self.config)
                description = self.config["description"].format(
                    mention=self.author.mention, name=self.author.name,
                    member_count=self.guild.member_count, server=self.guild.name
                )
                file = discord.File(filename)
                embed = discord.Embed(
                    title=f"🔍 Önizleme: {self.config.get('welcome_text', 'HOŞ GELDİN!')}",
                    description=description,
                    color=self.config["color"]
                )
                embed.set_image(url=f"attachment://{os.path.basename(filename)}")
                embed.set_footer(text="Bu bir önizlemedir. Değişiklik yapmak için önceki adımlara dönebilirsiniz.")
                await interaction.followup.send(file=file, embed=embed, ephemeral=True)
                try:
                    os.remove(filename)
                except Exception as e:
                    logger.error(f"Failed to remove temporary file: {e}")
            except Exception as e:
                logger.error(f"Failed to create preview: {e}")
                await interaction.followup.send(
                    embed=create_embed(
                        description=f"❌ Önizleme oluşturulurken bir hata oluştu: {str(e)}",
                        color=discord.Color.red()
                    ),
                    ephemeral=True
                )
        preview_button.callback = show_preview
        self.add_item(preview_button)
        save_button = Button(style=discord.ButtonStyle.green, label="💾 Kaydet", custom_id="save")
        async def save_settings(interaction):
            result = await self.save_configuration()
            if result:
                await interaction.response.edit_message(
                    embed=create_embed(
                        title="✅ Yapılandırma Tamamlandı",
                        description="Hoş geldin sistemi başarıyla yapılandırıldı!\n\n"
                                   f"Hoş geldin mesajları {self.channel.mention} kanalına gönderilecek.\n\n"
                                   "Test etmek için `/welcomer test` komutunu kullanabilirsiniz.",
                        color=discord.Color.green()
                    ),
                    view=None
                )
            else:
                await interaction.response.edit_message(
                    embed=create_embed(
                        title="❌ Hata",
                        description="Yapılandırma kaydedilirken bir hata oluştu. Lütfen daha sonra tekrar deneyin.",
                        color=discord.Color.red()
                    ),
                    view=None
                )
        save_button.callback = save_settings
        self.add_item(save_button)
        cancel_button = Button(style=discord.ButtonStyle.red, label="❌ İptal", custom_id="cancel")
        async def cancel_setup(interaction):
            await interaction.response.edit_message(
                embed=create_embed(
                    title="❌ İptal Edildi",
                    description="Hoş geldin sistemi yapılandırması iptal edildi.",
                    color=discord.Color.red()
                ),
                view=None
            )
        cancel_button.callback = cancel_setup
        self.add_item(cancel_button)
        await self.message.edit(
            embed=create_embed(
                title="✅ Yapılandırmayı Tamamlayın",
                description="Hoş geldin sistemi yapılandırmasını tamamlamak üzeresiniz.\n\n"
                           "Önizleme görmek için 'Önizleme' butonuna tıklayın.\n"
                           "Ayarları kaydetmek için 'Kaydet' butonuna tıklayın.\n"
                           "İptal etmek için 'İptal' butonuna tıklayın.",
                color=self.config["color"]
            ),
            view=self
        )

    async def save_configuration(self):
        try:
            collection = self.mongo_db[self.config_type]
            result = await collection.replace_one(
                {"guild_id": self.config["guild_id"]},
                self.config,
                upsert=True
            )
            return result.acknowledged
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
            return False

    def get_predefined_backgrounds(self):
        return {
            "Varsayılan": "data/Backgrounds/welcome_default.png",
            "Doğa": "data/Backgrounds/nature.png",
            "Şehir": "data/Backgrounds/city.png"
        }

    def process_uploaded_image(self, image_data):
        try:
            from PIL import Image
            image = Image.open(BytesIO(image_data))
            image = image.resize((1024, 500))
            output = BytesIO()
            image.save(output, format="PNG")
            return output.getvalue()
        except Exception as e:
            logger.error(f"Failed to process uploaded image: {e}")
            return None


class WelcomerConfigView(BaseConfigView):
    def __init__(self, bot, mongo_db, author, guild, channel):
        super().__init__(bot, mongo_db, author, guild, channel, "welcomer")


class ByeByeConfigView(BaseConfigView):
    def __init__(self, bot, mongo_db, author, guild, channel):
        super().__init__(bot, mongo_db, author, guild, channel, "byebye")
        self.config["description"] = "{mention} güle güle!"
        self.config["welcome_text"] = "GÜLE GÜLE!"
        self.config["background_url"] = "data/Backgrounds/byebye_default.png"