import discord
from discord.ext import commands, tasks
from discord import app_commands
import asyncio
import logging
import random
from datetime import datetime
from typing import Optional, Dict, Any, List
from dateutil import parser

from src.utils.core.formatting import create_embed
from src.utils.database.connection import initialize_mongodb

logger = logging.getLogger('giveaways')
logger.setLevel(logging.INFO)
handler = logging.FileHandler(filename='logs/giveaways.log', encoding='utf-8', mode='a')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

# Persistent view for active giveaways
class GiveawayView(discord.ui.View):
    def __init__(self, cog, giveaway_data=None):
        super().__init__(timeout=None)
        self.cog = cog
        self.giveaway_data = giveaway_data
    
    @discord.ui.button(label="Join", style=discord.ButtonStyle.primary, custom_id="participate_button")
    async def participate_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.cog:
            await self.cog.handle_participate_button(interaction)
        else:
            await interaction.response.send_message(
                embed=create_embed("I cannot process this button right now. Please try again later.", discord.Color.red()),
                ephemeral=True
            )
    
    @discord.ui.button(label="Participants", style=discord.ButtonStyle.secondary, custom_id="participants_button")
    async def participants_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.cog:
            await self.cog.handle_participants_button(interaction)
        else:
            await interaction.response.send_message(
                embed=create_embed("I cannot process this button right now. Please try again later.", discord.Color.red()),
                ephemeral=True
            )
    
    @discord.ui.button(label="End Giveaway", style=discord.ButtonStyle.danger, custom_id="reroll_button")
    async def reroll_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.cog:
            await self.cog.handle_reroll_button(interaction)
        else:
            await interaction.response.send_message(
                embed=create_embed("I cannot process this button right now. Please try again later.", discord.Color.red()),
                ephemeral=True
            )

# Persistent view for completed giveaways
class GiveawayEditView(discord.ui.View):
    def __init__(self, cog):
        super().__init__(timeout=None)
        self.cog = cog
    
    @discord.ui.button(label="Participants", style=discord.ButtonStyle.secondary, custom_id="participants_button")
    async def participants_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.cog:
            await self.cog.handle_participants_button(interaction)
        else:
            await interaction.response.send_message(
                embed=create_embed("I cannot process this button right now. Please try again later.", discord.Color.red()),
                ephemeral=True
            )
    
    @discord.ui.button(label="Active Giveaways", style=discord.ButtonStyle.secondary, custom_id="active_giveaways_button")
    async def active_giveaways_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.cog:
            await self.cog.active_giveaways_handler(interaction)
        else:
            await interaction.response.send_message(
                embed=create_embed("I cannot process this button right now. Please try again later.", discord.Color.red()),
                ephemeral=True
            )
    
    @discord.ui.button(label="Reroll Giveaway", style=discord.ButtonStyle.danger, custom_id="reroll_button")
    async def reroll_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.cog:
            await self.cog.handle_reroll_button(interaction)
        else:
            await interaction.response.send_message(
                embed=create_embed("I cannot process this button right now. Please try again later.", discord.Color.red()),
                ephemeral=True
            )

