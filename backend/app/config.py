from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite:///autocode.db"
    secret_key: str = "change-me-in-production"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    data_dir: str = "/data/users"
    encryption_key: str = "change-me-in-production"

    class Config:
        env_prefix = "AUTOCODE_"


settings = Settings()
