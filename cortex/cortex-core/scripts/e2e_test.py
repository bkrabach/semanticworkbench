#!/usr/bin/env python
"""
End-to-End Test Script for Cortex Core

This script automates the end-to-end testing process for Cortex Core.
It performs the following steps:
1. Starts the Cortex Core server
2. Verifies authentication endpoints
3. Creates a workspace and conversation
4. Sends a message and verifies the response via SSE
5. Cleans up and shuts down the server

Usage:
    python e2e_test.py [--host HOST] [--port PORT]
"""

import argparse
import json
import os
import signal
import subprocess
import sys
import time

import requests
# The package is sseclient-py but the module is sseclient
try:
    import sseclient
except ImportError:
    print("⚠️ Missing dependency: sseclient-py")
    print("Please install it with: pip install sseclient-py")

# Default configuration
DEFAULT_HOST = "localhost"
DEFAULT_PORT = 8000
DEFAULT_TIMEOUT = 30  # seconds

# Colors for terminal output
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
RESET = "\033[0m"
BOLD = "\033[1m"


def log_success(message: str) -> None:
    """Log a success message in green."""
    print(f"{GREEN}✅ {message}{RESET}")


def log_warning(message: str) -> None:
    """Log a warning message in yellow."""
    print(f"{YELLOW}⚠️ {message}{RESET}")


def log_error(message: str) -> None:
    """Log an error message in red."""
    print(f"{RED}❌ {message}{RESET}")


def log_section(message: str) -> None:
    """Log a section header in bold."""
    print(f"\n{BOLD}=== {message} ==={RESET}")


def start_server(host: str, port: int) -> subprocess.Popen:
    """Start the Cortex Core server."""
    log_section("Starting Cortex Core Server")

    # Create a new process group to ensure we can kill the server and its children
    process = subprocess.Popen(
        [sys.executable, "-m", "app.main"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        preexec_fn=os.setsid,  # Create a new process group
    )

    # Wait for the server to start
    base_url = f"http://{host}:{port}"
    start_time = time.time()
    server_started = False

    while time.time() - start_time < DEFAULT_TIMEOUT:
        try:
            response = requests.get(f"{base_url}/health")
            if response.status_code == 200:
                server_started = True
                break
        except requests.RequestException:
            pass
        time.sleep(0.5)

    if server_started:
        log_success(f"Server started at {base_url}")
        return process
    else:
        log_error("Failed to start server within timeout")
        # Try to read any error output
        stderr = process.stderr.read().decode("utf-8") if process.stderr else "No error output available"
        print(f"Server error output: {stderr}")
        stop_server(process)
        sys.exit(1)


def stop_server(process: subprocess.Popen) -> None:
    """Stop the Cortex Core server."""
    log_section("Stopping Cortex Core Server")
    try:
        # Send SIGTERM to the process group
        os.killpg(os.getpgid(process.pid), signal.SIGTERM)
        process.wait(timeout=5)
        log_success("Server stopped gracefully")
    except (subprocess.TimeoutExpired, ProcessLookupError):
        log_warning("Server did not stop gracefully, forcing termination")
        try:
            os.killpg(os.getpgid(process.pid), signal.SIGKILL)
        except ProcessLookupError:
            pass


def get_auth_token(base_url: str) -> str:
    """Get an authentication token from the server."""
    log_section("Authenticating")

    try:
        # For development/testing purposes, we use the simple login endpoint
        response = requests.post(
            f"{base_url}/auth/login",
            data={"username": "user@example.com", "password": "password123"}
        )

        if response.status_code == 200:
            token = response.json().get("access_token")
            if token:
                log_success("Authentication successful")
                return token
            else:
                log_error("Failed to get token from response")
                sys.exit(1)
        else:
            log_error(f"Authentication failed: {response.status_code} {response.text}")
            sys.exit(1)
    except requests.RequestException as e:
        log_error(f"Authentication request failed: {e}")
        sys.exit(1)


def verify_token(base_url: str, token: str) -> None:
    """Verify that the token is valid."""
    try:
        response = requests.get(
            f"{base_url}/auth/verify",
            headers={"Authorization": f"Bearer {token}"}
        )

        if response.status_code == 200 and response.json().get("authenticated"):
            log_success("Token verification successful")
        else:
            log_error(f"Token verification failed: {response.status_code} {response.text}")
            sys.exit(1)
    except requests.RequestException as e:
        log_error(f"Token verification request failed: {e}")
        sys.exit(1)


def create_workspace(base_url: str, token: str) -> str:
    """Create a workspace and return its ID."""
    log_section("Creating Workspace")

    try:
        response = requests.post(
            f"{base_url}/config/workspaces",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            },
            json={
                "name": "E2E Test Workspace",
                "description": "Created by end-to-end test script",
                "metadata": {"test": True}
            }
        )

        if response.status_code == 200:
            workspace_id = response.json().get("workspace", {}).get("id")
            if workspace_id:
                log_success(f"Workspace created: {workspace_id}")
                return workspace_id
            else:
                log_error("Failed to get workspace ID from response")
                sys.exit(1)
        else:
            log_error(f"Workspace creation failed: {response.status_code} {response.text}")
            sys.exit(1)
    except requests.RequestException as e:
        log_error(f"Workspace creation request failed: {e}")
        sys.exit(1)


