"""Health check utilities for dependencies."""
import redis
from pathlib import Path
from typing import Dict, Any


def check_redis(redis_url: str, timeout: int = 2) -> bool:
    """
    Check Redis connectivity.

    Args:
        redis_url: Redis connection URL
        timeout: Connection timeout in seconds

    Returns:
        True if Redis is accessible, False otherwise
    """
    try:
        r = redis.from_url(redis_url, socket_connect_timeout=timeout, decode_responses=True)
        r.ping()
        return True
    except Exception:
        return False


def check_filesystem(data_dir: str) -> bool:
    """
    Check filesystem writability.

    Args:
        data_dir: Directory to test write access

    Returns:
        True if filesystem is writable, False otherwise
    """
    try:
        data_path = Path(data_dir)
        # Create directory if it doesn't exist
        data_path.mkdir(parents=True, exist_ok=True)

        # Test write access
        test_file = data_path / ".health_check"
        test_file.touch()
        test_file.unlink()
        return True
    except Exception:
        return False


def check_all_dependencies(redis_url: str, data_dir: str) -> Dict[str, Any]:
    """
    Check all service dependencies.

    Args:
        redis_url: Redis connection URL
        data_dir: Data directory path

    Returns:
        Dict with overall health status and individual checks:
        {
            "status": "healthy" | "unhealthy",
            "redis_healthy": bool,
            "filesystem_healthy": bool,
            "redis_url": str,
            "data_dir": str
        }
    """
    redis_healthy = check_redis(redis_url)
    filesystem_healthy = check_filesystem(data_dir)

    all_healthy = redis_healthy and filesystem_healthy

    return {
        "status": "healthy" if all_healthy else "unhealthy",
        "redis_healthy": redis_healthy,
        "filesystem_healthy": filesystem_healthy,
        "redis_url": redis_url,
        "data_dir": data_dir
    }
