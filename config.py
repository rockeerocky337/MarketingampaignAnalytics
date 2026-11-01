"""Project paths and database configuration, loaded from the local .env file."""

from pathlib import Path
import os

from dotenv import load_dotenv
import pymysql

BASE_DIR = Path(__file__).resolve().parent
ENV_FILE = BASE_DIR / ".env"


def database_settings():
    """Return connection options without opening a connection or printing secrets.

    Load .env beside this module regardless of the working directory. Explicit
    environment variables override values stored in .env.
    """
    load_dotenv(ENV_FILE, override=False)
    port = int(os.getenv("DB_PORT", "3306"))
    if not 1 <= port <= 65535:
        raise ValueError("DB_PORT must be between 1 and 65535.")
    database_name = os.getenv("DB_NAME", "marketing_campaign_analytics").strip()
    if not database_name:
        raise ValueError("DB_NAME cannot be empty.")
    return {
        "host": os.getenv("DB_HOST", "127.0.0.1"),
        "port": port,
        "user": os.getenv("DB_USER", "root"),
        "password": os.getenv("DB_PASSWORD", ""),
        "database": database_name,
        "charset": "utf8mb4",
        "autocommit": False,
        "connect_timeout": 10,
        "cursorclass": pymysql.cursors.DictCursor,
    }
