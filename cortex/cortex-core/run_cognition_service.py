#!/usr/bin/env python3
"""
Script to run the Cognition Service.

Usage:
    python run_cognition_service.py
"""

import logging
import sys

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("run_cognition")

# Import and run the Cognition Service
try:
    from cognition_service.main import run

    logger.info("Starting Cognition Service...")
    run()
except ImportError as e:
    logger.error(f"Failed to import Cognition Service: {e}")
    logger.error("Make sure all required packages are installed.")
    sys.exit(1)
except Exception as e:
    logger.error(f"Error starting Cognition Service: {e}")
    sys.exit(1)
