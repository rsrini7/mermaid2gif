"""
Pydantic Settings-based configuration for Mermaid-GIF.

All secrets and configuration parameters are loaded from environment variables
or .env file. Strict validation is enforced at startup.
"""

import sys
from pathlib import Path
from typing import Optional

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    """
    Application configuration with strict validation.
    
    Secrets are loaded from environment variables or .env file.
    Invalid configuration results in immediate process termination.
    """
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    
    # ============================================
    # LLM Provider Configuration
    # ============================================
    
    groq_api_key: Optional[str] = Field(
        default=None,
        description="Groq API key (optional, must start with 'gsk_' if provided)",
    )
    
    openrouter_api_key: Optional[str] = Field(
        default=None,
        description="OpenRouter API key (optional, must start with 'sk-or-' if provided)",
    )
    
    litellm_model: str = Field(
        default="groq/llama-3.3-70b-versatile",
        description="LiteLLM model identifier",
    )
    
    # ============================================
    # Browser Configuration
    # ============================================
    
    chromium_executable_path: Optional[Path] = Field(
        default=None,
        description="Path to Chromium executable (auto-detected if not set)",
    )
    
    browser_timeout_ms: int = Field(
        default=30000,
        ge=1000,
        le=300000,
        description="Browser operation timeout in milliseconds",
    )
    
    viewport_width: int = Field(
        default=1920,
        ge=800,
        le=3840,
        description="Browser viewport width",
    )
    
    viewport_height: int = Field(
        default=1080,
        ge=600,
        le=2160,
        description="Browser viewport height",
    )
    
    # ============================================
    # FFmpeg Configuration
    # ============================================
    
    ffmpeg_path: Optional[Path] = Field(
        default=None,
        description="Path to FFmpeg executable (auto-detected if not set)",
    )
    
    # ============================================
    # Animation Configuration
    # ============================================
    
    default_animation_duration: float = Field(
        default=5.0,
        ge=1.0,
        le=60.0,
        description="Default animation duration in seconds",
    )
    
    default_fps: int = Field(
        default=30,
        ge=10,
        le=60,
        description="Default frame rate for GIF output",
    )
    
    # ============================================
    # Logging Configuration
    # ============================================
    
    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
    )
    
    structured_logging: bool = Field(
        default=True,
        description="Enable structured JSON logging",
    )
    
    # ============================================
    # Validators
    # ============================================
    
    @field_validator("groq_api_key")
    @classmethod
    def validate_groq_key(cls, v: Optional[str]) -> Optional[str]:
        """Validate Groq API key format if provided."""
        if v is not None and not v.startswith("gsk_"):
            raise ValueError("GROQ_API_KEY must start with 'gsk_'")
        return v
    
    @field_validator("openrouter_api_key")
    @classmethod
    def validate_openrouter_key(cls, v: Optional[str]) -> Optional[str]:
        """Validate OpenRouter API key format if provided."""
        if v is not None:
            if not v.startswith("sk-or-"):
                raise ValueError("OPENROUTER_API_KEY must start with 'sk-or-'")
            if len(v) < 20:
                raise ValueError("OPENROUTER_API_KEY appears to be invalid (too short)")
        return v
    
    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level."""
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(f"LOG_LEVEL must be one of {valid_levels}")
        return v_upper
    
    @model_validator(mode="after")
    def validate_api_keys(self) -> "Config":
        """Ensure at least one LLM API key is provided."""
        if not self.groq_api_key and not self.openrouter_api_key:
            raise ValueError(
                "At least one LLM API key must be provided: GROQ_API_KEY or OPENROUTER_API_KEY"
            )
        return self


from pydantic import model_validator


def load_config() -> Config:
    """
    Load and validate configuration.
    
    Terminates the process immediately if configuration is invalid.
    
    Returns:
        Config: Validated configuration object
    """
    try:
        config = Config()
        return config
    except Exception as e:
        print(f"FATAL: Configuration validation failed: {e}", file=sys.stderr)
        sys.exit(1)


# Global configuration instance
# This will be initialized on first import
_config: Optional[Config] = None


def get_config() -> Config:
    """
    Get the global configuration instance.
    
    Returns:
        Config: The global configuration object
    """
    global _config
    if _config is None:
        _config = load_config()
    return _config
