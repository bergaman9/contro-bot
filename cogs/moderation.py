import time
import io

import discord
from discord.ext import commands, tasks
from discord import app_commands
import re
import asyncio

from utils.core.formatting import create_embed
from utils.database.connection import initialize_mongodb
from utils.core.helpers import check_video_url

TURKISH_PROFANITY_WORDS = ["abaza", "abazan", "ag", "ağzına sıçayım", "ahmak", "allah",
                           "allahsız", "am", "amarım", "ambiti", "am biti", "amcığı",
                           "amcığın", "amcığını", "amcığınızı", "amcık", "amcık hoşafı",
                           "amcıklama", "amcıklandı", "amcik", "amck", "amckl", "amcklama", "amcklaryla",
                           "amckta", "amcktan", "amcuk", "amık", "amına", "amınako", "amına koy",
                           "amına koyarım", "amına koyayım", "amınakoyim", "amına koyyim",
                           "amına s", "amına sikem", "amına sokam", "amın feryadı",
                           "amını", "amını s", "amın oglu", "amınoğlu",
                           "amın oğlu", "amısına", "amısını", "amina", "amina g",
                           "amina k", "aminako", "aminakoyarim", "amina koyarim", "amina koyayım", "amina koyayim",
                           "aminakoyim", "aminda", "amindan", "amindayken", "amini", "aminiyarraaniskiim", "aminoglu",
                           "amin oglu", "amiyum", "amk", "amkafa", "amk çocuğu", "amlarnzn", "amlı",
                           "amm", "ammak", "ammna", "amn", "amna", "amnda", "amndaki", "amngtn", "amnn", "amona", "amq",
                           "amsız", "amsiz", "amsz", "amteri", "amugaa", "amuğa", "amuna", "ana", "anaaann",
                           "anal", "analarn", "anam", "anamla", "anan", "anana", "anandan", "ananı", "ananı",
                           "ananın", "ananın am", "ananın amı", "ananın dölü",
                           "ananınki", "ananısikerim", "ananı sikerim", "ananısikeyim",
                           "ananı sikeyim", "ananızın", "ananızın am", "anani", "ananin",
                           "ananisikerim", "anani sikerim", "ananisikeyim", "anani sikeyim", "anann", "ananz", "anas",
                           "anasını", "anasının am", "anası orospu", "anasi", "anasinin",
                           "anay", "anayin", "angut", "anneni", "annenin", "annesiz", "anuna", "aptal", "aq", "a.q",
                           "a.q.", "aq.", "ass", "atkafası", "atmık", "attırdığım",
                           "attrrm", "auzlu", "avrat", "ayklarmalrmsikerim", "azdım", "azdır",
                           "azdırıcı", "babaannesi kaşar", "babanı", "babanın", "babani",
                           "babası pezevenk", "bacağına sıçayım", "bacına", "bacını", "bacının", "bacini",
                           "bacn", "bacndan", "bacy", "bastard", "basur", "beyinsiz", "bızır", "bitch", "biting", "bok",
                           "boka", "bokbok", "bokça", "bokhu", "bokkkumu", "boklar", "boktan", "boku", "bokubokuna",
                           "bokum", "bombok", "boner", "bosalmak", "boşalmak", "cenabet", "cibiliyetsiz", "cibilliyetini",
                           "cibilliyetsiz", "cif", "cikar", "cim", "çük", "dalaksız", "dallama",
                           "daltassak", "dalyarak", "dalyarrak", "dangalak", "dassagi", "diktim", "dildo", "dingil",
                           "dingilini", "dinsiz", "dkerim", "domal", "domalan", "domaldı", "domaldın",
                           "domalık", "domalıyor", "domalmak", "domalmış", "domalsın",
                           "domalt", "domaltarak", "domaltıp", "domaltır", "domaltırım", "domaltip",
                           "domaltmak", "dölü", "dönek", "düdük", "eben", "ebeni", "ebenin",
                           "ebeninki", "ebleh", "ecdadını", "ecdadini", "embesil", "emi", "fahise",
                           "fahişe", "feriştah", "ferre", "fuck", "fucker", "fuckin", "fucking", "gavad",
                           "gavat", "geber", "geberik", "gebermek", "gebermiş", "gebertir", "gerızekalı",
                           "gerizekalı", "gerizekali", "gerzek", "giberim", "giberler", "gibis", "gibiş",
                           "gibmek", "gibtiler", "goddamn", "godoş", "godumun", "gotelek", "gotlalesi", "gotlu",
                           "gotten", "gotundeki", "gotunden", "gotune", "gotunu", "gotveren", "goyiim", "goyum",
                           "goyuyim", "goyyim", "göt", "göt deliği", "götelek", "göt herif",
                           "götlalesi", "götlek", "götoğlanı", "göt oğlanı",
                           "götoş", "götten", "götü", "götün", "götüne",
                           "götünekoyim", "götüne koyim", "götünü", "götveren",
                           "göt veren", "göt verir", "gtelek", "gtn", "gtnde", "gtnden", "gtne", "gtten",
                           "gtveren", "hasiktir", "hassikome", "hassiktir", "has siktir", "hassittir", "haysiyetsiz",
                           "hayvan herif", "hoşafı", "hödük", "hsktr", "huur", "ıbnelık",
                           "ibina", "ibine", "ibinenin", "ibne", "ibnedir", "ibneleri", "ibnelik", "ibnelri", "ibneni",
                           "ibnenin", "ibnerator", "ibnesi", "idiot", "idiyot", "imansz", "ipne", "iserim",
                           "işerim", "itoğlu it", "kafam girsin", "kafasız", "kafasiz", "kahpe",
                           "kahpenin", "kahpenin feryadı", "kaka", "kaltak", "kancık", "kancik", "kappe",
                           "karhane", "kaşar", "kavat", "kavatn", "kaypak", "kayyum", "kerane", "kerhane",
                           "kerhanelerde", "kevase", "kevaşe", "kevvase", "koca göt", "koduğmun",
                           "koduğmunun", "kodumun", "kodumunun", "koduumun", "koyarm", "koyayım", "koyiim",
                           "koyiiym", "koyim", "koyum", "koyyim", "krar", "kukudaym", "laciye boyadım", "lavuk",
                           "liboş", "madafaka", "mal", "malafat", "malak", "manyak", "mcik", "meme", "memelerini",
                           "mezveleli", "minaamcık", "mincikliyim", "mna", "monakkoluyum", "motherfucker", "mudik",
                           "oc", "ocuu", "ocuun", "OÇ", "oç", "o. çocuğu", "oğlan",
                           "oğlancı", "oğlu it", "orosbucocuu", "orospu", "orospucocugu",
                           "orospu cocugu", "orospu çoc", "orospuçocuğu", "orospu çocuğu",
                           "orospu çocuğudur", "orospu çocukları", "orospudur", "orospular",
                           "orospunun", "orospunun evladı", "orospuydu", "orospuyuz", "orostoban", "orostopol",
                           "orrospu", "oruspu", "oruspuçocuğu", "oruspu çocuğu", "osbir",
                           "ossurduum", "ossurmak", "ossuruk", "osur", "osurduu", "osuruk", "osururum", "otuzbir",
                           "öküz", "öşex", "patlak zar", "penis", "pezevek", "pezeven", "pezeveng",
                           "pezevengi", "pezevengin evladı", "pezevenk", "pezo", "pic", "pici", "picler",
                           "piç", "piçin oğlu", "piç kurusu", "piçler", "pipi", "pipiş",
                           "pisliktir", "porno", "pussy", "puşt", "puşttur", "rahminde", "revizyonist",
                           "s1kerim", "s1kerm", "s1krm", "sakso", "saksofon", "salaak", "salak", "saxo", "sekis",
                           "serefsiz", "sevgi koyarım", "sevişelim", "sexs", "sıçarım",
                           "sıçtığım", "sıecem", "sicarsin", "sie", "sik", "sikdi",
                           "sikdiğim", "sike", "sikecem", "sikem", "siken", "sikenin", "siker", "sikerim",
                           "sikerler", "sikersin", "sikertir", "sikertmek", "sikesen", "sikesicenin", "sikey",
                           "sikeydim", "sikeyim", "sikeym", "siki", "sikicem", "sikici", "sikien", "sikienler",
                           "sikiiim", "sikiiimmm", "sikiim", "sikiir", "sikiirken", "sikik", "sikil", "sikildiini",
                           "sikilesice", "sikilmi", "sikilmiş", "sikmis", "sikilmiş", "sikilsin", "sikim",
                           "sikimde", "sikimden", "sikime", "sikimi", "sikimiin", "sikimin", "sikimle", "sikimsonik",
                           "sikimtrak", "sikin", "sikinde", "sikinden", "sikine", "sikini", "sikip", "sikis", "sikisek",
                           "sikisen", "sikish", "sikismis", "sikiş", "sikiş", "sikiş",
                           "sikişme", "sikitiin", "sikiyim", "sikiym", "sikiyorum", "sikkim", "sikko", "sikleri",
                           "sikleriii", "sikli", "sikm", "sikmek", "sikmem", "sikmiler", "sikmisligim", "siksem",
                           "sikseydin", "sikseyidin", "siksin", "siksinbaya", "siksinler", "siksiz", "siksok", "siksz",
                           "sikt", "sikti", "siktigimin", "siktigiminin", "siktiğim", "siktiğimin",
                           "siktiğiminin", "siktii", "siktiim", "siktiimin", "siktiiminin", "siktiler", "siktim",
                           "siktim", "siktimin", "siktiminin", "siktir", "siktir et", "siktirgit", "siktir git", "siktirir",
                           "siktiririm", "siktiriyor", "siktir lan", "siktirolgit", "siktir ol git", "sittimin", "sittir",
                           "skcem", "skecem", "skem", "sker", "skerim", "skerm", "skeyim", "skiim", "skik", "skim",
                           "skime", "skmek", "sksin", "sksn", "sksz", "sktiimin", "sktrr", "skyim", "slaleni", "sokam",
                           "sokarım", "sokarim", "sokarm", "sokarmkoduumun", "sokayım", "sokaym", "sokiim",
                           "soktuğumunun", "sokuk", "sokum", "sokuş", "sokuyum", "soxum", "sulaleni",
                           "süla", "sülalenizi", "sürtük", "şerefsiz", "şıllık", "taaklarn",
                           "taaklarna", "tarrakimin", "tasak", "tassak", "taşak", "taşşak",
                           "tipini s.k", "tipinizi s.keyim", "tiyniyat", "toplarm", "topsun", "totoş", "vajina",
                           "vajinanı", "veled", "veledizina", "veled i zina", "verdiimin", "weled", "weledizina",
                           "whore", "xikeyim", "yaaraaa", "yalama", "yalarım", "yalarun", "yaraaam", "yarak",
                           "yaraksız", "yaraktr", "yaram", "yaraminbasi", "yaramn", "yararmorospunun", "yarra",
                           "yarraaaa", "yarraak", "yarraam", "yarraami", "yarragi", "yarragimi", "yarragina",
                           "yarragindan", "yarragm", "yarrağ", "yarrağım", "yarrağımı",
                           "yarraimin", "yarrak", "yarram", "yarramin", "yarramın", "yarramn",
                           "yarran", "yarrana", "yarrrak", "yavak", "yavş", "yavşak", "yavşaktır",
                           "yavuşak", "yılışık", "yilisik", "yogurtlayam", "yoğurtlayam", "yrrak",
                           "zıkkımım", "zibidi", "zigsin", "zikeyim", "zikiiim", "zikiim", "zikik",
                           "zikim", "ziksiiin", "ziksiin", "zulliyetini", "zviyetini"]


