# app/core/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, computed_field
from typing import Optional

class Settings(BaseSettings):
    # MongoDB Settings
    MONGO_URI: str = Field(..., description="MongoDB Atlas Connection String")
    
    # Redis Settings
    # We support a full REDIS_URL
    REDIS_URL: Optional[str] = None

    DEBUG_ROUTER: bool = True
    
    # Pinecone Settings
    PINECONE_API_KEY: str = Field(..., description="Pinecone API Key")
    PINECONE_INDEX_NAME: str = Field(..., description="Pinecone Index Name")
    
    # OpenAI Settings
    OPENAI_API_KEY: str = Field(..., description="OpenAI API Key")
    ROUTER_MODEL: str = Field(description="The model to use for routing decisions")
    CHAT_MODEL: str = Field(description="The model to use for routing decisions")
    # Google Service Account Settings
    GOOGLE_SERVICE_ACCOUNT_FILE: str = Field(..., description="Path to Google Service Account JSON file")

    JWT_SECRET_KEY: str = Field()
    JWT_ALGORITHM: str = Field()

    RESEND_API_KEY: str = Field()
    RESEND_EMAIL: str = Field()

    # App Settings
    ENVIRONMENT: str = Field(default="development")
    DEBUG: bool = Field(default=True)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore" # Ignore extra fields in the .env file
    )

    @property
    def REDIS_CONNECTION(self) -> str:
        """
        Constructs the standard Redis connection string used by LangChain.
        Format: redis://:password@host:port/db
        """
        if self.REDIS_URL:
            return self.REDIS_URL

# Instantiate a singleton to be imported across the application
settings = Settings()