import glob
import os

#!/usr/bin/env python3
"""
Script to reset the project's SQLite database by deleting files matching "cortex-db*"
from the parent directory of this script.
"""


def reset_db():
    # Determine the parent directory relative to this script
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.join(current_dir, "..")

    # Pattern to match the SQLite database files
    pattern = os.path.join(parent_dir, "cortex-db*")

    # Find all matching files
    files_to_delete = glob.glob(pattern)

    if not files_to_delete:
        print("No database files found to delete.")
        return

    for file_path in files_to_delete:
        try:
            os.remove(file_path)
            print(f"Deleted: {file_path}")
        except Exception as e:
            print(f"Error deleting {file_path}: {e}")


if __name__ == "__main__":
    # clear the terminal
    os.system("cls" if os.name == "nt" else "clear")
    print("Resetting database...")

    reset_db()
