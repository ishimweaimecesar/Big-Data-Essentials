import json
import subprocess
import time
from pathlib import Path
from decimal import Decimal
from datetime import datetime, date

import ijson
from kafka import KafkaProducer
from kafka.errors import KafkaError


# ============================================================
# Configuration
# ============================================================

HDFS_COMMAND = Path(r"C:\Hadoop\bin\hdfs.cmd")

HDFS_SESSION_FILE = "/ecommerce/raw/sessions/sessions_0.json"

KAFKA_BOOTSTRAP_SERVERS = ["127.0.0.1:9092"]
KAFKA_TOPIC = "ecommerce_sessions"

# Explicit API version (avoids auto-detection timeout)
KAFKA_API_VERSION = (2, 8, 0)

# Number of messages to send
# Set to None to stream the whole file
MAX_MESSAGES = 1000

# Delay between records
INTERVAL_SECONDS = 0.5


# ============================================================
# Custom JSON Serializer
# ============================================================

def json_serializer(obj):
    """
    Convert unsupported Python objects into JSON serializable types.
    """

    if isinstance(obj, Decimal):
        return float(obj)

    if isinstance(obj, (datetime, date)):
        return obj.isoformat()

    raise TypeError(
        f"Object of type {type(obj).__name__} is not JSON serializable"
    )


# ============================================================
# Validation
# ============================================================

if not HDFS_COMMAND.exists():
    raise FileNotFoundError(
        f"hdfs.cmd was not found at: {HDFS_COMMAND}"
    )


# ============================================================
# Kafka Producer
# ============================================================

producer = KafkaProducer(
    bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,

    api_version=KAFKA_API_VERSION,

    value_serializer=lambda value: json.dumps(
        value,
        ensure_ascii=False,
        default=json_serializer
    ).encode("utf-8"),

    key_serializer=lambda key: key.encode("utf-8"),

    acks="all",

    retries=5,

    batch_size=16384,

    linger_ms=10
)

print("Connected to Kafka successfully.")


# ============================================================
# Open HDFS File
# ============================================================

command = [
    str(HDFS_COMMAND),
    "dfs",
    "-cat",
    HDFS_SESSION_FILE
]

print(f"Opening HDFS file: {HDFS_SESSION_FILE}")

hdfs_process = subprocess.Popen(
    command,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    encoding="utf-8",
    errors="replace",
    bufsize=1
)

if hdfs_process.stdout is None:
    raise RuntimeError(
        "Could not open the HDFS output stream."
    )


# ============================================================
# Stream Sessions to Kafka
# ============================================================

sent_count = 0

try:

    sessions = ijson.items(
        hdfs_process.stdout,
        "item"
    )

    for session in sessions:

        session_id = session.get("session_id")

        if not session_id:
            print("Skipping record without session_id")
            continue

        future = producer.send(
            topic=KAFKA_TOPIC,
            key=session_id,
            value=session
        )

        try:

            metadata = future.get(timeout=30)

            sent_count += 1

            print(
                f"Sent {sent_count}: "
                f"session_id={session_id}, "
                f"partition={metadata.partition}, "
                f"offset={metadata.offset}"
            )

        except KafkaError as error:

            print(
                f"Failed to send session "
                f"{session_id}: {error}"
            )

        if (
            MAX_MESSAGES is not None
            and sent_count >= MAX_MESSAGES
        ):
            break

        time.sleep(INTERVAL_SECONDS)

except Exception as error:

    print(f"\nStreaming error: {error}")

finally:

    print("\nClosing producer...")

    producer.flush()
    producer.close()

    if hdfs_process.stdout:
        hdfs_process.stdout.close()

    hdfs_process.terminate()

    stderr_output = ""

    if hdfs_process.stderr:
        stderr_output = hdfs_process.stderr.read()
        hdfs_process.stderr.close()

    if stderr_output.strip():
        print("\nHDFS messages:")
        print(stderr_output)

print(f"\nProducer finished. Messages sent: {sent_count}")