class Moderation(commands.Cog):
    """
    Server moderation commands for managing users
    """
    
    def __init__(self, bot):
        self.bot = bot
        self.mongo_db = initialize_mongodb()

    async def check_profanity(self, message):
        content = message.content.lower()

        words = re.findall(r'\w+', content)

        for word in words:
            if word in TURKISH_PROFANITY_WORDS:
                return True
        return False

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author == self.bot.user:
            return

        record = self.mongo_db['filters'].find_one({"guild_id": message.guild.id})
        if record:
            try:
                if message.channel.id in record.get("only_image_channels", []):
                    if message.channel.id not in record.get("only_image_channels", []):
                        return
                    if not message.attachments:
                        await message.delete()
                        message = await message.channel.send(
                            embed=create_embed(f"{message.author.mention}, you can only share images in this channel!",
                                               discord.Colour.red()))
                        await asyncio.sleep(3)
                        await message.delete()
                    else:
                        for attachment in message.attachments:
                            if not attachment.filename.endswith((".png", ".jpg", ".jpeg", ".gif")):
                                await message.delete()
                                message = await message.channel.send(
                                    embed=create_embed(
                                        f"{message.author.mention}, you can only share images in this channel!",
                                        discord.Colour.red()))
                                await asyncio.sleep(3)
                                await message.delete()

                if message.channel.id in record.get("only_video_channels", []):
                    if message.channel.id not in record.get("only_video_channels", []):
                        return
                    if not check_video_url(message.content):
                        await message.delete()
                        message = await message.channel.send(embed=create_embed(
                            f"{message.author.mention}, you can only share videos in this channel!",
                            discord.Colour.red()))
                        await asyncio.sleep(3)
                        await message.delete()
                    if message.attachments:
                        for attachment in message.attachments:
                            if not attachment.filename.endswith((".mp4", ".mov", ".avi", ".mkv")):
                                await message.delete()
                                message = await message.channel.send(embed=create_embed(
                                    f"{message.author.mention}, you can only share videos in this channel!",
                                    discord.Colour.red()))
                                await asyncio.sleep(3)
                                await message.delete()

                if message.channel.id in record.get("only_link_channels", []):
                    if message.channel.id not in record.get("only_link_channels", []):
                        return

                    if message.content.startswith("https://"):
                        return

                    await message.delete()
                    message = await message.channel.send(
                        embed=create_embed(f"{message.author.mention}, you can only share links in this channel!",
                                           discord.Colour.red()))
                    await asyncio.sleep(3)
                    await message.delete()

                if record.get("profanity_filter_enabled", False):
                    if await self.check_profanity(message):
                        await message.delete()
                        message = await message.channel.send(
                            embed=create_embed(f"{message.author.mention} küfür etmek yasak!", discord.Colour.red()))
                        await asyncio.sleep(3)
                        await message.delete()

            except Exception as e:
                print(f"An error occurred: {e}")

    @commands.hybrid_command(name="kick", description="Kicks a member from the server.")
    @app_commands.describe(
        member="The member to kick from the server",
        reason="The reason for kicking the member"
    )
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx, member: discord.Member, *, reason="No reason provided"):
        """
        Kicks a member from the server with an optional reason.
        
        Requires the Kick Members permission. The kicked member can rejoin with a new invite.
        """
        if member.id == ctx.author.id:
            await ctx.send(embed=create_embed("You cannot kick yourself.", discord.Color.red()))
            return
        
        if member.top_role.position >= ctx.author.top_role.position and ctx.author.id != ctx.guild.owner_id:
            await ctx.send(embed=create_embed("You cannot kick someone with a higher or equal role.", discord.Color.red()))
            return
            
        try:
            await member.kick(reason=reason)
            await ctx.send(embed=create_embed(f"Successfully kicked {member.mention} for: {reason}", discord.Color.green()))
        except discord.Forbidden:
            await ctx.send(embed=create_embed("I don't have permission to kick that member.", discord.Color.red()))
        except Exception as e:
            await ctx.send(embed=create_embed(f"An error occurred: {str(e)}", discord.Color.red()))

    @commands.hybrid_command(name="ban", description="Bans a member from the server.")
    @app_commands.describe(
        member="The member to ban from the server",
        reason="The reason for banning the member"
    )
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx, member: discord.Member, *, reason="No reason provided"):
        """
        Bans a member from the server with an optional reason.
        
        Requires the Ban Members permission. The banned member cannot rejoin unless unbanned.
        """
        if member.id == ctx.author.id:
            await ctx.send(embed=create_embed("You cannot ban yourself.", discord.Color.red()))
            return
        
        if member.top_role.position >= ctx.author.top_role.position and ctx.author.id != ctx.guild.owner_id:
            await ctx.send(embed=create_embed("You cannot ban someone with a higher or equal role.", discord.Color.red()))
            return
            
        try:
            await member.ban(reason=reason)
            await ctx.send(embed=create_embed(f"Successfully banned {member.mention} for: {reason}", discord.Color.green()))
        except discord.Forbidden:
            await ctx.send(embed=create_embed("I don't have permission to ban that member.", discord.Color.red()))
        except Exception as e:
            await ctx.send(embed=create_embed(f"An error occurred: {str(e)}", discord.Color.red()))

    @commands.hybrid_command(name="unban", description="Unbans a previously banned user from the server.")
    @app_commands.describe(
        user_id="The ID of the user to unban",
        reason="The reason for unbanning the user"
    )
    @commands.has_permissions(ban_members=True)
    async def unban(self, ctx, user_id: int, *, reason="No reason provided"):
        """
        Unbans a previously banned user from the server using their user ID.
        
        Requires the Ban Members permission. Note that you need the user's ID, not their name.
        """
        try:
            user = await self.bot.fetch_user(user_id)
            await ctx.guild.unban(user, reason=reason)
            await ctx.send(embed=create_embed(f"Successfully unbanned {user.mention} ({user_id}) for: {reason}", discord.Color.green()))
        except discord.NotFound:
            await ctx.send(embed=create_embed(f"Could not find a user with ID: {user_id}", discord.Color.red()))
        except discord.Forbidden:
            await ctx.send(embed=create_embed("I don't have permission to unban users.", discord.Color.red()))
        except Exception as e:
            await ctx.send(embed=create_embed(f"An error occurred: {str(e)}", discord.Color.red()))

    @commands.hybrid_command(name="clear", description="Clears a specified number of messages from the channel.")
    @app_commands.describe(
        amount="The number of messages to delete (1-100)",
        user="Optional: Only delete messages from this user"
    )
    @commands.has_permissions(manage_messages=True)
    async def clear(self, ctx, amount: int, user: discord.Member = None):
        """
        Clears a specified number of messages from the current channel.
        
        Requires the Manage Messages permission. Can filter to delete only messages from a specific user.
        Limited to 1-100 messages at a time due to Discord API limitations.
        """
        if amount < 1 or amount > 100:
            await ctx.send(embed=create_embed("Please provide a number between 1 and 100.", discord.Color.red()))
            return
            
        await ctx.defer(ephemeral=True)
        
        try:
            def check(message):
                return user is None or message.author.id == user.id
                
            deleted = await ctx.channel.purge(limit=amount + 1, check=check)
            
            # Account for the command message that was also deleted
            count = len(deleted) - 1
            
            user_text = f" from {user.mention}" if user else ""
            await ctx.send(
                embed=create_embed(f"Successfully deleted {count} messages{user_text}.", discord.Color.green()),
                ephemeral=True
            )
        except discord.Forbidden:
            await ctx.send(embed=create_embed("I don't have permission to delete messages.", discord.Color.red()))
        except discord.HTTPException as e:
            await ctx.send(embed=create_embed(
                f"Error: {str(e)}\nMessages older than 14 days cannot be bulk deleted.",
                discord.Color.red()
            ))

    @commands.hybrid_command(name="set_nick", description="Sets a nickname for a member.")
    @app_commands.describe(
        member="The member to set the nickname for",
        nickname="The new nickname to set"
    )
    @commands.has_permissions(manage_nicknames=True)
    async def set_nick(self, ctx, member: discord.Member, *, nickname: str):
        """
        Sets a nickname for the specified member.
        
        Requires the Manage Nicknames permission. The nickname must be within Discord's length limits.
        """
        try:
            old_nick = member.display_name
            await member.edit(nick=nickname)
            await ctx.send(embed=create_embed(
                f"Changed {member.mention}'s nickname from '{old_nick}' to '{nickname}'",
                discord.Color.green()
            ))
        except discord.Forbidden:
            await ctx.send(embed=create_embed("I don't have permission to change that member's nickname.", discord.Color.red()))
        except discord.HTTPException as e:
            await ctx.send(embed=create_embed(f"Error: {str(e)}", discord.Color.red()))

    @commands.hybrid_command(name="reset_nick", description="Resets a member's nickname to their username.")
    @app_commands.describe(member="The member whose nickname to reset")
    @commands.has_permissions(manage_nicknames=True)
    async def reset_nick(self, ctx, member: discord.Member):
        """
        Resets a member's nickname to their original username.
        
        Requires the Manage Nicknames permission.
        """
        try:
            old_nick = member.display_name
            await member.edit(nick=None)
            await ctx.send(embed=create_embed(
                f"Reset {member.mention}'s nickname from '{old_nick}' to their username",
                discord.Color.green()
            ))
        except discord.Forbidden:
            await ctx.send(embed=create_embed("I don't have permission to change that member's nickname.", discord.Color.red()))
        except discord.HTTPException as e:
            await ctx.send(embed=create_embed(f"Error: {str(e)}", discord.Color.red()))

    @commands.hybrid_command(name="send_dm", description="Sends a direct message to members through the bot (max 10 members).")
    @app_commands.describe(
        message="The message to send to the members"
    )
    @commands.has_permissions(administrator=True)
    @commands.cooldown(1, 300, commands.BucketType.user)  # 5 minute cooldown
    async def send_dm(self, ctx, *, message: str):
        """Sends a direct message to members through the bot (max 10 members)."""
        # Create a modal for member selection
        modal = SendDMModal(self.bot, message)
        await ctx.send("Please select the members you want to send a DM to.", view=SendDMSelectView(self.bot, modal, ctx.author, message))

    @commands.hybrid_command(name="advertisements", description="Manage server advertisements")
    @commands.has_permissions(administrator=True)
    async def advertisements(self, ctx):
        """Manage server advertisements"""
        embed = discord.Embed(
            title="📢 Advertisement Management",
            description="Manage server advertisements and promotional settings.",
            color=discord.Color.blue()
        )
        embed.add_field(name="Available Options", value="Use the buttons below to configure advertisement settings.", inline=False)
        
        # This would be replaced with actual implementation
        await ctx.send(embed=embed, ephemeral=True)

    @commands.hybrid_command(name="edit_nicknames", description="Edit nicknames in bulk")
    @commands.has_permissions(manage_nicknames=True)
    async def edit_nicknames(self, ctx, role: discord.Role = None):
        """Edit nicknames in bulk for members with a specific role"""
        if role:
            members = [member for member in ctx.guild.members if role in member.roles]
        else:
            members = ctx.guild.members
            
        embed = discord.Embed(
            title="✏️ Bulk Nickname Editor",
            description=f"This will allow you to edit nicknames for {len(members)} members.",
            color=discord.Color.blue()
        )
        
        # This would be replaced with actual implementation
        await ctx.send(embed=embed, ephemeral=True)

    @commands.hybrid_command(name="reset_nicknames", description="Reset nicknames in bulk")
    @commands.has_permissions(manage_nicknames=True)
    async def reset_nicknames(self, ctx, role: discord.Role = None):
        """Reset nicknames in bulk for members with a specific role"""
        if role:
            members = [member for member in ctx.guild.members if role in member.roles]
        else:
            members = ctx.guild.members
            
        embed = discord.Embed(
            title="🔄 Bulk Nickname Reset",
            description=f"This will reset nicknames for {len(members)} members.",
            color=discord.Color.blue()
        )
        
        # This would be replaced with actual implementation
        await ctx.send(embed=embed, ephemeral=True)

    @commands.hybrid_command(name="give_everyone", description="Give everyone a specific role")
    @commands.has_permissions(administrator=True)
    async def give_everyone(self, ctx, role: discord.Role):
        """Give everyone a specific role"""
        embed = discord.Embed(
            title="👥 Mass Role Assignment",
            description=f"This will give the {role.mention} role to all members in the server.",
            color=discord.Color.blue()
        )
        embed.add_field(name="⚠️ Warning", value="This action can take a long time for servers with many members and may be rate limited by Discord.", inline=False)
        
        # Create confirmation view
        view = discord.ui.View(timeout=60)
        
        async def confirm_callback(interaction):
            if interaction.user != ctx.author:
                return await interaction.response.send_message("You cannot use this confirmation button.", ephemeral=True)
            
            await interaction.response.defer()
            
            # Create progress message
            progress_embed = discord.Embed(
                title="👥 Assigning Roles",
                description="Starting role assignment process...",
                color=discord.Color.blue()
            )
            progress_msg = await interaction.followup.send(embed=progress_embed)
            
            # Process members
            success_count = 0
            fail_count = 0
            total_members = len(ctx.guild.members)
            
            for i, member in enumerate(ctx.guild.members):
                try:
                    if role not in member.roles:
                        await member.add_roles(role)
                        success_count += 1
                except Exception as e:
                    fail_count += 1
                
                # Update progress every 10 members
                if i % 10 == 0 or i == total_members - 1:
                    progress = min(i + 1, total_members) / total_members
                    bar = '█' * int(progress * 10) + '░' * int(10 - progress * 10)
                    
                    progress_embed.description = f"Assigning roles: {i+1}/{total_members} members processed\n\n{bar} {progress:.1%}\n\n✅ Success: {success_count}\n❌ Failed: {fail_count}"
                    await progress_msg.edit(embed=progress_embed)
                    
                    # Add a small delay to avoid rate limits
                    await asyncio.sleep(0.5)
            
            final_embed = discord.Embed(
                title="👥 Role Assignment Complete",
                description=f"Role assignment process for {role.mention} has completed.",
                color=discord.Color.green()
            )
            final_embed.add_field(name="Results", value=f"✅ Success: {success_count}\n❌ Failed: {fail_count}", inline=False)
            
            await progress_msg.edit(embed=final_embed)
        
        async def cancel_callback(interaction):
            if interaction.user != ctx.author:
                return await interaction.response.send_message("You cannot use this cancellation button.", ephemeral=True)
            
            await interaction.message.delete()
        
        # Add buttons
        view.add_item(discord.ui.Button(label="Confirm", style=discord.ButtonStyle.success, custom_id="confirm"))
        view.add_item(discord.ui.Button(label="Cancel", style=discord.ButtonStyle.danger, custom_id="cancel"))
        
        # Set callbacks
        view.children[0].callback = confirm_callback
        view.children[1].callback = cancel_callback
        
        await ctx.send(embed=embed, view=view, ephemeral=True)
