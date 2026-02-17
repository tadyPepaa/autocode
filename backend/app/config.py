from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite:///autocode.db"
    secret_key: str = "change-me-in-production"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    data_dir: str = "/data/users"
    encryption_key: str = "change-me-in-production"
    instagram_app_id: str = ""
    instagram_app_secret: str = ""
    facebook_app_id: str = ""
    facebook_app_secret: str = ""
    app_base_url: str = "http://localhost:8000"

    class Config:
        env_prefix = "AUTOCODE_"


settings = Settings()
