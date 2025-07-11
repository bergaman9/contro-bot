"""
Configuration management for Contro Discord Bot
Uses Pydantic for type-safe configuration with environment variable support
"""

import os
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings


class DatabaseConfig(BaseModel):
    """Database configuration settings."""
    url: str = Field(default="mongodb://localhost:27017", env="DB_URL")
    database_name: str = Field(default="contro_bot", env="DB_DATABASE_NAME")
    max_pool_size: int = Field(default=20, env="DB_MAX_POOL_SIZE")
    min_pool_size: int = Field(default=5, env="DB_MIN_POOL_SIZE")
    connect_timeout: int = Field(default=30000, env="DB_CONNECT_TIMEOUT")
    server_selection_timeout: int = Field(default=5000, env="DB_SERVER_SELECTION_TIMEOUT")
    socket_timeout: int = Field(default=120000, env="DB_SOCKET_TIMEOUT")
    heartbeat_frequency: int = Field(default=120000, env="DB_HEARTBEAT_FREQUENCY")
    max_idle_time: int = Field(default=180000, env="DB_MAX_IDLE_TIME")


class CacheConfig(BaseModel):
    """Cache configuration settings."""
    enabled: bool = Field(default=True, env="CACHE_ENABLED")
    redis_url: Optional[str] = Field(default=None, env="CACHE_REDIS_URL")
    default_ttl: int = Field(default=3600, env="CACHE_DEFAULT_TTL")
    max_size: int = Field(default=1000, env="CACHE_MAX_SIZE")
    strategy: str = Field(default="LRU", env="CACHE_STRATEGY")


class APIConfig(BaseModel):
    """API configuration settings."""
    enabled: bool = Field(default=True, env="API_ENABLED")
    host: str = Field(default="0.0.0.0", env="API_HOST")
    port: int = Field(default=8080, env="API_PORT")
    cors_origins: List[str] = Field(default=["*"], env="API_CORS_ORIGINS")
    rate_limit: int = Field(default=100, env="API_RATE_LIMIT")
    rate_limit_window: int = Field(default=60, env="API_RATE_LIMIT_WINDOW")
    url: str = Field(default="", env="API_URL")
    secret_key: str = Field(default="your-secret-key-change-this", env="SECURITY_JWT_SECRET")


class LoggingConfig(BaseModel):
    """Logging configuration settings."""
    level: str = Field(default="INFO", env="LOG_LEVEL")
    file_enabled: bool = Field(default=True, env="LOG_FILE_ENABLED")
    file_path: str = Field(default="logs/bot.log", env="LOG_FILE_PATH")
    max_file_size: int = Field(default=10485760, env="LOG_MAX_FILE_SIZE")
    backup_count: int = Field(default=5, env="LOG_BACKUP_COUNT")
    format: str = Field(default="%(asctime)s - %(name)s - %(levelname)s - %(message)s", env="LOG_FORMAT")
    colored: bool = Field(default=True, env="LOG_COLORED")
    
    @field_validator('level')
    @classmethod
    def validate_level(cls, v):
        allowed = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in allowed:
            raise ValueError(f'Log level must be one of: {allowed}')
        return v.upper()


class SecurityConfig(BaseModel):
    """Security configuration settings."""
    enabled: bool = Field(default=True, env="SECURITY_ENABLED")
    jwt_secret: str = Field(default="contro-bot-ultra-secret-2024", env="SECURITY_JWT_SECRET")
    jwt_expiry: int = Field(default=3600, env="SECURITY_JWT_EXPIRY")
    password_salt_rounds: int = Field(default=12, env="SECURITY_PASSWORD_SALT_ROUNDS")


class FeatureConfig(BaseModel):
    """Feature flags configuration."""
    ai_chat: bool = Field(default=True, env="FEATURE_AI_CHAT")
    game_logs: bool = Field(default=True, env="FEATURE_GAME_LOGS")
    leveling: bool = Field(default=True, env="FEATURE_LEVELING")
    moderation: bool = Field(default=True, env="FEATURE_MODERATION")
    welcome: bool = Field(default=True, env="FEATURE_WELCOME")
    tickets: bool = Field(default=True, env="FEATURE_TICKETS")
    giveaways: bool = Field(default=True, env="FEATURE_GIVEAWAYS")
    reddit: bool = Field(default=True, env="FEATURE_REDDIT")
    spotify: bool = Field(default=True, env="FEATURE_SPOTIFY")
    tmdb: bool = Field(default=True, env="FEATURE_TMDB")


