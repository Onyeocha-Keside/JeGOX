from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    # OpenAI Settings
    OPENAI_API_KEY: str
    OPENAI_MODEL: str = "gpt-3.5-turbo"
    MAX_TOKENS: int = 500
    TEMPERATURE: float = 0.7
    
    # Qdrant Cloud Settings
    QDRANT_HOST: str
    QDRANT_API_KEY: str
    QDRANT_COLLECTION_NAME: str = "Fred"
    
    # App Settings
    APP_NAME: str = "Fred - Company Assistant"
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    
    # Document Processing Settings
    RAW_DATA_DIR: str = "data/raw"
    PROCESSED_DATA_DIR: str = "data/processed"
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200
    
    # Security Settings
    ENCRYPTION_KEY: str
    MAX_REQUESTS_PER_MINUTE: int = 60
    
    class Config:
        env_file = ".env"

@lru_cache()
def get_settings() -> Settings:
    """Get settings instance."""
    return Settings()

# Export Settings instance
settings = get_settings()