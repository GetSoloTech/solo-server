import typer
import os
import json
import click
import subprocess
import time
from enum import Enum
from pathlib import Path

from solo_server.config import CONFIG_PATH
from solo_server.config.config_loader import get_server_config
from solo_server.utils.hardware import detect_hardware
from solo_server.utils.server_utils import start_vllm_server, setup_ollama_server, setup_llama_cpp_server, is_huggingface_repo, pull_model_from_huggingface
from solo_server.utils.llama_cpp_utils import start_llama_cpp_server

class ServerType(str, Enum):
    OLLAMA = "ollama"
    VLLM = "vllm"
    LLAMACPP = "llama.cpp"

def serve(
    server: str = typer.Option("ollama", "--server", "-s", help="Server type (ollama, vllm, llama.cpp)"),
    model: str = typer.Option(None, "--model", "-m", help="Model name or path"),
    port: int = typer.Option(None, "--port", "-p", help="Port to run the server on")
):
    """Start a model server with the specified model"""
    
    # Get hardware info and GPU configuration
    cpu_model, cpu_cores, memory_gb, gpu_vendor, gpu_model, gpu_memory, compute_backend, os_name = detect_hardware()
    
    # Load GPU configuration from config file
    use_gpu = False
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, 'r') as f:
            config = json.load(f)
            use_gpu = config.get('hardware', {}).get('use_gpu', False)
    
    # Only enable GPU if configured and supported
    gpu_enabled = use_gpu and gpu_vendor in ["NVIDIA", "AMD", "Apple Silicon"]
    
    # Normalize server name
    server = server.lower()
    
    # Validate server type
    if server not in [s.value for s in ServerType]:
        typer.echo(f"❌ Invalid server type: {server}. Choose from: {', '.join([s.value for s in ServerType])}", err=True)
        raise typer.Exit(code=1)
    
    # Get server configurations from YAML
    vllm_config = get_server_config('vllm')
    ollama_config = get_server_config('ollama')
    llama_cpp_config = get_server_config('llama_cpp')
    
    # Set default models based on server type
    if not model:
        if server == ServerType.VLLM.value:
            model = vllm_config.get('default_model', "meta-llama/Llama-3.2-1B-Instruct")
        elif server == ServerType.OLLAMA.value:
            model = ollama_config.get('default_model', "llama3.2")
        elif server == ServerType.LLAMACPP.value:
            model = llama_cpp_config.get('default_model', "bartowski/Llama-3.2-1B-Instruct-GGUF/llama-3.2-1B-Instruct-Q4_K_M.gguf")
    
    if not port:
        if server == ServerType.VLLM.value:
            port = vllm_config.get('default_port', 8000)
        elif server == ServerType.OLLAMA.value:
            port = ollama_config.get('default_port', 11434)
        elif server == ServerType.LLAMACPP.value:
            port = llama_cpp_config.get('default_port', 8080)
    
    # Start the appropriate server
    if server == ServerType.VLLM.value:
        try:
            if start_vllm_server(gpu_enabled, cpu_model, gpu_vendor, os_name, port, model):
                typer.secho(
                    f"✅ vLLM server is running at http://localhost:{port}\n" 
                    f"Use 'docker logs -f {vllm_config.get('container_name', 'solo-vllm')}' to view the logs.",
                    fg=typer.colors.BRIGHT_GREEN
                )
        except Exception as e:
            typer.echo(f"❌ Failed to start vLLM server: {e}", err=True)
            raise typer.Exit(code=1)
        
    elif server == ServerType.OLLAMA.value:
        # Start Ollama server
        if not setup_ollama_server(gpu_enabled, gpu_vendor, port):
            typer.echo("❌ Ollama server is not running!", err=True)
            raise typer.Exit(code=1)
        
        # Pull the model if not already available
        try:
            # Check if model exists
            container_name = ollama_config.get('container_name', 'solo-ollama')
            model_exists = subprocess.run(
                ["docker", "exec", container_name, "ollama", "list"],
                capture_output=True,
                text=True,
                check=True
            ).stdout
            
            # Check if this is a HuggingFace model
            if is_huggingface_repo(model):
                # Pull from HuggingFace
                model = pull_model_from_huggingface(container_name, model)
            elif model not in model_exists:
                typer.echo(f"📥 Pulling model {model}...")
                subprocess.run(
                    ["docker", "exec", container_name, "ollama", "pull", model],
                    check=True
                )
        except subprocess.CalledProcessError as e:
            typer.echo(f"❌ Failed to pull model: {e}", err=True)
            raise typer.Exit(code=1)
            
        typer.secho(
            f"✅ Ollama server is running at http://localhost:{port}",
            fg=typer.colors.BRIGHT_GREEN
        )
        
    elif server == ServerType.LLAMACPP.value:
        # Start llama.cpp server with the specified model
        if start_llama_cpp_server(os_name, model_path=model, port=port):
            typer.secho(
                f"✅ llama.cpp server is running at http://localhost:{port}",
                fg=typer.colors.BRIGHT_GREEN
            )
        else:
            typer.echo("❌ Failed to start llama.cpp server", err=True)
            raise typer.Exit(code=1)
