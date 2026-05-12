import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    database_url: str
    
    openai_api_key: str
    openai_base_url: str
    openai_model: str
    
    podcast_index_api_key: str | None
    podcast_index_api_secret: str | None
    youtube_api_key: str | None
    
    postgres_password: str | None
    postgres_db: str | None
    

def _required_env(name: str) -> str:
    value = os.getenv(name)
    
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value

def get_settings() -> Settings:
    return Settings(
        database_url=_required_env("DATABASE_URL"),
        openai_api_key=_required_env("OPENAI_API_KEY"),
        openai_base_url=os.getenv("OPENAI_BASE_URL", "https://openrouter.ai/api/v1"),
        openai_model=os.getenv("OPENAI_MODEL", "openai/gpt-4o-mini"),
        podcast_index_api_key=os.getenv("PODCAST_INDEX_API_KEY"),
        podcast_index_api_secret=os.getenv("PODCAST_INDEX_API_SECRET"),
        youtube_api_key=os.getenv("YOUTUBE_API_KEY"),
        postgres_password=os.getenv("POSTGRES_PASSWORD"),
        postgres_db=os.getenv("POSTGRES_DB"),
    )
    

settings = get_settings()