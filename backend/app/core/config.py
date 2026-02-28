from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "AITutor API"
    DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost:5430/aitutordb"
    SECRET_KEY: str = "super_secret_key_change_in_production"
    ADMIN_REGISTRATION_KEY: str = "change_this_admin_registration_key"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7 # 7 days
    PREMIUM_TRIAL_DAYS: int = 7
    FREE_DAILY_COURSE_LIMIT: int = 1
    FREE_DAILY_LESSON_LIMIT: int = 2
    
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
