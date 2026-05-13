from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str
    GEMINI_API_KEY: str
    TWILIO_AUTH_TOKEN: str = ""  # Optional for local testing

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()