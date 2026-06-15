import json
import logging
import os
import sys
from typing import Any, Dict

def get_logger(name: str) -> logging.Logger:
    """Get a configured logger instance"""
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        # Console handler
        ch = logging.StreamHandler(sys.stdout)
        ch.setFormatter(formatter)
        logger.addHandler(ch)
        # File handler
        fh = logging.FileHandler('agent.log')
        fh.setFormatter(formatter)
        logger.addHandler(fh)
    return logger

def load_json(file_path: str, default: Any = None) -> Any:
    """Safely load JSON from file"""
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        if default is not None:
            return default
        raise

def save_json(file_path: str, data: Any):
    """Safely save JSON to file"""
    try:
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        raise IOError(f"Failed to save JSON to {file_path}: {e}")

def ensure_dir(directory: str):
    """Ensure directory exists"""
    if not os.path.exists(directory):
        os.makedirs(directory)