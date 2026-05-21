"""Utility Functions"""

import logging
from pathlib import Path
from typing import List
from datetime import datetime
import json


def setup_logging(log_level: str = "INFO", log_file: str = None):
    """
    Setup logging configuration.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_file: Optional log file path
    """
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # Configure root logger
    logger = logging.getLogger()
    logger.setLevel(log_level)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(log_format))
    logger.addHandler(console_handler)
    
    # File handler
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(logging.Formatter(log_format))
        logger.addHandler(file_handler)


def load_stock_list(filepath: str) -> List[str]:
    """
    Load stock symbols from a file.
    
    Args:
        filepath: Path to stock list file
        
    Returns:
        List of stock symbols
    """
    symbols = []
    try:
        with open(filepath, 'r') as f:
            for line in f:
                symbol = line.strip()
                if symbol and not symbol.startswith('#'):
                    symbols.append(symbol)
        return symbols
    except FileNotFoundError:
        logging.error(f"Stock list file not found: {filepath}")
        return []


def save_results_to_json(results: List[dict], filename: str):
    """
    Save screening results to JSON file.
    
    Args:
        results: List of screening results
        filename: Output filename
    """
    with open(filename, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    logging.info(f"Results saved to {filename}")


def format_result_for_display(result: dict) -> str:
    """
    Format a screening result for console display.
    
    Args:
        result: Single screening result
        
    Returns:
        Formatted string
    """
    return f"""
    Symbol: {result.get('symbol')}
    Market: {result.get('market')}
    Price: ${result.get('price', 'N/A'):.2f}
    RSI: {result.get('rsi', 'N/A')} ({result.get('rsi_signal', 'N/A')})
    Divergence: {result.get('divergence_type', 'NONE')} ({result.get('divergence_strength', '')})
    Time: {result.get('timestamp', 'N/A')}
    """
