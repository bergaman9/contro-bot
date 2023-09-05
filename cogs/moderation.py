import time

import discord
from discord.ext import commands

from discord import app_commands

import re
import asyncio

from utils import create_embed, initialize_mongodb, check_video_url

TURKISH_PROFANITY_WORDS = ["abaza","abazan","ag","a\u011fz\u0131na s\u0131\u00e7ay\u0131m","ahmak","allah","allahs\u0131z","am","amar\u0131m","ambiti","am biti","amc\u0131\u011f\u0131","amc\u0131\u011f\u0131n","amc\u0131\u011f\u0131n\u0131","amc\u0131\u011f\u0131n\u0131z\u0131","amc\u0131k","amc\u0131k ho\u015faf\u0131","amc\u0131klama","amc\u0131kland\u0131","amcik","amck","amckl","amcklama","amcklaryla","amckta","amcktan","amcuk","am\u0131k","am\u0131na","am\u0131nako","am\u0131na koy","am\u0131na koyar\u0131m","am\u0131na koyay\u0131m","am\u0131nakoyim","am\u0131na koyyim","am\u0131na s","am\u0131na sikem","am\u0131na sokam","am\u0131n feryad\u0131","am\u0131n\u0131","am\u0131n\u0131 s","am\u0131n oglu","am\u0131no\u011flu","am\u0131n o\u011flu","am\u0131s\u0131na","am\u0131s\u0131n\u0131","amina","amina g","amina k","aminako","aminakoyarim","amina koyarim","amina koyay\u0131m","amina koyayim","aminakoyim","aminda","amindan","amindayken","amini","aminiyarraaniskiim","aminoglu","amin oglu","amiyum","amk","amkafa","amk \u00e7ocu\u011fu","amlarnzn","aml\u0131","amm","ammak","ammna","amn","amna","amnda","amndaki","amngtn","amnn","amona","amq","ams\u0131z","amsiz","amsz","amteri","amugaa","amu\u011fa","amuna","ana","anaaann","anal","analarn","anam","anamla","anan","anana","anandan","anan\u0131","anan\u0131","anan\u0131n","anan\u0131n am","anan\u0131n am\u0131","anan\u0131n d\u00f6l\u00fc","anan\u0131nki","anan\u0131sikerim","anan\u0131 sikerim","anan\u0131sikeyim","anan\u0131 sikeyim","anan\u0131z\u0131n","anan\u0131z\u0131n am","anani","ananin","ananisikerim","anani sikerim","ananisikeyim","anani sikeyim","anann","ananz","anas","anas\u0131n\u0131","anas\u0131n\u0131n am","anas\u0131 orospu","anasi","anasinin","anay","anayin","angut","anneni","annenin","annesiz","anuna","aptal","aq","a.q","a.q.","aq.","ass","atkafas\u0131","atm\u0131k","att\u0131rd\u0131\u011f\u0131m","attrrm","auzlu","avrat","ayklarmalrmsikerim","azd\u0131m","azd\u0131r","azd\u0131r\u0131c\u0131","babaannesi ka\u015far","baban\u0131","baban\u0131n","babani","babas\u0131 pezevenk","baca\u011f\u0131na s\u0131\u00e7ay\u0131m","bac\u0131na","bac\u0131n\u0131","bac\u0131n\u0131n","bacini","bacn","bacndan","bacy","bastard","basur","beyinsiz","b\u0131z\u0131r","bitch","biting","bok","boka","bokbok","bok\u00e7a","bokhu","bokkkumu","boklar","boktan","boku","bokubokuna","bokum","bombok","boner","bosalmak","bo\u015falmak","cenabet","cibiliyetsiz","cibilliyetini","cibilliyetsiz","cif","cikar","cim","\u00e7\u00fck","dalaks\u0131z","dallama","daltassak","dalyarak","dalyarrak","dangalak","dassagi","diktim","dildo","dingil","dingilini","dinsiz","dkerim","domal","domalan","domald\u0131","domald\u0131n","domal\u0131k","domal\u0131yor","domalmak","domalm\u0131\u015f","domals\u0131n","domalt","domaltarak","domalt\u0131p","domalt\u0131r","domalt\u0131r\u0131m","domaltip","domaltmak","d\u00f6l\u00fc","d\u00f6nek","d\u00fcd\u00fck","eben","ebeni","ebenin","ebeninki","ebleh","ecdad\u0131n\u0131","ecdadini","embesil","emi","fahise","fahi\u015fe","feri\u015ftah","ferre","fuck","fucker","fuckin","fucking","gavad","gavat","geber","geberik","gebermek","gebermi\u015f","gebertir","ger\u0131zekal\u0131","gerizekal\u0131","gerizekali","gerzek","giberim","giberler","gibis","gibi\u015f","gibmek","gibtiler","goddamn","godo\u015f","godumun","gotelek","gotlalesi","gotlu","gotten","gotundeki","gotunden","gotune","gotunu","gotveren","goyiim","goyum","goyuyim","goyyim","g\u00f6t","g\u00f6t deli\u011fi","g\u00f6telek","g\u00f6t herif","g\u00f6tlalesi","g\u00f6tlek","g\u00f6to\u011flan\u0131","g\u00f6t o\u011flan\u0131","g\u00f6to\u015f","g\u00f6tten","g\u00f6t\u00fc","g\u00f6t\u00fcn","g\u00f6t\u00fcne","g\u00f6t\u00fcnekoyim","g\u00f6t\u00fcne koyim","g\u00f6t\u00fcn\u00fc","g\u00f6tveren","g\u00f6t veren","g\u00f6t verir","gtelek","gtn","gtnde","gtnden","gtne","gtten","gtveren","hasiktir","hassikome","hassiktir","has siktir","hassittir","haysiyetsiz","hayvan herif","ho\u015faf\u0131","h\u00f6d\u00fck","hsktr","huur","\u0131bnel\u0131k","ibina","ibine","ibinenin","ibne","ibnedir","ibneleri","ibnelik","ibnelri","ibneni","ibnenin","ibnerator","ibnesi","idiot","idiyot","imansz","ipne","iserim","i\u015ferim","ito\u011flu it","kafam girsin","kafas\u0131z","kafasiz","kahpe","kahpenin","kahpenin feryad\u0131","kaka","kaltak","kanc\u0131k","kancik","kappe","karhane","ka\u015far","kavat","kavatn","kaypak","kayyum","kerane","kerhane","kerhanelerde","kevase","keva\u015fe","kevvase","koca g\u00f6t","kodu\u011fmun","kodu\u011fmunun","kodumun","kodumunun","koduumun","koyarm","koyay\u0131m","koyiim","koyiiym","koyim","koyum","koyyim","krar","kukudaym","laciye boyad\u0131m","lavuk","libo\u015f","madafaka","mal","malafat","malak","manyak","mcik","meme","memelerini","mezveleli","minaamc\u0131k","mincikliyim","mna","monakkoluyum","motherfucker","mudik","oc","ocuu","ocuun","O\u00c7","o\u00e7","o. \u00e7ocu\u011fu","o\u011flan","o\u011flanc\u0131","o\u011flu it","orosbucocuu","orospu","orospucocugu","orospu cocugu","orospu \u00e7oc","orospu\u00e7ocu\u011fu","orospu \u00e7ocu\u011fu","orospu \u00e7ocu\u011fudur","orospu \u00e7ocuklar\u0131","orospudur","orospular","orospunun","orospunun evlad\u0131","orospuydu","orospuyuz","orostoban","orostopol","orrospu","oruspu","oruspu\u00e7ocu\u011fu","oruspu \u00e7ocu\u011fu","osbir","ossurduum","ossurmak","ossuruk","osur","osurduu","osuruk","osururum","otuzbir","\u00f6k\u00fcz","\u00f6\u015fex","patlak zar","penis","pezevek","pezeven","pezeveng","pezevengi","pezevengin evlad\u0131","pezevenk","pezo","pic","pici","picler","pi\u00e7","pi\u00e7in o\u011flu","pi\u00e7 kurusu","pi\u00e7ler","pipi","pipi\u015f","pisliktir","porno","pussy","pu\u015ft","pu\u015fttur","rahminde","revizyonist","s1kerim","s1kerm","s1krm","sakso","saksofon","salaak","salak","saxo","sekis","serefsiz","sevgi koyar\u0131m","sevi\u015felim","sexs","s\u0131\u00e7ar\u0131m","s\u0131\u00e7t\u0131\u011f\u0131m","s\u0131ecem","sicarsin","sie","sik","sikdi","sikdi\u011fim","sike","sikecem","sikem","siken","sikenin","siker","sikerim","sikerler","sikersin","sikertir","sikertmek","sikesen","sikesicenin","sikey","sikeydim","sikeyim","sikeym","siki","sikicem","sikici","sikien","sikienler","sikiiim","sikiiimmm","sikiim","sikiir","sikiirken","sikik","sikil","sikildiini","sikilesice","sikilmi","sikilmie","sikilmis","sikilmi\u015f","sikilsin","sikim","sikimde","sikimden","sikime","sikimi","sikimiin","sikimin","sikimle","sikimsonik","sikimtrak","sikin","sikinde","sikinden","sikine","sikini","sikip","sikis","sikisek","sikisen","sikish","sikismis","siki\u015f","siki\u015fen","siki\u015fme","sikitiin","sikiyim","sikiym","sikiyorum","sikkim","sikko","sikleri","sikleriii","sikli","sikm","sikmek","sikmem","sikmiler","sikmisligim","siksem","sikseydin","sikseyidin","siksin","siksinbaya","siksinler","siksiz","siksok","siksz","sikt","sikti","siktigimin","siktigiminin","sikti\u011fim","sikti\u011fimin","sikti\u011fiminin","siktii","siktiim","siktiimin","siktiiminin","siktiler","siktim","siktim","siktimin","siktiminin","siktir","siktir et","siktirgit","siktir git","siktirir","siktiririm","siktiriyor","siktir lan","siktirolgit","siktir ol git","sittimin","sittir","skcem","skecem","skem","sker","skerim","skerm","skeyim","skiim","skik","skim","skime","skmek","sksin","sksn","sksz","sktiimin","sktrr","skyim","slaleni","sokam","sokar\u0131m","sokarim","sokarm","sokarmkoduumun","sokay\u0131m","sokaym","sokiim","soktu\u011fumunun","sokuk","sokum","soku\u015f","sokuyum","soxum","sulaleni","s\u00fclaleni","s\u00fclalenizi","s\u00fcrt\u00fck","\u015ferefsiz","\u015f\u0131ll\u0131k","taaklarn","taaklarna","tarrakimin","tasak","tassak","ta\u015fak","ta\u015f\u015fak","tipini s.k","tipinizi s.keyim","tiyniyat","toplarm","topsun","toto\u015f","vajina","vajinan\u0131","veled","veledizina","veled i zina","verdiimin","weled","weledizina","whore","xikeyim","yaaraaa","yalama","yalar\u0131m","yalarun","yaraaam","yarak","yaraks\u0131z","yaraktr","yaram","yaraminbasi","yaramn","yararmorospunun","yarra","yarraaaa","yarraak","yarraam","yarraam\u0131","yarragi","yarragimi","yarragina","yarragindan","yarragm","yarra\u011f","yarra\u011f\u0131m","yarra\u011f\u0131m\u0131","yarraimin","yarrak","yarram","yarramin","yarraminba\u015f\u0131","yarramn","yarran","yarrana","yarrrak","yavak","yav\u015f","yav\u015fak","yav\u015fakt\u0131r","yavu\u015fak","y\u0131l\u0131\u015f\u0131k","yilisik","yogurtlayam","yo\u011furtlayam","yrrak","z\u0131kk\u0131m\u0131m","zibidi","zigsin","zikeyim","zikiiim","zikiim","zikik","zikim","ziksiiin","ziksiin","zulliyetini","zviyetini"]