class PerformanceConfig(BaseModel):
    """Performance configuration settings."""
    max_concurrent_tasks: int = Field(default=100, env="PERFORMANCE_MAX_CONCURRENT_TASKS")
    task_timeout: int = Field(default=30, env="PERFORMANCE_TASK_TIMEOUT")
    memory_limit: int = Field(default=512, env="PERFORMANCE_MEMORY_LIMIT")


class ExternalServicesConfig(BaseModel):
    """External services API keys."""
    openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    perplexity_api_key: Optional[str] = Field(default=None, env="PERPLEXITY_API_KEY")
    guilds_api_key: Optional[str] = Field(default=None, env="GUILDS_API_KEY")
    tmdb_api_key: Optional[str] = Field(default=None, env="TMDB_API_KEY")
    reddit_client_id: Optional[str] = Field(default=None, env="REDDIT_CLIENT_ID")
    reddit_client_secret: Optional[str] = Field(default=None, env="REDDIT_CLIENT_SECRET")
    reddit_password: Optional[str] = Field(default=None, env="REDDIT_PASSWORD")
    reddit_user_agent: Optional[str] = Field(default=None, env="REDDIT_USER_AGENT")
    reddit_username: Optional[str] = Field(default=None, env="REDDIT_USERNAME")
    spotify_client_id: Optional[str] = Field(default=None, env="SPOTIFY_CLIENT_ID")
    spotify_client_secret: Optional[str] = Field(default=None, env="SPOTIFY_CLIENT_SECRET")


class AdminConfig(BaseModel):
    """Admin configuration settings."""
    admin_user_id: str = Field(default="", env="ADMIN_USER_ID")
    authorization: str = Field(default="", env="AUTHORIZATION")
    user_token: str = Field(default="", env="USER_TOKEN")
    user_id: str = Field(default="", env="USER_ID")


class ServerConfig(BaseModel):
    """Server and channel configuration."""
    session_id: str = Field(default="", env="SESSION_ID")
    teknominator_cid: str = Field(default="", env="TEKNOMINATOR_CID")
    teknominator_gid: str = Field(default="", env="TEKNOMINATOR_GID")
    community_cid: str = Field(default="", env="COMMUNITY_CID")
    community_gid: str = Field(default="", env="COMMUNITY_GID")


