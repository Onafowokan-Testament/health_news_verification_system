import sys

from loguru import logger

# Remove default handler and set a concise, readable format for terminal output
logger.remove()
logger.add(
    sys.stderr,
    level="INFO",
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - {message}",
)

# Expose the logger for import
__all__ = ["logger"]
