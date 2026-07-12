import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load env file explicitly
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env"))

class Settings(BaseSettings):
    SECRET_KEY: str = "supersecretjwtkeyreplaceinproduction123456!"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    MONGODB_URI: str = "mongodb://localhost:27017"
    MONGO_DB_NAME: str = "meeting_notes_db"
    CHROMADB_DIR: str = "./chroma_db"
    GEMINI_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    USE_MOCK_SERVICES: bool = True

    class Config:
        env_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env")
        extra = "ignore"

settings = Settings()
