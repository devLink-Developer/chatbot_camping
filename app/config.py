from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Configuración de la aplicación"""

    # Database
    database_url: str = "postgresql://chatbot:password@postgres:5432/aca_lujan_bot"

    # WhatsApp
    whatsapp_phone_id: str
    whatsapp_access_token: str
    whatsapp_verify_token: str

    # App
    debug: bool = False
    log_level: str = "INFO"
    secret_key: str

    # Timeouts
    session_timeout_seconds: int = 900
    inactive_timeout_seconds: int = 1800

    # API
    api_title: str = "Aca Lujan Chatbot"
    api_version: str = "1.0.0"

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
