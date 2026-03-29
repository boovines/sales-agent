from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    BRAVE_API_KEY: str = ''
    GROK_API_KEY: str = ''
    GITHUB_TOKEN: str = ''
    ANTHROPIC_API_KEY: str = ''
    FIRECRAWL_API_KEY: str = ''
    PERPLEXITY_API_KEY: str = ''
    COMPOSIO_API_KEY: str = ''
    GMAIL_SENDER_ADDRESS: str = ''
    DAILY_DISCOVERY_CAP: int = 20
    DAILY_EMAIL_CAP: int = 20
    DAILY_GITHUB_CAP: int = 5
    DAILY_LINKEDIN_CAP: int = 10
    DISCOVERY_INTERVAL_HOURS: int = 12
    DB_PATH: str = 'adela.db'
    DASHBOARD_TOKEN: str = 'dev-token'

    class Config:
        env_file = '.env'
        env_file_encoding = 'utf-8'


config = Settings()
