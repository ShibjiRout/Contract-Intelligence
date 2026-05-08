from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # MongoDB
    MONGODB_URL: str
    MONGODB_DB_NAME: str = "contract_platform"

    # PostgreSQL
    POSTGRES_DSN: str
    POSTGRES_DB: str = "contract_platform"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = ""

    # Qdrant
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_API_KEY: str = ""

    # Neo4j
    NEO4J_URL: str
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str

    # Redis
    REDIS_URL: str
    CELERY_BROKER_URL: str
    CELERY_RESULT_BACKEND: str
    UPSTASH_REDIS_TOKEN: str = ""

    # Azure Storage
    AZURE_STORAGE_CONNECTION_STRING: str
    AZURE_STORAGE_CONTAINER_NAME: str = "contracts"
    AZURE_FILE_SHARE_CONNECTION_STRING: str
    AZURE_FILE_SHARE_NAME: str = "contract-temp"

    # OpenAI
    OPENAI_API_KEY: str
    LLM_MODEL: str = "gpt-4o"
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_MODEL_VERSION: str = "1.0"

    # OCR
    OCR_PROVIDER: str = "azure"
    AZURE_OCR_ENDPOINT: str = ""
    AZURE_OCR_KEY: str = ""

    # Auth
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Encryption
    ENCRYPTION_KEY: str

    # Observability
    APPLICATIONINSIGHTS_CONNECTION_STRING: str = ""

    # App
    APP_ENV: str = "development"
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    LOG_LEVEL: str = "INFO"
    ALLOWED_ORIGINS: str = "http://localhost:5173"


settings = Settings()
