import time
import logging
import threading
from datetime import datetime

class HeartbeatMonitor:
    """
    A simple heartbeat monitor that writes timestamps to a log file
    to indicate that the application is still running.
    """
    
    def __init__(self, log_path: str, interval: int = 30):
        """
        Initialize the heartbeat monitor
        
        Args:
            log_path: Path to the log file where heartbeats will be recorded
            interval: Time between heartbeats in seconds (default: 30)
        """
        self.log_path = log_path
        self.interval = interval
        self.running = False
        self.thread = None
        self.logger = logging.getLogger("heartbeat")
        
        # Create a file handler for the heartbeat log
        file_handler = logging.FileHandler(log_path)
        file_handler.setFormatter(logging.Formatter("%(asctime)s - HEARTBEAT - %(message)s"))
        self.logger.addHandler(file_handler)
        self.logger.setLevel(logging.INFO)
    
    def start(self):
        """Start the heartbeat monitor"""
        if self.running:
            return
            
        self.running = True
        self.logger.info("Heartbeat monitoring started")
        
        # Create and start the monitoring thread
        self.thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self.thread.start()
    
    def stop(self):
        """Stop the heartbeat monitor"""
        if not self.running:
            return
            
        self.running = False
        self.logger.info("Heartbeat monitoring stopped")
        
        # Wait for the thread to complete if it's running
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2.0)
    
    def _heartbeat_loop(self):
        """Background thread that writes periodic heartbeats to the log file"""
        try:
            while self.running:
                self._log_heartbeat()
                # Sleep for the specified interval
                time.sleep(self.interval)
        except Exception as e:
            self.logger.error(f"Error in heartbeat loop: {e}")
            self.running = False
    
    def _log_heartbeat(self):
        """Write a single heartbeat entry to the log"""
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.logger.info(f"Bot is alive at {timestamp}")
        except Exception as e:
            self.logger.error(f"Failed to write heartbeat: {e}")
