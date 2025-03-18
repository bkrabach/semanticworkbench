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

# Try to load environment variables from .env file
try:
    from dotenv import load_dotenv
    # Load from project root .env file
    env_path = Path(os.getcwd()) / '.env'
    if env_path.exists():
        print(f"Loading environment variables from: {env_path}")
        load_dotenv(dotenv_path=env_path)
    else:
        print(f"No .env file found at: {env_path}")
except ImportError:
    print("python-dotenv not installed, skipping .env loading")

# Get log level from environment variable or default to INFO
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
LOG_DIR = os.environ.get("LOG_DIR", os.path.join(os.getcwd(), "logs"))

# Check if debug log files should be created (cleared on each run)
DEBUG_LOG_ENABLED = os.environ.get("DEBUG_LOG_ENABLED", "false").lower() == "true"
print(f"DEBUG_LOG_ENABLED: {DEBUG_LOG_ENABLED}, value: {os.environ.get('DEBUG_LOG_ENABLED', 'not set')}")

# Default debug log paths
DEBUG_MAIN_LOG_PATH = os.environ.get("DEBUG_MAIN_LOG_PATH", os.path.join(LOG_DIR, "cortex.log.debug_current"))
DEBUG_ERROR_LOG_PATH = os.environ.get("DEBUG_ERROR_LOG_PATH", os.path.join(LOG_DIR, "cortex-error.log.debug_current"))
DEBUG_REQUESTS_LOG_PATH = os.environ.get("DEBUG_REQUESTS_LOG_PATH", os.path.join(LOG_DIR, "cortex-requests.log.debug_current"))
print(f"DEBUG_MAIN_LOG_PATH: {DEBUG_MAIN_LOG_PATH}")
print(f"DEBUG_ERROR_LOG_PATH: {DEBUG_ERROR_LOG_PATH}")
print(f"DEBUG_REQUESTS_LOG_PATH: {DEBUG_REQUESTS_LOG_PATH}")

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

# Create debug file handlers if enabled (cleared on each run)
debug_main_handler = None
debug_error_handler = None
debug_requests_handler = None

if DEBUG_LOG_ENABLED:
    try:
        # Setup main debug log
        debug_main_file = Path(DEBUG_MAIN_LOG_PATH)
        debug_main_file.parent.mkdir(parents=True, exist_ok=True)
        if debug_main_file.exists():
            try:
                debug_main_file.write_text("")  # Clear the file
            except Exception as e:
                print(f"Error clearing main debug log: {e}")
        
        debug_main_handler = logging.FileHandler(DEBUG_MAIN_LOG_PATH, mode='w')
        debug_main_handler.setLevel(logging.DEBUG)
        debug_main_handler.setFormatter(formatter)
        
        # Setup error debug log
        debug_error_file = Path(DEBUG_ERROR_LOG_PATH)
        debug_error_file.parent.mkdir(parents=True, exist_ok=True)
        if debug_error_file.exists():
            try:
                debug_error_file.write_text("")  # Clear the file
            except Exception as e:
                print(f"Error clearing error debug log: {e}")
        
        debug_error_handler = logging.FileHandler(DEBUG_ERROR_LOG_PATH, mode='w')
        debug_error_handler.setLevel(logging.ERROR)
        debug_error_handler.setFormatter(formatter)
        
        # Setup requests debug log
        debug_requests_file = Path(DEBUG_REQUESTS_LOG_PATH)
        debug_requests_file.parent.mkdir(parents=True, exist_ok=True)
        if debug_requests_file.exists():
            try:
                debug_requests_file.write_text("")  # Clear the file
            except Exception as e:
                print(f"Error clearing requests debug log: {e}")
        
        debug_requests_handler = logging.FileHandler(DEBUG_REQUESTS_LOG_PATH, mode='w')
        debug_requests_handler.setLevel(logging.DEBUG)
        debug_requests_handler.setFormatter(formatter)
        
        print(f"Debug log files enabled at: {DEBUG_MAIN_LOG_PATH}, {DEBUG_ERROR_LOG_PATH}, {DEBUG_REQUESTS_LOG_PATH}")
    except Exception as e:
        print(f"Error setting up debug logs: {e}")
        # Log error but continue - don't crash app startup due to debug logs

# Add handlers to logger
logger.addHandler(console_handler)
logger.addHandler(file_handler)
logger.addHandler(error_file_handler)

# Add debug file handlers if enabled
if DEBUG_LOG_ENABLED:
    try:
        if debug_main_handler:
            logger.addHandler(debug_main_handler)
            print(f"Added main debug handler to logger")
            
        if debug_error_handler:
            logger.addHandler(debug_error_handler)
            print(f"Added error debug handler to logger")
            
        # Create a special test message to verify debug logs are working
        logger.debug("TEST DEBUG LOG - This message should appear in the debug log file")
    except Exception as e:
        print(f"Error adding debug handlers to logger: {e}")

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

# Add debug request handler to request logger if enabled
if DEBUG_LOG_ENABLED:
    try:
        if debug_requests_handler:
            request_logger.addHandler(debug_requests_handler)
            print(f"Added requests debug handler to request_logger")
            
            # Create a special test message to verify request debug logs are working
            request_logger.info("TEST REQUEST DEBUG LOG - This message should appear in the requests debug log file")
    except Exception as e:
        print(f"Error adding debug request handler: {e}")


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