class Config(BaseSettings):
    """Main configuration class for Contro Discord Bot."""
    
    # Bot Configuration
    discord_token: str = Field(default="", env="CONTRO_TOKEN")
    discord_dev_token: str = Field(default="", env="CONTRO_DEV_TOKEN")
    discord_premium_token: str = Field(default="", env="CONTRO_PREMIUM_TOKEN")
    discord_prefix: str = Field(default=">", env="DISCORD_PREFIX")
    discord_dev_prefix: str = Field(default=">>", env="DISCORD_DEV_PREFIX")
    environment: str = Field(default="development", env="ENVIRONMENT")
    debug: bool = Field(default=True, env="DEBUG")
    bot_name: str = Field(default="Contro Bot", env="BOT_NAME")
    bot_version: str = Field(default="2.0.0", env="BOT_VERSION")
    
    # Sub-configurations
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    cache: CacheConfig = Field(default_factory=CacheConfig)
    api: APIConfig = Field(default_factory=APIConfig)
    logging: LoggingConfig = Field(default_factory=lambda: LoggingConfig(
        level="INFO",
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        file="logs/bot.log",
        max_size=10 * 1024 * 1024,
        backup_count=5
    ))
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    features: FeatureConfig = Field(default_factory=FeatureConfig)
    performance: PerformanceConfig = Field(default_factory=PerformanceConfig)
    external_services: ExternalServicesConfig = Field(default_factory=ExternalServicesConfig)
    admin: AdminConfig = Field(default_factory=AdminConfig)
    server: ServerConfig = Field(default_factory=ServerConfig)
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"
    
    def __init__(self, **values):
        super().__init__(**values)
        # Map environment variables to the correct field names
        if not self.discord_token:
            self.discord_token = os.environ.get("CONTRO_TOKEN", os.environ.get("DISCORD_TOKEN", ""))
        if not self.discord_dev_token:
            self.discord_dev_token = os.environ.get("CONTRO_DEV_TOKEN", os.environ.get("DISCORD_DEV_TOKEN", ""))
        if not self.discord_premium_token:
            self.discord_premium_token = os.environ.get("CONTRO_PREMIUM_TOKEN", os.environ.get("DISCORD_PREMIUM_TOKEN", ""))
        if not self.database.url or self.database.url == "mongodb://localhost:27017":
            self.database.url = os.environ.get("DB_URL", "mongodb://localhost:27017")

    @field_validator('environment')
    @classmethod
    def validate_environment(cls, v):
        allowed = ['development', 'production', 'testing']
        if v not in allowed:
            raise ValueError(f'Environment must be one of: {allowed}')
        return v

    def get_discord_token(self) -> str:
        """Get the appropriate Discord token based on environment."""
        print(f"🔍 Environment: {self.environment}")
        print(f"🔍 Debug mode: {self.debug}")
        
        if self.environment == "development":
            # Use CONTRO_DEV_TOKEN for development
            dev_token = os.environ.get("CONTRO_DEV_TOKEN", "")
            if dev_token:
                print(f"✅ Using CONTRO_DEV_TOKEN for development mode")
                return dev_token
            # Fallback to discord_dev_token if CONTRO_DEV_TOKEN not found
            token = self.discord_dev_token or self.discord_token
            print(f"⚠️  CONTRO_DEV_TOKEN not found, using fallback: {token[:20]}...")
            return token
        elif self.environment == "production":
            # Use CONTRO_PREMIUM_TOKEN for production
            premium_token = os.environ.get("CONTRO_PREMIUM_TOKEN", "")
            if premium_token:
                print(f"✅ Using CONTRO_PREMIUM_TOKEN for production mode")
                return premium_token
            # Fallback to discord_premium_token if CONTRO_PREMIUM_TOKEN not found
            token = self.discord_premium_token or self.discord_token
            print(f"⚠️  CONTRO_PREMIUM_TOKEN not found, using fallback: {token[:20]}...")
            return token
        else:
            # Default to main token (CONTRO_TOKEN)
            main_token = os.environ.get("CONTRO_TOKEN", "")
            if main_token:
                print(f"✅ Using CONTRO_TOKEN for default mode")
                return main_token
            print(f"⚠️  CONTRO_TOKEN not found, using discord_token: {self.discord_token[:20]}...")
            return self.discord_token

    def get_prefix(self) -> str:
        if self.environment == "development":
            return self.discord_dev_prefix or self.discord_prefix
        return self.discord_prefix


# Global config instance
_config: Optional[Config] = None


def get_config() -> Config:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = Config()
    return _config


def reload_config(mode: str = None) -> Config:
    """Reload configuration from environment variables."""
    global _config
    
    # Force reload environment variables from .env file
    from dotenv import load_dotenv
    load_dotenv(override=True)
    
    _config = Config()
    if mode:
        _config.environment = mode
        _config.debug = mode == 'development'
    
    return _config


def validate_config() -> bool:
    """Validate the current configuration."""
    try:
        config = get_config()
        # Additional validation logic can be added here
        return True
    except Exception as e:
        print(f"Configuration validation failed: {e}")
        return False


# Environment-specific configuration helpers
def is_development() -> bool:
    """Check if running in development mode."""
    return get_config().environment.lower() == "development"


def is_production() -> bool:
    """Check if running in production mode."""
    return get_config().environment.lower() == "production"


def is_debug() -> bool:
    """Check if debug mode is enabled."""
    return get_config().debug or is_development() 