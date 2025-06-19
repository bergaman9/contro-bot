import discord
from discord.ui import View, Button, Select
import logging
from datetime import datetime
import asyncio
import random

from src.utils.formatting import create_embed

logger = logging.getLogger('turkoyto.views.game_matching')

class GameMatchingView(View):
    """View for matching players with similar game interests and creating game sessions"""
    
    def __init__(self, bot, mongo_db, user_id, guild_id):
        super().__init__(timeout=600)  # 10 minute timeout
        self.bot = bot
        self.mongo_db = mongo_db
        self.user_id = user_id
        self.guild_id = guild_id
        self.message = None
        self.selected_game = None
    
    async def send_initial_message(self, ctx):
        """Send the initial game matching message"""
        # Get user's game preferences
        user_data = self.mongo_db.turkoyto_users.find_one({
            "user_id": self.user_id,
            "guild_id": self.guild_id
        })
        
        if not user_data or not user_data.get("games"):
            embed = create_embed(
                title="❌ Oyun Bilgisi Bulunamadı",
                description="Oyun eşleştirmesini kullanabilmek için önce `/register` komutu ile kayıt olmalısınız.",
                color=discord.Color.red()
            )
            self.message = await ctx.send(embed=embed)
            return self.message
        
        # Initialize select menu with user's games
        self.initialize_game_select(user_data["games"])
        
        embed = create_embed(
            title="🎮 Oyun Eşleştirme",
            description="Birlikte oynamak istediğiniz bir oyun seçin ve benzer oyuncuları bulun veya oyun oturumu başlatın.",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="Favori Oyunlarınız",
            value=", ".join(user_data["games"][:5]) + ("..." if len(user_data["games"]) > 5 else ""),
            inline=False
        )
        
        embed.add_field(
            name="Nasıl Kullanılır?",
            value="1. Aşağıdaki menüden bir oyun seçin\n"
                  "2. 'Oyuncuları Bul' ile benzer oyuncuları görün\n"
                  "3. 'Oturum Başlat' ile oyun oturumu oluşturun",
            inline=False
        )
        
        self.message = await ctx.send(embed=embed, view=self)
        return self.message
    
    def initialize_game_select(self, games):
        """Initialize the game select dropdown with the user's games"""
        # Limit to 25 options (Discord limit)
        games = games[:25]
        
        options = [
            discord.SelectOption(label=game[:100], value=game[:100])  # Discord limits option label length
            for game in games
        ]
        
        # Create the select menu
        select = Select(
            placeholder="Oyun seçin...",
            options=options
        )
        
        # Set the callback
        select.callback = self.on_game_selected
        
        # Add to the view (clear any existing select first)
        for item in self.children[:]:
            if isinstance(item, Select):
                self.remove_item(item)
        
        self.add_item(select)
    
    async def on_game_selected(self, interaction: discord.Interaction):
        """Handle game selection"""
        select = [child for child in self.children if isinstance(child, Select)][0]
        self.selected_game = select.values[0]
        
        await interaction.response.defer()
        
        # Update the UI to show the selected game
        embed = create_embed(
            title="🎮 Oyun Eşleştirme",
            description=f"Seçilen oyun: **{self.selected_game}**\n\n"
                        f"Şimdi 'Oyuncuları Bul' veya 'Oturum Başlat' butonlarını kullanabilirsiniz.",
            color=discord.Color.blue()
        )
        
        await interaction.message.edit(embed=embed, view=self)
    
    @discord.ui.button(label="Oyuncuları Bul", style=discord.ButtonStyle.primary, emoji="🔍", row=1)
    async def find_players(self, interaction: discord.Interaction, button: Button):
        """Find players who play the selected game"""
        if not self.selected_game:
            await interaction.response.send_message(
                embed=create_embed(
                    description="❌ Lütfen önce bir oyun seçin!",
                    color=discord.Color.red()
                ),
                ephemeral=True
            )
            return
        
        await interaction.response.defer(ephemeral=True)
        
        # Find players who play this game
        players = list(self.mongo_db.turkoyto_users.find({
            "guild_id": self.guild_id,
            "games": self.selected_game,
            "user_id": {"$ne": self.user_id}  # Exclude the current user
        }))
        
        if not players:
            await interaction.followup.send(
                embed=create_embed(
                    description=f"❌ **{self.selected_game}** oynayan başka üye bulunamadı.",
                    color=discord.Color.red()
                ),
                ephemeral=True
            )
            return
        
        # Create an embed to display the players
        embed = create_embed(
            title=f"🎮 {self.selected_game} Oyuncuları",
            description=f"**{len(players)}** üye bu oyunu oynuyor:",
            color=discord.Color.green()
        )
        
        guild = self.bot.get_guild(self.guild_id)
        
        # Add players to the embed
        for i, player in enumerate(players[:10]):  # Limit to 10 players
            user_id = player["user_id"]
            member = guild.get_member(user_id)
            
            if member:
                status = "🟢 Çevrimiçi" if member.status == discord.Status.online else "⚪ Çevrimdışı"
                
                # Get user's activity if playing a game
                activity = next((a for a in member.activities if isinstance(a, discord.Game)), None)
                activity_text = f"Şu anda oynuyor: {activity.name}" if activity else ""
                
                embed.add_field(
                    name=f"{i+1}. {member.display_name}",
                    value=f"{status}\n"
                          f"Seviye: {player.get('level', 0)}\n"
                          f"{activity_text}",
                    inline=True
                )
        
        # Add a button to message these players
        view = PlayerContactView(self.bot, players[:10], guild)
        
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)
    
    @discord.ui.button(label="Oturum Başlat", style=discord.ButtonStyle.success, emoji="🎲", row=1)
    async def create_session(self, interaction: discord.Interaction, button: Button):
        """Create a gaming session for the selected game"""
        if not self.selected_game:
            await interaction.response.send_message(
                embed=create_embed(
                    description="❌ Lütfen önce bir oyun seçin!",
                    color=discord.Color.red()
                ),
                ephemeral=True
            )
            return
        
        # Send a modal to get session details
        modal = GameSessionModal(self.bot, self.mongo_db, self.guild_id, self.selected_game)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="İptal", style=discord.ButtonStyle.secondary, row=1)
    async def cancel(self, interaction: discord.Interaction, button: Button):
        """Cancel the game matching process"""
        await interaction.response.defer()
        
        # Clear the view and update the message
        for child in self.children[:]:
            self.remove_item(child)
            
        embed = create_embed(
            title="🎮 Oyun Eşleştirme İptal Edildi",
            description="Oyun eşleştirme işlemi iptal edildi.",
            color=discord.Color.red()
        )
        
        await interaction.message.edit(embed=embed, view=None)
        self.stop()

