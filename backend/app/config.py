import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv(
    dotenv_path=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env")
)

class Settings(BaseSettings):
    LLM_PROVIDER: str = "groq"
    LLM_MODEL: str = "openai/gpt-oss-20b"
    LLM_BASE_URL: str = "http://localhost:11434"
    GROQ_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    
    SEARCH_PROVIDER: str = "tavily"
    TAVILY_API_KEY: str = ""
    BRAVE_API_KEY: str = ""
    
    EMBEDDING_MODEL_NAME: str = "all-MiniLM-L6-v2"
    EMBEDDING_DEVICE: str = "cpu"
    
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "aifutureprocess"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    
    LANGCHAIN_TRACING_V2: bool = False
    LANGCHAIN_ENDPOINT: str = "https://api.smith.langchain.com"
    LANGCHAIN_API_KEY: str = ""
    LANGCHAIN_PROJECT: str = "aipossibilities"

    @property
    def database_url(self) -> str:
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

settings = Settings()
