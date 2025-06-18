import os
import json
import logging
from typing import Dict, List, Any, Optional, Set
import dotenv

logger = logging.getLogger('config_manager')

class ConfigManager:
    """
    Manages bot configuration, including client-specific settings
    and controlled loading of cogs based on client permissions.
    """
    
    def __init__(self, config_path: str = "config/config.json"):
        """
        Initialize the configuration manager.
        
        Args:
            config_path: Path to the config.json file
        """
        self.config_path = config_path
        self.config = self._load_config()
        self._load_env_variables()

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from JSON file"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            logger.info(f"Configuration loaded from {self.config_path}")
            return config
        except FileNotFoundError:
            logger.error(f"Configuration file not found: {self.config_path}")
            # Create a minimal default config
            default_config = {
                "default_prefix": "!",
                "owners": [],
                "default_cogs": ["utility", "config", "help"],
                "client_settings": {}
            }
            return default_config
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON in configuration file: {self.config_path}")
            return {}

    def _load_env_variables(self):
        """Load environment variables from .env file"""
        dotenv.load_dotenv()
        self.env_vars = {}
        
        # Load only the three standard tokens - direct access from environment
        dev_token = os.getenv("CONTRO_DEV_TOKEN")
        main_token = os.getenv("CONTRO_TOKEN")
        premium_token = os.getenv("CONTRO_PREMIUM_TOKEN")
        
        self.env_vars["tokens"] = {}
        if main_token:
            self.env_vars["tokens"]["main"] = main_token
            logger.info("Loaded MAIN token from environment")
        if dev_token:
            self.env_vars["tokens"]["dev"] = dev_token
            logger.info("Loaded DEV token from environment")
        if premium_token:
            self.env_vars["tokens"]["premium"] = premium_token
            logger.info("Loaded PREMIUM token from environment")
        
        # Log available tokens for debugging
        logger.info(f"Available tokens: {', '.join(self.env_vars['tokens'].keys())}")

    def get_client_by_name(self, name: str) -> str:
        """Get client ID by name (exact match or case-insensitive)"""
        # Direct match
        if name in self.config.get("client_settings", {}):
            return name
        
        # Case-insensitive match
        name_lower = name.lower()
        for client_name in self.config.get("client_settings", {}):
            if client_name.lower() == name_lower:
                return client_name
                
        return name  # Return original if no match found

    def get_token(self, client_id: str = "main") -> str:
        """
        Get the token for a specific client
        
        Args:
            client_id: Client identifier
            
        Returns:
            str: Token for the specified client or empty string if not found
        """
        original_client_id = client_id
        client_id_lower = client_id.lower()
        
        # Print detailed debug info
        logger.info(f"Getting token for client: '{original_client_id}'")
        
        # Direct environment variable check first - only support the three main tokens
        if client_id_lower == "dev":
            dev_token = os.getenv("CONTRO_DEV_TOKEN")
            if dev_token:
                logger.info(f"✓ Using CONTRO_DEV_TOKEN for '{original_client_id}'")
                return dev_token
            else:
                logger.warning(f"✗ CONTRO_DEV_TOKEN environment variable not found for '{original_client_id}'")
                
        elif client_id_lower == "main":
            main_token = os.getenv("CONTRO_TOKEN")
            if main_token:
                logger.info(f"✓ Using CONTRO_TOKEN for '{original_client_id}'")
                return main_token
            else:
                logger.warning(f"✗ CONTRO_TOKEN environment variable not found for '{original_client_id}'")
                
        elif client_id_lower == "premium":
            premium_token = os.getenv("CONTRO_PREMIUM_TOKEN")
            if premium_token:
                logger.info(f"✓ Using CONTRO_PREMIUM_TOKEN for '{original_client_id}'")
                return premium_token
            else:
                logger.warning(f"✗ CONTRO_PREMIUM_TOKEN environment variable not found for '{original_client_id}'")
        else:
            # For other clients, log warning that we're using main token
            logger.warning(f"Client '{original_client_id}' is not a standard client (main/dev/premium)")
            logger.warning(f"Using main token for non-standard client '{original_client_id}'")
            
        # IMPORTANT: Special handling for dev mode - we should NOT fallback to main token for dev mode
        if client_id_lower == "dev":
            logger.error("No DEV token found. Exiting to prevent using main bot token in dev mode.")
            return ""  # Return empty token to force exit in main.py
            
        # Last resort fallback to main token (but not for dev mode)
        main_token = os.getenv("CONTRO_TOKEN")
        if main_token:
            logger.warning(f"⚠ No specific token found for '{original_client_id}', falling back to CONTRO_TOKEN")
            return main_token
            
        logger.error(f"✗ No token found for '{original_client_id}' and no fallback available")
        return ""

    def get_prefix(self, client_id: str = None) -> str:
        """
        Get the command prefix for a specific client
        
        Args:
            client_id: Client identifier
            
        Returns:
            str: Command prefix for the specified client
        """
        default_prefix = self.config.get("default_prefix", "!")
        
        # Handle name-based client IDs
        if client_id:
            client_id = self.get_client_by_name(client_id)
            
        # If client_id is specified and exists in client_settings, get its prefix
        if client_id and client_id in self.config.get("client_settings", {}):
            return self.config["client_settings"][client_id].get("prefix", default_prefix)
        
        return default_prefix

    def get_enabled_cogs(self, client_id: str = None) -> Set[str]:
        """
        Get the set of enabled cogs for a specific client
        
        Args:
            client_id: Client identifier
            
        Returns:
            Set[str]: Set of enabled cog names
        """
        logger.info(f"Getting enabled cogs for client: '{client_id}'")
        
        # Get the default cogs from the config
        default_cogs = set(self.config.get("default_cogs", []))
        logger.debug(f"Default cogs: {default_cogs}")
        
        # If no client_id specified, return the default cogs
        if not client_id:
            logger.info(f"No client_id specified, returning default cogs: {default_cogs}")
            return default_cogs
        
        # Handle name-based client IDs
        client_id = self.get_client_by_name(client_id)
        logger.debug(f"Resolved client_id: '{client_id}'")
        
        # Check if client exists in configuration
        if client_id not in self.config.get("client_settings", {}):
            logger.warning(f"Client '{client_id}' not found in client_settings, returning default cogs")
            return default_cogs
            
        # Get client configuration
        client_config = self.config["client_settings"][client_id]
        logger.debug(f"Client config for '{client_id}': {client_config}")
        
        # Check for 'enabled_cogs' setting
        enabled_cogs_setting = client_config.get("enabled_cogs")
        logger.debug(f"Enabled cogs setting for '{client_id}': {enabled_cogs_setting}")
        
        # Handle "all" cogs setting - scan cogs directory
        if enabled_cogs_setting == "all":
            logger.info(f"Client '{client_id}' is configured to load ALL available cogs")
            
            # Find all available cogs by scanning the cogs directory
            cogs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "cogs")
            logger.debug(f"Scanning cogs directory: {cogs_dir}")
            
            if os.path.exists(cogs_dir):
                all_cogs = set()
                for filename in os.listdir(cogs_dir):
                    if filename.endswith(".py") and not filename.startswith("_"):
                        all_cogs.add(filename[:-3])
                logger.info(f"Found {len(all_cogs)} cogs in directory: {all_cogs}")
                return all_cogs
            else:
                logger.warning(f"Cogs directory not found: {cogs_dir}, falling back to default cogs")
                return default_cogs
        
        # Regular case - load specific cogs
        if isinstance(enabled_cogs_setting, list):
            client_cogs = set(enabled_cogs_setting)
            combined_cogs = default_cogs.union(client_cogs)
            logger.info(f"Client '{client_id}' has {len(client_cogs)} specific cogs, combined with defaults: {combined_cogs}")
            return combined_cogs
        
        # Fallback for invalid configuration
        logger.warning(f"Invalid 'enabled_cogs' configuration for client '{client_id}', using default cogs")
        return default_cogs

    def is_owner(self, user_id: int) -> bool:
        """
        Check if a user is a bot owner
        
        Args:
            user_id: Discord user ID to check
            
        Returns:
            bool: True if the user is an owner, False otherwise
        """
        return user_id in self.config.get("owners", [])

    def get_client_name(self, client_id: str) -> str:
        """Get the display name for a client"""
        # Special case for built-in client types
        if client_id == "main":
            return self.config.get("client_settings", {}).get("main", {}).get("name", "Contro Bot")
        elif client_id == "dev":
            return self.config.get("client_settings", {}).get("dev", {}).get("name", "Contro Development")
        elif client_id == "premium":
            return self.config.get("client_settings", {}).get("premium", {}).get("name", "Contro Premium")
        
        # Handle name-based client IDs
        client_id = self.get_client_by_name(client_id)
        
        # If it's in client_settings, return its name
        if client_id in self.config.get("client_settings", {}):
            return self.config["client_settings"][client_id].get("name", client_id)
        
        return f"Client {client_id}"

    def is_cog_enabled(self, cog_name: str, client_id: str = None) -> bool:
        """Check if a specific cog is enabled for the client"""
        enabled_cogs = self.get_enabled_cogs(client_id)
        return cog_name.lower() in [c.lower() for c in enabled_cogs]

    def get_all_available_cogs(self) -> Set[str]:
        """Get all available cogs across all configurations"""
        all_cogs = set(self.config.get("default_cogs", []))
        
        for client_settings in self.config.get("client_settings", {}).values():
            all_cogs.update(client_settings.get("enabled_cogs", []))
            
        return all_cogs
    
    def get_available_clients(self) -> List[str]:
        """
        Get list of all configured clients
        
        Returns:
            List[str]: List of client IDs that are available in the configuration
        """
        # Always include the standard clients
        clients = ["main", "dev", "premium"]
        
        # Add any custom clients from the configuration
        for client_id in self.config.get("client_settings", {}).keys():
            if client_id not in clients:
                clients.append(client_id)
        
        return clients
    
    def save_config(self) -> bool:
        """Save the current configuration back to the JSON file"""
        try:
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4)
            logger.info(f"Configuration saved to {self.config_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to save configuration: {str(e)}")
            return False

    def get_description(self, client_id: str = None) -> str:
        """
        Get the description for a specific client
        
        Args:
            client_id: Client identifier
            
        Returns:
            str: Description for the specified client
        """
        default_description = "Contro Discord Bot"
        
        # Handle name-based client IDs
        if client_id:
            client_id = self.get_client_by_name(client_id)
            
        # If client_id is specified and exists in client_settings, get its description
        if client_id and client_id in self.config.get("client_settings", {}):
            return self.config["client_settings"][client_id].get("description", default_description)
        
        return default_description
        
    def get_main_client(self) -> str:
        """
        Get the main client ID
        
        Returns:
            str: Main client ID, defaults to 'main'
        """
        # Return the main client ID from config or default to 'main'
        return self.config.get("main_client", "main")
    
    def get_dev_client(self) -> str:
        """
        Get the development client ID
        
        Returns:
            str: Development client ID, defaults to 'dev'
        """
        # Return the dev client ID from config or default to 'dev'
        return self.config.get("dev_client", "dev")
    
    def get_premium_client(self) -> str:
        """
        Get the premium client ID
        
        Returns:
            str: Premium client ID, defaults to 'premium'
        """
        # Return the premium client ID from config or default to 'premium'
        return self.config.get("premium_client", "premium")