class PlayerContactView(View):
    """View for contacting players who play a specific game"""
    
    def __init__(self, bot, players, guild):
        super().__init__(timeout=300)  # 5 minute timeout
        self.bot = bot
        self.players = players
        self.guild = guild
    
    @discord.ui.button(label="Mesaj Gönder", style=discord.ButtonStyle.primary, emoji="✉️")
    async def send_message(self, interaction: discord.Interaction, button: Button):
        """Send a message to the selected players"""
        # Send a modal to get the message content
        modal = PlayerMessageModal(self.players, self.guild)
        await interaction.response.send_modal(modal)

class PlayerMessageModal(discord.ui.Modal, title="Oyunculara Mesaj Gönder"):
    """Modal for sending a message to players"""
    
    def __init__(self, players, guild):
        super().__init__()
        self.players = players
        self.guild = guild
        
        self.add_item(
            discord.ui.TextInput(
                label="Mesajınız",
                style=discord.TextStyle.paragraph,
                placeholder="Oyun oynamak için davet mesajınızı yazın",
                required=True,
                max_length=1000
            )
        )
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle the message submission"""
        message_content = self.children[0].value
        
        sent_count = 0
        failed_count = 0
        
        # Send DMs to all players
        for player in self.players:
            user_id = player["user_id"]
            member = self.guild.get_member(user_id)
            
            if member:
                try:
                    embed = create_embed(
                        title=f"🎮 Oyun Daveti",
                        description=f"{interaction.user.mention} sizinle oyun oynamak istiyor!",
                        color=discord.Color.blue()
                    )
                    embed.add_field(
                        name="Mesaj",
                        value=message_content,
                        inline=False
                    )
                    embed.add_field(
                        name="İletişim",
                        value=f"Yanıt vermek istiyorsanız {interaction.user.mention} ile iletişime geçebilirsiniz.",
                        inline=False
                    )
                    
                    await member.send(embed=embed)
                    sent_count += 1
                except:
                    failed_count += 1
            else:
                failed_count += 1
        
        # Inform the user about the results
        await interaction.response.send_message(
            embed=create_embed(
                title="✉️ Mesaj Sonuçları",
                description=f"Mesajınız {sent_count} oyuncuya gönderildi.\n"
                            f"{failed_count} oyuncuya gönderilemedi.",
                color=discord.Color.green() if sent_count > 0 else discord.Color.red()
            ),
            ephemeral=True
        )

class GameSessionModal(discord.ui.Modal, title="Oyun Oturumu Oluştur"):
    """Modal for creating a gaming session"""
    
    def __init__(self, bot, mongo_db, guild_id, game_name):
        super().__init__()
        self.bot = bot
        self.mongo_db = mongo_db
        self.guild_id = guild_id
        self.game_name = game_name
        
        self.add_item(
            discord.ui.TextInput(
                label="Oturum Başlığı",
                placeholder="Örn: CS2 Rekabetçi Maç",
                required=True,
                max_length=100
            )
        )
        
        self.add_item(
            discord.ui.TextInput(
                label="Açıklama",
                style=discord.TextStyle.paragraph,
                placeholder="Oyun oturumu hakkında detaylar",
                required=True,
                max_length=1000
            )
        )
        
        self.add_item(
            discord.ui.TextInput(
                label="Başlangıç Zamanı",
                placeholder="Bugün 21:00, Yarın 15:30 gibi",
                required=True
            )
        )
        
        self.add_item(
            discord.ui.TextInput(
                label="Oyuncu Sayısı",
                placeholder="Örn: 5",
                required=True,
                max_length=2
            )
        )
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle the session creation"""
        try:
            title = self.children[0].value
            description = self.children[1].value
            start_time = self.children[2].value
            
            # Validate player count
            try:
                player_count = int(self.children[3].value)
                if player_count < 2 or player_count > 64:
                    await interaction.response.send_message(
                        embed=create_embed(
                            description="❌ Oyuncu sayısı 2-64 arasında olmalıdır!",
                            color=discord.Color.red()
                        ),
                        ephemeral=True
                    )
                    return
            except ValueError:
                await interaction.response.send_message(
                    embed=create_embed(
                        description="❌ Geçersiz oyuncu sayısı! Sayısal bir değer girin.",
                        color=discord.Color.red()
                    ),
                    ephemeral=True
                )
                return
            
            # Create session record
            session_id = f"{interaction.user.id}-{datetime.now().timestamp()}"
            session_data = {
                "session_id": session_id,
                "game": self.game_name,
                "title": title,
                "description": description,
                "start_time": start_time,
                "max_players": player_count,
                "host_id": interaction.user.id,
                "guild_id": self.guild_id,
                "created_at": datetime.now(),
                "participants": [interaction.user.id],  # Host is automatically a participant
                "status": "open"
            }
            
            # Save to database
            self.mongo_db.turkoyto_sessions.insert_one(session_data)
            
            # Send confirmation to the user
            await interaction.response.send_message(
                embed=create_embed(
                    title="✅ Oyun Oturumu Oluşturuldu!",
                    description=f"**{self.game_name}** için oyun oturumu başarıyla oluşturuldu!",
                    color=discord.Color.green()
                ),
                ephemeral=True
            )
            
            # Find a suitable channel to announce this session
            guild = self.bot.get_guild(self.guild_id)
            
            # Try to find a gaming channel first
            gaming_channel = discord.utils.find(
                lambda c: any(keyword in c.name.lower() for keyword in ["oyun", "game", "gaming"]),
                guild.text_channels
            )
            
            # If no gaming channel, use the general channel
            if not gaming_channel:
                gaming_channel = discord.utils.find(
                    lambda c: any(keyword in c.name.lower() for keyword in ["genel", "general", "chat"]),
                    guild.text_channels
                )
            
            # If neither, use the first text channel with proper permissions
            if not gaming_channel:
                gaming_channel = next((c for c in guild.text_channels 
                                     if c.permissions_for(guild.me).send_messages), None)
            
            if gaming_channel:
                # Create a public announcement
                embed = create_embed(
                    title=f"🎮 Yeni Oyun Oturumu: {title}",
                    description=f"**{self.game_name}** için yeni bir oyun oturumu oluşturuldu!",
                    color=discord.Color.blue()
                )
                
                embed.add_field(name="Açıklama", value=description, inline=False)
                embed.add_field(name="Başlangıç", value=start_time, inline=True)
                embed.add_field(name="Oyuncular", value=f"1/{player_count}", inline=True)
                embed.add_field(name="Durum", value="✅ Açık", inline=True)
                embed.set_footer(text=f"Oturum ID: {session_id}")
                
                # Add the host's info
                embed.add_field(
                    name="Kurucu", 
                    value=interaction.user.mention,
                    inline=False
                )
                
                # Create a join button view
                view = GameSessionView(self.bot, self.mongo_db, session_id)
                
                # Post the announcement
                announcement = await gaming_channel.send(
                    content=f"📢 **{self.game_name}** oynamak isteyen var mı? {interaction.user.mention} yeni bir oturum oluşturdu!",
                    embed=embed,
                    view=view
                )
                
                # Update the session with the announcement message ID
                self.mongo_db.turkoyto_sessions.update_one(
                    {"session_id": session_id},
                    {"$set": {"announcement_id": announcement.id, "channel_id": gaming_channel.id}}
                )
        
        except Exception as e:
            logger.error(f"Error creating game session: {e}", exc_info=True)
            await interaction.response.send_message(
                embed=create_embed(
                    description="❌ Oturum oluşturulurken bir hata oluştu. Lütfen daha sonra tekrar deneyin.",
                    color=discord.Color.red()
                ),
                ephemeral=True
            )

