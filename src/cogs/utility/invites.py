import discord
from discord.ext import commands
import logging
import asyncio
from datetime import datetime
import time
from discord import app_commands

# Fix imports - replace utils with core modules
from utils.core.formatting import create_embed
from utils.database.connection import initialize_mongodb

# Set up logging
logger = logging.getLogger('invites')
logger.setLevel(logging.INFO)
handler = logging.FileHandler(filename='logs/invites.log', encoding='utf-8', mode='a')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

class InviteTracker(commands.Cog):
    """
    Track and manage server invites
    """
    
    def __init__(self, bot):
        self.bot = bot
        self.mongo_db = initialize_mongodb()
        self.invite_cache = {}
        self.bot.loop.create_task(self.initialize_invite_cache())
        logger.info("InviteTracker cog initialized")

    async def initialize_invite_cache(self):
        """Initialize the invite cache when the bot starts"""
        await self.bot.wait_until_ready()
        
        try:
            # Loop through all guilds and cache their invites
            for guild in self.bot.guilds:
                try:
                    # Only cache if the bot has the necessary permissions
                    if guild.me.guild_permissions.manage_guild:
                        self.invite_cache[guild.id] = {}
                        
                        # Fetch and cache all invites
                        invites = await guild.invites()
                        for invite in invites:
                            self.invite_cache[guild.id][invite.code] = {
                                'uses': invite.uses,
                                'creator': invite.inviter.id if invite.inviter else None,
                                'created_at': invite.created_at,
                                'max_uses': invite.max_uses,
                                'max_age': invite.max_age
                            }
                        
                        logger.info(f"Cached {len(invites)} invites for {guild.name} (ID: {guild.id})")
                    else:
                        logger.warning(f"Missing 'Manage Server' permission in {guild.name} (ID: {guild.id}), cannot cache invites")
                        
                except discord.Forbidden:
                    logger.error(f"Forbidden: Cannot fetch invites for {guild.name} (ID: {guild.id})")
                except discord.HTTPException as e:
                    logger.error(f"HTTP error when fetching invites for {guild.name} (ID: {guild.id}): {e}")
                except Exception as e:
                    logger.error(f"Unexpected error caching invites for {guild.name} (ID: {guild.id}): {e}")
                
                # Add a small delay to avoid rate limiting
                await asyncio.sleep(1)
                
        except Exception as e:
            logger.error(f"Error initializing invite cache: {e}")

    @commands.Cog.listener()
    async def on_invite_create(self, invite):
        """Track when a new invite is created"""
        try:
            if invite.guild.id not in self.invite_cache:
                self.invite_cache[invite.guild.id] = {}
                
            self.invite_cache[invite.guild.id][invite.code] = {
                'uses': invite.uses,
                'creator': invite.inviter.id if invite.inviter else None,
                'created_at': invite.created_at,
                'max_uses': invite.max_uses,
                'max_age': invite.max_age
            }
            
            logger.info(f"New invite created in {invite.guild.name} (ID: {invite.guild.id}): {invite.code}")
            
            # Store in database
            await self.mongo_db.invites.update_one(
                {"guild_id": invite.guild.id, "code": invite.code},
                {"$set": {
                    "uses": invite.uses,
                    "creator_id": invite.inviter.id if invite.inviter else None,
                    "created_at": invite.created_at,
                    "max_uses": invite.max_uses,
                    "max_age": invite.max_age,
                    "channel_id": invite.channel.id
                }},
                upsert=True
            )
            
        except Exception as e:
            logger.error(f"Error in on_invite_create: {e}")

    @commands.Cog.listener()
    async def on_invite_delete(self, invite):
        """Track when an invite is deleted"""
        try:
            if invite.guild.id in self.invite_cache and invite.code in self.invite_cache[invite.guild.id]:
                del self.invite_cache[invite.guild.id][invite.code]
                logger.info(f"Invite deleted in {invite.guild.name} (ID: {invite.guild.id}): {invite.code}")
                
                # Remove from database
                await self.mongo_db.invites.delete_one(
                    {"guild_id": invite.guild.id, "code": invite.code}
                )
                
        except Exception as e:
            logger.error(f"Error in on_invite_delete: {e}")

    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Detect which invite was used when a member joins"""
        if member.bot:
            logger.info(f"Bot {member.name}#{member.discriminator} joined {member.guild.name}, skipping invite tracking")
            return
            
        try:
            if not member.guild.me.guild_permissions.manage_guild:
                logger.warning(f"Missing 'Manage Server' permission in {member.guild.name}, cannot track invites")
                return
                
            # Wait a bit for Discord's invite cache to update
            await asyncio.sleep(1)
            
            # Get the invites after the member joined
            try:
                new_invites = await member.guild.invites()
            except (discord.Forbidden, discord.HTTPException) as e:
                logger.error(f"Could not fetch invites when {member} joined {member.guild.name}: {e}")
                return
                
            # If we don't have a cache for this guild yet, create it
            if member.guild.id not in self.invite_cache:
                self.invite_cache[member.guild.id] = {}
                for invite in new_invites:
                    self.invite_cache[member.guild.id][invite.code] = {
                        'uses': invite.uses - 1,  # Subtract 1 to account for the current join
                        'creator': invite.inviter.id if invite.inviter else None,
                        'created_at': invite.created_at,
                        'max_uses': invite.max_uses,
                        'max_age': invite.max_age
                    }
                logger.info(f"Created new invite cache for {member.guild.name} when {member} joined")
                return
            
            # Find which invite was used by comparing the cached uses to current uses
            used_invite = None
            invite_codes = list(self.invite_cache[member.guild.id].keys())
            
            for invite in new_invites:
                if invite.code not in self.invite_cache[member.guild.id]:
                    # This is a new invite created after we cached
                    continue
                    
                cached_uses = self.invite_cache[member.guild.id][invite.code]['uses']
                
                if invite.uses > cached_uses:
                    used_invite = invite
                    # Update the cache
                    self.invite_cache[member.guild.id][invite.code]['uses'] = invite.uses
                    break
            
            # Check for new invites we didn't have cached
            for invite in new_invites:
                if invite.code not in invite_codes:
                    self.invite_cache[member.guild.id][invite.code] = {
                        'uses': invite.uses,
                        'creator': invite.inviter.id if invite.inviter else None,
                        'created_at': invite.created_at,
                        'max_uses': invite.max_uses,
                        'max_age': invite.max_age
                    }
            
            # Update all invites in the cache
            for invite in new_invites:
                if invite.code in self.invite_cache[member.guild.id]:
                    self.invite_cache[member.guild.id][invite.code]['uses'] = invite.uses
            
            # Handle the used invite information
            if used_invite:
                inviter = used_invite.inviter
                logger.info(f"{member} joined {member.guild.name} using invite code {used_invite.code} created by {inviter}")
                
                # Store this join in the database
                await self.mongo_db.invite_joins.insert_one({
                    "guild_id": member.guild.id,
                    "member_id": member.id,
                    "member_name": f"{member.name}#{member.discriminator}",
                    "inviter_id": inviter.id if inviter else None,
                    "inviter_name": f"{inviter.name}#{inviter.discriminator}" if inviter else "Unknown",
                    "invite_code": used_invite.code,
                    "invite_uses": used_invite.uses,
                    "joined_at": datetime.utcnow(),
                })
                
                # Update inviter's stats
                if inviter:
                    await self.mongo_db.invite_stats.update_one(
                        {"guild_id": member.guild.id, "user_id": inviter.id},
                        {"$inc": {"total_invites": 1, "regular_invites": 1}},
                        upsert=True
                    )
                
                # Send welcome message if configured
                welcome_config = await self.mongo_db.welcome_config.find_one({"guild_id": member.guild.id})
                if welcome_config and welcome_config.get("invite_tracking_enabled", False):
                    welcome_channel = member.guild.get_channel(welcome_config.get("channel_id"))
                    if welcome_channel:
                        try:
                            invite_message = welcome_config.get("invite_message", "{member_mention} was invited by {inviter_name}")
                            formatted_message = invite_message.format(
                                member_mention=member.mention,
                                member_name=member.name,
                                inviter_name=f"{inviter.name}#{inviter.discriminator}" if inviter else "Unknown",
                                inviter_mention=inviter.mention if inviter else "Unknown",
                                invite_uses=used_invite.uses
                            )
                            
                            embed = discord.Embed(
                                description=formatted_message,
                                color=discord.Color.green()
                            )
                            await welcome_channel.send(embed=embed)
                        except Exception as e:
                            logger.error(f"Error sending invite tracking welcome message: {e}")
            else:
                # Couldn't determine which invite was used
                logger.warning(f"{member} joined {member.guild.name} but the invite used could not be determined")
                
        except Exception as e:
            logger.error(f"Error tracking invite for {member} in {member.guild.name}: {e}")

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        """Track when a member leaves to adjust invite statistics"""
        try:
            # Find if this member was invited by someone
            join_info = await self.mongo_db.invite_joins.find_one({
                "guild_id": member.guild.id,
                "member_id": member.id
            })
            
            if join_info and join_info.get("inviter_id"):
                inviter_id = join_info["inviter_id"]
                
                # Decrement the inviter's regular_invites count and increment left_invites count
                await self.mongo_db.invite_stats.update_one(
                    {"guild_id": member.guild.id, "user_id": inviter_id},
                    {"$inc": {"regular_invites": -1, "left_invites": 1}},
                    upsert=True
                )
                
                logger.info(f"{member} left {member.guild.name}. Invite stats updated for inviter ID: {inviter_id}")
                
        except Exception as e:
            logger.error(f"Error updating invite stats when {member} left {member.guild.name}: {e}")

    @commands.group(name="invites", invoke_without_command=True)
    async def invites(self, ctx, member: discord.Member = None):
        """Show invite statistics for a member or yourself"""
        try:
            target = member or ctx.author
            
            stats = await self.mongo_db.invite_stats.find_one({
                "guild_id": ctx.guild.id,
                "user_id": target.id
            })
            
            if not stats:
                stats = {
                    "total_invites": 0,
                    "regular_invites": 0,
                    "left_invites": 0,
                    "fake_invites": 0,
                    "bonus_invites": 0
                }
            
            total = stats.get("regular_invites", 0) + stats.get("bonus_invites", 0) - stats.get("left_invites", 0) - stats.get("fake_invites", 0)
            
            embed = discord.Embed(
                title=f"Invite Statistics for {target.name}",
                color=discord.Color.blue()
            )
            
            embed.add_field(name="Total Invites", value=str(total), inline=True)
            embed.add_field(name="Regular", value=str(stats.get("regular_invites", 0)), inline=True)
            embed.add_field(name="Bonus", value=str(stats.get("bonus_invites", 0)), inline=True)
            embed.add_field(name="Left", value=str(stats.get("left_invites", 0)), inline=True)
            embed.add_field(name="Fake", value=str(stats.get("fake_invites", 0)), inline=True)
            embed.add_field(name="‎", value="‎", inline=True)  # Empty field for formatting
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in invites command: {e}")
            await ctx.send(embed=create_embed("An error occurred while fetching invite statistics.", discord.Color.red()))

    @invites.command(name="leaderboard")
    async def invites_leaderboard(self, ctx):
        """Show the top inviters in the server"""
        try:
            # Get top 10 inviters
            cursor = self.mongo_db.invite_stats.find({"guild_id": ctx.guild.id}).sort("total_invites", -1).limit(10)
            
            leaderboard = []
            index = 1
            
            async for entry in cursor:
                user_id = entry.get("user_id")
                total = entry.get("regular_invites", 0) + entry.get("bonus_invites", 0) - entry.get("left_invites", 0) - entry.get("fake_invites", 0)
                
                member = ctx.guild.get_member(user_id)
                name = f"{member.name}#{member.discriminator}" if member else f"User ID: {user_id}"
                
                leaderboard.append(f"{index}. {name} - **{total}** invites")
                index += 1
            
            if leaderboard:
                embed = discord.Embed(
                    title="Invite Leaderboard",
                    description="\n".join(leaderboard),
                    color=discord.Color.gold()
                )
                await ctx.send(embed=embed)
            else:
                await ctx.send(embed=create_embed("No invite data found for this server.", discord.Color.blue()))
                
        except Exception as e:
            logger.error(f"Error in invites leaderboard command: {e}")
            await ctx.send(embed=create_embed("An error occurred while fetching the leaderboard.", discord.Color.red()))

    @invites.command(name="refresh")
    @commands.has_permissions(manage_guild=True)
    async def invites_refresh(self, ctx):
        """Manually refresh the invite cache for this server"""
        try:
            await ctx.send(embed=create_embed("Refreshing invite cache...", discord.Color.blue()))
            
            if not ctx.guild.me.guild_permissions.manage_guild:
                await ctx.send(embed=create_embed("I need the 'Manage Server' permission to refresh invites.", discord.Color.red()))
                return
                
            # Fetch fresh invites
            invites = await ctx.guild.invites()
            
            # Update the cache
            self.invite_cache[ctx.guild.id] = {}
            for invite in invites:
                self.invite_cache[ctx.guild.id][invite.code] = {
                    'uses': invite.uses,
                    'creator': invite.inviter.id if invite.inviter else None,
                    'created_at': invite.created_at,
                    'max_uses': invite.max_uses,
                    'max_age': invite.max_age
                }
                
            logger.info(f"Manually refreshed invite cache for {ctx.guild.name} ({len(invites)} invites)")
            await ctx.send(embed=create_embed(f"Successfully refreshed invite cache. Cached {len(invites)} invites.", discord.Color.green()))
            
        except discord.Forbidden:
            await ctx.send(embed=create_embed("I don't have permission to view invites.", discord.Color.red()))
        except Exception as e:
            logger.error(f"Error refreshing invite cache: {e}")
            await ctx.send(embed=create_embed("An error occurred while refreshing invites.", discord.Color.red()))

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        """Initialize invite tracking when the bot joins a new server"""
        try:
            if guild.me.guild_permissions.manage_guild:
                self.invite_cache[guild.id] = {}
                invites = await guild.invites()
                
                for invite in invites:
                    self.invite_cache[guild.id][invite.code] = {
                        'uses': invite.uses,
                        'creator': invite.inviter.id if invite.inviter else None,
                        'created_at': invite.created_at,
                        'max_uses': invite.max_uses,
                        'max_age': invite.max_age
                    }
                    
                logger.info(f"Initialized invite cache for new guild {guild.name} (ID: {guild.id}) with {len(invites)} invites")
        except Exception as e:
            logger.error(f"Failed to initialize invite cache for {guild.name} (ID: {guild.id}): {e}")


async def setup(bot):
    await bot.add_cog(InviteTracker(bot))
