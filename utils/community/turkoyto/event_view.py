import discord
from discord.ui import View, Button, Select, Modal, TextInput
import logging
from datetime import datetime
import asyncio

from utils.formatting import create_embed

logger = logging.getLogger('turkoyto.views.events')

class EventParticipationView(View):
    """View for participating in events"""
    
    def __init__(self, bot, mongo_db, event_id):
        super().__init__(timeout=None)
        self.bot = bot
        self.mongo_db = mongo_db
        self.event_id = event_id
    
    @discord.ui.button(label="Katıl", style=discord.ButtonStyle.success, emoji="✅", custom_id="join_event")
    async def join_event(self, interaction: discord.Interaction, button: Button):
        """Join the event"""
        event = self.mongo_db.turkoyto_events.find_one({"event_id": self.event_id})
        
        if not event:
            await interaction.response.send_message(
                embed=create_embed(
                    description="❌ Bu etkinlik artık mevcut değil.",
                    color=discord.Color.red()
                ),
                ephemeral=True
            )
            return
        
        if interaction.user.id in event["participants"]:
            await interaction.response.send_message(
                embed=create_embed(
                    description="❌ Zaten bu etkinliğe katıldınız!",
                    color=discord.Color.red()
                ),
                ephemeral=True
            )
            return
        
        if len(event["participants"]) >= event["max_participants"]:
            await interaction.response.send_message(
                embed=create_embed(
                    description="❌ Etkinlik dolu! Daha fazla katılımcı alınamıyor.",
                    color=discord.Color.red()
                ),
                ephemeral=True
            )
            return
        
        self.mongo_db.turkoyto_events.update_one(
            {"event_id": self.event_id},
            {"$push": {"participants": interaction.user.id}}
        )
        
        event = self.mongo_db.turkoyto_events.find_one({"event_id": self.event_id})
        
        try:
            channel = interaction.guild.get_channel(event["channel_id"])
            if channel:
                message = await channel.fetch_message(event["announcement_id"])
                
                if message:
                    embed = message.embeds[0]
                    
                    for i, field in enumerate(embed.fields):
                        if field.name == "Katılımcılar":
                            embed.set_field_at(
                                i,
                                name="Katılımcılar",
                                value=f"{len(event['participants'])}/{event['max_participants']}",
                                inline=True
                            )
                    
                    await message.edit(embed=embed)
                    
                    if len(event["participants"]) >= event["max_participants"]:
                        for child in self.children:
                            if child.custom_id == "join_event":
                                child.disabled = True
                                break
                        
                        await message.edit(view=self)
        except Exception as e:
            logger.error(f"Error updating event message: {e}", exc_info=True)
        
        await interaction.response.send_message(
            embed=create_embed(
                title="✅ Etkinliğe Katıldınız!",
                description=f"**{event['title']}** etkinliğine başarıyla katıldınız!",
                color=discord.Color.green()
            ),
            ephemeral=True
        )
        
        host = interaction.guild.get_member(event["creator_id"])
        if host:
            try:
                embed = create_embed(
                    title="🎮 Etkinlik Güncellemesi",
                    description=f"{interaction.user.mention} **{event['title']}** etkinliğinize katıldı!",
                    color=discord.Color.blue()
                )
                
                embed.add_field(
                    name="Durum",
                    value=f"Şu anda {len(event['participants'])}/{event['max_participants']} katılımcı var."
                )
                
                await host.send(embed=embed)
            except:
                pass
    
    @discord.ui.button(label="Detaylar", style=discord.ButtonStyle.primary, emoji="ℹ️", custom_id="view_details")
    async def view_details(self, interaction: discord.Interaction, button: Button):
        """View detailed information about the event"""
        event = self.mongo_db.turkoyto_events.find_one({"event_id": self.event_id})
        
        if not event:
            await interaction.response.send_message(
                embed=create_embed(
                    description="❌ Bu etkinlik artık mevcut değil.",
                    color=discord.Color.red()
                ),
                ephemeral=True
            )
            return
        
        embed = create_embed(
            title=f"🎮 {event['title']} - Detaylar",
            description=f"**{event['game']}** için etkinlik detayları:",
            color=discord.Color.blue()
        )
        
        embed.add_field(name="Türü", value=EventCreationView.get_event_type_name(event["event_type"]), inline=True)
        embed.add_field(name="Tarih/Saat", value=event["date_time"], inline=True)
        embed.add_field(name="Katılımcılar", value=f"{len(event['participants'])}/{event['max_participants']}", inline=True)
        embed.add_field(name="Açıklama", value=event["description"], inline=False)
        
        participants_text = ""
        for i, user_id in enumerate(event["participants"]):
            member = interaction.guild.get_member(user_id)
            name = member.display_name if member else f"Bilinmeyen Üye ({user_id})"
            
            if user_id == event["creator_id"]:
                name += " 👑"
                
            participants_text += f"{i+1}. {name}\n"
        
        embed.add_field(name="Katılımcılar", value=participants_text or "Henüz katılımcı yok", inline=False)
        
        creator = interaction.guild.get_member(event["creator_id"])
        creator_name = creator.mention if creator else "Bilinmeyen"
        embed.add_field(name="Düzenleyen", value=creator_name, inline=False)
        
        embed.set_footer(text=f"Oluşturma: {event['created_at'].strftime('%d.%m.%Y %H:%M')}")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @discord.ui.button(label="Ayrıl", style=discord.ButtonStyle.danger, emoji="❌", custom_id="leave_event")
    async def leave_event(self, interaction: discord.Interaction, button: Button):
        """Leave the event"""
        event = self.mongo_db.turkoyto_events.find_one({"event_id": self.event_id})
        
        if not event:
            await interaction.response.send_message(
                embed=create_embed(
                    description="❌ Bu etkinlik artık mevcut değil.",
                    color=discord.Color.red()
                ),
                ephemeral=True
            )
            return
        
        if interaction.user.id == event["creator_id"]:
            await interaction.response.send_message(
                embed=create_embed(
                    description="❌ Etkinliğin düzenleyicisi olduğunuz için ayrılamazsınız. Etkinliği iptal etmek istiyorsanız 'İptal Et' butonunu kullanın.",
                    color=discord.Color.red()
                ),
                ephemeral=True
            )
            return
        
        if interaction.user.id not in event["participants"]:
            await interaction.response.send_message(
                embed=create_embed(
                    description="❌ Bu etkinliğe zaten katılmıyorsunuz!",
                    color=discord.Color.red()
                ),
                ephemeral=True
            )
            return
        
        self.mongo_db.turkoyto_events.update_one(
            {"event_id": self.event_id},
            {"$pull": {"participants": interaction.user.id}}
        )
        
        event = self.mongo_db.turkoyto_events.find_one({"event_id": self.event_id})
        
        try:
            channel = interaction.guild.get_channel(event["channel_id"])
            if channel:
                message = await channel.fetch_message(event["announcement_id"])
                
                if message:
                    embed = message.embeds[0]
                    
                    for i, field in enumerate(embed.fields):
                        if field.name == "Katılımcılar":
                            embed.set_field_at(
                                i,
                                name="Katılımcılar",
                                value=f"{len(event['participants'])}/{event['max_participants']}",
                                inline=True
                            )
                    
                    await message.edit(embed=embed)
                    
                    if len(event["participants"]) < event["max_participants"]:
                        for child in self.children:
                            if child.custom_id == "join_event":
                                child.disabled = False
                                break
                        
                        await message.edit(view=self)
        except Exception as e:
            logger.error(f"Error updating event message: {e}", exc_info=True)
        
        await interaction.response.send_message(
            embed=create_embed(
                title="✅ Etkinlikten Ayrıldınız",
                description=f"**{event['title']}** etkinliğinden başarıyla ayrıldınız.",
                color=discord.Color.green()
            ),
            ephemeral=True
        )
        
        host = interaction.guild.get_member(event["creator_id"])
        if host:
            try:
                await host.send(
                    embed=create_embed(
                        title="🎮 Etkinlik Güncellemesi",
                        description=f"{interaction.user.mention} **{event['title']}** etkinliğinizden ayrıldı.",
                        color=discord.Color.orange()
                    )
                )
            except:
                pass

