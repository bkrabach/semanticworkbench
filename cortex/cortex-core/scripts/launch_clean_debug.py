# File: launch_clean_debug.py

import os
import subprocess
import platform

def clear_screen():
    """Clear the terminal screen."""
    os.system('cls' if platform.system() == 'Windows' else 'clear')

def delete_database(file_name):
    """Remove the specified file if it exists."""
    if os.path.exists(file_name):
        os.remove(file_name)
        print(f"Deleted '{file_name}'")
    else:
        print(f"'{file_name}' not found, skipping deletion.")

def run_uvicorn():
    """Run the uvicorn server via subprocess."""
    try:
        subprocess.run(
            ["uvicorn", "app.main:app"],
            cwd=os.getcwd(),  # Use current working directory
            check=True
        )
    except subprocess.CalledProcessError as e:
        print(f"Error while running uvicorn: {e}")

if __name__ == "__main__":
    # Step 1: Clear the screen
    clear_screen()

    # Step 2: Delete 'cortex.db'
    delete_database("cortex.db")

    # Step 3: Start uvicorn
    run_uvicorn()