# SendDMModal ve SendDMSelectView sınıfları
class SendDMSelectView(discord.ui.View):
    """View for selecting members to send DMs to"""
    def __init__(self, bot, modal, author, message, timeout=180):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.modal = modal
        self.author = author
        self.message = message
        self.selected_members = []
        self.add_item(MemberSelectMenu(bot.users, self.selected_members))
    
    @discord.ui.button(label="Gönder", style=discord.ButtonStyle.success, row=1)
    async def send_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.selected_members or len(self.selected_members) == 0:
            return await interaction.response.send_message("Lütfen en az bir üye seçin.", ephemeral=True)
        
        if len(self.selected_members) > 10:
            return await interaction.response.send_message("En fazla 10 üyeye DM gönderebilirsiniz.", ephemeral=True)
        
        # Create the embed for DM
        embed = discord.Embed(
            title=f"{interaction.guild.name} sunucusundan mesaj",
            description=self.message,
            color=discord.Color.blue()
        )
        embed.set_footer(text=f"Gönderen: {self.author.name}", icon_url=self.author.display_avatar.url)
        
        # Create progress embed
        progress_embed = discord.Embed(
            title="DM Gönderimi",
            description="Mesaj gönderme işlemi başlatılıyor...",
            color=discord.Color.blue()
        )
        
        await interaction.response.send_message(embed=progress_embed, ephemeral=True)
        progress_msg = await interaction.original_response()
        
        # Send DMs with progress updates
        success_count = 0
        fail_count = 0
        total_members = len(self.selected_members)
        
        for i, member_id in enumerate(self.selected_members):
            try:
                member = await self.bot.fetch_user(member_id)
                await member.send(embed=embed)
                success_count += 1
                
                # Update progress
                progress = (i + 1) / total_members
                bar = '█' * int(progress * 10) + '░' * (10 - int(progress * 10))
                
                progress_embed.description = f"DM gönderiliyor: {i+1}/{total_members} üye\n\n{bar} {progress:.1%}\n\n✅ Başarılı: {success_count}\n❌ Başarısız: {fail_count}"
                await progress_msg.edit(embed=progress_embed)
                
                # Add delay to avoid rate limits
                await asyncio.sleep(1.5)
                
            except Exception as e:
                fail_count += 1
                progress_embed.description = f"DM gönderiliyor: {i+1}/{total_members} üye\n\n{bar} {progress:.1%}\n\n✅ Başarılı: {success_count}\n❌ Başarısız: {fail_count}"
                await progress_msg.edit(embed=progress_embed)
        
        # Final report
        final_embed = discord.Embed(
            title="DM Gönderimi Tamamlandı",
            description=f"Mesaj gönderme işlemi tamamlandı.",
            color=discord.Color.green() if success_count > 0 else discord.Color.red()
        )
        final_embed.add_field(name="Sonuçlar", value=f"✅ Başarılı: {success_count}\n❌ Başarısız: {fail_count}", inline=False)
        
        await progress_msg.edit(embed=final_embed)
        
    @discord.ui.button(label="İptal", style=discord.ButtonStyle.danger, row=1)
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("DM gönderme işlemi iptal edildi.", ephemeral=True)
        self.stop()


