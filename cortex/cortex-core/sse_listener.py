
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
    # SSEClient accepts headers as a keyword argument
    # According to the library docs: https://github.com/mpetazzoni/sseclient
    client = SSEClient(url, headers=headers)  # type: ignore # pyright doesn't know about headers parameter
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
