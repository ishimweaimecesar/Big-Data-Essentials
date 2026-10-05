import os
import subprocess
from pathlib import Path

# ============================================================
# Configuration
# ============================================================
LOCAL_DATASET = Path(
    r"C:\Users\HP\Desktop\Books and Notes\AUCA\Big Data Analytics\Final Project\generated_ecommerce_big_dataset(1)"
)

HDFS_COMMAND = r"C:\Hadoop\bin\hdfs.cmd"
HDFS_ROOT = "/ecommerce/raw"

# ============================================================
# Validate local paths
# ============================================================
if not Path(HDFS_COMMAND).exists():
    raise FileNotFoundError(
        f"HDFS command was not found at:\n{HDFS_COMMAND}\n"
        "Update HDFS_COMMAND to the location of hdfs.cmd."
    )

if not LOCAL_DATASET.exists():
    raise FileNotFoundError(
        f"Dataset directory was not found:\n{LOCAL_DATASET}"
    )

# ============================================================
# Helper function
# ============================================================
def run_hdfs(arguments):
    command = [HDFS_COMMAND, "dfs", *arguments]

    print("Running:", " ".join(command))

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False
    )

    if result.stdout:
        print(result.stdout)

    if result.stderr:
        print(result.stderr)

    if result.returncode != 0:
        raise RuntimeError(
            f"HDFS command failed with return code {result.returncode}"
        )

# ============================================================
# Create HDFS directories
# ============================================================
hdfs_directories = [
    "users",
    "products",
    "categories",
    "transactions",
    "sessions"
]

print("\nCreating HDFS directories...")

for directory in hdfs_directories:
    run_hdfs([
        "-mkdir",
        "-p",
        f"{HDFS_ROOT}/{directory}"
    ])

print("HDFS directories created successfully.")

# ============================================================
# Upload individual files
# ============================================================
single_files = {
    "users.json": "users",
    "products.json": "products",
    "categories.json": "categories",
    "transactions.json": "transactions"
}

for filename, destination_folder in single_files.items():
    local_file = LOCAL_DATASET / filename

    if not local_file.exists():
        raise FileNotFoundError(
            f"Required file was not found:\n{local_file}"
        )

    print(f"\nUploading {filename}...")

    run_hdfs([
        "-put",
        "-f",
        str(local_file),
        f"{HDFS_ROOT}/{destination_folder}/"
    ])

# ============================================================
# Upload session files
# ============================================================
session_files = sorted(
    LOCAL_DATASET.glob("sessions_*.json"),
    key=lambda path: int(path.stem.split("_")[1])
)

if not session_files:
    raise FileNotFoundError(
        f"No sessions_*.json files were found in:\n{LOCAL_DATASET}"
    )

print(f"\nFound {len(session_files)} session files.")

for session_file in session_files:
    print(f"\nUploading {session_file.name}...")

    run_hdfs([
        "-put",
        "-f",
        str(session_file),
        f"{HDFS_ROOT}/sessions/"
    ])

# ============================================================
# Verify uploaded data
# ============================================================
print("\nVerifying HDFS directory structure...")

run_hdfs([
    "-ls",
    "-R",
    HDFS_ROOT
])

print("\nChecking total HDFS storage usage...")

run_hdfs([
    "-du",
    "-h",
    HDFS_ROOT
])

print("\nDataset uploaded successfully.")