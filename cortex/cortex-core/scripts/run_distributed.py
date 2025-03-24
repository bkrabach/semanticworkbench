#!/usr/bin/env python
"""
Run Cortex Core in distributed mode.

This script launches the Memory and Cognition services as separate processes,
and then starts the main Cortex Core application in distributed mode.
"""

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

# Ensure we're in the correct directory
project_root = Path(__file__).resolve().parent.parent
os.chdir(project_root)

# Processes to track
processes = []

def signal_handler(sig, frame):
    """Handle Ctrl+C to terminate all processes."""
    print("\nShutting down all services...")
    for process in processes:
        try:
            if process.poll() is None:  # If process is still running
                process.terminate()
        except Exception as e:
            print(f"Error terminating process: {e}")
    sys.exit(0)

# Register signal handler
signal.signal(signal.SIGINT, signal_handler)

# Set common environment variables
env = os.environ.copy()
env["ALLOW_ORIGINS"] = "*"

def start_service(name, module, port, extra_env=None):
    """Start a service as a separate process."""
    service_env = env.copy()
    if extra_env:
        service_env.update(extra_env)
    
    print(f"Starting {name} on port {port}...")
    process = subprocess.Popen(
        [sys.executable, "-m", module],
        env=service_env,
        stderr=subprocess.STDOUT
    )
    processes.append(process)
    return process

def main():
    """Launch all services."""
    # Start Memory Service
    memory_env = {"MEMORY_SERVICE_PORT": "9000"}
    memory_process = start_service(
        "Memory Service", 
        "app.services.standalone_memory_service", 
        9000, 
        memory_env
    )
    
    # Wait a moment for the Memory Service to start
    time.sleep(2)
    
    # Start Cognition Service
    cognition_env = {
        "COGNITION_SERVICE_PORT": "9100",
        "MEMORY_SERVICE_URL": "http://localhost:9000"
    }
    cognition_process = start_service(
        "Cognition Service", 
        "app.services.standalone_cognition_service", 
        9100, 
        cognition_env
    )
    
    # Wait a moment for the Cognition Service to start
    time.sleep(2)
    
    # Start Cortex Core in distributed mode
    core_env = {
        "CORTEX_DISTRIBUTED_MODE": "true",
        "MEMORY_SERVICE_URL": "http://localhost:9000",
        "COGNITION_SERVICE_URL": "http://localhost:9100"
    }
    core_process = start_service(
        "Cortex Core", 
        "app.main", 
        8000, 
        core_env
    )
    
    print("\nAll services started!")
    print("- Memory Service: http://localhost:9000")
    print("- Cognition Service: http://localhost:9100")
    print("- Cortex Core: http://localhost:8000")
    print("\nPress Ctrl+C to terminate all services.")
    
    # Wait for the Core process to finish
    try:
        core_process.wait()
    except KeyboardInterrupt:
        signal_handler(None, None)
    
    # If Core process exits, terminate others
    signal_handler(None, None)

if __name__ == "__main__":
    main()