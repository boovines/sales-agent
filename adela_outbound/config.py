from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    BRAVE_API_KEY: str = ''
    GROK_API_KEY: str = ''
    GITHUB_TOKEN: str = ''
    ANTHROPIC_API_KEY: str = ''
    FIRECRAWL_API_KEY: str = ''
    PERPLEXITY_API_KEY: str = ''
    COMPOSIO_API_KEY: str = ''
    DAILY_DISCOVERY_CAP: int = 20
    DISCOVERY_INTERVAL_HOURS: int = 12
    DB_PATH: str = 'adela.db'
    DASHBOARD_TOKEN: str = 'dev-token'

    class Config:
        env_file = '.env'
        env_file_encoding = 'utf-8'


config = Settings()
