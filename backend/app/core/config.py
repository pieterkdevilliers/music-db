from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    secret_key: str = "change-me-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7  # 7 days

    # Roon Core connection (IP address required; mDNS not available inside Docker)
    roon_host: str = ""
    roon_port: int = 9330

    # Anthropic API key for AI enrichment
    anthropic_api_key: str = ""


settings = Settings()
