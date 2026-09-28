from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://returnguard:returnguard_secret@localhost:5432/returnguard"
    redis_url: str = "redis://localhost:6379/0"
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin_secret"
    minio_bucket: str = "return-photos"
    smtp_host: str = "localhost"
    smtp_port: int = 1025
    email_from: str = "noreply@returnguard.io"
    groq_api_key: str = ""
    gemini_api_key: str = ""
    
    class Config:
        env_file = ".env"


settings = Settings()
