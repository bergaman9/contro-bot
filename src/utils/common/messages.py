import discord
from typing import Optional, Union
from discord import Embed, Color


class MessageEmbed:
    """Common embed message utilities for consistent UI"""
    
    @staticmethod
    def error(
        title: str = "❌ Hata",
        description: str = "Bir hata oluştu.",
        fields: Optional[list] = None,
        footer: Optional[str] = None,
        thumbnail: Optional[str] = None
    ) -> Embed:
        """Create an error embed with red color"""
        embed = Embed(
            title=title,
            description=description,
            color=Color.red()
        )
        
        if fields:
            for field in fields:
                embed.add_field(
                    name=field.get("name", ""),
                    value=field.get("value", ""),
                    inline=field.get("inline", True)
                )
        
        if footer:
            embed.set_footer(text=footer)
            
        if thumbnail:
            embed.set_thumbnail(url=thumbnail)
            
        return embed
    
    @staticmethod
    def success(
        title: str = "✅ Başarılı",
        description: str = "İşlem başarıyla tamamlandı.",
        fields: Optional[list] = None,
        footer: Optional[str] = None,
        thumbnail: Optional[str] = None
    ) -> Embed:
        """Create a success embed with green color"""
        embed = Embed(
            title=title,
            description=description,
            color=Color.green()
        )
        
        if fields:
            for field in fields:
                embed.add_field(
                    name=field.get("name", ""),
                    value=field.get("value", ""),
                    inline=field.get("inline", True)
                )
        
        if footer:
            embed.set_footer(text=footer)
            
        if thumbnail:
            embed.set_thumbnail(url=thumbnail)
            
        return embed
    
    @staticmethod
    def info(
        title: str = "ℹ️ Bilgi",
        description: str = "",
        fields: Optional[list] = None,
        footer: Optional[str] = None,
        thumbnail: Optional[str] = None
    ) -> Embed:
        """Create an info embed with blue color"""
        embed = Embed(
            title=title,
            description=description,
            color=Color.blue()
        )
        
        if fields:
            for field in fields:
                embed.add_field(
                    name=field.get("name", ""),
                    value=field.get("value", ""),
                    inline=field.get("inline", True)
                )
        
        if footer:
            embed.set_footer(text=footer)
            
        if thumbnail:
            embed.set_thumbnail(url=thumbnail)
            
        return embed
    
    @staticmethod
    def warning(
        title: str = "⚠️ Uyarı",
        description: str = "",
        fields: Optional[list] = None,
        footer: Optional[str] = None,
        thumbnail: Optional[str] = None
    ) -> Embed:
        """Create a warning embed with orange color"""
        embed = Embed(
            title=title,
            description=description,
            color=Color.orange()
        )
        
        if fields:
            for field in fields:
                embed.add_field(
                    name=field.get("name", ""),
                    value=field.get("value", ""),
                    inline=field.get("inline", True)
                )
        
        if footer:
            embed.set_footer(text=footer)
            
        if thumbnail:
            embed.set_thumbnail(url=thumbnail)
            
        return embed
    
    @staticmethod
    def loading(
        title: str = "⏳ İşleniyor",
        description: str = "Lütfen bekleyin...",
        footer: Optional[str] = None
    ) -> Embed:
        """Create a loading embed with blurple color"""
        embed = Embed(
            title=title,
            description=description,
            color=Color.blurple()
        )
        
        if footer:
            embed.set_footer(text=footer)
            
        return embed
    
    @staticmethod
    def custom(
        title: str,
        description: str = "",
        color: Union[Color, int] = Color.default(),
        fields: Optional[list] = None,
        footer: Optional[str] = None,
        thumbnail: Optional[str] = None,
        image: Optional[str] = None,
        author: Optional[dict] = None
    ) -> Embed:
        """Create a custom embed with all options"""
        embed = Embed(
            title=title,
            description=description,
            color=color
        )
        
        if fields:
            for field in fields:
                embed.add_field(
                    name=field.get("name", ""),
                    value=field.get("value", ""),
                    inline=field.get("inline", True)
                )
        
        if footer:
            embed.set_footer(text=footer)
            
        if thumbnail:
            embed.set_thumbnail(url=thumbnail)
            
        if image:
            embed.set_image(url=image)
            
        if author:
            embed.set_author(
                name=author.get("name", ""),
                url=author.get("url"),
                icon_url=author.get("icon_url")
            )
            
        return embed


# Convenience functions for quick access
def error_embed(description: str, title: str = "❌ Hata") -> Embed:
    """Quick error embed creation"""
    return MessageEmbed.error(title=title, description=description)


def success_embed(description: str, title: str = "✅ Başarılı") -> Embed:
    """Quick success embed creation"""
    return MessageEmbed.success(title=title, description=description)


def info_embed(description: str, title: str = "ℹ️ Bilgi") -> Embed:
    """Quick info embed creation"""
    return MessageEmbed.info(title=title, description=description)


def warning_embed(description: str, title: str = "⚠️ Uyarı") -> Embed:
    """Quick warning embed creation"""
    return MessageEmbed.warning(title=title, description=description)


def loading_embed(description: str = "Lütfen bekleyin...", title: str = "⏳ İşleniyor") -> Embed:
    """Quick loading embed creation"""
    return MessageEmbed.loading(title=title, description=description) 