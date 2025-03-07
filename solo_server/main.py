import os
import json
import typer
import subprocess
import shutil
import click
import socket


from enum import Enum
from solo_server.config import CONFIG_PATH
from solo_server.utils.docker_utils import start_docker_engine
from solo_server.utils.hardware import detect_hardware, display_hardware_info, recommended_server
from solo_server.utils.nvidia import check_nvidia_toolkit, install_nvidia_toolkit_linux, install_nvidia_toolkit_windows
from solo_server.simple_setup import run_command, detect_gpu
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn


class ServerType(str, Enum):
    OLLAMA = "Ollama"
    VLLM = "vLLM"
    LLAMACPP = "Llama.cpp"

# move to utils
def choose_smol_model(hardware_specs):
    """
    Select the appropriate SmolLM2 model based on the provided hardware specifications.
    
    Returns one of:
      - "HuggingFaceTB/SmolLM2-135M-Instruct"
      - "HuggingFaceTB/SmolLM2-360M-Instruct"
      - "HuggingFaceTB/SmolLM2-1.7B-Instruct"
    """
    gpu_vendor = hardware_specs.get("gpu_vendor")
    gpu_memory = hardware_specs.get("gpu_memory")
    memory_gb = hardware_specs.get("memory_gb", 0)
    
    # Prefer GPU memory for decision if available
    if gpu_vendor and gpu_memory:
        if gpu_memory >= 8:
            return "HuggingFaceTB/SmolLM2-1.7B-Instruct"
        elif gpu_memory >= 4:
            return "HuggingFaceTB/SmolLM2-360M-Instruct"
        else:
            return "HuggingFaceTB/SmolLM2-135M-Instruct"
    else:
        # Fallback to CPU memory thresholds
        if memory_gb >= 16:
            return "HuggingFaceTB/SmolLM2-1.7B-Instruct"
        elif memory_gb >= 8:
            return "HuggingFaceTB/SmolLM2-360M-Instruct"
        else:
            return "HuggingFaceTB/SmolLM2-135M-Instruct"


# move to utils
def run_with_spinner(command, spinner_message):
    """
    Run a subprocess command while displaying a blue spinner with a custom message.
    """
    with Progress(
        SpinnerColumn(style="blue"),
        TextColumn("[blue]{task.description}[/blue]"),
        transient=True,
    ) as progress:
        task = progress.add_task(spinner_message, total=None)
        try:
            # Run the command and wait for it to complete
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = process.communicate()
        finally:
            progress.stop()
    return process, stdout, stderr

def setup_core_llm(hardware_specs):
    console = Console()
    port = "5070"
    device_arg = "0"
    accelerator_arg = "cpu"
    
    console.print("[blue]Solo setup: Installing optimal inference engine, hold tight![/blue]\n")

    selected_model = choose_smol_model(hardware_specs)
    print(f"Based on your hardware, we recommend downloading: {selected_model}")
    # Run the download command with a blue spinner
    download_command = ["litgpt", "download", selected_model]
    run_with_spinner(download_command, "Solo download in progress: Optimizing model for your hardware")
    
    console.print("\n")
    
    # Display a blue bordered panel indicating the server is live
    panel_text = (
        f"🎉 LIVE: solo server is now live!\n"
        f"🔗 Swagger docs available at: http://localhost:{port}/docs"
    )
    console.print(Panel.fit(panel_text, title="Solo Server", border_style="blue"))
    
    # Print the curl command in blue
    console.print(
        f"[blue]curl -X POST http://127.0.0.1:{port}/predict -H 'Content-Type: application/json' -d '{{\"prompt\": \"hello Solo\"}}'[/blue]\n"
    )

    # Start the server process
    serve_command = [
        "litgpt",
        "serve",
        selected_model,
        "--port", port,
        "--devices", device_arg,
        "--accelerator", accelerator_arg
    ]
    process = subprocess.run(serve_command)
    console.print(f"[blue]Solo server is running on core port 5070 [/blue]")

def setup():
    """Interactive setup for Solo Server environment"""
    # Display hardware info
    display_hardware_info(typer)
    cpu_model, cpu_cores, memory_gb, gpu_vendor, gpu_model, gpu_memory, compute_backend, os_name = detect_hardware()
    
    typer.echo("\nStarting Solo Server Setup...\n")
    gpu = detect_gpu()
    if gpu:
        print("💻 Solo Sighting: GPU detected ->", gpu)
        device_arg = "1"
    else:
        print("😎 Solo Mode: No GPU found; rocking CPU mode!")
        device_arg = "0"
    

    hardware_specs = {
        "cpu_model": cpu_model,
        "cpu_cores": cpu_cores,
        "memory_gb": memory_gb,
        "gpu_vendor": gpu_vendor,
        "gpu_model": gpu_model,
        "gpu_memory": gpu_memory,
        "compute_backend": compute_backend,
        "os_name": os_name
    }
    setup_core_llm(hardware_specs)


if __name__ == "__main__":
    typer.run(setup)