class Moderation(commands.Cog):
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
                            embed=create_embed(f"{message.author.mention} bu kanalda sadece resim paylaşabilirsin!",
                                               discord.Colour.red()))
                        await asyncio.sleep(3)
                        await message.delete()
                    else:
                        for attachment in message.attachments:
                            if not attachment.filename.endswith((".png", ".jpg", ".jpeg", ".gif")):
                                await message.delete()
                                message = await message.channel.send(
                                    embed=create_embed(
                                        f"{message.author.mention} bu kanalda sadece resim paylaşabilirsin!",
                                        discord.Colour.red()))
                                await asyncio.sleep(3)
                                await message.delete()

                if message.channel.id in record.get("only_video_channels", []):
                    if message.channel.id not in record.get("only_video_channels", []):
                        return
                    if not check_video_url(message.content):
                        await message.delete()
                        message = await message.channel.send(embed=create_embed(
                            f"{message.author.mention} bu kanalda sadece video paylaşabilirsin!",
                            discord.Colour.red()))
                        await asyncio.sleep(3)
                        await message.delete()
                    if message.attachments:
                        for attachment in message.attachments:
                            if not attachment.filename.endswith((".mp4", ".mov", ".avi", ".mkv")):
                                await message.delete()
                                message = await message.channel.send(embed=create_embed(
                                    f"{message.author.mention} bu kanalda sadece video paylaşabilirsin!",
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
                        embed=create_embed(f"{message.author.mention} bu kanalda sadece link paylaşabilirsin!",
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





    @commands.hybrid_command(name="filter", description="Filter commands.", aliases=['filters'])
    @app_commands.describe(profanity="Enables or disables profanity filter.")
    @commands.has_permissions(manage_guild=True)
    async def filter(self, ctx, profanity: bool = None, only_link_channels: commands.Greedy[discord.TextChannel] = None,
                     only_image_channels: commands.Greedy[discord.TextChannel] = None, only_video_channels: commands.Greedy[discord.TextChannel] = None, reset: bool = False):

        if reset:
            self.mongo_db['filters'].delete_one({"guild_id": ctx.guild.id})
            return await ctx.send(embed=create_embed("Filters have been reset.", discord.Colour.green()))

        if profanity:
            self.mongo_db['filters'].update_one(
                {"guild_id": ctx.guild.id},
                {
                    "$set": {
                        "profanity_filter_enabled": True
                    }
                },
                upsert=True
            )
            await ctx.send(embed=create_embed("Profanity filter has been enabled.", discord.Colour.green()))

        if only_link_channels:
            self.mongo_db['filters'].update_one(
                {"guild_id": ctx.guild.id},
                {
                    "$set": {
                        "only_link_channels": [channel.id for channel in only_link_channels]
                    }
                },
                upsert=True
            )
            await ctx.send(embed=create_embed("Only link channels have been set.", discord.Colour.green()))

        if only_image_channels:
            self.mongo_db['filters'].update_one(
                {"guild_id": ctx.guild.id},
                {
                    "$set": {
                        "only_image_channels": [channel.id for channel in only_image_channels]
                    }
                },
                upsert=True
            )
            await ctx.send(embed=create_embed("Only image channels have been set.", discord.Colour.green()))

        if only_video_channels:
            self.mongo_db['filters'].update_one(
                {"guild_id": ctx.guild.id},
                {
                    "$set": {
                        "only_video_channels": [channel.id for channel in only_video_channels]
                    }
                },
                upsert=True
            )
            await ctx.send(embed=create_embed("Only video channels have been set.", discord.Colour.green()))


    @commands.hybrid_command(name="give_roles", description="Belirli rolleri üyelere verir.")
    @app_commands.describe(member="Rolleri verilecek üye.", roles="Verilecek roller.")
    async def give_roles(self, ctx, member: discord.Member, roles: commands.Greedy[discord.Role]):
        record = self.mongo_db['roles'].find_one({"guild_id": ctx.guild.id})

        if record is None:
            return await ctx.send(embed=create_embed("Verilebilecek rolleri ayarlamadınız.", discord.Colour.red()))

        requester_roles = [r.id for r in ctx.author.roles]
        allowed_givable_roles = []

        # Kullanıcının rollerini kontrol edip, hangi rolleri verebileceğini bul
        for role_id in requester_roles:
            allowed_givable_roles.extend(record["roles"].get(str(role_id), []))

        allowed_givable_roles = list(set(allowed_givable_roles))  # Tekrar eden rolleri kaldır

        roles_to_give = []
        for role in roles:
            if str(role.id) in allowed_givable_roles:
                roles_to_give.append(role)

        if not roles_to_give:
            return await ctx.send(embed=create_embed("Bu rolleri vermek için izniniz yok.", discord.Colour.red()))

        for role in roles_to_give:
            try:
                await member.add_roles(role)
                await ctx.send(embed=create_embed(f"{role.mention} rolü {member.mention} üyesine verildi.",
                                                  discord.Colour.green()))
            except discord.Forbidden:
                await ctx.send(
                    embed=create_embed(f"{role.mention} rolünü vermek için iznim yok.", discord.Colour.red()))

    @commands.hybrid_command(name="give_roles_settings", description="Rolleri verebilme ayarlarını yapar.")
    @app_commands.describe(for_role="Rolleri verebilecek rol.", allowed_givable_roles="Verilebilecek roller.")
    async def give_roles_settings(self, ctx, for_role: discord.Role,
                                  allowed_givable_roles: commands.Greedy[discord.Role]):
        if ctx.message.author.guild_permissions.manage_guild:

            record = self.mongo_db['roles'].find_one({"guild_id": ctx.guild.id})

            # Eğer yapı yoksa oluştur
            if record is None:
                self.mongo_db['roles'].insert_one({
                    "guild_id": ctx.guild.id,
                    "roles": {
                        str(for_role.id): [str(role.id) for role in allowed_givable_roles]
                    }
                })
            else:
                # Mevcut yapıyı güncelle
                record["roles"][str(for_role.id)] = [str(role.id) for role in allowed_givable_roles]
                self.mongo_db['roles'].update_one({"guild_id": ctx.guild.id}, {"$set": record})

            await ctx.send(embed=create_embed("Rolleri verebilme ayarları güncellendi.", discord.Colour.green()))
        else:
            await ctx.send(embed=create_embed("Bunu yapmaya iznin yok.", discord.Colour.red()))

    @commands.hybrid_command(name="give_roles_remove", description="Rolleri verebilme ayarlarını sıfırlar.")
    async def give_roles_remove(self, ctx):
        if ctx.message.author.guild_permissions.manage_guild:
            self.mongo_db['roles'].delete_one({"guild_id": ctx.guild.id})
            await ctx.send(embed=create_embed("Rolleri verebilme ayarları sıfırlandı.", discord.Colour.green()))
        else:
            await ctx.send(embed=create_embed("Bunu yapmaya iznin yok.", discord.Colour.red()))




    @commands.hybrid_command(name="kick", description="Kicks member from the guild.")
    @app_commands.describe(member="Member to kick.", reason="Reason for kick.")
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx, member: discord.Member, *, reason="None"):
        await member.kick(reason=reason)
        await ctx.send(embed=create_embed(description=member.mention + " has been kicked from Türk Oyuncu Topluluğu!", color=discord.Colour.red()))
        try:
            await member.send(embed=create_embed(description=f"You have been kicked from {member.guild.name}!", color=discord.Colour.red()))
        except:
            await ctx.send(embed=create_embed(description="The member has their dms closed.", color=discord.Colour.red()))


    @commands.hybrid_command(name="ban", description="Bans member from the guild.")
    @app_commands.describe(member="Member to ban.", reason="Reason for ban.")
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx, member: discord.Member, *, reason="None"):
        await member.ban(reason=reason)
        await ctx.send(embed=create_embed(description=member.mention + " has been banned!", color=discord.Colour.red()))
        try:
            await member.send(embed=create_embed(description=f"You have been banned from {member.guild.name}!", color=discord.Colour.red()))
        except:
            await ctx.send(embed=create_embed(description="The member has their dms closed.", color=discord.Colour.red()))


    @commands.hybrid_command(name="unban", description="Bans member from the guild.")
    @app_commands.describe(member="Member to unban.")
    @commands.has_permissions(ban_members=True)
    async def unban(self, ctx, *, member):

        banned_users = await ctx.guild.bans()

        member_name, member_discriminator = member.split('#')
        for ban_entry in banned_users:
            user = ban_entry.user

            if (user.name, user.discriminator) == (member_name, member_discriminator):
                await ctx.guild.unban(user)
                await ctx.channel.send(create_embed(description=f"{user.mention} has been unbanned!", color=discord.Colour.dark_gray()))

    @commands.hybrid_command(name="clear", description="Clear messages in a channel.", aliases=['purge'])
    @app_commands.describe(amount="Amount of messages to clear.")
    @commands.has_permissions(manage_messages=True)
    async def clear(self, ctx, amount:str):
        await ctx.channel.purge(limit = int(amount) + 1)
        message = await ctx.send(embed=create_embed(description=f"**{amount}** messages cleared!", color=discord.Colour.green()))
        time.sleep(3)
        await message.delete()

    @commands.hybrid_command(name="set_nick", description="Sets nick for a member.")
    @app_commands.describe(member="Member to set nick for.", nick="Nick to set.")
    @commands.has_permissions(manage_nicknames=True)
    async def set_nick(self, ctx, member: discord.Member, nick):
        await member.edit(nick=nick)
        await ctx.send(embed=create_embed(description=f"Nickname was set to {nick} for {member.mention}", color=discord.Colour.green()))

    @commands.hybrid_command(name="reset_nick", description="Resets nick for a member.")
    @app_commands.describe(member="Member to reset nick for.")
    @commands.has_permissions(manage_nicknames=True)
    async def reset_nick(self, ctx, member: discord.Member = None):
        await member.edit(nick=None)
        await ctx.send(embed=create_embed(description=f"Nickname was reset for {member.mention}", color=discord.Colour.green()))

    @commands.hybrid_command(name="send_dm", description="Sends a message to member.")
    @app_commands.describe(member="Member to send message to.", message="Message to send.")
    @commands.has_permissions(manage_nicknames=True)
    async def send_dm(self, ctx, member: discord.Member, *, message):
        await member.send(message)
        await ctx.send(embed=create_embed(description=f"Message was sent to {member.mention}", color=discord.Colour.green()))

async def setup(bot):
    await bot.add_cog(Moderation(bot))