class GameSessionView(View):
    """View for joining or managing a game session"""
    
    def __init__(self, bot, mongo_db, session_id):
        super().__init__(timeout=None)  # No timeout for session buttons
        self.bot = bot
        self.mongo_db = mongo_db
        self.session_id = session_id
    
    @discord.ui.button(label="Katıl", style=discord.ButtonStyle.success, emoji="✅", custom_id="join_session")
    async def join_session(self, interaction: discord.Interaction, button: Button):
        """Join the gaming session"""
        # Get session data
        session = self.mongo_db.turkoyto_sessions.find_one({"session_id": self.session_id})
        
        if not session:
            await interaction.response.send_message(
                embed=create_embed(
                    description="❌ Bu oturum artık mevcut değil.",
                    color=discord.Color.red()
                ),
                ephemeral=True
            )
            return
        
        # Check if session is open
        if session["status"] != "open":
            await interaction.response.send_message(
                embed=create_embed(
                    description="❌ Bu oturum artık açık değil.",
                    color=discord.Color.red()
                ),
                ephemeral=True
            )
            return
        
        # Check if user is already a participant
        if interaction.user.id in session["participants"]:
            await interaction.response.send_message(
                embed=create_embed(
                    description="❌ Zaten bu oturuma katıldınız!",
                    color=discord.Color.red()
                ),
                ephemeral=True
            )
            return
        
        # Check if session is full
        if len(session["participants"]) >= session["max_players"]:
            await interaction.response.send_message(
                embed=create_embed(
                    description="❌ Bu oturum doldu!",
                    color=discord.Color.red()
                ),
                ephemeral=True
            )
            return
        
        # Add user to participants
        self.mongo_db.turkoyto_sessions.update_one(
            {"session_id": self.session_id},
            {"$push": {"participants": interaction.user.id}}
        )
        
        # Update the session data
        session = self.mongo_db.turkoyto_sessions.find_one({"session_id": self.session_id})
        
        # Check if session is now full
        is_full = len(session["participants"]) >= session["max_players"]
        
        # Update the status if full
        if is_full:
            self.mongo_db.turkoyto_sessions.update_one(
                {"session_id": self.session_id},
                {"$set": {"status": "full"}}
            )
        
        # Update the announcement message
        try:
            channel = interaction.guild.get_channel(session["channel_id"])
            if channel:
                message = await channel.fetch_message(session["announcement_id"])
                
                if message:
                    embed = message.embeds[0]
                    
                    # Update player count
                    for i, field in enumerate(embed.fields):
                        if field.name == "Oyuncular":
                            embed.set_field_at(
                                i,
                                name="Oyuncular",
                                value=f"{len(session['participants'])}/{session['max_players']}",
                                inline=True
                            )
                        elif field.name == "Durum" and is_full:
                            embed.set_field_at(
                                i,
                                name="Durum",
                                value="🔴 Dolu",
                                inline=True
                            )
                    
                    # Update the message
                    await message.edit(embed=embed)
                    
                    # If session is full, disable the join button
                    if is_full:
                        for child in self.children:
                            if child.custom_id == "join_session":
                                child.disabled = True
                                break
                        
                        await message.edit(view=self)
        except Exception as e:
            logger.error(f"Error updating session message: {e}", exc_info=True)
        
        # Notify the user
        await interaction.response.send_message(
            embed=create_embed(
                title="✅ Oturuma Katıldınız!",
                description=f"**{session['game']}** oturumuna başarıyla katıldınız!",
                color=discord.Color.green()
            ),
            ephemeral=True
        )
        
        # Notify the host about the new participant
        host = interaction.guild.get_member(session["host_id"])
        if host:
            try:
                embed = create_embed(
                    title="🎮 Oturum Güncellemesi",
                    description=f"{interaction.user.mention} oluşturduğunuz **{session['game']}** oturumuna katıldı!",
                    color=discord.Color.blue()
                )
                
                embed.add_field(
                    name="Durum",
                    value=f"Şu anda {len(session['participants'])}/{session['max_players']} oyuncu var."
                )
                
                await host.send(embed=embed)
            except:
                pass  # Ignore if we can't DM the host
    
    @discord.ui.button(label="Detaylar", style=discord.ButtonStyle.primary, emoji="ℹ️", custom_id="session_details")
    async def show_details(self, interaction: discord.Interaction, button: Button):
        """Show session details including participants"""
        # Get session data
        session = self.mongo_db.turkoyto_sessions.find_one({"session_id": self.session_id})
        
        if not session:
            await interaction.response.send_message(
                embed=create_embed(
                    description="❌ Bu oturum artık mevcut değil.",
                    color=discord.Color.red()
                ),
                ephemeral=True
            )
            return
        
        # Create detailed embed
        embed = create_embed(
            title=f"🎮 {session['title']} - Detaylar",
            description=f"**{session['game']}** için oturum detayları:",
            color=discord.Color.blue()
        )
        
        embed.add_field(name="Açıklama", value=session["description"], inline=False)
        embed.add_field(name="Başlangıç", value=session["start_time"], inline=True)
        embed.add_field(name="Oyuncular", value=f"{len(session['participants'])}/{session['max_players']}", inline=True)
        
        status_text = "✅ Açık"
        if session["status"] == "full":
            status_text = "🔴 Dolu"
        elif session["status"] == "closed":
            status_text = "❌ Kapalı"
        elif session["status"] == "completed":
            status_text = "🏁 Tamamlandı"
            
        embed.add_field(name="Durum", value=status_text, inline=True)
        
        # Add participant list
        participants_text = ""
        for i, user_id in enumerate(session["participants"]):
            member = interaction.guild.get_member(user_id)
            name = member.display_name if member else f"Bilinmeyen Üye ({user_id})"
            
            if user_id == session["host_id"]:
                name += " 👑"  # Crown for host
                
            participants_text += f"{i+1}. {name}\n"
        
        embed.add_field(name="Katılımcılar", value=participants_text or "Henüz katılımcı yok", inline=False)
        
        # Add host information
        host = interaction.guild.get_member(session["host_id"])
        host_name = host.mention if host else "Bilinmeyen"
        embed.add_field(name="Kurucu", value=host_name, inline=False)
        
        # Show when the session was created
        embed.set_footer(text=f"Oluşturma: {session['created_at'].strftime('%d.%m.%Y %H:%M')}")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @discord.ui.button(label="İptal", style=discord.ButtonStyle.danger, emoji="❌", custom_id="cancel_session")
    async def cancel_session(self, interaction: discord.Interaction, button: Button):
        """Cancel the session (host only)"""
        # Get session data
        session = self.mongo_db.turkoyto_sessions.find_one({"session_id": self.session_id})
        
        if not session:
            await interaction.response.send_message(
                embed=create_embed(
                    description="❌ Bu oturum artık mevcut değil.",
                    color=discord.Color.red()
                ),
                ephemeral=True
            )
            return
        
        # Check if user is the host
        if interaction.user.id != session["host_id"]:
            await interaction.response.send_message(
                embed=create_embed(
                    description="❌ Sadece oturumun kurucusu iptal edebilir!",
                    color=discord.Color.red()
                ),
                ephemeral=True
            )
            return
        
        # Update session status
        self.mongo_db.turkoyto_sessions.update_one(
            {"session_id": self.session_id},
            {"$set": {"status": "closed"}}
        )
        
        # Update the message
        try:
            channel = interaction.guild.get_channel(session["channel_id"])
            if channel:
                message = await channel.fetch_message(session["announcement_id"])
                
                if message:
                    embed = message.embeds[0]
                    
                    # Update status
                    for i, field in enumerate(embed.fields):
                        if field.name == "Durum":
                            embed.set_field_at(
                                i,
                                name="Durum",
                                value="❌ İptal Edildi",
                                inline=True
                            )
                    
                    # Update the message
                    for child in self.children:
                        child.disabled = True
                    
                    await message.edit(embed=embed, view=self)
                    
                    # Add a notice to the message
                    await message.reply(
                        embed=create_embed(
                            description=f"⚠️ Bu oturum {interaction.user.mention} tarafından iptal edildi.",
                            color=discord.Color.orange()
                        )
                    )
        except Exception as e:
            logger.error(f"Error updating canceled session message: {e}", exc_info=True)
        
        # Notify the user
        await interaction.response.send_message(
            embed=create_embed(
                title="✅ Oturum İptal Edildi",
                description=f"**{session['game']}** için oluşturduğunuz oturum başarıyla iptal edildi.",
                color=discord.Color.green()
            ),
            ephemeral=True
        )
        
        # Notify all participants
        for user_id in session["participants"]:
            if user_id != interaction.user.id:  # Don't notify the host
                member = interaction.guild.get_member(user_id)
                if member:
                    try:
                        await member.send(
                            embed=create_embed(
                                title="❌ Oturum İptal Edildi",
                                description=f"Katıldığınız **{session['game']}** oturumu {interaction.user.mention} tarafından iptal edildi.",
                                color=discord.Color.red()
                            )
                        )
                    except:
                        pass  # Ignore if we can't DM the participant
