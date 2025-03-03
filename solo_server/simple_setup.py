#!/usr/bin/env python3
import os
import sys
import subprocess
import threading
import time
import shutil


# Ensure Python 3.8+ is installed
if sys.version_info < (3, 8):
    sys.exit("🚫 Python 3.8 or higher is required.")

def detect_gpu():
    """Return the GPU name if an NVIDIA GPU is detected, else None."""
    if shutil.which("nvidia-smi"):
        try:
            output = subprocess.check_output(
                ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
                stderr=subprocess.STDOUT
            ).decode().strip()
            return output.splitlines()[0] if output else None
        except Exception:
            return None
    return None

def run_command(cmd, spinner_message=None, ignore_error=False):
    """
    Run a command with error checking.
    Optionally display a spinner (an infinity symbol) while the command is running.
    If ignore_error is True, print a warning and continue on failure.
    """
    spinner_stop = None
    if spinner_message:
        spinner_stop = threading.Event()
        def spinner():
            while not spinner_stop.is_set():
                sys.stdout.write("\r" + spinner_message + " ∞")
                sys.stdout.flush()
                time.sleep(0.1)
        t = threading.Thread(target=spinner)
        t.start()
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        if ignore_error:
            print(f"\nWarning: Command '{' '.join(cmd)}' failed: {e}. Continuing...")
        else:
            sys.exit(f"\nError running command: {' '.join(cmd)}\n{e}")
    finally:
        if spinner_message:
            spinner_stop.set()
            t.join()
            sys.stdout.write("\r" + " " * (len(spinner_message) + 2) + "\r")
            if not ignore_error:
                print(spinner_message + " Done.")
    if spinner_message and ignore_error:
        print(spinner_message + " (attempted)")

def main():
    # Solo hardware reconnaissance
    gpu = detect_gpu()
    if gpu:
        print("💻 Solo Sighting: GPU detected ->", gpu)
        device_arg = "1"
    else:
        print("😎 Solo Mode: No GPU found; rocking CPU mode!")
        device_arg = "0"
    
    # Install litgpt with all extras
    run_command(["uv", "pip", "install", "litgpt[download,serve]"],
                spinner_message="Solo setup: Installing optimal inference engine, hold tight...")
    # Download the model with a spinner
    run_command(["litgpt", "download", "HuggingFaceTB/SmolLM2-135M-Instruct"],
                spinner_message="Solo download in progress: Grabbing lightest model...")
    # Start the server endpoint
    from rich.console import Console
    from rich.panel import Panel

    console = Console()

    console.print("\n")
    console.print(Panel.fit(
        "🎉 LIVE: solo server is now live!\n"
        "🔗 Swagger docs available at: http://127.0.0.1:50700/docs",
        title="Solo Server", border_style="blue"))
    console.print(
        "curl -X POST http://127.0.0.1:50700/predict -H 'Content-Type: application/json' -d '{\"prompt\": \"hello Solo\"}'")
    command = [
    "litgpt",
    "serve",
    "HuggingFaceTB/SmolLM2-135M-Instruct",
    "--port", "50700",
    "--devices", device_arg
]
    process = subprocess.Popen(command)
    print(f"Command is running in the background with PID: {process.pid}")

if __name__ == "__main__":
    main()
