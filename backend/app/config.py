from pathlib import Path
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=[str(BASE_DIR / ".env"), ".env"],
        extra="ignore",
    )

    db_url: str = f"sqlite:///{BASE_DIR / 'jobs.db'}"
    llm_base_url: str = "http://localhost:11434/v1"
    llm_api_key: str = "ollama"
    llm_model: str = "qwen2.5:7b-instruct"
    embed_model: str = "BAAI/bge-m3"          # multilingual: en/hi/kn queries hit English jobs
    whisper_model: str = "large-v3"
    whisper_device: str = "auto"
    whisper_compute: str = "int8"
    jitsi_base: str = "https://meet.jit.si"   # open source; self-host later
    coding_base_url: str = ""                 # e.g. your self-hosted collaborative editor
    dev_mode: bool = True

    @field_validator("db_url", mode="after")
    @classmethod
    def resolve_db_path(cls, v: str) -> str:
        prefix = "sqlite:///./"
        if v.startswith(prefix):
            rel = v[len(prefix):]
            return f"sqlite:///{BASE_DIR / rel}"
        return v


settings = Settings()