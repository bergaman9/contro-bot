"""
Member Commands Cog - Organized command groups for Discord bot members

This cog loads the new organized command groups:
- /info: User information commands (user, avatar, server)
- /fun: Entertainment commands (love, zodiac, love calculator)
- /media: Media search commands (movie, tv, game, spotify)
- /text: Text manipulation commands (word, sentence, reverse, echo)
- /utility: Utility commands (crypto, shorten, poll, privacy)

This replaces the scattered individual commands from utility.py and fun.py
"""

import discord
from discord.ext import commands
import logging

# Import the new command groups
from utils.commands.member_groups import (
    InfoCommands,
    FunCommands, 
    MediaCommands,
    TextCommands,
    UtilityCommands
)

logger = logging.getLogger('member_commands')

class MemberCommands(commands.Cog):
    """Meta-cog that manages organized member command groups"""
    
    def __init__(self, bot):
        self.bot = bot
        logger.info("Initializing organized member command groups...")
        
    @commands.Cog.listener()
    async def on_ready(self):
        logger.info("Member command groups loaded successfully!")
          # Standalone commands that don't belong in groups
    # Note: ping command is handled by utility.py, so we don't duplicate it here
        
    @commands.hybrid_command(name="support", description="Get support and bot information")
    async def support(self, ctx):
        """Show support information"""
        embed = discord.Embed(
            title="🛠️ Support & Information",
            description="Get help with the bot and access useful links",
            color=discord.Color.blue()
        )
        embed.add_field(
            name="📞 Support Server",
            value="Join our Discord server for help and updates",
            inline=False
        )
        embed.add_field(
            name="🔗 Useful Links", 
            value="• [Support Server](https://discord.gg/ynGqvsYxah)\n"
                  "• [Invite Bot](https://discord.com/api/oauth2/authorize?client_id={}/permissions=8&scope=bot)\n"
                  "• [Vote on Top.gg](https://top.gg/bot/869041978467201280/vote)".format(self.bot.application_id),
            inline=False
        )
        embed.set_thumbnail(url=self.bot.user.avatar.url)
        
        # Create view with buttons
        view = discord.ui.View()
        view.add_item(discord.ui.Button(
            label="Support Server",
            url="https://discord.gg/ynGqvsYxah",
            style=discord.ButtonStyle.url,
            emoji="📞"
        ))
        view.add_item(discord.ui.Button(
            label="Invite Bot", 
            url=f"https://discord.com/api/oauth2/authorize?client_id={self.bot.application_id}&permissions=8&scope=bot",
            style=discord.ButtonStyle.url,
            emoji="➕"
        ))
        view.add_item(discord.ui.Button(
            label="Vote Bot",
            url="https://top.gg/bot/869041978467201280/vote", 
            style=discord.ButtonStyle.url,
            emoji="⭐"
        ))
        
        await ctx.send(embed=embed, view=view)

async def setup(bot):
    """Setup function to load all command groups"""
    # Add the command groups to the bot
    await bot.add_cog(InfoCommands(bot))
    await bot.add_cog(FunCommands(bot))
    await bot.add_cog(MediaCommands(bot))
    await bot.add_cog(TextCommands(bot))
    await bot.add_cog(UtilityCommands(bot))
    
    # Add the meta-cog for standalone commands
    await bot.add_cog(MemberCommands(bot))
    
    logger.info("All member command groups loaded successfully!")
