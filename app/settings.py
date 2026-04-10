from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    HF_TOKEN: SecretStr
    POSTGRES_DSN: SecretStr
    OPENAI_API_KEY: SecretStr
    OPENAI_API_BASE_URL: str

    RABBITMQ_URL: str
    REDIS_URL: str

    # JWT Settings
    SECRET_KEY: SecretStr = SecretStr("super-secret-key-please-change-in-prod")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 120

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


SETTINGS = Settings()  # type: ignore

if __name__ == "__main__":
    print(SETTINGS)
