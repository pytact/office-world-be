from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://postgres:1112@db:5432/office_world"
    
    # Redis
    redis_url: str = "redis://redis:6379/0"
    
    # Celery
    celery_broker_url: str = "redis://redis:6379/0"
    celery_result_backend: str = "redis://redis:6379/0"
    
    # Email SMTP Configuration
    email_sender: str = "shahidm@pytact.com"
    email_app_password: str = "pnkd sowf pghx tiqq"
    email_smtp_host: str = "smtp.gmail.com"
    email_smtp_port: int = 587
    frontend_url: str = "http://localhost:3000"  # Frontend URL for invitation links
    
    # API
    api_title: str = "FastAPI Boilerplate"
    api_version: str = "1.0.0"
    api_prefix: str = "/v1"
    
    # JWT
    jwt_secret_key: str = "your-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_seconds: int = 3600  # 1 hour
    
    # Environment
    environment: str = "local"
    debug: bool = True
    
    # CORS
    cors_origins: List[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:5173",
        "http://localhost:8080",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:8080",
    ]  # Add your frontend URLs here
    cors_allow_credentials: bool = True
    cors_allow_methods: List[str] = ["*"]
    cors_allow_headers: List[str] = ["*"]
    
    model_config = {
        "env_file": ".env",
        "case_sensitive": False,
    }


settings = Settings()

