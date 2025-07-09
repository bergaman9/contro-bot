"""Moderation action commands."""
import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional, Union
import asyncio
from datetime import datetime, timedelta

from ..base import BaseCog
from ...bot.constants import Colors, Emojis
from ...utils.helpers.discord import create_embed, check_permissions
from ...utils.helpers.text import pluralize


class ModerationActions(BaseCog):
    """Cog for moderation action commands."""
    
    def __init__(self, bot):
        super().__init__(bot)
    
    async def can_moderate(self, ctx: commands.Context, target: discord.Member) -> bool:
        """Check if the user can moderate the target."""
        if target.id == ctx.author.id:
            await ctx.send(embed=create_embed(
                title="Error",
                description="You cannot moderate yourself.",
                color=Colors.ERROR
            ))
            return False
        
        if target.id == self.bot.user.id:
            await ctx.send(embed=create_embed(
                title="Error", 
                description="I cannot moderate myself.",
                color=Colors.ERROR
            ))
            return False
        
        if target.top_role.position >= ctx.author.top_role.position and ctx.author.id != ctx.guild.owner_id:
            await ctx.send(embed=create_embed(
                title="Error",
                description="You cannot moderate someone with a higher or equal role.",
                color=Colors.ERROR
            ))
        return False

        if target.top_role.position >= ctx.guild.me.top_role.position:
            await ctx.send(embed=create_embed(
                title="Error",
                description="I cannot moderate someone with a higher or equal role than mine.",
                color=Colors.ERROR
            ))
            return False
        
        return True
    
    @commands.hybrid_command(
        name="kick",
        description="Kick a member from the server"
    )
    @commands.has_permissions(kick_members=True)
    @app_commands.describe(
        member="The member to kick",
        reason="The reason for kicking"
    )
    async def kick(
        self,
        ctx: commands.Context,
        member: discord.Member,
        *,
        reason: Optional[str] = "No reason provided"
    ):
        """Kick a member from the server."""
        if not await self.can_moderate(ctx, member):
            return
        
        try:
            # Send DM to member
            try:
                dm_embed = create_embed(
                    title=f"Kicked from {ctx.guild.name}",
                    description=f"You have been kicked from **{ctx.guild.name}**",
                    color=Colors.WARNING
                )
                dm_embed.add_field(name="Reason", value=reason, inline=False)
                dm_embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
                await member.send(embed=dm_embed)
            except:
                pass  # User has DMs disabled
            
            # Kick the member
            await member.kick(reason=f"{ctx.author} ({ctx.author.id}): {reason}")
            
            # Send success message
            embed = create_embed(
                title=f"{Emojis.SUCCESS} Member Kicked",
                description=f"{member.mention} has been kicked from the server.",
                color=Colors.SUCCESS
            )
            embed.add_field(name="Reason", value=reason, inline=False)
            embed.set_footer(text=f"Kicked by {ctx.author}")
            
            await ctx.send(embed=embed)
            
        except discord.Forbidden:
            await ctx.send(embed=create_embed(
                title="Error",
                description="I don't have permission to kick that member.",
                color=Colors.ERROR
            ))
        except Exception as e:
            await ctx.send(embed=create_embed(
                title="Error",
                description=f"An error occurred: {str(e)}",
                color=Colors.ERROR
            ))
    
    @commands.hybrid_command(
        name="ban", 
        description="Ban a member from the server"
    )
    @commands.has_permissions(ban_members=True)
    @app_commands.describe(
        member="The member to ban",
        reason="The reason for banning",
        delete_messages="Number of days of messages to delete (0-7)"
    )
    async def ban(
        self,
        ctx: commands.Context,
        member: discord.Member,
        delete_messages: Optional[int] = 0,
        *,
        reason: Optional[str] = "No reason provided"
    ):
        """Ban a member from the server."""
        if not await self.can_moderate(ctx, member):
            return
        
        try:
            # Send DM to member
            try:
                dm_embed = create_embed(
                    title=f"Banned from {ctx.guild.name}",
                    description=f"You have been banned from **{ctx.guild.name}**",
                    color=Colors.ERROR
                )
                dm_embed.add_field(name="Reason", value=reason, inline=False)
                dm_embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
                await member.send(embed=dm_embed)
            except:
                pass  # User has DMs disabled
            
            # Ban the member
            await member.ban(
                reason=f"{ctx.author} ({ctx.author.id}): {reason}",
                delete_message_days=min(delete_messages, 7)
            )
            
            # Send success message
            embed = create_embed(
                title=f"{Emojis.SUCCESS} Member Banned",
                description=f"{member.mention} has been banned from the server.",
                color=Colors.SUCCESS
            )
            embed.add_field(name="Reason", value=reason, inline=False)
            if delete_messages > 0:
                embed.add_field(name="Messages Deleted", value=f"Last {delete_messages} days", inline=True)
            embed.set_footer(text=f"Banned by {ctx.author}")
            
            await ctx.send(embed=embed)
            
        except discord.Forbidden:
            await ctx.send(embed=create_embed(
                title="Error",
                description="I don't have permission to ban that member.",
                color=Colors.ERROR
            ))
        except Exception as e:
            await ctx.send(embed=create_embed(
                title="Error",
                description=f"An error occurred: {str(e)}",
                color=Colors.ERROR
            ))
    
    @commands.hybrid_command(
        name="unban",
        description="Unban a user from the server"
    )
    @commands.has_permissions(ban_members=True)
    @app_commands.describe(
        user_id="The ID of the user to unban",
        reason="The reason for unbanning"
    )
    async def unban(
        self,
        ctx: commands.Context,
        user_id: str,
        *,
        reason: Optional[str] = "No reason provided"
    ):
        """Unban a user from the server."""
        try:
            user_id = int(user_id)
            user = await self.bot.fetch_user(user_id)
            
            await ctx.guild.unban(user, reason=f"{ctx.author} ({ctx.author.id}): {reason}")
            
            embed = create_embed(
                title=f"{Emojis.SUCCESS} User Unbanned",
                description=f"{user.mention} ({user.id}) has been unbanned.",
                color=Colors.SUCCESS
            )
            embed.add_field(name="Reason", value=reason, inline=False)
            embed.set_footer(text=f"Unbanned by {ctx.author}")
            
            await ctx.send(embed=embed)
            
        except ValueError:
            await ctx.send(embed=create_embed(
                title="Error",
                description="Please provide a valid user ID.",
                color=Colors.ERROR
            ))
        except discord.NotFound:
            await ctx.send(embed=create_embed(
                title="Error",
                description=f"Could not find a banned user with ID: {user_id}",
                color=Colors.ERROR
            ))
        except discord.Forbidden:
            await ctx.send(embed=create_embed(
                title="Error",
                description="I don't have permission to unban users.",
                color=Colors.ERROR
            ))
        except Exception as e:
            await ctx.send(embed=create_embed(
                title="Error",
                description=f"An error occurred: {str(e)}",
                color=Colors.ERROR
            ))
    
    @commands.hybrid_command(
        name="mute",
        description="Timeout a member"
    )
    @commands.has_permissions(moderate_members=True)
    @app_commands.describe(
        member="The member to mute",
        duration="The duration of the mute (e.g., 1d2h30m)",
        reason="The reason for muting"
    )
    async def mute(
        self,
        ctx: commands.Context,
        member: discord.Member,
        duration: str,
        *,
        reason: Optional[str] = "No reason provided"
    ):
        """Timeout a member for a specified duration."""
        if not await self.can_moderate(ctx, member):
            return
        
        # Parse duration
        from ...utils.helpers.time import parse_time_string
        time_delta = parse_time_string(duration)
        
        if not time_delta:
            await ctx.send(embed=create_embed(
                title="Error",
                description="Invalid duration format. Use: 1d2h30m",
                color=Colors.ERROR
            ))
            return
            
        if time_delta > timedelta(days=28):
            await ctx.send(embed=create_embed(
                title="Error",
                description="Timeout duration cannot exceed 28 days.",
                color=Colors.ERROR
            ))
            return
        
        try:
            # Apply timeout
            await member.timeout_for(time_delta, reason=f"{ctx.author} ({ctx.author.id}): {reason}")
            
            # Send DM to member
            try:
                dm_embed = create_embed(
                    title=f"Muted in {ctx.guild.name}",
                    description=f"You have been muted in **{ctx.guild.name}**",
                    color=Colors.WARNING
                )
                dm_embed.add_field(name="Duration", value=duration, inline=True)
                dm_embed.add_field(name="Reason", value=reason, inline=False)
                dm_embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
                await member.send(embed=dm_embed)
            except:
                pass  # User has DMs disabled
            
            # Send success message
            embed = create_embed(
                title=f"{Emojis.SUCCESS} Member Muted",
                description=f"{member.mention} has been muted.",
                color=Colors.SUCCESS
            )
            embed.add_field(name="Duration", value=duration, inline=True)
            embed.add_field(name="Reason", value=reason, inline=False)
            embed.set_footer(text=f"Muted by {ctx.author}")
            
            await ctx.send(embed=embed)
            
        except discord.Forbidden:
            await ctx.send(embed=create_embed(
                title="Error",
                description="I don't have permission to timeout that member.",
                color=Colors.ERROR
            ))
        except Exception as e:
            await ctx.send(embed=create_embed(
                title="Error",
                description=f"An error occurred: {str(e)}",
                color=Colors.ERROR
            ))
    
    @commands.hybrid_command(
        name="unmute",
        description="Remove timeout from a member"
    )
    @commands.has_permissions(moderate_members=True)
    @app_commands.describe(
        member="The member to unmute",
        reason="The reason for unmuting"
    )
    async def unmute(
        self,
        ctx: commands.Context,
        member: discord.Member,
        *,
        reason: Optional[str] = "No reason provided"
    ):
        """Remove timeout from a member."""
        try:
            await member.remove_timeout(reason=f"{ctx.author} ({ctx.author.id}): {reason}")
            
            embed = create_embed(
                title=f"{Emojis.SUCCESS} Member Unmuted",
                description=f"{member.mention} has been unmuted.",
                color=Colors.SUCCESS
            )
            embed.add_field(name="Reason", value=reason, inline=False)
            embed.set_footer(text=f"Unmuted by {ctx.author}")
            
            await ctx.send(embed=embed)
            
        except discord.Forbidden:
            await ctx.send(embed=create_embed(
                title="Error",
                description="I don't have permission to remove timeout from that member.",
                color=Colors.ERROR
            ))
        except Exception as e:
            await ctx.send(embed=create_embed(
                title="Error",
                description=f"An error occurred: {str(e)}",
                color=Colors.ERROR
            ))
    
    @commands.hybrid_command(
        name="warn",
        description="Warn a member"
    )
    @commands.has_permissions(moderate_members=True)
    @app_commands.describe(
        member="The member to warn",
        reason="The reason for the warning"
    )
    async def warn(
        self,
        ctx: commands.Context,
        member: discord.Member,
        *,
        reason: str
    ):
        """Warn a member."""
        if not await self.can_moderate(ctx, member):
            return
        
        # Add warning to database
        if self.bot.member_service:
            success = await self.bot.member_service.add_warning(
                ctx.guild.id,
                member.id,
                reason,
                ctx.author.id
            )
            
            if success:
                # Get total warnings
                warnings = await self.bot.member_service.get_warnings(ctx.guild.id, member.id)
                warning_count = len(warnings)
                
                # Send DM to member
                try:
                    dm_embed = create_embed(
                        title=f"Warning in {ctx.guild.name}",
                        description=f"You have received a warning in **{ctx.guild.name}**",
                        color=Colors.WARNING
                    )
                    dm_embed.add_field(name="Reason", value=reason, inline=False)
                    dm_embed.add_field(name="Total Warnings", value=str(warning_count), inline=True)
                    dm_embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
                    await member.send(embed=dm_embed)
                except:
                    pass  # User has DMs disabled
                
                # Send success message
                embed = create_embed(
                    title=f"{Emojis.WARNING} Member Warned",
                    description=f"{member.mention} has been warned.",
                    color=Colors.WARNING
                )
                embed.add_field(name="Reason", value=reason, inline=False)
                embed.add_field(name="Total Warnings", value=str(warning_count), inline=True)
                embed.set_footer(text=f"Warned by {ctx.author}")
                
                await ctx.send(embed=embed)
            else:
                await ctx.send(embed=create_embed(
                    title="Error",
                    description="Failed to add warning to database.",
                    color=Colors.ERROR
                ))
        else:
            await ctx.send(embed=create_embed(
                title="Error",
                description="Warning system is not available.",
                color=Colors.ERROR
            ))
    
    @commands.hybrid_command(
        name="warnings",
        description="View warnings for a member"
    )
    @commands.has_permissions(moderate_members=True)
    @app_commands.describe(
        member="The member whose warnings to view"
    )
    async def warnings(
        self,
        ctx: commands.Context,
        member: discord.Member
    ):
        """View warnings for a member."""
        if not self.bot.member_service:
            await ctx.send(embed=create_embed(
                title="Error",
                description="Warning system is not available.",
                color=Colors.ERROR
            ))
            return
        
        warnings = await self.bot.member_service.get_warnings(ctx.guild.id, member.id)
        
        if not warnings:
            embed = create_embed(
                title="No Warnings",
                description=f"{member.mention} has no warnings.",
                color=Colors.INFO
            )
        else:
            embed = create_embed(
                title=f"Warnings for {member}",
                description=f"Total warnings: {len(warnings)}",
                color=Colors.WARNING
            )
            
            for i, warning in enumerate(warnings[-10:], 1):  # Show last 10 warnings
                moderator = self.bot.get_user(warning.get('moderator_id', 0))
                mod_text = moderator.mention if moderator else "Unknown"
                timestamp = warning.get('timestamp', 'Unknown')
                
                embed.add_field(
                    name=f"Warning #{i}",
                    value=f"**Reason:** {warning.get('reason', 'No reason')}\n"
                          f"**By:** {mod_text}\n"
                          f"**Date:** {timestamp}",
                    inline=False
                )
        
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(
        name="purge",
        description="Delete multiple messages"
    )
    @commands.has_permissions(manage_messages=True)
    @app_commands.describe(
        amount="The number of messages to delete (1-100)",
        user="Delete messages only from this user (optional)"
    )
    async def purge(
        self,
        ctx: commands.Context,
        amount: int,
        user: Optional[discord.Member] = None
    ):
        """Delete multiple messages."""
        if amount < 1 or amount > 100:
            await ctx.send(embed=create_embed(
                title="Error",
                description="Please provide a number between 1 and 100.",
                color=Colors.ERROR
            ), ephemeral=True)
            return
        
        # Delete the invocation message if it's a prefix command
        if ctx.interaction is None:
            await ctx.message.delete()
            amount -= 1  # Reduce amount since we deleted the command message
        
        try:
            def check(message):
                return user is None or message.author.id == user.id
            
            deleted = await ctx.channel.purge(limit=amount, check=check)
            
            user_text = f" from {user.mention}" if user else ""
            msg = await ctx.send(embed=create_embed(
                title=f"{Emojis.SUCCESS} Messages Deleted",
                description=f"Successfully deleted {len(deleted)} messages{user_text}.",
                color=Colors.SUCCESS
            ))
            
            # Delete the success message after 5 seconds
            await asyncio.sleep(5)
            await msg.delete()
            
        except discord.Forbidden:
            await ctx.send(embed=create_embed(
                title="Error",
                description="I don't have permission to delete messages.",
                color=Colors.ERROR
            ))
        except discord.HTTPException as e:
            await ctx.send(embed=create_embed(
                title="Error",
                description=f"Failed to delete messages: {str(e)}",
                color=Colors.ERROR
            ))


async def setup(bot):
    """Load the cog."""
    await bot.add_cog(ModerationActions(bot))
