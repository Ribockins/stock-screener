"""Database Module - Support for SQLite, PostgreSQL, and MongoDB"""

import sqlite3
import pandas as pd
from typing import Optional, List, Dict
from datetime import datetime
from dataclasses import asdict
import logging
from abc import ABC, abstractmethod

try:
    from sqlalchemy import create_engine, Column, String, Float, DateTime, Integer
    from sqlalchemy.ext.declarative import declarative_base
    from sqlalchemy.orm import sessionmaker
    SQLALCHEMY_AVAILABLE = True
except ImportError:
    SQLALCHEMY_AVAILABLE = False

try:
    import pymongo
    PYMONGO_AVAILABLE = True
except ImportError:
    PYMONGO_AVAILABLE = False

logger = logging.getLogger(__name__)

Base = declarative_base() if SQLALCHEMY_AVAILABLE else None


class ScreeningResult(Base):
    """SQLAlchemy model for screening results"""
    __tablename__ = 'screening_results'
    
    if SQLALCHEMY_AVAILABLE:
        id = Column(Integer, primary_key=True)
        symbol = Column(String, index=True)
        timestamp = Column(DateTime, default=datetime.utcnow, index=True)
        rsi = Column(Float)
        rsi_signal = Column(String)  # OVERSOLD, OVERBOUGHT, NEUTRAL
        price = Column(Float)
        divergence_type = Column(String)  # BULLISH, BEARISH, NONE
        divergence_strength = Column(String)  # WEAK, MEDIUM, STRONG
        market = Column(String)  # US500, UK100, CAC40, NASDAQ


class DatabaseManager(ABC):
    """Abstract base class for database managers"""

    @abstractmethod
    def save_result(self, result: Dict):
        pass

    @abstractmethod
    def save_results(self, results: List[Dict]):
        pass

    @abstractmethod
    def get_latest_results(self, symbol: str, limit: int = 10) -> List[Dict]:
        pass


class SQLiteManager(DatabaseManager):
    """SQLite database manager"""

    def __init__(self, db_path: str = "screener.db"):
        self.db_path = db_path
        self._init_database()

    def _init_database(self):
        """Initialize SQLite database tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS screening_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                rsi REAL,
                rsi_signal TEXT,
                price REAL,
                divergence_type TEXT,
                divergence_strength TEXT,
                market TEXT,
                INDEX idx_symbol (symbol),
                INDEX idx_timestamp (timestamp)
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info(f"SQLite database initialized at {self.db_path}")

    def save_result(self, result: Dict):
        """Save single screening result"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO screening_results 
            (symbol, rsi, rsi_signal, price, divergence_type, divergence_strength, market)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            result.get('symbol'),
            result.get('rsi'),
            result.get('rsi_signal'),
            result.get('price'),
            result.get('divergence_type'),
            result.get('divergence_strength'),
            result.get('market')
        ))
        
        conn.commit()
        conn.close()

    def save_results(self, results: List[Dict]):
        """Save multiple screening results"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for result in results:
            cursor.execute('''
                INSERT INTO screening_results 
                (symbol, rsi, rsi_signal, price, divergence_type, divergence_strength, market)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                result.get('symbol'),
                result.get('rsi'),
                result.get('rsi_signal'),
                result.get('price'),
                result.get('divergence_type'),
                result.get('divergence_strength'),
                result.get('market')
            ))
        
        conn.commit()
        conn.close()
        logger.info(f"Saved {len(results)} results to database")

    def get_latest_results(self, symbol: str, limit: int = 10) -> List[Dict]:
        """Get latest results for a symbol"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM screening_results 
            WHERE symbol = ? 
            ORDER BY timestamp DESC 
            LIMIT ?
        ''', (symbol, limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]

    def export_to_csv(self, filename: str, days: int = 7):
        """Export recent results to CSV"""
        conn = sqlite3.connect(self.db_path)
        query = f"SELECT * FROM screening_results WHERE timestamp > datetime('now', '-{days} days')"
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        df.to_csv(filename, index=False)
        logger.info(f"Exported results to {filename}")


class MongoDBManager(DatabaseManager):
    """MongoDB database manager"""

    def __init__(self, uri: str = "mongodb://localhost:27017", db_name: str = "stock_screener"):
        if not PYMONGO_AVAILABLE:
            raise ImportError("pymongo not installed. Install with: pip install pymongo")
        
        self.client = pymongo.MongoClient(uri)
        self.db = self.client[db_name]
        self.collection = self.db['screening_results']
        self._create_indexes()

    def _create_indexes(self):
        """Create database indexes"""
        self.collection.create_index("symbol")
        self.collection.create_index("timestamp")
        logger.info("MongoDB indexes created")

    def save_result(self, result: Dict):
        """Save single screening result"""
        result['timestamp'] = datetime.utcnow()
        self.collection.insert_one(result)

    def save_results(self, results: List[Dict]):
        """Save multiple screening results"""
        for result in results:
            result['timestamp'] = datetime.utcnow()
        self.collection.insert_many(results)
        logger.info(f"Saved {len(results)} results to MongoDB")

    def get_latest_results(self, symbol: str, limit: int = 10) -> List[Dict]:
        """Get latest results for a symbol"""
        results = list(self.collection.find(
            {"symbol": symbol},
            sort=[("timestamp", pymongo.DESCENDING)],
            limit=limit
        ))
        return results


def get_database_manager(db_type: str, **kwargs) -> DatabaseManager:
    """
    Factory function to get appropriate database manager.
    
    Args:
        db_type: 'sqlite', 'postgresql', or 'mongodb'
        **kwargs: Database-specific arguments
        
    Returns:
        DatabaseManager instance
    """
    if db_type.lower() == 'sqlite':
        return SQLiteManager(kwargs.get('db_path', 'screener.db'))
    elif db_type.lower() == 'mongodb':
        return MongoDBManager(kwargs.get('uri', 'mongodb://localhost:27017'))
    elif db_type.lower() == 'postgresql':
        if not SQLALCHEMY_AVAILABLE:
            raise ImportError("sqlalchemy not installed")
        # PostgreSQL implementation
        logger.warning("PostgreSQL support coming soon")
        return SQLiteManager()  # Fallback to SQLite
    else:
        raise ValueError(f"Unsupported database type: {db_type}")