def create_conversation(base_url: str, token: str, workspace_id: str) -> str:
    """Create a conversation in the workspace and return its ID."""
    log_section("Creating Conversation")

    try:
        response = requests.post(
            f"{base_url}/config/conversations",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            },
            json={
                "workspace_id": workspace_id,
                "topic": "E2E Test Conversation",
                "metadata": {"test": True}
            }
        )

        if response.status_code == 200:
            conversation_id = response.json().get("conversation", {}).get("id")
            if conversation_id:
                log_success(f"Conversation created: {conversation_id}")
                return conversation_id
            else:
                log_error("Failed to get conversation ID from response")
                sys.exit(1)
        else:
            log_error(f"Conversation creation failed: {response.status_code} {response.text}")
            sys.exit(1)
    except requests.RequestException as e:
        log_error(f"Conversation creation request failed: {e}")
        sys.exit(1)


class SSEListener:
    """Listener for Server-Sent Events."""

    def __init__(self, url: str, token: str, conversation_id: str):
        """Initialize the SSE listener."""
        self.url = url
        self.token = token
        self.conversation_id = conversation_id
        self.events = []
        self.process = None
        self.output_file = "sse_events.log"

    def start(self):
        """Start listening for SSE events in a separate process."""
        # Write a simple script to listen for SSE events and save them to a file
        script_path = "sse_listener.py"
        with open(script_path, "w") as f:
            f.write("""
#!/usr/bin/env python
import sys
import json
import time
from sseclient import SSEClient

url = sys.argv[1]
token = sys.argv[2]
output_file = sys.argv[3]

headers = {"Authorization": f"Bearer {token}"}

with open(output_file, "w") as f:
    f.write("")

try:
    client = SSEClient(url, headers=headers)
    for event in client.events():
        with open(output_file, "a") as f:
            timestamp = time.time()
            event_data = {
                "timestamp": timestamp,
                "event": event.event,
                "data": json.loads(event.data) if event.data.strip() else None
            }
            f.write(json.dumps(event_data) + "\n")
            f.flush()
except Exception as e:
    with open(output_file, "a") as f:
        f.write(f"ERROR: {str(e)}\n")
""")

        # Make the script executable
        os.chmod(script_path, 0o755)

        # Start the listener in a separate process
        url_with_params = f"{self.url}?conversation_id={self.conversation_id}"
        self.process = subprocess.Popen(
            [sys.executable, script_path, url_with_params, self.token, self.output_file],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            preexec_fn=os.setsid,  # Create a new process group
        )

        # Wait a bit for the listener to start
        time.sleep(2)
        log_success("SSE listener started")

    def stop(self):
        """Stop the SSE listener."""
        if self.process:
            try:
                os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
                self.process.wait(timeout=5)
                log_success("SSE listener stopped")
            except (subprocess.TimeoutExpired, ProcessLookupError):
                log_warning("SSE listener did not stop gracefully, forcing termination")
                try:
                    os.killpg(os.getpgid(self.process.pid), signal.SIGKILL)
                except ProcessLookupError:
                    pass

    def get_events(self):
        """Get the events received by the listener."""
        events = []
        try:
            with open(self.output_file, "r") as f:
                for line in f:
                    if line.strip():
                        try:
                            events.append(json.loads(line))
                        except json.JSONDecodeError:
                            pass
        except FileNotFoundError:
            pass

        return events


def send_message(base_url: str, token: str, conversation_id: str, content: str) -> bool:
    """Send a message to the conversation."""
    log_section("Sending Message")

    try:
        response = requests.post(
            f"{base_url}/input",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            },
            json={
                "content": content,
                "conversation_id": conversation_id,
                "metadata": {"test": True}
            }
        )

        if response.status_code == 200:
            log_success(f"Message sent: {content}")
            return True
        else:
            log_error(f"Message sending failed: {response.status_code} {response.text}")
            return False
    except requests.RequestException as e:
        log_error(f"Message sending request failed: {e}")
        return False


def verify_response(sse_listener: SSEListener, timeout: int = 10) -> bool:
    """Verify that a response was received via SSE."""
    log_section("Verifying Response")

    start_time = time.time()
    while time.time() - start_time < timeout:
        events = sse_listener.get_events()
        output_events = [e for e in events if e.get("event") == "output"]

        if output_events:
            log_success(f"Response received: {json.dumps(output_events[-1], indent=2)}")
            return True

        time.sleep(1)

    log_error("No response received within timeout")
    return False


def run_e2e_test(host: str, port: int) -> None:
    """Run the end-to-end test."""
    base_url = f"http://{host}:{port}"
    sse_url = f"{base_url}/output/stream"

    # Start the server
    server_process = start_server(host, port)

    try:
        # Get authentication token
        token = get_auth_token(base_url)
        verify_token(base_url, token)

        # Create workspace and conversation
        workspace_id = create_workspace(base_url, token)
        conversation_id = create_conversation(base_url, token, workspace_id)

        # Start SSE listener
        sse_listener = SSEListener(sse_url, token, conversation_id)
        sse_listener.start()

        try:
            # Send a message and verify response
            message_content = "Hello, this is an end-to-end test message!"
            send_message(base_url, token, conversation_id, message_content)

            # Wait for and verify response
            response_received = verify_response(sse_listener)

            if response_received:
                log_success("END-TO-END TEST PASSED! 🎉")
            else:
                log_error("END-TO-END TEST FAILED: No response received")
        finally:
            # Stop SSE listener
            sse_listener.stop()
    finally:
        # Stop the server
        stop_server(server_process)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Run end-to-end tests for Cortex Core")
    parser.add_argument("--host", default=DEFAULT_HOST, help=f"Server host (default: {DEFAULT_HOST})")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"Server port (default: {DEFAULT_PORT})")

    args = parser.parse_args()
    run_e2e_test(args.host, args.port)


if __name__ == "__main__":
    main()
