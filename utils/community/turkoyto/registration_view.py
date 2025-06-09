import discord
from discord.ui import Modal, TextInput, View, Button
import logging
from datetime import datetime
import re

from utils.formatting import create_embed

logger = logging.getLogger('turkoyto.views.registration')

# Common game names for autocomplete
POPULAR_GAMES = [
    "Counter-Strike 2", "VALORANT", "League of Legends", "Dota 2", 
    "Fortnite", "Apex Legends", "PUBG", "Rocket League", "Grand Theft Auto V", 
    "Minecraft", "Call of Duty: Warzone", "Overwatch 2", "Rainbow Six Siege",
    "FIFA 23", "Rust", "ARK: Survival Evolved", "Elden Ring", "Among Us",
    "Red Dead Redemption 2", "Destiny 2", "World of Warcraft", "Genshin Impact"
]

class GamerRegistrationModal(Modal, title="Oyuncu Kaydı"):
    """Modal for registering a gamer with game preferences."""
    
    def __init__(self, bot, mongo_db):
        super().__init__(timeout=None)
        self.bot = bot
        self.mongo_db = mongo_db
        
        # Add all the fields
        self.add_item(
            TextInput(
                label="İsminiz",
                placeholder="Gerçek isminizi girin (isteğe bağlı)",
                required=False,
                max_length=50
            )
        )
        
        self.add_item(
            TextInput(
                label="Yaşınız",
                placeholder="Yaşınızı girin (isteğe bağlı)",
                required=False,
                max_length=3
            )
        )
        
        self.add_item(
            TextInput(
                label="Steam ID / Epic Games / Riot ID",
                placeholder="Oyun hesabı ID'nizi girin",
                required=False,
                max_length=50
            )
        )
        
        self.add_item(
            TextInput(
                label="Favori Oyunlarınız",
                placeholder="En sevdiğiniz oyunları virgülle ayırarak yazın",
                required=True,
                style=discord.TextStyle.paragraph
            )
        )
        
        self.add_item(
            TextInput(
                label="Sunucudan Beklentileriniz ve Oynamak İstediğiniz Oyunlar",
                placeholder="Sunucudan beklentilerinizi ve oynamak istediğiniz oyunları yazın",
                required=True,
                style=discord.TextStyle.paragraph
            )
        )
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle the submitted registration data"""
        try:
            # Extract and validate the input
            name = self.children[0].value.strip()
            
            # Age validation
            age_text = self.children[1].value.strip()
            age = None
            if age_text:
                try:
                    age = int(age_text)
                    if age < 13 or age > 99:
                        await interaction.response.send_message(
                            embed=create_embed(
                                description="❌ Geçersiz yaş değeri! Yaş 13-99 arasında olmalıdır.",
                                color=discord.Color.red()
                            ),
                            ephemeral=True
                        )
                        return
                except ValueError:
                    await interaction.response.send_message(
                        embed=create_embed(
                            description="❌ Geçersiz yaş değeri! Lütfen sayısal bir değer girin.",
                            color=discord.Color.red()
                        ),
                        ephemeral=True
                    )
                    return
            
            game_id = self.children[2].value.strip()
            
            # Process favorite games
            favorite_games_text = self.children[3].value.strip()
            favorite_games = [game.strip() for game in favorite_games_text.split(',') if game.strip()]
            
            expectations = self.children[4].value.strip()
            
            # Get existing user data or create new entry
            user_data = self.mongo_db.turkoyto_users.find_one({
                "user_id": interaction.user.id,
                "guild_id": interaction.guild.id
            })
            
            if not user_data:
                user_data = {
                    "user_id": interaction.user.id,
                    "guild_id": interaction.guild.id,
                    "xp": 0,
                    "level": 0,
                    "next_level_xp": 1000,
                    "messages": 0,
                    "voice_minutes": 0,
                    "registered": False,
                    "registration_date": datetime.now()
                }
            
            # Update with new registration data
            user_data.update({
                "name": name if name else None,
                "age": age,
                "game_id": game_id if game_id else None,
                "games": favorite_games,
                "expectations": expectations,
                "registered": True,
                "last_updated": datetime.now()
            })
            
            # Save to database
            self.mongo_db.turkoyto_users.update_one(
                {"user_id": interaction.user.id, "guild_id": interaction.guild.id},
                {"$set": user_data},
                upsert=True
            )
            
            # Also save game information separately for better querying
            for game in favorite_games:
                # Check if game exists in the games collection
                existing_game = self.mongo_db.turkoyto_games.find_one({"name_lower": game.lower()})
                
                if not existing_game:
                    # Add new game to collection
                    self.mongo_db.turkoyto_games.insert_one({
                        "name": game,
                        "name_lower": game.lower(),
                        "player_count": 1,
                        "first_added": datetime.now()
                    })
                else:
                    # Update existing game's player count
                    self.mongo_db.turkoyto_games.update_one(
                        {"name_lower": game.lower()},
                        {"$inc": {"player_count": 1}}
                    )
            
            # Log registration to register-logs channel
            try:
                register_log_channel = discord.utils.get(interaction.guild.channels, name="register-logs")
                if register_log_channel and isinstance(register_log_channel, discord.TextChannel):
                    # Create a log embed with registration details
                    log_embed = create_embed(
                        title="📝 Yeni Kayıt",
                        description=f"{interaction.user.mention} sunucuya kayıt oldu!",
                        color=discord.Color.green()
                    )
                    
                    # Add user info to the log
                    field_data = []
                    if name:
                        field_data.append(f"**İsim:** {name}")
                    if age:
                        field_data.append(f"**Yaş:** {age}")
                    if game_id:
                        field_data.append(f"**Oyun ID:** {game_id}")
                    
                    field_data.append(f"**Favori Oyunlar:** {', '.join(favorite_games)}")
                    field_data.append(f"**Beklentiler:** {expectations[:100]}{'...' if len(expectations) > 100 else ''}")
                    
                    log_embed.add_field(
                        name="Kullanıcı Bilgileri",
                        value="\n".join(field_data),
                        inline=False
                    )
                    
                    # Add timestamp
                    log_embed.timestamp = datetime.now()
                    
                    # Add user avatar as thumbnail
                    log_embed.set_thumbnail(url=interaction.user.display_avatar.url)
                    
                    await register_log_channel.send(embed=log_embed)
                else:
                    logger.warning(f"Could not find register-logs channel to log registration for user {interaction.user.id}")
            except Exception as log_error:
                logger.error(f"Failed to send registration log: {log_error}")
            
            # Send success message to user
            embed = create_embed(
                title="✅ Kayıt Başarılı!",
                description="Türk Oyuncu Topluluğu'na kaydınız başarıyla tamamlandı!",
                color=discord.Color.green()
            )
            
            field_data = []
            if name:
                field_data.append(f"**İsim:** {name}")
            if age:
                field_data.append(f"**Yaş:** {age}")
            if game_id:
                field_data.append(f"**Oyun ID:** {game_id}")
            
            field_data.append(f"**Favori Oyunlar:** {', '.join(favorite_games)}")
            
            embed.add_field(
                name="Bilgileriniz",
                value="\n".join(field_data),
                inline=False
            )
            
            # Add recommendations based on games
            similar_players = list(self.mongo_db.turkoyto_users.find({
                "guild_id": interaction.guild.id,
                "games": {"$in": favorite_games},
                "user_id": {"$ne": interaction.user.id}
            }).limit(5))
            
            if similar_players:
                similar_users_text = []
                for player in similar_players:
                    member = interaction.guild.get_member(player["user_id"])
                    if member:
                        similar_games = set(player["games"]) & set(favorite_games)
                        similar_users_text.append(
                            f"• {member.mention} - Ortak: {', '.join(similar_games)}"
                        )
                
                if similar_users_text:
                    embed.add_field(
                        name="Benzer Oyunları Oynayan Üyeler",
                        value="\n".join(similar_users_text[:3]),  # Limit to 3 for cleaner display
                        inline=False
                    )
            
            # Suggest a role based on games if you have game-specific roles
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
            # Show game buddy finder button
            view = GameBuddyView(self.bot, self.mongo_db, favorite_games)
            await interaction.followup.send(
                embed=create_embed(
                    description="🎮 Benzer oyunları oynayan arkadaşları bulmak ister misiniz?",
                    color=discord.Color.blue()
                ),
                view=view,
                ephemeral=True
            )
            
            # Log registration
            logger.info(f"User {interaction.user.id} ({interaction.user.name}) registered with games: {favorite_games}")
            
            # Award XP for registration
            await self.award_registration_xp(interaction.user, interaction.guild.id)
            
        except Exception as e:
            logger.error(f"Registration error: {e}", exc_info=True)
            await interaction.response.send_message(
                embed=create_embed(
                    description="❌ Kayıt sırasında bir hata oluştu. Lütfen daha sonra tekrar deneyin.",
                    color=discord.Color.red()
                ),
                ephemeral=True
            )
    
    async def award_registration_xp(self, user, guild_id):
        """Award XP for completing registration"""
        try:
            # Award 100 XP for registration
            registration_xp = 100
            
            self.mongo_db.turkoyto_users.update_one(
                {"user_id": user.id, "guild_id": guild_id},
                {"$inc": {"xp": registration_xp}}
            )
            
            # Check if user leveled up
            user_data = self.mongo_db.turkoyto_users.find_one({"user_id": user.id, "guild_id": guild_id})
            
            if user_data["xp"] >= user_data["next_level_xp"]:
                # Update level and next_level_xp
                new_level = user_data["level"] + 1
                next_level_xp = 1000 * (new_level + 1) * 1.5
                
                self.mongo_db.turkoyto_users.update_one(
                    {"user_id": user.id, "guild_id": guild_id},
                    {"$set": {"level": new_level, "next_level_xp": next_level_xp}}
                )
        except Exception as e:
            logger.error(f"Error awarding registration XP: {e}", exc_info=True)

class GameBuddyView(View):
    """View for finding game buddies after registration"""
    
    def __init__(self, bot, mongo_db, games):
        super().__init__(timeout=300)  # 5 minute timeout
        self.bot = bot
        self.mongo_db = mongo_db
        self.games = games
    
    @discord.ui.button(label="Oyun Arkadaşlarını Bul", style=discord.ButtonStyle.green, emoji="🔍")
    async def find_buddies(self, interaction: discord.Interaction, button: Button):
        """Find and display users who play similar games"""
        await interaction.response.defer(ephemeral=True)
        
        if not self.games:
            await interaction.followup.send(
                embed=create_embed(
                    description="❌ Oyun listesi bulunamadı!",
                    color=discord.Color.red()
                ),
                ephemeral=True
            )
            return
        
        # Find players with similar game preferences
        similar_players = list(self.mongo_db.turkoyto_users.find({
            "guild_id": interaction.guild.id,
            "games": {"$in": self.games},
            "user_id": {"$ne": interaction.user.id}
        }))
        
        if not similar_players:
            await interaction.followup.send(
                embed=create_embed(
                    description="❌ Benzer oyunları oynayan üye bulunamadı.",
                    color=discord.Color.red()
                ),
                ephemeral=True
            )
            return
        
        # Organize players by game similarity
        players_by_similarity = {}
        for player in similar_players:
            member = interaction.guild.get_member(player["user_id"])
            if not member:
                continue
                
            common_games = set(player["games"]) & set(self.games)
            similarity_score = len(common_games)
            
            if similarity_score not in players_by_similarity:
                players_by_similarity[similarity_score] = []
                
            players_by_similarity[similarity_score].append({
                "member": member,
                "common_games": common_games
            })
        
        # Sort by similarity score (descending)
        sorted_scores = sorted(players_by_similarity.keys(), reverse=True)
        
        embed = create_embed(
            title="🎮 Benzer Oyunları Oynayan Üyeler",
            description="İşte sizinle aynı oyunları oynayan sunucu üyeleri:",
            color=discord.Color.blue()
        )
        
        total_added = 0
        for score in sorted_scores:
            if total_added >= 10:  # Limit to 10 users max
                break
                
            for player_data in players_by_similarity[score][:5]:  # Max 5 per similarity level
                if total_added >= 10:
                    break
                    
                member = player_data["member"]
                common_games = player_data["common_games"]
                
                embed.add_field(
                    name=f"{member.display_name} ({len(common_games)} ortak oyun)",
                    value=f"Ortak oyunlar: {', '.join(list(common_games)[:3])}{'...' if len(common_games) > 3 else ''}",
                    inline=False
                )
                total_added += 1
        
        if total_added > 0:
            embed.set_footer(text="Oyun arkadaşı bulmak için bu üyelere mesaj gönderebilirsiniz!")
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await interaction.followup.send(
                embed=create_embed(
                    description="❌ Benzer oyunları oynayan aktif üye bulunamadı.",
                    color=discord.Color.red()
                ),
                ephemeral=True
            )
    
    @discord.ui.button(label="Vazgeç", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: Button):
        """Cancel the buddy finder"""
        await interaction.response.defer(ephemeral=True)
        await interaction.followup.send(
            embed=create_embed(
                description="✅ İşlem iptal edildi.",
                color=discord.Color.green()
            ),
            ephemeral=True
        )
        self.stop()
