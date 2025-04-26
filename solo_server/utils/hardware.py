import platform
import psutil
import GPUtil
import typer
import subprocess
import os
import json
from typing import Tuple
from rich.console import Console
from rich.panel import Panel
from solo_server.config import CONFIG_PATH

console = Console()

def detect_hardware() -> Tuple[str, int, float, str, str, float, str, str]:
    # OS Info
    os_name = platform.system()
    
    # CPU Info
    cpu_model = "Unknown"
    cpu_cores = psutil.cpu_count(logical=False)
    
    if os_name == "Windows":
        cpu_model = platform.processor()
    elif os_name == "Linux":
        try:
            cpu_model = subprocess.check_output("lscpu | grep 'Model name'", shell=True, text=True).split(":")[1].strip()
        except:
            cpu_model = "Unknown Linux CPU"
    elif os_name == "Darwin":
        try:
            cpu_model = subprocess.check_output("sysctl -n machdep.cpu.brand_string", shell=True, text=True).strip()
        except:
            cpu_model = "Unknown Mac CPU"
    
    # Memory Info
    memory_gb = round(psutil.virtual_memory().total / (1024**3), 2)
    
    # GPU Info
    gpu_vendor = "None"
    gpu_model = "None"
    compute_backend = "CPU"
    gpu_memory = 0

    gpus = GPUtil.getGPUs()
    if gpus:
        gpu = gpus[0]  # Get first GPU
        gpu_model = gpu.name
        gpu_memory = round(gpu.memoryTotal, 2)  # GPU memory in GB
        if "NVIDIA" in gpu_model:
            gpu_vendor = "NVIDIA"
            compute_backend = "CUDA"
        elif "AMD" in gpu_model:
            gpu_vendor = "AMD"
            compute_backend = "HIP"
        elif "Intel" in gpu_model:
            gpu_vendor = "Intel"
            compute_backend = "OpenCL"
        elif "Apple Silicon" in gpu_model:
            gpu_vendor = "Apple Silicon"
            compute_backend = "Metal"
        else:
            gpu_vendor = "Unknown"
            compute_backend = "CPU"

    return cpu_model, cpu_cores, memory_gb, gpu_vendor, gpu_model, gpu_memory, compute_backend, os_name

def recommended_server(memory_gb, gpu_vendor, gpu_memory) -> str:
    """
    Determines the recommended server based on hardware specifications.
    Returns the recommended server type after displaying the recommendation.
    """
    # vLLM recommendation criteria
    if (gpu_vendor in ["NVIDIA","AMD","Intel"] and gpu_memory >= 8) and (memory_gb >= 16):
        typer.echo(f"\n✨ vLLM Recommended for your system")
        return "vLLM"
    
    # Ollama recommendation criteria
    elif (gpu_vendor in ["NVIDIA", "AMD"] and gpu_memory >= 6) or (memory_gb >= 16):
        typer.echo(f"\n✨ Ollama is recommended for your system")
        return "ollama"
    
    # Llama.cpp recommendation criteria
    else:
        typer.echo("\n✨ Llama.cpp is recommended for your system")
        return "llama.cpp"


    
def hardware_info(typer):

    cpu_model, cpu_cores, memory_gb, gpu_vendor, gpu_model, gpu_memory, compute_backend, os_name = detect_hardware()
    panel = Panel.fit(
        f"[bold]Operating System:[/] {os_name}\n"
        f"[bold]CPU:[/] {cpu_model}\n"
        f"[bold]CPU Cores:[/] {cpu_cores}\n"
        f"[bold]Memory:[/] {memory_gb}GB\n"
        f"[bold]GPU:[/] {gpu_vendor}\n"
        f"[bold]GPU Model:[/] {gpu_model}\n"
        f"[bold]GPU Memory:[/] {gpu_memory}GB\n"
        f"[bold]Compute Backend:[/] {compute_backend}",
        title="[bold cyan]System Information[/]"
    )
    console.print(panel)
    return cpu_model, cpu_cores, memory_gb, gpu_vendor, gpu_model, gpu_memory, compute_backend, os_name