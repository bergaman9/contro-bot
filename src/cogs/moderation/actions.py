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
    
    async def can_moderate(self, ctx: Union[discord.ApplicationContext, commands.Context], target: discord.Member) -> bool:
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
    
    @discord.slash_command(
        name="kick",
        description="Kick a member from the server"
    )
    @discord.default_permissions(kick_members=True)
    async def kick(
        self,
        ctx: discord.ApplicationContext,
        member: discord.Member,
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
            
            await ctx.respond(embed=embed)
            
        except discord.Forbidden:
            await ctx.respond(embed=create_embed(
                title="Error",
                description="I don't have permission to kick that member.",
                color=Colors.ERROR
            ))
        except Exception as e:
            await ctx.respond(embed=create_embed(
                title="Error",
                description=f"An error occurred: {str(e)}",
                color=Colors.ERROR
            ))
    
    @discord.slash_command(
        name="ban", 
        description="Ban a member from the server"
    )
    @discord.default_permissions(ban_members=True)
    async def ban(
        self,
        ctx: discord.ApplicationContext,
        member: discord.Member,
        reason: Optional[str] = "No reason provided",
        delete_messages: Optional[int] = 0
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
            
            await ctx.respond(embed=embed)
            
        except discord.Forbidden:
            await ctx.respond(embed=create_embed(
                title="Error",
                description="I don't have permission to ban that member.",
                color=Colors.ERROR
            ))
        except Exception as e:
            await ctx.respond(embed=create_embed(
                title="Error",
                description=f"An error occurred: {str(e)}",
                color=Colors.ERROR
            ))
    
    @discord.slash_command(
        name="unban",
        description="Unban a user from the server"
    )
    @discord.default_permissions(ban_members=True)
    async def unban(
        self,
        ctx: discord.ApplicationContext,
        user_id: str,
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
            
            await ctx.respond(embed=embed)
            
        except ValueError:
            await ctx.respond(embed=create_embed(
                title="Error",
                description="Please provide a valid user ID.",
                color=Colors.ERROR
            ))
        except discord.NotFound:
            await ctx.respond(embed=create_embed(
                title="Error",
                description=f"Could not find a banned user with ID: {user_id}",
                color=Colors.ERROR
            ))
        except discord.Forbidden:
            await ctx.respond(embed=create_embed(
                title="Error",
                description="I don't have permission to unban users.",
                color=Colors.ERROR
            ))
        except Exception as e:
            await ctx.respond(embed=create_embed(
                title="Error",
                description=f"An error occurred: {str(e)}",
                color=Colors.ERROR
            ))
    
    @discord.slash_command(
        name="mute",
        description="Timeout a member"
    )
    @discord.default_permissions(moderate_members=True)
    async def mute(
        self,
        ctx: discord.ApplicationContext,
        member: discord.Member,
        duration: str,
        reason: Optional[str] = "No reason provided"
    ):
        """Timeout a member for a specified duration."""
        if not await self.can_moderate(ctx, member):
            return
        
        # Parse duration
        from ...utils.helpers.time import parse_time_string
        time_delta = parse_time_string(duration)
        
        if not time_delta:
            await ctx.respond(embed=create_embed(
                title="Error",
                description="Invalid duration format. Use: 1d2h30m",
                color=Colors.ERROR
            ))
            return
        
        if time_delta > timedelta(days=28):
            await ctx.respond(embed=create_embed(
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
            
            await ctx.respond(embed=embed)
            
        except discord.Forbidden:
            await ctx.respond(embed=create_embed(
                title="Error",
                description="I don't have permission to timeout that member.",
                color=Colors.ERROR
            ))
        except Exception as e:
            await ctx.respond(embed=create_embed(
                title="Error",
                description=f"An error occurred: {str(e)}",
                color=Colors.ERROR
            ))
    
    @discord.slash_command(
        name="unmute",
        description="Remove timeout from a member"
    )
    @discord.default_permissions(moderate_members=True)
    async def unmute(
        self,
        ctx: discord.ApplicationContext,
        member: discord.Member,
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
            
            await ctx.respond(embed=embed)
            
        except discord.Forbidden:
            await ctx.respond(embed=create_embed(
                title="Error",
                description="I don't have permission to remove timeout from that member.",
                color=Colors.ERROR
            ))
        except Exception as e:
            await ctx.respond(embed=create_embed(
                title="Error",
                description=f"An error occurred: {str(e)}",
                color=Colors.ERROR
            ))
    
    @discord.slash_command(
        name="warn",
        description="Warn a member"
    )
    @discord.default_permissions(moderate_members=True)
    async def warn(
        self,
        ctx: discord.ApplicationContext,
        member: discord.Member,
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
                
                await ctx.respond(embed=embed)
            else:
                await ctx.respond(embed=create_embed(
                    title="Error",
                    description="Failed to add warning to database.",
                    color=Colors.ERROR
                ))
        else:
            await ctx.respond(embed=create_embed(
                title="Error",
                description="Warning system is not available.",
                color=Colors.ERROR
            ))
    
    @discord.slash_command(
        name="warnings",
        description="View warnings for a member"
    )
    @discord.default_permissions(moderate_members=True)
    async def warnings(
        self,
        ctx: discord.ApplicationContext,
        member: discord.Member
    ):
        """View warnings for a member."""
        if not self.bot.member_service:
            await ctx.respond(embed=create_embed(
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
        
        await ctx.respond(embed=embed)
    
    @discord.slash_command(
        name="purge",
        description="Delete multiple messages"
    )
    @discord.default_permissions(manage_messages=True)
    async def purge(
        self,
        ctx: discord.ApplicationContext,
        amount: int,
        user: Optional[discord.Member] = None
    ):
        """Delete multiple messages."""
        if amount < 1 or amount > 100:
            await ctx.respond(embed=create_embed(
                title="Error",
                description="Please provide a number between 1 and 100.",
                color=Colors.ERROR
            ), ephemeral=True)
            return
        
        await ctx.defer(ephemeral=True)
        
        try:
            def check(message):
                return user is None or message.author.id == user.id
            
            deleted = await ctx.channel.purge(limit=amount, check=check)
            
            user_text = f" from {user.mention}" if user else ""
            await ctx.followup.send(embed=create_embed(
                title=f"{Emojis.SUCCESS} Messages Deleted",
                description=f"Successfully deleted {len(deleted)} messages{user_text}.",
                color=Colors.SUCCESS
            ), ephemeral=True)
            
        except discord.Forbidden:
            await ctx.followup.send(embed=create_embed(
                title="Error",
                description="I don't have permission to delete messages.",
                color=Colors.ERROR
            ), ephemeral=True)
        except discord.HTTPException as e:
            await ctx.followup.send(embed=create_embed(
                title="Error",
                description=f"Failed to delete messages: {str(e)}",
                color=Colors.ERROR
            ), ephemeral=True)


def setup(bot):
    """Load the cog."""
    bot.add_cog(ModerationActions(bot))
