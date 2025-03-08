"""
Logger utility for Cortex Core
"""

import logging
import sys
import os
from pathlib import Path
from logging.handlers import TimedRotatingFileHandler
import json
from datetime import datetime

# Get log level from environment variable or default to INFO
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
LOG_DIR = os.environ.get("LOG_DIR", os.path.join(os.getcwd(), "logs"))

# Create log directory if it doesn't exist
Path(LOG_DIR).mkdir(parents=True, exist_ok=True)

# Create logger
logger = logging.getLogger("cortex")
logger.setLevel(getattr(logging, LOG_LEVEL))


# Define log format
class ExtendedLogRecord(logging.LogRecord):
    """Extended LogRecord with extra attribute"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add extra field directly to the object
        setattr(self, 'extra', {})


class CustomFormatter(logging.Formatter):
    """Custom formatter that adds timestamp and handles extra fields"""

    def format(self, record):
        # ISO format with milliseconds
        timestamp = datetime.fromtimestamp(record.created).strftime(
            "%Y-%m-%d %H:%M:%S.%f"
        )[:-3]

        # Basic log message
        log_message = f"{timestamp} [{record.levelname}]: {record.getMessage()}"

        # Add exception info if present
        if record.exc_info:
            log_message += f"\n{self.formatException(record.exc_info)}"

        # Add extra fields if present
        try:
            if hasattr(record, "extra") and getattr(record, "extra"):
                try:
                    extra_data = getattr(record, "extra")
                    log_message += f" {json.dumps(extra_data)}"
                except Exception:
                    pass
        except Exception:
            pass

        return log_message


# Create formatters
formatter = CustomFormatter()

# Create console handler
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(getattr(logging, LOG_LEVEL))
console_handler.setFormatter(formatter)

# Create file handler (all logs)
file_handler = TimedRotatingFileHandler(
    os.path.join(LOG_DIR, "cortex.log"),
    when="midnight",
    backupCount=14,  # Keep logs for 14 days
)
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(formatter)

# Create error file handler (errors only)
error_file_handler = TimedRotatingFileHandler(
    os.path.join(LOG_DIR, "cortex-error.log"),
    when="midnight",
    backupCount=30,  # Keep error logs for 30 days
)
error_file_handler.setLevel(logging.ERROR)
error_file_handler.setFormatter(formatter)

# Add handlers to logger
logger.addHandler(console_handler)
logger.addHandler(file_handler)
logger.addHandler(error_file_handler)

# Create a special request logger
request_logger = logging.getLogger("cortex.request")
request_logger.setLevel(logging.INFO)

# Create request file handler
request_file_handler = TimedRotatingFileHandler(
    os.path.join(LOG_DIR, "cortex-requests.log"),
    when="midnight",
    backupCount=7,  # Keep request logs for 7 days
)
request_file_handler.setLevel(logging.INFO)
request_file_handler.setFormatter(formatter)

# Add handler to request logger
request_logger.addHandler(request_file_handler)


# Register our custom log record factory
logging.setLogRecordFactory(ExtendedLogRecord)

# Set up exception handling
def handle_exception(exc_type, exc_value, exc_traceback):
    """Handle uncaught exceptions"""
    # Skip KeyboardInterrupt
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    # Log the exception
    logger.error("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))


# Set the exception hook
sys.excepthook = handle_exception

# Log startup message
logger.info("Logger initialized")
