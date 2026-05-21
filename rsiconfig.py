import os
from dotenv import load_dotenv

load_dotenv()

# Database Configuration
DB_TYPE = os.getenv("DB_TYPE", "sqlite")  # sqlite, postgresql, mongodb
DB_PATH = os.getenv("DB_PATH", "screener.db")  # For SQLite
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "stock_screener")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")

# MongoDB Configuration
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB = os.getenv("MONGO_DB", "stock_screener")

# Screening Parameters
RSI_PERIOD = int(os.getenv("RSI_PERIOD", "14"))
RSI_OVERSOLD = int(os.getenv("RSI_OVERSOLD", "30"))
RSI_OVERBOUGHT = int(os.getenv("RSI_OVERBOUGHT", "70"))

# Timeframe
TIMEFRAME = os.getenv("TIMEFRAME", "60")  # 60 = 1 hour

# Scan Intervals (in minutes)
SCAN_INTERVAL = int(os.getenv("SCAN_INTERVAL", "60"))

# Stock Lists
STOCK_LISTS = {
    "US500": "data/stocks/us500.txt",
    "UK100": "data/stocks/uk100.txt",
    "CAC40": "data/stocks/cac40.txt",
    "NASDAQ": "data/stocks/nasdaq.txt",
}

# Dashboard Configuration
DASHBOARD_PORT = int(os.getenv("DASHBOARD_PORT", "8501"))
DASHBOARD_HOST = os.getenv("DASHBOARD_HOST", "localhost")

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", "screener.log")