class MemberSelectMenu(discord.ui.Select):
    """Select menu for choosing members to send DMs to"""
    def __init__(self, users, selected_members):
        self.selected_members = selected_members
        
        # Get a reasonable sample of users
        sample_users = [user for user in users if not user.bot][:25]
        
        options = [
            discord.SelectOption(
                label=f"{user.name}",
                value=str(user.id),
                description=f"ID: {user.id}"
            ) for user in sample_users
        ]
        
        if not options:
            options = [discord.SelectOption(label="Üye bulunamadı", value="0")]
        
        super().__init__(
            placeholder="DM göndermek istediğiniz üyeleri seçin (maks. 10)",
            min_values=1,
            max_values=min(10, len(options)),
            options=options
        )
    
    async def callback(self, interaction: discord.Interaction):
        # Clear previous selections and add new ones
        self.selected_members.clear()
        for value in self.values:
            if value != "0":  # Skip the placeholder
                self.selected_members.append(int(value))
        
        await interaction.response.send_message(
            f"{len(self.selected_members)} üye seçildi. Mesaj göndermek için 'Gönder' butonuna tıklayın.", 
            ephemeral=True
        )


class SendDMModal(discord.ui.Modal, title="Send DM"):
    """Modal for entering DM content"""
    dm_content = discord.ui.TextInput(
        label="Mesaj İçeriği",
        style=discord.TextStyle.paragraph,
        placeholder="Göndermek istediğiniz mesajı yazın...",
        required=True,
        max_length=2000
    )
    
    def __init__(self, bot, message=None):
        super().__init__()
        self.bot = bot
        if message:
            self.dm_content.default = message
    
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            "Mesaj içeriği kaydedildi. Şimdi mesajı göndermek istediğiniz üyeleri seçin.",
            ephemeral=True,
            view=SendDMSelectView(self.bot, self, interaction.user, self.dm_content.value)
        )

async def setup(bot):
    await bot.add_cog(Moderation(bot))
