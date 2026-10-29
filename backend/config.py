import os
from pathlib import Path
from pydantic import BaseModel

BASE_DIR = Path(__file__).resolve().parent

# Automatically load backend/.env if present
env_file = BASE_DIR / ".env"
if env_file.exists():
    with open(env_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                os.environ.setdefault(key.strip(), val.strip())

INSECURE_SECRETS = {
    "your_secure_random_jwt_secret_here",
    "default",
    "change_in_production",
    "",
}

jwt_secret_candidate = os.getenv("JWT_SECRET", "").strip()
if not jwt_secret_candidate or jwt_secret_candidate in INSECURE_SECRETS:
    raise RuntimeError(
        "Application startup refused: JWT_SECRET is missing or using default placeholder. "
        "Please set a secure, unique JWT_SECRET in backend/.env."
    )

class Settings(BaseModel):
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    CORS_ORIGINS: list[str] = [
        origin.strip()
        for origin in os.getenv(
            "CORS_ORIGINS",
            "http://localhost:8443,http://localhost:5173,http://127.0.0.1:5173,http://127.0.0.1:8443"
        ).split(",")
        if origin.strip()
    ]
    JWT_SECRET: str = jwt_secret_candidate
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./medisense.db")
    STORAGE_DIR: Path = BASE_DIR / "storage"
    REPORTS_DIR: Path = STORAGE_DIR / "reports"
    AVATARS_DIR: Path = STORAGE_DIR / "avatars"
    REPORT_TTL_HOURS: int = int(os.getenv("REPORT_TTL_HOURS", "24"))
    MAX_UPLOAD_SIZE_MB: int = int(os.getenv("MAX_UPLOAD_SIZE_MB", "25"))

    # Model paths relative to backend root
    MODELS_DIR: Path = BASE_DIR / "models" / "models"

settings = Settings()
settings.STORAGE_DIR.mkdir(parents=True, exist_ok=True)
settings.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
settings.AVATARS_DIR.mkdir(parents=True, exist_ok=True)
