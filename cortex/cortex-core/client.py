# client.py

import httpx


def parse_sse(response):
    """
    A minimal SSE parser that processes an httpx streaming response.
    Accumulates lines until an empty line is encountered (which indicates the end of an event)
    and yields the concatenated 'data:' fields as the event data.
    """
    event_lines = []
    for line in response.iter_lines():
        if isinstance(line, bytes):
            line = line.decode("utf-8")
        line = line.strip()
        if line == "":
            # End of an event, yield if there's any data.
            if event_lines:
                data = ""
                for event_line in event_lines:
                    if event_line.startswith("data:"):
                        data += event_line[len("data:") :].strip() + "\n"
                yield data.strip()
                event_lines = []
        else:
            event_lines.append(line)
    # Yield any leftover event.
    if event_lines:
        data = ""
        for event_line in event_lines:
            if event_line.startswith("data:"):
                data += event_line[len("data:") :].strip() + "\n"
        yield data.strip()


def main():
    api_url = "http://localhost:8000/process"
    sse_url = "http://localhost:8000/notifications"

    payload = {
        "user_id": "user1",
        "token": "secret-token",
        "input_text": "Can you help me write some code to reverse a string?",
    }

    try:
        response = httpx.post(api_url, json=payload)
        response.raise_for_status()
    except Exception as e:
        print("Error calling API:", e)
        return

    data = response.json()
    print("API Response:", data)

    print("Subscribing to notifications...")
    try:
        with httpx.Client(timeout=None) as client:
            with client.stream("GET", sse_url) as response:
                for event_data in parse_sse(response):
                    if event_data.strip():  # Only print non-empty notifications.
                        print("Received notification:", event_data)
    except Exception as e:
        print("Error subscribing to notifications:", e)


if __name__ == "__main__":
    main()
