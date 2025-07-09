"""
Stats API Routes
Bot istatistikleri ve performans metrikleri
"""

from flask import Blueprint, jsonify, current_app
import psutil
import time
from datetime import datetime, timedelta
from typing import Dict, Any

# Blueprint oluştur
bp = Blueprint('stats', __name__)

def get_bot_stats() -> Dict[str, Any]:
    """Bot istatistiklerini topla"""
    try:
        # Bot instance'ını al (eğer varsa)
        bot = getattr(current_app, 'bot_instance', None)
        start_time = getattr(current_app, 'start_time', None)
        
        if not bot:
            return {
                "error": "Bot instance not available",
                "status": "offline"
            }
        
        # Temel bot bilgileri
        guild_count = len(bot.guilds)
        user_count = sum(guild.member_count for guild in bot.guilds if guild.member_count)
        
        # Komut sayıları
        text_commands = len(bot.commands)
        slash_commands = 0
        try:
            slash_commands = len(bot.tree.get_commands())
        except:
            pass
        
        # Uptime hesaplama
        uptime_str = "Unknown"
        if start_time:
            uptime_seconds = int(time.time() - start_time)
            uptime_str = str(timedelta(seconds=uptime_seconds))
        
        # Sistem metrikleri
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        
        # Latency
        latency_ms = round(bot.latency * 1000, 2)
        
        return {
            "status": "online",
            "bot": {
                "guild_count": guild_count,
                "user_count": user_count,
                "uptime": uptime_str,
                "latency_ms": latency_ms
            },
            "commands": {
                "text_commands": text_commands,
                "slash_commands": slash_commands,
                "total_commands": text_commands + slash_commands
            },
            "system": {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_used_mb": round(memory.used / 1024 / 1024, 2),
                "memory_total_mb": round(memory.total / 1024 / 1024, 2)
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        current_app.logger.error(f"Error getting bot stats: {str(e)}")
        return {
            "error": str(e),
            "status": "error"
        }

@bp.route('/', methods=['GET'])
def get_stats():
    """Bot istatistiklerini döndür"""
    stats = get_bot_stats()
    return jsonify(stats)

@bp.route('/summary', methods=['GET'])
def get_stats_summary():
    """Özet bot istatistikleri"""
    try:
        bot = getattr(current_app, 'bot_instance', None)
        
        if not bot:
            return jsonify({
                "error": "Bot instance not available"
            }), 503
        
        return jsonify({
            "guild_count": len(bot.guilds),
            "user_count": sum(guild.member_count for guild in bot.guilds if guild.member_count),
            "latency_ms": round(bot.latency * 1000, 2),
            "status": "online"
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting stats summary: {str(e)}")
        return jsonify({
            "error": str(e)
        }), 500

@bp.route('/health', methods=['GET'])
def health_check():
    """Bot sağlık kontrolü"""
    try:
        bot = getattr(current_app, 'bot_instance', None)
        
        if not bot:
            return jsonify({
                "status": "unhealthy",
                "reason": "Bot instance not available"
            }), 503
        
        # Bot bağlantı durumu kontrolü
        if not bot.is_ready():
            return jsonify({
                "status": "unhealthy",
                "reason": "Bot not ready"
            }), 503
        
        return jsonify({
            "status": "healthy",
            "latency_ms": round(bot.latency * 1000, 2),
            "guild_count": len(bot.guilds),
            "timestamp": datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        current_app.logger.error(f"Error in health check: {str(e)}")
        return jsonify({
            "status": "unhealthy",
            "error": str(e)
        }), 500 