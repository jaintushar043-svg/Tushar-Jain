from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg2://aegis:aegis_dev_pw@localhost:5432/aegis"


settings = Settings()
