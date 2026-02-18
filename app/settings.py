from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    HF_TOKEN: SecretStr
    POSTGRES_DSN: SecretStr

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


SETTINGS = Settings()  # type: ignore

if __name__ == "__main__":
    print(SETTINGS)