class Giveaways(commands.Cog):
    """
    Create and manage giveaways in your server
    """
    
    def __init__(self, bot):
        self.bot = bot
        self.mongo_db = initialize_mongodb()
        self.giveaway_cache = {}  # Cache for active giveaways
        self.cache_ttl = 300  # 5 minutes cache TTL
        self.last_cache_update = {}
        self.cleanup_task.start()
        self.check_new_giveaways.start()
        
        # Add persistent views
        self.bot.add_view(GiveawayView(self))
        self.bot.add_view(GiveawayEditView(self))

    # Define the giveaway command group as a decorator
    @commands.group(
        name="giveaway",
        description="Create and manage giveaways in your server"
    )
    async def giveaway_group(self, ctx):
        """Command group for giveaway related commands"""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    def cog_unload(self):
        """Clean up resources when cog is unloaded"""
        self.cleanup_task.cancel()
        self.giveaway_cache.clear()
        logger.info("Giveaways cog unloaded")

    @tasks.loop(minutes=30)
    async def cleanup_task(self):
        """Clean up expired giveaways and refresh the cache"""
        try:
            now = datetime.now().timestamp()
            # Clear expired cache entries
            expired_keys = [k for k, v in self.last_cache_update.items() 
                          if now - v > self.cache_ttl]
            
            for key in expired_keys:
                self.giveaway_cache.pop(key, None)
                self.last_cache_update.pop(key, None)
                
            logger.info(f"Cleaned up {len(expired_keys)} expired cache entries")
        except Exception as e:
            logger.error(f"Error in cleanup task: {e}")

    @tasks.loop(seconds=10)
    async def check_new_giveaways(self):
        # Find giveaways with no message_id
        giveaways = list(self.mongo_db['giveaways'].find({"message_id": None}))
        for giveaway in giveaways:
            try:
                # Skip if message_id is already set (extra safety)
                if giveaway.get('message_id'):
                    continue
                # Parse end_time to int (ms)
                end_time = giveaway.get('end_time')
                if isinstance(end_time, str):
                    end_time = int(parser.isoparse(end_time).timestamp() * 1000)
                elif isinstance(end_time, float):
                    end_time = int(end_time)
                channel_id = int(giveaway['channel_id'])
                channel = self.bot.get_channel(channel_id)
                if not channel:
                    self.bot.logger.warning(f"Channel {channel_id} not found for giveaway {giveaway['_id']}")
                    continue
                embed = discord.Embed(
                    title=f"🎉 {giveaway['title']}",
                    description=giveaway.get('description', ''),
                    color=int(giveaway.get('embed_color', '#FF6B9D').replace('#', ''), 16)
                )
                embed.add_field(name="🏆 Prize", value=giveaway['prize'], inline=False)
                embed.add_field(name="👥 Winners", value=str(giveaway.get('winner_count', 1)), inline=True)
                # end_time is ms, convert to seconds for Discord timestamp
                if end_time > 1e12:  # ms
                    end_time = end_time // 1000
                embed.add_field(name="⏰ Ends", value=f"<t:{end_time}:R>", inline=True)
                embed.add_field(name="🎯 Participants", value="0", inline=True)
                embed.set_footer(text=f"Giveaway ID: {giveaway['_id']}")
                view = GiveawayView(self)
                message = await channel.send(embed=embed, view=view)
                # Mesaj gönderildikten sonra message_id'yi güncelle
                self.mongo_db['giveaways'].update_one(
                    {'_id': giveaway['_id']},
                    {'$set': {'message_id': str(message.id)}}
                )
                logger.info(f"Created Discord message for giveaway {giveaway['_id']}: {message.id}")
            except Exception as e:
                logger.error(f"Failed to send Discord message for giveaway {giveaway['_id']}: {e}")

    async def get_giveaway_data(self, message_id: int) -> Optional[Dict[str, Any]]:
        """Get giveaway data with caching"""
        cache_key = f"giveaway_{message_id}"
        now = datetime.now().timestamp()
        
        # Return from cache if available and not expired
        if cache_key in self.giveaway_cache and now - self.last_cache_update.get(cache_key, 0) < self.cache_ttl:
            return self.giveaway_cache[cache_key]
            
        # Fetch from database (try both int and string message_id)
        giveaway_data = self.mongo_db['giveaways'].find_one({
            "$or": [
                {"message_id": message_id},
                {"message_id": str(message_id)}
            ]
        })
        
        # Update cache
        if giveaway_data:
            self.giveaway_cache[cache_key] = giveaway_data
            self.last_cache_update[cache_key] = now
        
        return giveaway_data

    async def invalidate_cache(self, message_id: int) -> None:
        """Invalidate cache for a specific giveaway"""
        cache_key = f"giveaway_{message_id}"
        self.giveaway_cache.pop(cache_key, None)
        self.last_cache_update.pop(cache_key, None)

    @giveaway_group.command(
        name="create", 
        description="Create a new giveaway with customizable settings"
    )
    @commands.has_permissions(manage_guild=True)
    async def giveaway_create(self, ctx, limit: int, prize: str, roles: Optional[str] = None):
        """Creates a new giveaway with customizable settings"""
        # Convert ctx to interaction-like object for consistency
        interaction = ctx.interaction if hasattr(ctx, 'interaction') and ctx.interaction else ctx
        
        try:
            # Validate inputs
            if limit <= 0:
                await ctx.send(
                    embed=create_embed("Participant limit must be a positive number.", discord.Color.red())
                )
                return
                
            # Parse roles if provided
            role_mentions = []
            role_ids = []
            
            if roles:
                # Try to parse role mentions or names
                guild_roles = ctx.guild.roles
                for role_name in roles.split():
                    # Remove <@& and > if it's a mention
                    if role_name.startswith("<@&") and role_name.endswith(">"):
                        role_id = int(role_name[3:-1])
                        role = ctx.guild.get_role(role_id)
                        if role:
                            role_mentions.append(role.mention)
                            role_ids.append(role.id)
                    else:
                        # Try to find by name
                        role = discord.utils.get(guild_roles, name=role_name)
                        if role:
                            role_mentions.append(role.mention)
                            role_ids.append(role.id)
            
            # Create the giveaway embed
            embed = discord.Embed(
                title=prize,
                description=f"Click the join button to participate! \nThe giveaway will end when **{limit}** people join.", 
                colour=0xff0076
            )
            embed.add_field(name="Host", value=ctx.author.mention, inline=True)
            
            # Handle role restrictions
            if role_mentions:
                embed.add_field(name="Eligible Roles", value=' '.join(role_mentions), inline=True)
            else:
                embed.add_field(name="Eligible Roles", value="@everyone", inline=True)
                
            embed.add_field(name="Winners", value="1", inline=True)
            embed.set_image(url="https://i.ibb.co/8Kn0L6t/giveaway-banner.png")
            
            # Create the persistent view
            view = GiveawayView(self)
            
            # Send the giveaway message
            message = await ctx.send(embed=embed, view=view)
            
            # Update embed with footer
            embed.set_footer(text=f"Giveaway ID: {message.id}")
            await message.edit(embed=embed)
            
            # Store giveaway information in database
            giveaway_data = {
                "guild_id": ctx.guild.id,
                "message_id": message.id,
                "channel_id": ctx.channel.id,
                "prize": prize,
                "limit": limit,
                "status": True,
                "created_at": datetime.now().timestamp(),
                "created_by": ctx.author.id,
                "winner": None,
                "participants": [],
                "allowed_roles": role_ids
            }
            self.mongo_db['giveaways'].insert_one(giveaway_data)
            
            # Update cache
            cache_key = f"giveaway_{message.id}"
            self.giveaway_cache[cache_key] = giveaway_data
            self.last_cache_update[cache_key] = datetime.now().timestamp()
            
            logger.info(f"Giveaway created by {ctx.author} (ID: {ctx.author.id}) with prize: {prize}")
            
        except Exception as e:
            logger.error(f"Error creating giveaway: {e}")
            await ctx.send(embed=create_embed("An error occurred while creating the giveaway.", discord.Color.red()))

    @giveaway_group.command(
        name="shuffle", 
        description="Shuffle giveaway participants and select a new winner"
    )
    @commands.has_permissions(ban_members=True)
    async def giveaway_shuffle(self, ctx, message_id: str):
        """Shuffles giveaway participants and selects a new winner"""
        try:
            # Validate message ID
            try:
                message_id_int = int(message_id)
            except ValueError:
                await ctx.send(embed=create_embed("Invalid message ID.", discord.Color.red()))
                return

            # Get giveaway data from cache or database
            giveaway_data = await self.get_giveaway_data(message_id_int)

            if not giveaway_data:
                await ctx.send(embed=create_embed("Invalid giveaway ID.", discord.Color.red()))
                return
                
            participants_list = giveaway_data.get("participants", [])

            if not participants_list:
                await ctx.send(embed=create_embed("No participants in this giveaway.", discord.Color.red()))
                return
                
            # Select a new winner randomly
            selected_user_id = random.choice(participants_list)
            selected_user = await self.bot.fetch_user(selected_user_id)

            # Update the winner in the database
            self.mongo_db['giveaways'].update_one(
                {"message_id": message_id_int},
                {"$set": {"winner": selected_user_id}}
            )
            
            # Invalidate cache
            await self.invalidate_cache(message_id_int)
            
            # Create success embed
            embed = discord.Embed(
                description=f"🎉 {selected_user.mention} is the new winner of the giveaway!",
                color=0xff0076
            )
            
            await ctx.send(embed=embed)
            logger.info(f"Giveaway {message_id} shuffled by {ctx.author} (ID: {ctx.author.id}), new winner: {selected_user}")
            
        except Exception as e:
            logger.error(f"Error in giveaway_shuffle: {e}")
            await ctx.send(embed=create_embed("An error occurred while reshuffling the giveaway.", discord.Color.red()))

    @giveaway_group.command(
        name="show", 
        description="Show active giveaways on the server"
    )
    @commands.has_permissions(ban_members=True)
    async def giveaway_show(self, ctx):
        """Displays a list of all currently active giveaways on the server"""
        await self.active_giveaways_handler(ctx)

    @giveaway_group.command(
        name="remove", 
        description="Remove a giveaway from the server"
    )
    @commands.has_permissions(ban_members=True)
    async def giveaway_remove(self, ctx, message_id: str):
        """Permanently removes a giveaway from the server"""
        try:
            message_id_int = int(message_id)
            giveaway_data = await self.get_giveaway_data(message_id_int)
            
            if not giveaway_data:
                await ctx.send(embed=create_embed("Giveaway not found.", discord.Color.red()))
                return
                
            # Delete from database
            self.mongo_db['giveaways'].delete_one({"message_id": message_id_int})
            
            # Invalidate cache
            await self.invalidate_cache(message_id_int)
            
            await ctx.send(embed=create_embed("Giveaway deleted.", discord.Color.green()))
            logger.info(f"Giveaway {message_id} removed by {ctx.author} (ID: {ctx.author.id})")
            
        except ValueError:
            await ctx.send(embed=create_embed("Invalid message ID.", discord.Color.red()))
        except Exception as e:
            logger.error(f"Error removing giveaway: {e}")
            await ctx.send(embed=create_embed("An error occurred while deleting the giveaway.", discord.Color.red()))

    async def active_giveaways_handler(self, ctx_or_interaction):
        """Handles displaying active giveaways"""
        try:
            # Handle both ctx and interaction
            if hasattr(ctx_or_interaction, 'guild'):
                guild = ctx_or_interaction.guild
                send_func = ctx_or_interaction.send
            else:
                guild = ctx_or_interaction.guild
                send_func = ctx_or_interaction.response.send_message

            # Query active giveaways
            active_giveaways = list(self.mongo_db['giveaways'].find(
                {"guild_id": guild.id, "status": True}
            ))
            
            # Format the active giveaways list
            active_giveaways_list = [
                f"[{giveaway['prize'].title()} Giveaway]"
                f"(https://discord.com/channels/{guild.id}/{giveaway['channel_id']}/{giveaway['message_id']})"
                for giveaway in active_giveaways
            ]

            if not active_giveaways_list:
                embed = discord.Embed(
                    title="Active Giveaways", 
                    description="No active giveaways.",
                    color=discord.Color.blue()
                )
            else:
                embed = discord.Embed(
                    title="Active Giveaways", 
                    description='\n'.join(active_giveaways_list),
                    color=discord.Color.green()
                )
                
            await send_func(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in active_giveaways_handler: {e}")
            try:
                await ctx_or_interaction.send(
                    embed=create_embed("An error occurred while listing active giveaways.", discord.Color.red())
                )
            except:
                pass

    async def select_winner(self, participants: List[int], channel_id: int, message_id: int, prize: str):
        """Helper method to select a winner and update the giveaway"""
        try:
            if not participants:
                return None, "no_participants"
                
            # Select random winner
            selected_user_id = random.choice(participants)
            selected_user = self.bot.get_user(selected_user_id)
            
            if not selected_user:
                selected_user = await self.bot.fetch_user(selected_user_id)
                
            # Update database
            self.mongo_db['giveaways'].update_one(
                {"message_id": message_id},
                {"$set": {"status": False, "winner": selected_user_id}}
            )
            
            # Invalidate cache
            await self.invalidate_cache(message_id)
            
            return selected_user, "success"
            
        except Exception as e:
            logger.error(f"Error selecting winner: {e}")
            return None, "error"

    async def handle_participate_button(self, interaction: discord.Interaction):
        """Handle participation button clicks"""
        # Get the giveaway data
        giveaway_data = await self.get_giveaway_data(interaction.message.id)
        if not giveaway_data:
            await interaction.response.send_message(
                embed=create_embed("This giveaway is no longer available.", discord.Color.red()),
                ephemeral=True
            )
            return
            
        guild = self.bot.get_guild(interaction.guild_id)
        member = guild.get_member(interaction.user.id)
        
        # Check allowed roles
        allowed_roles = giveaway_data.get("allowed_roles", [])
        can_participate = not allowed_roles or any(role.id in allowed_roles for role in member.roles)
        
        if not can_participate:
            await interaction.response.send_message(
                embed=create_embed("You cannot participate in this giveaway.", discord.Color.red()),
                ephemeral=True
            )
            return
            
        # Extract giveaway data
        limit = int(giveaway_data["limit"])
        prize = giveaway_data["prize"]
        status = giveaway_data["status"]
        participants_list = giveaway_data["participants"]
        
        # Check if already participating
        if member.id in participants_list:
            await interaction.response.send_message(
                embed=create_embed("You have already joined this giveaway.", discord.Color.red()),
                ephemeral=True
            )
            return
            
        # Check if giveaway is still active
        if not status:
            await interaction.response.send_message(
                embed=create_embed("This giveaway is not active!", discord.Color.red()),
                ephemeral=True
            )
            return
            
        # Add user to participants
        participants_list.append(member.id)
        
        # Update database
        self.mongo_db['giveaways'].update_one(
            {"message_id": interaction.message.id},
            {"$set": {"participants": participants_list}}
        )
        
        # Invalidate cache
        await self.invalidate_cache(interaction.message.id)
        
        # Send confirmation
        await interaction.response.send_message(
            embed=create_embed("You joined the giveaway.", discord.Color.green()),
            ephemeral=True
        )
        
        # Check if participant limit reached
        if len(participants_list) >= limit:
            selected_user, result = await self.select_winner(
                participants_list, 
                interaction.channel_id,
                interaction.message.id,
                prize
            )
            
            if result == "success":
                channel = self.bot.get_channel(interaction.channel_id)
                
                # Announce winner
                await channel.send(embed=create_embed(
                    f"🎉 Congratulations {selected_user.mention}! You won **{prize}**!",
                    0xff0076
                ))
                
                # Try to DM the winner
                try:
                    await selected_user.send(embed=create_embed(
                        f"🎉 Congratulations {selected_user.mention}! You won **{prize}**!",
                        0xff0076
                    ))
                except:
                    logger.warning(f"Could not DM winner {selected_user.id}")
                
                # Update giveaway message
                message = await channel.fetch_message(interaction.message.id)
                embed = discord.Embed(
                    title=prize, 
                    description="Giveaway completed, thanks to everyone who participated!", 
                    colour=0xff0076
                )
                
                # Copy fields from original embed
                embed.add_field(name="Host", value=message.embeds[0].fields[0].value, inline=True)
                embed.add_field(name="Eligible Roles", value=message.embeds[0].fields[1].value, inline=True)
                embed.add_field(name="Winner", value=selected_user.mention, inline=True)
                embed.set_image(url="https://i.ibb.co/8Kn0L6t/giveaway-banner.png")
                
                await message.edit(embed=embed, view=GiveawayEditView(self))

    async def handle_participants_button(self, interaction: discord.Interaction):
        """Handle participants button clicks"""
        giveaway_data = await self.get_giveaway_data(interaction.message.id)
        if not giveaway_data:
            await interaction.response.send_message(
                embed=create_embed("Giveaway not found.", discord.Color.red()),
                ephemeral=True
            )
            return
            
        participants_list = giveaway_data["participants"]
        
        # Get user objects for all participants
        participants = []
        for user_id in participants_list:
            user = self.bot.get_user(user_id)
            if user:
                participants.append(f"{user.mention}")
        
        if not participants:
            participants = ["No one has joined the giveaway yet."]
            
        # Send participants list
        embed = discord.Embed(
            title="Giveaway Participants", 
            description="\n".join(participants), 
            color=discord.Color.green()
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def handle_reroll_button(self, interaction: discord.Interaction):
        """Handle reroll button clicks"""
        guild = self.bot.get_guild(interaction.guild_id)
        member = guild.get_member(interaction.user.id)
        
        # Check permissions
        if not member.guild_permissions.ban_members:
            await interaction.response.send_message(
                embed=create_embed("You don't have permission to reroll this giveaway.", discord.Color.red()),
                ephemeral=True
            )
            return
            
        giveaway_data = await self.get_giveaway_data(interaction.message.id)
        if not giveaway_data:
            await interaction.response.send_message(
                embed=create_embed("Giveaway not found.", discord.Color.red()),
                ephemeral=True
            )
            return
            
        participants_list = giveaway_data["participants"]
        
        # Select new winner
        selected_user, result = await self.select_winner(
            participants_list, 
            interaction.channel_id,
            interaction.message.id,
            giveaway_data["prize"]
        )
        
        if result == "no_participants":
            await interaction.response.send_message(
                embed=create_embed("No participants in this giveaway.", discord.Color.red()),
                ephemeral=True
            )
            return
            
        if result == "error":
            await interaction.response.send_message(
                embed=create_embed("An error occurred while rerolling the giveaway.", discord.Color.red()),
                ephemeral=True
            )
            return
            
        # Announce new winner
        channel = self.bot.get_channel(interaction.channel_id)
        await channel.send(embed=create_embed(
            f"🎉 {selected_user.mention} is the new winner of the giveaway!",
            0xff0076
        ))
        
        # Try to DM the winner
        try:
            await selected_user.send(embed=create_embed(
                f"🎉 Congratulations {selected_user.mention}! You won **{giveaway_data['prize']}**!",
                0xff0076
            ))
        except:
            logger.warning(f"Could not DM winner {selected_user.id}")
        
        # Update giveaway message
        message = await channel.fetch_message(interaction.message.id)
        embed = discord.Embed(
            title=giveaway_data['prize'], 
            description="Giveaway completed, thanks to everyone who participated!", 
            colour=0xff0076
        )
        
        # Copy fields from original embed
        embed.add_field(name="Host", value=message.embeds[0].fields[0].value, inline=True)
        embed.add_field(name="Eligible Roles", value=message.embeds[0].fields[1].value, inline=True)
        embed.add_field(name="Winner", value=selected_user.mention, inline=True)
        embed.set_image(url="https://i.ibb.co/8Kn0L6t/giveaway-banner.png")
        
        await message.edit(embed=embed, view=GiveawayEditView(self))
        
        await interaction.response.send_message(
            embed=create_embed("Giveaway rerolled.", discord.Color.green()),
            ephemeral=True
        )

    async def end_giveaway_handler(self, ctx_or_interaction, message_id: str):
        """Handle ending a giveaway manually"""
        try:
            message_id_int = int(message_id)
            giveaway_data = await self.get_giveaway_data(message_id_int)
            
            if not giveaway_data:
                if hasattr(ctx_or_interaction, 'response'):
                    await ctx_or_interaction.response.send_message(
                        embed=create_embed("Giveaway not found.", discord.Color.red()),
                        ephemeral=True
                    )
                else:
                    await ctx_or_interaction.send(embed=create_embed("Giveaway not found.", discord.Color.red()))
                return
                
            participants_list = giveaway_data.get("participants", [])
            
            if not participants_list:
                if hasattr(ctx_or_interaction, 'response'):
                    await ctx_or_interaction.response.send_message(
                        embed=create_embed("No participants in this giveaway.", discord.Color.red()),
                        ephemeral=True
                    )
                else:
                    await ctx_or_interaction.send(embed=create_embed("No participants in this giveaway.", discord.Color.red()))
                return
                
            # Select winner and end giveaway
            selected_user, result = await self.select_winner(
                participants_list,
                giveaway_data['channel_id'],
                message_id_int,
                giveaway_data['prize']
            )
            
            if result == "success":
                if hasattr(ctx_or_interaction, 'response'):
                    await ctx_or_interaction.response.send_message(
                        embed=create_embed(f"Giveaway ended! Winner: {selected_user.mention}", discord.Color.green()),
                        ephemeral=True
                    )
                else:
                    await ctx_or_interaction.send(embed=create_embed(f"Giveaway ended! Winner: {selected_user.mention}", discord.Color.green()))
            else:
                if hasattr(ctx_or_interaction, 'response'):
                    await ctx_or_interaction.response.send_message(
                        embed=create_embed("An error occurred while ending the giveaway.", discord.Color.red()),
                        ephemeral=True
                    )
                else:
                    await ctx_or_interaction.send(embed=create_embed("An error occurred while ending the giveaway.", discord.Color.red()))
                    
        except ValueError:
            error_msg = embed=create_embed("Invalid message ID.", discord.Color.red())
            if hasattr(ctx_or_interaction, 'response'):
                await ctx_or_interaction.response.send_message(error_msg, ephemeral=True)
            else:
                await ctx_or_interaction.send(error_msg)
        except Exception as e:
            logger.error(f"Error ending giveaway: {e}")
            error_msg = embed=create_embed("An error occurred while ending the giveaway.", discord.Color.red())
            if hasattr(ctx_or_interaction, 'response'):
                await ctx_or_interaction.response.send_message(error_msg, ephemeral=True)
            else:
                await ctx_or_interaction.send(error_msg)

    @app_commands.command(name="end_giveaway", description="End a giveaway manually")
    @app_commands.describe(message_id="The ID of the giveaway message")
    @commands.has_permissions(manage_messages=True)
    async def end_giveaway_slash(self, interaction: discord.Interaction, message_id: str):
        """End a giveaway manually (slash command)"""
        try:
            await self.end_giveaway_handler(interaction, message_id)
        except Exception as e:
            logger.error(f"Error in end_giveaway slash command: {e}")
            await interaction.response.send_message(
                embed=create_embed("Çekiliş bitirilirken bir hata oluştu.", discord.Color.red()),
                ephemeral=True
            )

def check_if_ctx_or_interaction(ctx_or_interaction):
    """Helper function to determine if the parameter is a Context or Interaction"""
    if hasattr(ctx_or_interaction, 'interaction') and ctx_or_interaction.interaction:
        # This is a hybrid command context with an interaction
        return ctx_or_interaction.interaction
    elif hasattr(ctx_or_interaction, 'response'):
        # This is a direct interaction
        return ctx_or_interaction
    else:
        # This is a regular context
        return ctx_or_interaction

async def setup(bot):
    await bot.add_cog(Giveaways(bot))