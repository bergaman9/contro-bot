import os
import sys
import time
import psutil
import logging
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, List
import tracemalloc
import gc
import inspect

# Setup logging for resource monitor
logger = logging.getLogger('resource_monitor')
logger.setLevel(logging.INFO)
handler = logging.FileHandler(filename='logs/resources.log', encoding='utf-8', mode='a')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

class CogMetrics:
    """Stores metrics for individual cogs"""
    def __init__(self, name: str):
        self.name = name
        self.memory_usage = 0.0  # MB
        self.cpu_percent = 0.0  # %
        self.command_count = 0
        self.listener_count = 0
        self.last_cpu_time = 0.0
        self.objects_count = 0

class ResourceMonitor:
    """
    Monitors resource usage (memory, CPU) of the bot and individual cogs
    """
    def __init__(self, bot, interval: int = 300):
        """
        Initialize the resource monitor
        
        Args:
            bot: The Discord bot instance
            interval: Monitoring interval in seconds (default: 300s / 5min)
        """
        self.bot = bot
        self.interval = interval
        self.process = psutil.Process(os.getpid())
        self.monitoring_task = None
        self.is_running = False
        self.cog_snapshots = {}
        self.cog_metrics = {}
        self.last_cpu_times = {}
        self.last_collection_time = time.time()
        self.is_collecting = False
        self.collection_start_time = 0
        self.tracemalloc_enabled = False
        
        try:
            # Initialize tracemalloc if not already started
            if not tracemalloc.is_tracing():
                tracemalloc.start()
                self.tracemalloc_enabled = True
                logger.info("Tracemalloc started for memory monitoring")
            else:
                self.tracemalloc_enabled = True
                logger.info("Using existing tracemalloc session")
        except Exception as e:
            logger.warning(f"Failed to initialize tracemalloc: {e}")
            self.tracemalloc_enabled = False
        
        logger.info(f"Resource monitoring initialized with {interval}s interval")
    
    def start(self):
        """Start the resource monitoring background task"""
        if self.is_running:
            return
            
        self.is_running = True
        self.monitoring_task = asyncio.create_task(self._monitor_resources())
        logger.info("Resource monitoring started")
    
    def stop(self):
        """Stop the resource monitoring background task"""
        if not self.is_running:
            return
            
        self.is_running = False
        self.is_collecting = False
        if self.monitoring_task:
            self.monitoring_task.cancel()
        logger.info("Resource monitoring stopped")
    
    async def _monitor_resources(self):
        """Background task to periodically monitor resource usage"""
        try:
            while self.is_running:
                try:
                    self.is_collecting = True
                    self.collection_start_time = time.time()
                    await self._collect_and_log_metrics()
                except asyncio.CancelledError:
                    raise  # Re-raise to be caught by outer try-except
                except Exception as e:
                    logger.error(f"Error in resource monitoring: {e}", exc_info=True)
                finally:
                    self.is_collecting = False
                
                await asyncio.sleep(self.interval)
        except asyncio.CancelledError:
            logger.info("Resource monitoring task cancelled")
        except Exception as e:
            logger.error(f"Fatal error in resource monitoring task: {e}", exc_info=True)
            self.is_running = False
            self.is_collecting = False
    
    async def _collect_and_log_metrics(self):
        """Collect and log system and bot resource metrics with timeout protection"""
        # Set a timeout for this operation
        try:
            # Use a reasonable timeout to prevent blocking the bot's heartbeat
            await asyncio.wait_for(self._do_collect_metrics(), timeout=20)
        except asyncio.TimeoutError:
            logger.warning("Resource metrics collection took too long and was aborted")
        except Exception as e:
            logger.error(f"Error collecting resource metrics: {e}", exc_info=True)

    async def _get_cog_memory_usage_async(self, cog, snapshot):
        """Get memory usage for a specific cog in a thread to avoid blocking event loop"""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._get_cog_memory_usage, cog, snapshot)

    async def _do_collect_metrics(self):
        """Actual implementation of metrics collection (async, non-blocking)"""
        metrics = {
            "timestamp": datetime.now().isoformat(),
            "system": self._get_system_metrics(),
            "bot": self._get_bot_metrics(),
            "cogs": {}
        }
        # Get memory usage by cog if tracemalloc is enabled
        if self.tracemalloc_enabled:
            try:
                current_snapshot = tracemalloc.take_snapshot()
                tasks = []
                for cog_name, cog in self.bot.cogs.items():
                    tasks.append((cog_name, self._get_cog_memory_usage_async(cog, current_snapshot)))
                results = await asyncio.gather(*(t[1] for t in tasks), return_exceptions=True)
                for idx, (cog_name, _) in enumerate(tasks):
                    result = results[idx]
                    if isinstance(result, Exception):
                        logger.error(f"Error getting memory usage for cog {cog_name}: {result}")
                        metrics["cogs"][cog_name] = {"error": str(result)}
                    else:
                        metrics["cogs"][cog_name] = result
            except Exception as e:
                logger.error(f"Failed to take or process tracemalloc snapshot: {e}")
        logger.debug(f"Resource metrics: {metrics}")
        return metrics

    def _get_system_metrics(self):
        """Get system resource metrics"""
        metrics = {}
        try:
            process = psutil.Process(os.getpid())
            metrics["cpu_percent"] = process.cpu_percent()
            memory_info = process.memory_info()
            metrics["memory_rss"] = memory_info.rss
            metrics["memory_vms"] = memory_info.vms
            metrics["system_cpu"] = psutil.cpu_percent()
            metrics["system_memory"] = psutil.virtual_memory().percent
            metrics["python_threads"] = len(process.threads())
        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")
        return metrics

    def _get_bot_metrics(self):
        """Get bot-specific metrics"""
        metrics = {}
        try:
            metrics["uptime_seconds"] = time.time() - self.bot.startTime
            metrics["guild_count"] = len(self.bot.guilds)
            metrics["user_count"] = sum(g.member_count for g in self.bot.guilds if hasattr(g, 'member_count'))
            metrics["command_count"] = len(self.bot.commands)
            metrics["cog_count"] = len(self.bot.cogs)
        except Exception as e:
            logger.error(f"Error collecting bot metrics: {e}")
        return metrics

    def _get_cog_memory_usage(self, cog, snapshot):
        """Get memory usage for a specific cog"""
        metrics = {"memory_usage": 0}
        
        try:
            # Get the module path for the cog
            cog_module_path = cog.__module__
            
            # Simplified and safer trace processing
            memory_usage = 0
            for stat in snapshot.statistics('filename'):
                try:
                    # Safer check that doesn't depend on trace structure
                    if cog_module_path in stat.traceback._frames[0][0]:
                        memory_usage += stat.size
                except (IndexError, AttributeError):
                    # Skip any malformed traces
                    pass
            
            metrics["memory_usage"] = memory_usage
        except Exception as e:
            logger.error(f"Error in _get_cog_memory_usage: {e}", exc_info=True)
            
        return metrics

    def get_current_usage(self) -> Dict[str, Any]:
        """
        Get current resource usage statistics
        
        Returns:
            Dict containing current resource usage metrics
        """
        cpu_percent = self.process.cpu_percent(interval=0.1)
        memory_usage = self.process.memory_info().rss / (1024 * 1024)  # MB
        system_cpu = psutil.cpu_percent(interval=None)
        system_memory = psutil.virtual_memory().percent
        
        return {
            "bot": {
                "cpu_percent": cpu_percent,
                "memory_mb": memory_usage
            },
            "system": {
                "cpu_percent": system_cpu,
                "memory_percent": system_memory
            },
            "cogs": {name: {
                "memory_mb": metrics.memory_usage,
                "commands": metrics.command_count,
                "listeners": metrics.listener_count,
                "objects": metrics.objects_count
            } for name, metrics in self.cog_metrics.items()},
            "timestamp": datetime.now().isoformat()
        }
    
    def get_detailed_cog_stats(self) -> List[Dict[str, Any]]:
        """Get detailed statistics about each cog for display"""
        stats = []
        
        for cog_name, metrics in self.cog_metrics.items():
            stats.append({
                "name": cog_name,
                "memory_mb": metrics.memory_usage,
                "commands": metrics.command_count,
                "listeners": metrics.listener_count,
                "objects": metrics.objects_count
            })
        
        # Sort by memory usage (descending)
        return sorted(stats, key=lambda x: x["memory_mb"], reverse=True)