class EventCreationView(View):
    """Simplified view for creating gaming events"""
    
    @staticmethod
    def get_event_type_name(event_type):
        """Get a human-readable name for the event type"""
        event_types = {
            "tournament": "Turnuva",
            "casual": "Arkadaş Buluşması",
            "workshop": "Eğitim/Workshop",
            "stream": "Yayın Etkinliği"
        }
        return event_types.get(event_type, event_type)
    
    def __init__(self, bot, mongo_db, user_id, guild_id):
        super().__init__(timeout=300)
        self.bot = bot
        self.mongo_db = mongo_db
        self.user_id = user_id
        self.guild_id = guild_id
        self.message = None
    
    async def send_initial_message(self, ctx):
        """Send the initial event creation message"""
        embed = create_embed(
            title="🎮 Oyun Etkinliği Oluştur",
            description="Sunucuda bir oyun etkinliği oluşturmak için aşağıdaki butona tıklayın.",
            color=discord.Color.blue()
        )
        
        self.message = await ctx.send(embed=embed, view=self)
        return self.message
    
    @discord.ui.button(label="Etkinlik Oluştur", style=discord.ButtonStyle.primary, emoji="🎮")
    async def create_event(self, interaction: discord.Interaction, button: Button):
        """Create an event using a modal"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                embed=create_embed(
                    description="❌ Bu komutu siz başlatmadınız!",
                    color=discord.Color.red()
                ),
                ephemeral=True
            )
            return
        
        modal = EventCreationModal(self.bot, self.mongo_db, self.guild_id, interaction.user.id)
        await interaction.response.send_modal(modal)

class EventCreationModal(Modal, title="Oyun Etkinliği Oluştur"):
    """Modal for creating a gaming event"""
    
    def __init__(self, bot, mongo_db, guild_id, user_id):
        super().__init__()
        self.bot = bot
        self.mongo_db = mongo_db
        self.guild_id = guild_id
        self.user_id = user_id
        
        self.add_item(
            TextInput(
                label="Etkinlik Adı",
                placeholder="Etkinliğin adını girin (örn: CS2 Turnuvası)",
                required=True,
                max_length=100
            )
        )
        
        self.add_item(
            TextInput(
                label="Oyun",
                placeholder="Etkinlikte oynanacak oyun",
                required=True,
                max_length=100
            )
        )
        
        self.add_item(
            TextInput(
                label="Etkinlik Türü",
                placeholder="Turnuva, Arkadaş Buluşması, Workshop, Yayın",
                required=True
            )
        )
        
        self.add_item(
            TextInput(
                label="Tarih ve Saat",
                placeholder="Örn: 25 Aralık 2023, 21:00",
                required=True
            )
        )
        
        self.add_item(
            TextInput(
                label="Detaylar",
                style=discord.TextStyle.paragraph,
                placeholder="Etkinlik hakkında detaylı bilgi verin",
                required=True,
                max_length=1000
            )
        )
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle the form submission"""
        await interaction.response.defer(ephemeral=True)
        
        try:
            title = self.children[0].value.strip()
            game = self.children[1].value.strip()
            event_type_input = self.children[2].value.strip().lower()
            date_time = self.children[3].value.strip()
            description = self.children[4].value.strip()
            
            event_type_mapping = {
                "turnuva": "tournament",
                "arkadaş buluşması": "casual",
                "buluşma": "casual",
                "workshop": "workshop",
                "eğitim": "workshop",
                "yayın": "stream",
                "canlı yayın": "stream"
            }
            
            event_type = None
            for key, value in event_type_mapping.items():
                if key in event_type_input:
                    event_type = value
                    break
            
            if not event_type:
                event_type = "casual"
            
            event_id = f"{self.user_id}-{datetime.now().timestamp()}"
            event_data = {
                "event_id": event_id,
                "title": title,
                "game": game,
                "event_type": event_type,
                "date_time": date_time,
                "description": description,
                "creator_id": self.user_id,
                "guild_id": self.guild_id,
                "created_at": datetime.now(),
                "participants": [self.user_id],
                "max_participants": 20,
                "status": "active"
            }
            
            self.mongo_db.turkoyto_events.insert_one(event_data)
            
            guild = self.bot.get_guild(self.guild_id)
            
            events_channel = discord.utils.find(
                lambda c: any(keyword in c.name.lower() for keyword in ["etkinlik", "event"]),
                guild.text_channels
            )
            
            if not events_channel:
                events_channel = discord.utils.find(
                    lambda c: any(keyword in c.name.lower() for keyword in ["duyuru", "announcement"]),
                    guild.text_channels
                )
            
            if not events_channel:
                events_channel = discord.utils.find(
                    lambda c: any(keyword in c.name.lower() for keyword in ["genel", "general", "chat"]),
                    guild.text_channels
                )
            
            embed = create_embed(
                title=f"🎮 Yeni Etkinlik: {title}",
                description=f"**{game}** için yeni bir etkinlik düzenleniyor!",
                color=discord.Color.blue()
            )
            
            embed.add_field(name="Türü", value=EventCreationView.get_event_type_name(event_type), inline=True)
            embed.add_field(name="Tarih/Saat", value=date_time, inline=True)
            embed.add_field(name="Katılımcılar", value=f"1/{event_data['max_participants']}", inline=True)
            embed.add_field(name="Açıklama", value=description, inline=False)
            
            embed.add_field(
                name="Düzenleyen", 
                value=interaction.user.mention,
                inline=False
            )
            
            embed.set_footer(text=f"Etkinlik ID: {event_id}")
            
            view = EventParticipationView(self.bot, self.mongo_db, event_id)
            
            if events_channel:
                mention = "@everyone" if event_data['max_participants'] > 10 else "@here"
                announcement = await events_channel.send(
                    content=f"{mention} Yeni bir **{game}** etkinliği düzenleniyor! Katılmak isteyenler aşağıdaki butonu kullanabilir.",
                    embed=embed,
                    view=view
                )
                
                self.mongo_db.turkoyto_events.update_one(
                    {"event_id": event_id},
                    {"$set": {"announcement_id": announcement.id, "channel_id": events_channel.id}}
                )
            
            await interaction.followup.send(
                embed=create_embed(
                    title="✅ Etkinlik Oluşturuldu!",
                    description=f"**{title}** etkinliği başarıyla oluşturuldu ve duyuruldu!",
                    color=discord.Color.green()
                ),
                ephemeral=True
            )
            
            await self.award_event_creation_xp(interaction.user)
            
        except Exception as e:
            logger.error(f"Error creating event: {e}", exc_info=True)
            await interaction.followup.send(
                embed=create_embed(
                    description="❌ Etkinlik oluşturulurken bir hata oluştu. Lütfen daha sonra tekrar deneyin.",
                    color=discord.Color.red()
                ),
                ephemeral=True
            )
    
    async def award_event_creation_xp(self, user):
        """Award XP for creating an event"""
        try:
            event_creation_xp = 200
            
            self.mongo_db.turkoyto_users.update_one(
                {"user_id": user.id, "guild_id": self.guild_id},
                {"$inc": {"xp": event_creation_xp}}
            )
            
            user_data = self.mongo_db.turkoyto_users.find_one({"user_id": user.id, "guild_id": self.guild_id})
            
            if user_data and user_data.get("xp", 0) >= user_data.get("next_level_xp", 1000):
                new_level = user_data.get("level", 0) + 1
                next_level_xp = 1000 * (new_level + 1) * 1.5
                
                self.mongo_db.turkoyto_users.update_one(
                    {"user_id": user.id, "guild_id": self.guild_id},
                    {"$set": {"level": new_level, "next_level_xp": next_level_xp}}
                )
        except Exception as e:
            logger.error(f"Error awarding event creation XP: {e}", exc_info=True)