import os
from pathlib import Path
from dotenv import load_dotenv

# Load the .env file
env_path = Path(__file__).parent / '.env'
print(f"Looking for .env file at: {env_path}")
print(f"File exists: {env_path.exists()}")

# Try to load with python-dotenv
load_dotenv(dotenv_path=env_path)

# Print all debug-related environment variables
debug_enabled = os.environ.get("DEBUG_LOG_ENABLED", "not set")
print(f"DEBUG_LOG_ENABLED: {debug_enabled}")

debug_main_path = os.environ.get("DEBUG_MAIN_LOG_PATH", "not set")
print(f"DEBUG_MAIN_LOG_PATH: {debug_main_path}")

debug_error_path = os.environ.get("DEBUG_ERROR_LOG_PATH", "not set")
print(f"DEBUG_ERROR_LOG_PATH: {debug_error_path}")

debug_requests_path = os.environ.get("DEBUG_REQUESTS_LOG_PATH", "not set")
print(f"DEBUG_REQUESTS_LOG_PATH: {debug_requests_path}")