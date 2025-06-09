import discord
from discord.ext import commands
from discord import app_commands
import json
import os
from typing import Dict, List, Optional

from core.config_manager import ConfigManager

class Owner(commands.Cog):
    """Owner-only commands for bot management and client configuration"""
    
    def __init__(self, bot):
        self.bot = bot
        self.config = bot.config if hasattr(bot, 'config') else ConfigManager()
    
    async def cog_check(self, ctx):
        """Only allow bot owners to use these commands"""
        return await self.bot.is_owner(ctx.author)
    
    @commands.group(name="config", invoke_without_command=True)
    async def config_cmd(self, ctx):
        """Manage bot configuration"""
        await ctx.send_help(ctx.command)
    
    @config_cmd.command(name="list")
    async def config_list(self, ctx):
        """List all available client configurations"""
        embed = discord.Embed(
            title="Client Configurations",
            description="List of all available client configurations",
            color=discord.Color.blue()
        )
        
        # Add main and dev client entries
        embed.add_field(
            name="main",
            value="Main bot configuration",
            inline=True
        )
        embed.add_field(
            name="dev",
            value="Development bot configuration",
            inline=True
        )
        
        # Add spacer
        embed.add_field(name="\u200b", value="\u200b", inline=True)
        
        # Add client-specific configurations
        client_settings = self.config.config.get("client_settings", {})
        
        if client_settings:
            for client_id, settings in client_settings.items():
                cogs = ", ".join(settings.get("enabled_cogs", ["default cogs"]))
                value = f"Name: {settings.get('name', 'Unnamed')}\n" \
                        f"Prefix: {settings.get('prefix', self.config.get_prefix())}\n" \
                        f"Cogs: {cogs[:100] + '...' if len(cogs) > 100 else cogs}"
                
                embed.add_field(
                    name=client_id,
                    value=value,
                    inline=True
                )
                
                # Add spacer every 2 clients for nice formatting
                if len(embed.fields) % 3 == 0:
                    embed.add_field(name="\u200b", value="\u200b", inline=True)
        else:
            embed.add_field(
                name="No Custom Clients",
                value="No custom client configurations found.",
                inline=False
            )
        
        embed.set_footer(text=f"Current client: {self.bot.client_id}")
        await ctx.send(embed=embed)
    
    @config_cmd.command(name="create")
    async def create_client(self, ctx, client_id: str, name: str, prefix: str = "!"):
        """Create a new client configuration"""
        client_id = client_id.lower()
        
        # Check if client already exists
        client_settings = self.config.config.get("client_settings", {})
        if client_id in client_settings:
            await ctx.send(f"Error: Client '{client_id}' already exists.")
            return
            
        # Create new client
        if "client_settings" not in self.config.config:
            self.config.config["client_settings"] = {}
            
        self.config.config["client_settings"][client_id] = {
            "name": name,
            "prefix": prefix,
            "enabled_cogs": self.config.config.get("default_cogs", [])
        }
        
        # Save changes
        if self.config.save_config():
            await ctx.send(f"Client '{client_id}' created successfully!")
        else:
            await ctx.send("Failed to save configuration.")
    
    @config_cmd.command(name="enable_cog")
    async def enable_cog(self, ctx, client_id: str, cog_name: str):
        """Enable a cog for a specific client"""
        client_id = client_id.lower()
        cog_name = cog_name.lower()
        
        # Check if client exists
        client_settings = self.config.config.get("client_settings", {})
        if client_id not in client_settings:
            await ctx.send(f"Error: Client '{client_id}' does not exist.")
            return
        
        # Check if cog exists
        if not os.path.exists(f"./cogs/{cog_name}.py"):
            await ctx.send(f"Error: Cog '{cog_name}' does not exist.")
            return
            
        # Enable cog
        if "enabled_cogs" not in client_settings[client_id]:
            client_settings[client_id]["enabled_cogs"] = []
            
        if cog_name not in client_settings[client_id]["enabled_cogs"]:
            client_settings[client_id]["enabled_cogs"].append(cog_name)
            
            # Save changes
            if self.config.save_config():
                await ctx.send(f"Cog '{cog_name}' enabled for client '{client_id}'!")
            else:
                await ctx.send("Failed to save configuration.")
        else:
            await ctx.send(f"Cog '{cog_name}' is already enabled for client '{client_id}'.")
    
    @config_cmd.command(name="disable_cog")
    async def disable_cog(self, ctx, client_id: str, cog_name: str):
        """Disable a cog for a specific client"""
        client_id = client_id.lower()
        cog_name = cog_name.lower()
        
        # Check if client exists
        client_settings = self.config.config.get("client_settings", {})
        if client_id not in client_settings:
            await ctx.send(f"Error: Client '{client_id}' does not exist.")
            return
            
        # Disable cog
        if "enabled_cogs" in client_settings[client_id] and cog_name in client_settings[client_id]["enabled_cogs"]:
            client_settings[client_id]["enabled_cogs"].remove(cog_name)
            
            # Save changes
            if self.config.save_config():
                await ctx.send(f"Cog '{cog_name}' disabled for client '{client_id}'!")
            else:
                await ctx.send("Failed to save configuration.")
        else:
            await ctx.send(f"Cog '{cog_name}' is not enabled for client '{client_id}'.")
    
    @commands.command(name="listcogs")
    async def list_cogs(self, ctx):
        """List all available cogs"""
        cogs = []
        
        # Get cogs from filesystem
        for file in os.listdir("./cogs"):
            if file.endswith(".py"):
                cogs.append(file[:-3])
        
        embed = discord.Embed(
            title="Available Cogs",
            description="List of all available cogs",
            color=discord.Color.blue()
        )
        
        # Group by loaded status for this client
        loaded_cogs = []
        unloaded_cogs = []
        
        for cog in cogs:
            if self.config.is_cog_enabled(cog, self.bot.client_id):
                loaded_cogs.append(cog)
            else:
                unloaded_cogs.append(cog)
        
        if loaded_cogs:
            embed.add_field(
                name="Loaded Cogs",
                value="\n".join(f"✅ {cog}" for cog in sorted(loaded_cogs)),
                inline=True
            )
        
        if unloaded_cogs:
            embed.add_field(
                name="Unloaded Cogs",
                value="\n".join(f"❌ {cog}" for cog in sorted(unloaded_cogs)),
                inline=True
            )
        
        embed.set_footer(text=f"Total: {len(cogs)} cogs | Client: {self.bot.client_id}")
        await ctx.send(embed=embed)
    
    @commands.command(name="load")
    @commands.is_owner()
    async def load_cog(self, ctx, cog_name: str):
        """Load a cog by name"""
        cog_name = cog_name.lower()
        
        # Check if cog exists
        if not os.path.exists(f"./cogs/{cog_name}.py"):
            await ctx.send(f"Error: Cog '{cog_name}' does not exist.")
            return
        
        # Check if already loaded
        if f"cogs.{cog_name}" in self.bot.extensions:
            await ctx.send(f"Cog '{cog_name}' is already loaded.")
            return
            
        try:
            await self.bot.load_extension(f"cogs.{cog_name}")
            await ctx.send(f"Successfully loaded cog: `{cog_name}`")
        except Exception as e:
            await ctx.send(f"Failed to load cog '{cog_name}': {str(e)}")
    
    @commands.command(name="unload")
    @commands.is_owner()
    async def unload_cog(self, ctx, cog_name: str):
        """Unload a loaded cog by name"""
        cog_name = cog_name.lower()
        
        # Prevent unloading owner cog
        if cog_name == "owner":
            await ctx.send("Cannot unload the owner cog.")
            return
        
        # Check if cog is loaded
        if f"cogs.{cog_name}" not in self.bot.extensions:
            await ctx.send(f"Cog '{cog_name}' is not loaded.")
            return
            
        try:
            await self.bot.unload_extension(f"cogs.{cog_name}")
            await ctx.send(f"Successfully unloaded cog: `{cog_name}`")
        except Exception as e:
            await ctx.send(f"Failed to unload cog '{cog_name}': {str(e)}")
    
    @commands.command(name="reload")
    @commands.is_owner()
    async def reload_cog(self, ctx, cog_name: str):
        """Reload a loaded cog by name"""
        cog_name = cog_name.lower()
        
        # Check if cog exists
        if not os.path.exists(f"./cogs/{cog_name}.py"):
            await ctx.send(f"Error: Cog '{cog_name}' does not exist.")
            return
        
        # Check if cog is loaded
        if f"cogs.{cog_name}" not in self.bot.extensions:
            await ctx.send(f"Cog '{cog_name}' is not loaded. Loading it now...")
            try:
                await self.bot.load_extension(f"cogs.{cog_name}")
                await ctx.send(f"Successfully loaded cog: `{cog_name}`")
                return
            except Exception as e:
                await ctx.send(f"Failed to load cog '{cog_name}': {str(e)}")
                return
            
        try:
            await self.bot.reload_extension(f"cogs.{cog_name}")
            await ctx.send(f"Successfully reloaded cog: `{cog_name}`")
        except Exception as e:
            await ctx.send(f"Failed to reload cog '{cog_name}': {str(e)}")
    
    @commands.command(name="sync")
    @commands.is_owner()
    async def sync_commands(self, ctx):
        """Manually synchronize slash commands with Discord"""
        await ctx.send("Synchronizing slash commands with Discord...")
        
        try:
            # Sync global commands
            synced = await self.bot.tree.sync()
            
            embed = discord.Embed(
                title="Command Sync Complete",
                description=f"Successfully synchronized {len(synced)} slash commands",
                color=discord.Color.green()
            )
            embed.set_footer(text=f"Client: {self.bot.client_id}")
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f"Error synchronizing commands: {e}")

async def setup(bot):
    await bot.add_cog(Owner(bot))
