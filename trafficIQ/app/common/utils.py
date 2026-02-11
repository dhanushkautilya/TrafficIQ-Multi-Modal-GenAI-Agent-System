"""Utility functions for TrafficIQ."""

import hashlib
import uuid
import time
from typing import Dict, Any
from functools import wraps
import logging

logger = logging.getLogger(__name__)


def generate_id(prefix: str = "") -> str:
    """Generate a unique ID."""
    uid = str(uuid.uuid4())[:8]
    return f"{prefix}-{uid}" if prefix else uid


def deterministic_hash(value: str) -> float:
    """Generate a deterministic float between 0 and 1 from a string."""
    hash_obj = hashlib.md5(value.encode())
    hash_int = int(hash_obj.hexdigest(), 16)
    return (hash_int % 100) / 100.0


def extract_image_uri_features(image_uri: str) -> Dict[str, Any]:
    """Extract features from image URI for mock predictions."""
    uri_lower = image_uri.lower()
    
    features = {
        "is_night": "night" in uri_lower,
        "is_blur": "blur" in uri_lower,
        "is_low_res": "low_res" in uri_lower,
        "is_rain": "rain" in uri_lower,
        "hash_value": deterministic_hash(image_uri),
    }
    
    return features


def measure_time(func):
    """Decorator to measure function execution time."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        elapsed_ms = (time.time() - start) * 1000
        logger.info(f"Function {func.__name__} took {elapsed_ms:.2f}ms")
        return result
    
    return wrapper


def log_operation(operation_name: str):
    """Decorator to log function operations."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger.info(f"Starting operation: {operation_name}")
            try:
                result = func(*args, **kwargs)
                logger.info(f"Completed operation: {operation_name}")
                return result
            except Exception as e:
                logger.error(f"Failed operation: {operation_name}, error: {str(e)}")
                raise
        return wrapper
    return decorator


def safe_json_serializable(obj: Any) -> Any:
    """Convert object to JSON-serializable format."""
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    elif hasattr(obj, "dict"):
        return obj.dict()
    elif hasattr(obj, "__dict__"):
        return obj.__dict__
    return str(obj)
